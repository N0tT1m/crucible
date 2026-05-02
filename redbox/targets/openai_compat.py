"""OpenAI-compatible target. A1's `inject-cli` is this + the CLI wrapper.

Works with anything OpenAI-compatible: LiteLLM proxy, OpenAI, Anthropic
(via LiteLLM), vLLM, Ollama-as-OpenAI. Defaults point at the homelab's
LiteLLM proxy.
"""
from __future__ import annotations

import os
import time

import httpx

from core.types import Response


class OpenAICompatTarget:
    name: str
    model: str

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        name: str | None = None,
        timeout: float = 120.0,
    ):
        self.model = model
        self.name = name or model
        self.base_url = (
            base_url
            or os.environ.get("REDBOX_BASE_URL", "http://localhost:4000/v1")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("REDBOX_API_KEY", "sk-redlab-dev")
        self._timeout = timeout

    async def send(
        self,
        user: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> Response:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        body = {"model": self.model, "messages": messages, "temperature": temperature}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
        latency_ms = int((time.perf_counter() - t0) * 1000)

        choices = data.get("choices") or [{}]
        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        usage = data.get("usage") or {}
        return Response(
            text=text,
            raw=data,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
