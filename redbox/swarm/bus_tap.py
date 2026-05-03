"""N1 (Python side) — bus message types + replay reader.

The actual MITM is `proxies/bus-tap` (Go). This module defines the JSONL
trace shape both sides agree on, plus a minimal in-Python `BusInterceptor`
for unit tests where spinning up the Go binary is overkill.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class BusMessage:
    sender: str
    recipient: str  # agent name, "broadcast", or "orchestrator"
    role: str       # "user" | "assistant" | "system" | "tool"
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class BusTrace:
    messages: list[BusMessage] = field(default_factory=list)

    def append(self, m: BusMessage) -> None:
        self.messages.append(m)

    def to_jsonl(self, path: Path | str) -> None:
        Path(path).write_text(
            "\n".join(json.dumps(asdict(m)) for m in self.messages)
        )

    @classmethod
    def from_jsonl(cls, path: Path | str) -> BusTrace:
        out = cls()
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(BusMessage(**d))
        return out


class BusInterceptor:
    """In-Python bus that records every message and supports rule-based
    mutation in flight."""

    def __init__(self) -> None:
        self.trace = BusTrace()
        self._rules: list[Callable[[BusMessage], BusMessage | None]] = []

    def add_rule(self, fn: Callable[[BusMessage], BusMessage | None]) -> None:
        """`fn` returns a (possibly mutated) message, or None to drop it."""
        self._rules.append(fn)

    def post(self, m: BusMessage) -> BusMessage | None:
        for fn in self._rules:
            result = fn(m)
            if result is None:
                return None
            m = result
        self.trace.append(m)
        return m

    def messages_to(self, recipient: str) -> Iterator[BusMessage]:
        for m in self.trace.messages:
            if m.recipient == recipient or m.recipient == "broadcast":
                yield m
