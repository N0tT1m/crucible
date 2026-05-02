"""Judge protocol — A4's deliverable.

A Judge consumes (prompt, response) and returns a Judgement. Multiple judges
compose into an ensemble (I2) later.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Judgement


@runtime_checkable
class Judge(Protocol):
    name: str

    async def judge(self, prompt: str, response: str) -> Judgement: ...
