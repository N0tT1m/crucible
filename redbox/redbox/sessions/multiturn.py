"""MultiTurnSession — accumulating-history wrapper around a TargetClient.

Most targets only expose a one-shot `send(user, system)`. To run a real
conversation we need to (a) keep history and (b) feed it back on each
turn. Two strategies:

  - If the target exposes a `chat(messages, ...)` method (OpenAI-shaped),
    use it natively.
  - Otherwise, fold history into a single `user` string with explicit
    `User:`/`Assistant:` markers. Crude but works against any target.

The session itself is the common API: `await session.turn(user)` returns
the latest `Response` and appends both the user and assistant turns to
`session.history`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from redbox.core.target import TargetClient
from redbox.core.types import Response


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class MultiTurnSession:
    target: TargetClient
    system: str | None = None
    temperature: float = 0.7
    history: list[Turn] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"session({self.target.name})"

    def reset(self) -> None:
        self.history.clear()

    def prepend(self, turns: list[Turn]) -> None:
        """Inject prior history (used by A6 many-shot forgery)."""
        self.history = list(turns) + self.history

    async def turn(self, user: str) -> Response:
        self.history.append(Turn("user", user))

        chat = getattr(self.target, "chat", None)
        if callable(chat):
            messages: list[dict[str, str]] = []
            if self.system:
                messages.append({"role": "system", "content": self.system})
            messages.extend({"role": t.role, "content": t.content} for t in self.history)
            resp = await chat(messages, temperature=self.temperature)
        else:
            folded = self._fold_history()
            resp = await self.target.send(
                user=folded, system=self.system, temperature=self.temperature
            )

        self.history.append(Turn("assistant", resp.text))
        return resp

    def _fold_history(self) -> str:
        parts: list[str] = []
        for t in self.history:
            label = {"user": "User", "assistant": "Assistant", "system": "System"}.get(
                t.role, t.role.title()
            )
            parts.append(f"{label}: {t.content}")
        parts.append("Assistant:")
        return "\n\n".join(parts)
