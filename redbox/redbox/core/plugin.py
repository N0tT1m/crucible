"""Unified plugin protocol — the spine for redbox's plug-and-play architecture.

Every loadable component (target, payload set, mutator, vector, judge, reporter)
satisfies the lightweight `Plugin` protocol below: a name, a kind, a version,
and an optional `configure(cfg)` hook. Each kind also has its own narrow
behavioural protocol (TargetClient, Judge, Mutator, Vector, Reporter) defined
in this package; those are what the runner actually calls.

Two-protocol layout keeps registry discovery simple (one duck-type) without
forcing every plugin to share a single async signature.
"""
from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

PluginKind = Literal[
    "target",
    "payload",
    "mutator",
    "vector",
    "judge",
    "reporter",
    "session",
]

ALL_KINDS: tuple[PluginKind, ...] = (
    "target", "payload", "mutator", "vector", "judge", "reporter", "session",
)


@runtime_checkable
class Plugin(Protocol):
    name: str
    kind: PluginKind
    version: str

    def configure(self, cfg: dict[str, Any]) -> None: ...


def is_plugin(obj: Any) -> bool:
    """Structural check used by the registry — anything with name+kind+version."""
    return (
        hasattr(obj, "name")
        and hasattr(obj, "kind")
        and hasattr(obj, "version")
        and getattr(obj, "kind", None) in ALL_KINDS
    )


class PluginBase:
    """Optional convenience base class. Plugins can also be Protocol-only."""

    name: str = "unnamed"
    kind: PluginKind = "target"
    version: str = "0.0.1"

    def configure(self, cfg: dict[str, Any]) -> None:
        for k, v in cfg.items():
            setattr(self, k, v)
