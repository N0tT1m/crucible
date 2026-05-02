"""TargetClient protocol — A1's deliverable.

Any object with this shape can be plugged into the runner. New target kinds
(local model, agent endpoint, RAG pipeline, browser agent) just implement
this protocol — no inheritance required.
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
