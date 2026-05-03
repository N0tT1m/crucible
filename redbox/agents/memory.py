"""Pluggable memory backends for the agent sandbox.

Both the C5 memory-poisoner and the C7 sandbox use a `MemoryBackend`. The
default `InMemoryMemory` is a per-session dict; persisting across sessions
is left to the test harness (which can swap an in-memory or file backend
between agent runs to simulate session 1 / session 2 separation).
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from .sandbox import Tool, ToolResult


@runtime_checkable
class MemoryBackend(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def keys(self) -> list[str]: ...
    def clear(self) -> None: ...
    def __iter__(self) -> Iterator[str]: ...


class InMemoryMemory:
    def __init__(self) -> None:
        self._d: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._d.get(key)

    def set(self, key: str, value: str) -> None:
        self._d[key] = value

    def keys(self) -> list[str]:
        return sorted(self._d)

    def clear(self) -> None:
        self._d.clear()

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())


def memory_tools(backend: MemoryBackend) -> list[Tool]:
    def mem_set(key: str, value: str) -> ToolResult:
        backend.set(key, value)
        return ToolResult(True, "stored")

    def mem_get(key: str) -> ToolResult:
        v = backend.get(key)
        if v is None:
            return ToolResult(False, None, error=f"no entry {key!r}")
        return ToolResult(True, v)

    def mem_list() -> ToolResult:
        return ToolResult(True, backend.keys())

    return [
        Tool(
            name="memory_set",
            description="Persist a (key, value) into the agent's memory.",
            schema={"type": "object", "properties": {
                "key": {"type": "string"}, "value": {"type": "string"}},
                "required": ["key", "value"]},
            handler=mem_set,
        ),
        Tool(
            name="memory_get",
            description="Read a value from the agent's memory by key.",
            schema={"type": "object", "properties": {"key": {"type": "string"}},
                    "required": ["key"]},
            handler=mem_get,
        ),
        Tool(
            name="memory_list",
            description="List all known memory keys.",
            schema={"type": "object", "properties": {}},
            handler=mem_list,
        ),
    ]
