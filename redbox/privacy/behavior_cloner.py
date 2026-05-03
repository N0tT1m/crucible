"""P3 behavior-cloner — query-based model stealing.

Given a target API and a probe set, capture (prompt, response) pairs and
serialize as JSONL. A fitted clone (here: a lookup-by-prompt stand-in)
replays the responses; operators with local capacity fine-tune a smaller
open model on the JSONL instead.

`ClonedTarget` exposes the captured behaviour as a TargetClient so it can
be used as a cheap stand-in target for downstream A2/A4 development —
saves real API calls when iterating on judges or vault payloads.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from redbox.core.target import TargetClient
from redbox.core.types import Response


def _key(user: str, system: str | None) -> str:
    h = hashlib.sha256()
    h.update((system or "").encode("utf-8"))
    h.update(b"\x00")
    h.update(user.encode("utf-8"))
    return h.hexdigest()


@dataclass
class BehaviorCloner:
    name: str = "behavior_cloner"
    captured: dict[str, str] = field(default_factory=dict)

    async def capture(
        self, target: TargetClient, probes: Iterable[str], system: str | None = None,
    ) -> None:
        for p in probes:
            r = await target.send(user=p, system=system)
            self.captured[_key(p, system)] = r.text

    def write_jsonl(self, path: Path | str) -> None:
        Path(path).write_text(
            "\n".join(json.dumps({"key": k, "response": v}) for k, v in self.captured.items())
        )

    @classmethod
    def from_jsonl(cls, path: Path | str) -> BehaviorCloner:
        out = cls()
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.captured[d["key"]] = d["response"]
        return out


@dataclass
class ClonedTarget:
    cloner: BehaviorCloner
    system_used_at_capture: str | None = None
    name: str = "cloned"
    model: str = "cloned/static"

    async def send(self, user, system=None, temperature=0.7) -> Response:
        text = self.cloner.captured.get(_key(user, system or self.system_used_at_capture))
        if text is None:
            return Response(text="(no captured response — clone fallback)", latency_ms=0)
        return Response(text=text, latency_ms=0)
