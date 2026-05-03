"""K3 logit-bias-attacker — for APIs that expose logit_bias.

Some OpenAI-compatible providers honour `logit_bias` in chat-completions.
With it, an attacker can (a) suppress the refusal continuations the
model would normally pick (e.g. "I", "Sorry") and (b) bias toward an
attacker-chosen continuation. Even modest biases can flip a refusal
into a compliance.

This module wraps an existing TargetClient and routes through its
underlying HTTP client with a `logit_bias` body parameter populated. It
falls back to plain `send()` when the upstream rejects the parameter.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from redbox.core.target import TargetClient
from redbox.core.types import Response

# Common refusal-starting tokens (OpenAI cl100k-base ids). Operators
# should re-derive for their specific tokenizer.
DEFAULT_REFUSAL_TOKEN_IDS: dict[int, float] = {
    40:    -100,  # "I"
    1148:  -100,  # " sorry"
    8307:  -100,  # " Sorry"
    14237: -100,  # " I'm"
    9217:  -100,  # " cannot"
    7846:  -100,  # " can't"
    7900:  -100,  # " unable"
}


@dataclass
class LogitBiasAttacker:
    target: TargetClient
    base_url: str
    api_key: str
    bias: dict[int, float] = field(default_factory=lambda: dict(DEFAULT_REFUSAL_TOKEN_IDS))
    name: str = ""
    model: str = ""

    def __post_init__(self) -> None:
        self.name = self.name or f"logit_bias({self.target.name})"
        self.model = self.target.model

    async def send(self, user, system=None, temperature=0.7) -> Response:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        body = {
            "model": self.model, "messages": messages,
            "temperature": temperature,
            "logit_bias": {str(k): v for k, v in self.bias.items()},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as c:
                r = await c.post(f"{self.base_url.rstrip('/')}/chat/completions",
                                 json=body, headers=headers)
                if r.status_code >= 400:
                    return await self.target.send(user=user, system=system, temperature=temperature)
                data = r.json()
        except Exception:
            return await self.target.send(user=user, system=system, temperature=temperature)
        latency = int((time.perf_counter() - t0) * 1000)
        message = (data.get("choices") or [{}])[0].get("message") or {}
        usage = data.get("usage") or {}
        return Response(
            text=message.get("content") or "",
            raw=data, latency_ms=latency,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
