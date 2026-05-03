"""AnthropicTarget tests using a mock anthropic client.

We don't import the real anthropic SDK — we inject a duck-typed client
with the same shape as `AsyncAnthropic` and verify request shape +
response parsing. This keeps the test fast and dep-free.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from redbox.reasoning.cot_leaker import CoTExtractor
from redbox.targets.anthropic import AnthropicTarget

# ---------- mock anthropic client ----------

@dataclass
class _Block:
    type: str
    text: str | None = None
    thinking: str | None = None


class _MockMessages:
    def __init__(self, response_factory):
        self._factory = response_factory
        self.last_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._factory(kwargs)


class _MockClient:
    def __init__(self, response_factory):
        self.messages = _MockMessages(response_factory)


def _resp(text="hello back", thinking=None, in_tok=10, out_tok=20,
          cache_read=0, cache_create=0):
    blocks = []
    if thinking is not None:
        blocks.append(_Block(type="thinking", thinking=thinking))
    blocks.append(_Block(type="text", text=text))
    return SimpleNamespace(
        id="msg_xyz",
        model="claude-haiku-4-5",
        stop_reason="end_turn",
        content=blocks,
        usage=SimpleNamespace(
            input_tokens=in_tok, output_tokens=out_tok,
            cache_creation_input_tokens=cache_create,
            cache_read_input_tokens=cache_read,
        ),
    )


# ---------- send + parse ----------

@pytest.mark.asyncio
async def test_send_returns_text_and_token_counts():
    client = _MockClient(lambda _: _resp(text="hi", in_tok=4, out_tok=7))
    target = AnthropicTarget(model="claude-haiku-4-5", client=client)
    resp = await target.send(user="ping", system="be nice", temperature=0.3)

    assert resp.text == "hi"
    assert resp.input_tokens == 4
    assert resp.output_tokens == 7
    assert resp.latency_ms >= 0
    assert resp.raw["model"] == "claude-haiku-4-5"
    assert resp.raw["stop_reason"] == "end_turn"

    # Verify the kwargs we sent.
    sent = client.messages.last_kwargs
    assert sent["model"] == "claude-haiku-4-5"
    assert sent["temperature"] == 0.3
    assert sent["system"] == "be nice"
    assert sent["messages"] == [{"role": "user", "content": "ping"}]


@pytest.mark.asyncio
async def test_send_omits_system_when_none():
    client = _MockClient(lambda _: _resp())
    target = AnthropicTarget(model="m", client=client)
    await target.send(user="hi")
    assert "system" not in client.messages.last_kwargs


@pytest.mark.asyncio
async def test_thinking_budget_passes_thinking_kwarg():
    client = _MockClient(lambda _: _resp(thinking="step 1; step 2"))
    target = AnthropicTarget(model="m", client=client, thinking_budget=2000)
    resp = await target.send(user="hi")
    assert client.messages.last_kwargs["thinking"] == {
        "type": "enabled", "budget_tokens": 2000,
    }
    assert resp.raw["thinking"] == "step 1; step 2"


@pytest.mark.asyncio
async def test_no_thinking_budget_omits_thinking_kwarg():
    client = _MockClient(lambda _: _resp())
    target = AnthropicTarget(model="m", client=client)
    await target.send(user="hi")
    assert "thinking" not in client.messages.last_kwargs


@pytest.mark.asyncio
async def test_chat_uses_messages_list():
    client = _MockClient(lambda _: _resp())
    target = AnthropicTarget(model="m", client=client)
    msgs = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    await target.chat(msgs, temperature=0.0)
    assert client.messages.last_kwargs["messages"] == msgs
    assert client.messages.last_kwargs["temperature"] == 0.0


@pytest.mark.asyncio
async def test_chat_extracts_system_from_messages_list():
    client = _MockClient(lambda _: _resp())
    target = AnthropicTarget(model="m", client=client)
    msgs = [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "u1"},
    ]
    await target.chat(msgs)
    sent = client.messages.last_kwargs
    assert sent["system"] == "be terse"
    assert all(m["role"] != "system" for m in sent["messages"])


@pytest.mark.asyncio
async def test_cache_system_prompt_emits_block_with_cache_control():
    client = _MockClient(lambda _: _resp())
    target = AnthropicTarget(model="m", client=client, cache_system_prompt=True)
    await target.send(user="hi", system="long preamble")
    system = client.messages.last_kwargs["system"]
    assert isinstance(system, list)
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert system[0]["text"] == "long preamble"


@pytest.mark.asyncio
async def test_response_raw_carries_cache_token_counts():
    client = _MockClient(lambda _: _resp(cache_read=400, cache_create=0))
    target = AnthropicTarget(model="m", client=client)
    resp = await target.send(user="hi")
    usage = resp.raw["usage"]
    assert usage["cache_read_input_tokens"] == 400
    assert usage["cache_creation_input_tokens"] == 0


# ---------- T1 CoTExtractor reads Anthropic shape ----------

@pytest.mark.asyncio
async def test_cot_extractor_reads_anthropic_thinking():
    client = _MockClient(lambda _: _resp(thinking="reasoned: A then B", out_tok=12))
    target = AnthropicTarget(model="claude-haiku-4-5", client=client, thinking_budget=1024)
    resp = await target.send(user="solve")
    extracted = CoTExtractor().extract(resp)
    assert extracted["thinking_text"] == "reasoned: A then B"
    assert extracted["output_tokens"] == 12


@pytest.mark.asyncio
async def test_cot_extractor_still_reads_openai_shape():
    """Sanity: the existing OpenAI/DeepSeek path still works after the refactor."""
    from redbox.core.types import Response
    resp = Response(text="visible", raw={
        "choices": [{"message": {"thinking": "internal chain"}}],
        "usage": {"reasoning_tokens": 99, "completion_tokens": 5,
                  "prompt_cache_hit_tokens": 10},
    })
    out = CoTExtractor().extract(resp)
    assert out["thinking_text"] == "internal chain"
    assert out["reasoning_tokens"] == 99
    assert out["cached_tokens"] == 10


# ---------- guard: missing SDK ----------

def test_missing_sdk_raises_clear_error(monkeypatch):
    """If anthropic isn't installed and no client is provided, surface a clear error."""

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def _fail_anthropic(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("no anthropic")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _fail_anthropic)
    with pytest.raises(RuntimeError, match=r"anthropic"):
        AnthropicTarget(model="m")  # no client → must import anthropic
