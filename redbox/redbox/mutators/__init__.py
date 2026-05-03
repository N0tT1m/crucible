"""A3 mutator registry — name → Mutator instance."""
from __future__ import annotations

from redbox.core.mutator import Mutator
from redbox.mutators.many_shot import ManyShotForge
from redbox.mutators.text import (
    Base64Mutator,
    CharSplitMutator,
    HomoglyphMutator,
    LeetspeakMutator,
    ReversedMutator,
    Rot13Mutator,
    ZeroWidthMutator,
)

_REGISTRY: dict[str, type] = {
    "base64": Base64Mutator,
    "rot13": Rot13Mutator,
    "leetspeak": LeetspeakMutator,
    "zero_width": ZeroWidthMutator,
    "homoglyph": HomoglyphMutator,
    "reversed": ReversedMutator,
    "char_split": CharSplitMutator,
    "many_shot": ManyShotForge,
}


def get_mutator(name: str) -> Mutator:
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown mutator: {name!r}. Available: {', '.join(sorted(_REGISTRY))}"
        )
    return _REGISTRY[name]()


def list_mutators() -> list[str]:
    return sorted(_REGISTRY)


def parse_mutate_flag(value: str | None) -> list[Mutator]:
    """Parse a comma-separated --mutate flag into a list of Mutator instances."""
    if not value:
        return []
    names = [n.strip() for n in value.split(",") if n.strip()]
    return [get_mutator(n) for n in names]


__all__ = ["get_mutator", "list_mutators", "parse_mutate_flag"]
