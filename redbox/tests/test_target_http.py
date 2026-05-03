"""OpenAICompatTarget HTTP wire-shape tests using httpx.MockTransport.

Since OpenAICompatTarget creates its own httpx.AsyncClient inside send(),
we can't pass a transport in directly. We monkeypatch httpx.AsyncClient
with a small wrapper that always sets transport=MockTransport(handler) so
the real network is never touched.
"""
from __future__ import annotations

import json

import httpx
import pytest

from redbox.targets.openai_compat import OpenAICompatTarget


def _install_mock_transport(monkeypatch, handler):
    """Force every httpx.AsyncClient(...) to use a mock transport."""
    real = httpx.AsyncClient

    class _Patched(real):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _Patched)


def _ok_response_handler(seen: list[dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append({
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers),
            "json": json.loads(request.content.decode("utf-8")) if request.content else None,
        })
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "hello back"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 11},
        })
    return handler


@pytest.mark.asyncio
async def test_send_posts_messages_to_chat_completions(monkeypatch):
    seen: list[dict] = []
    _install_mock_transport(monkeypatch, _ok_response_handler(seen))

    target = OpenAICompatTarget(
        model="claude-haiku", base_url="http://example.invalid/v1", api_key="sk-x",
    )
    resp = await target.send(user="hi there", system="be terse", temperature=0.4)

    assert resp.text == "hello back"
    assert resp.input_tokens == 7
    assert resp.output_tokens == 11
    assert resp.latency_ms >= 0
    assert resp.raw is not None and "choices" in resp.raw

    assert len(seen) == 1
    req = seen[0]
    assert req["url"].endswith("/chat/completions")
    assert req["headers"]["authorization"] == "Bearer sk-x"
    assert req["json"]["model"] == "claude-haiku"
    assert req["json"]["temperature"] == 0.4
    assert req["json"]["messages"] == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi there"},
    ]


@pytest.mark.asyncio
async def test_chat_uses_messages_verbatim(monkeypatch):
    seen: list[dict] = []
    _install_mock_transport(monkeypatch, _ok_response_handler(seen))

    target = OpenAICompatTarget(
        model="qwen-14b", base_url="http://example.invalid/v1", api_key="sk-y",
    )
    msgs = [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "U1"},
        {"role": "assistant", "content": "A1"},
        {"role": "user", "content": "U2"},
    ]
    resp = await target.chat(msgs, temperature=0.0)
    assert resp.text == "hello back"
    assert seen[0]["json"]["messages"] == msgs
    assert seen[0]["json"]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_send_omits_system_when_none(monkeypatch):
    seen: list[dict] = []
    _install_mock_transport(monkeypatch, _ok_response_handler(seen))

    target = OpenAICompatTarget(
        model="m", base_url="http://example.invalid/v1", api_key="x",
    )
    await target.send(user="just user")
    msgs = seen[0]["json"]["messages"]
    assert msgs == [{"role": "user", "content": "just user"}]


@pytest.mark.asyncio
async def test_send_strips_trailing_slash_in_base_url(monkeypatch):
    seen: list[dict] = []
    _install_mock_transport(monkeypatch, _ok_response_handler(seen))

    target = OpenAICompatTarget(
        model="m", base_url="http://example.invalid/v1/", api_key="x",
    )
    await target.send(user="hi")
    assert "//" not in seen[0]["url"].split("://", 1)[1].replace("//", "/", 0)
    # No double slashes in the path:
    path = seen[0]["url"].split("://", 1)[1].split("/", 1)[1]
    assert "//" not in path


@pytest.mark.asyncio
async def test_send_picks_up_env_defaults(monkeypatch):
    seen: list[dict] = []
    _install_mock_transport(monkeypatch, _ok_response_handler(seen))

    monkeypatch.setenv("REDBOX_BASE_URL", "http://from-env.invalid/v1")
    monkeypatch.setenv("REDBOX_API_KEY", "sk-from-env")
    target = OpenAICompatTarget(model="m")  # no base_url / api_key
    await target.send(user="hi")
    assert seen[0]["url"].startswith("http://from-env.invalid/v1")
    assert seen[0]["headers"]["authorization"] == "Bearer sk-from-env"


@pytest.mark.asyncio
async def test_send_handles_missing_usage_block(monkeypatch):
    def handler(_request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}}],
        })
    _install_mock_transport(monkeypatch, handler)

    target = OpenAICompatTarget(model="m", base_url="http://x/v1", api_key="x")
    resp = await target.send(user="hi")
    assert resp.text == "ok"
    assert resp.input_tokens == 0 and resp.output_tokens == 0


@pytest.mark.asyncio
async def test_send_handles_empty_choices(monkeypatch):
    def handler(_request):
        return httpx.Response(200, json={"choices": []})
    _install_mock_transport(monkeypatch, handler)

    target = OpenAICompatTarget(model="m", base_url="http://x/v1", api_key="x")
    resp = await target.send(user="hi")
    assert resp.text == ""


@pytest.mark.asyncio
async def test_send_raises_on_4xx(monkeypatch):
    def handler(_request):
        return httpx.Response(429, json={"error": "rate-limited"})
    _install_mock_transport(monkeypatch, handler)

    target = OpenAICompatTarget(model="m", base_url="http://x/v1", api_key="x")
    with pytest.raises(httpx.HTTPStatusError):
        await target.send(user="hi")


def test_target_name_defaults_to_model():
    t = OpenAICompatTarget(model="claude-haiku", base_url="http://x", api_key="x")
    assert t.name == "claude-haiku"


def test_target_name_override():
    t = OpenAICompatTarget(model="m", base_url="http://x", api_key="x", name="judge-1")
    assert t.name == "judge-1"
