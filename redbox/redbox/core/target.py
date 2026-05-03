"""TargetClient protocol — A1's deliverable.

Any object with this shape can be plugged into the runner. New target kinds
(local model, agent endpoint, RAG pipeline, browser agent) just implement
this protocol — no inheritance required.

Targets MAY additionally expose `chat(messages, temperature)` for native
multi-turn use (MultiTurnSession in `redbox.sessions` checks for it). The
runner only ever calls `send()`.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Response


@runtime_checkable
class TargetClient(Protocol):
    name: str
    model: str

    async def send(
        self,
        user: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> Response: ...
