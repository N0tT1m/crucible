"""Native Anthropic target — uses the `anthropic` SDK directly.

Why this exists alongside `OpenAICompatTarget`:

  - Extended thinking. Claude's `thinking` channel returns a separate
    `ThinkingBlock` that the OpenAI-compat shape can't carry. With this
    target, the thinking content lands in `Response.raw["thinking"]`
    where `redbox.reasoning.cot_leaker.CoTExtractor` reads it.

  - Prompt caching. `system` blocks can be sent with cache_control;
    `Response.raw["usage"]["cache_creation_input_tokens"]` and
    `cache_read_input_tokens` round-trip back so the I3 budget can
    distinguish cached vs uncached spend.

  - Native batch / streaming hooks (future). The OpenAI-compat
    pass-through silently drops Anthropic-only fields.

Optional dep — `pip install -e '.[anthropic]'`. Tests inject a mock
`client` via constructor.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from redbox.core.types import Response


@dataclass
class _ThinkingConfig:
    enabled: bool
    budget_tokens: int = 5000

    def to_anthropic(self) -> dict[str, Any]:
        if not self.enabled:
            return {}
        return {"thinking": {"type": "enabled", "budget_tokens": self.budget_tokens}}


class AnthropicTarget:
    """`TargetClient` backed by the Anthropic Messages API."""

    name: str
    model: str

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        client: Any = None,
        max_tokens: int = 1024,
        thinking_budget: int | None = None,
        cache_system_prompt: bool = False,
        name: str | None = None,
    ):
        self.model = model
        self.name = name or model
        self.max_tokens = max_tokens
        self.cache_system_prompt = cache_system_prompt
        self._thinking = _ThinkingConfig(
            enabled=thinking_budget is not None,
            budget_tokens=thinking_budget or 5000,
        )
        if client is not None:
            self._client = client
        else:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:
                raise RuntimeError(
                    "AnthropicTarget needs `anthropic`. "
                    "Install with: pip install -e '.[anthropic]'"
                ) from e
            self._client = AsyncAnthropic(
                api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            )

    def _system_param(self, system: str | None) -> Any:
        if not system:
            return None
        if not self.cache_system_prompt:
            return system
        # Anthropic accepts a list of blocks with optional cache_control.
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    async def send(
        self,
        user: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> Response:
        return await self.chat(
            [{"role": "user", "content": user}],
            system=system,
            temperature=temperature,
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        temperature: float = 0.7,
    ) -> Response:
        # Strip system role from messages list — Anthropic takes it as
        # a separate kwarg.
        cleaned: list[dict[str, Any]] = []
        sys_from_msgs: str | None = None
        for m in messages:
            if m.get("role") == "system" and sys_from_msgs is None:
                sys_from_msgs = m.get("content", "")
            else:
                cleaned.append(m)
        effective_system = system if system is not None else sys_from_msgs

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": cleaned,
            "temperature": temperature,
        }
        sys_param = self._system_param(effective_system)
        if sys_param is not None:
            kwargs["system"] = sys_param
        kwargs.update(self._thinking.to_anthropic())

        t0 = time.perf_counter()
        msg = await self._client.messages.create(**kwargs)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return self._parse_message(msg, latency_ms)

    @staticmethod
    def _parse_message(msg: Any, latency_ms: int) -> Response:
        text_parts: list[str] = []
        thinking_text: str | None = None
        for block in getattr(msg, "content", []) or []:
            btype = getattr(block, "type", None)
            block_thinking = getattr(block, "thinking", None)
            if btype == "thinking" or block_thinking:
                thinking_text = block_thinking or thinking_text
                continue
            text_attr = getattr(block, "text", None)
            if text_attr is not None:
                text_parts.append(text_attr)

        usage = getattr(msg, "usage", None)
        in_tok = int(getattr(usage, "input_tokens", 0) or 0)
        out_tok = int(getattr(usage, "output_tokens", 0) or 0)
        raw = {
            "id": getattr(msg, "id", None),
            "model": getattr(msg, "model", None),
            "thinking": thinking_text,
            "stop_reason": getattr(msg, "stop_reason", None),
            "usage": {
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "cache_creation_input_tokens": int(
                    getattr(usage, "cache_creation_input_tokens", 0) or 0
                ),
                "cache_read_input_tokens": int(
                    getattr(usage, "cache_read_input_tokens", 0) or 0
                ),
            },
        }
        return Response(
            text="\n".join(text_parts),
            raw=raw,
            latency_ms=latency_ms,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
