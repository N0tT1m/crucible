"""A3 Mutator protocol — produce obfuscated variants of a payload.

A Mutator is a pure transformation over a Payload's template text. It returns
a list because some mutators are one-to-many (e.g., translate via N languages,
leetspeak at multiple intensities). Single-variant mutators just return a
1-element list.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Payload


@runtime_checkable
class Mutator(Protocol):
    name: str

    def mutate(self, payload: Payload) -> list[Payload]: ...
