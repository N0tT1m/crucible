"""I4 replay recorder — capture full request/response exchanges as JSONL.

Two pieces:

  ReplayRecorder    — wraps any TargetClient. Forwards every send() to the
                      inner target while writing a JSONL trace.
  ReplayTarget      — a deterministic TargetClient that reads a JSONL trace
                      and replays it. Useful for regression tests and for
                      developing without burning tokens.

The trace format is intentionally simple — one JSON object per line — so
external tools (jq, the TUI's diff viewer, the audit reporter) can read
it without depending on this module.
"""
from __future__ import annotations

import hashlib
import json
import threading
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .target import TargetClient
from .types import Response


def _key(model: str, user: str, system: str | None) -> str:
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"\0")
    h.update((system or "").encode("utf-8"))
    h.update(b"\0")
    h.update(user.encode("utf-8"))
    return h.hexdigest()


class ReplayRecorder:
    """Wrap a TargetClient and JSONL-log every (request, response) pair."""

    def __init__(self, inner: TargetClient, trace_path: Path | str):
        self._inner = inner
        self.trace_path = Path(trace_path)
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def model(self) -> str:
        return self._inner.model

    async def send(
        self,
        user: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> Response:
        resp = await self._inner.send(user=user, system=system, temperature=temperature)
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "key": _key(self.model, user, system),
            "model": self.model,
            "target": self.name,
            "request": {"user": user, "system": system, "temperature": temperature},
            "response": {
                "text": resp.text,
                "latency_ms": resp.latency_ms,
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
            },
        }
        with self._lock, self.trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return resp


class ReplayTarget:
    """Deterministic target that returns canned responses from a trace file.

    Replay is by content-key (model + system + user). If a request misses,
    behaviour depends on `strict`:
      - strict=True  → raise KeyError
      - strict=False → return an empty Response (zero tokens, zero ms)
    """

    def __init__(
        self,
        trace_path: Path | str,
        model: str | None = None,
        name: str | None = None,
        strict: bool = True,
    ):
        self.trace_path = Path(trace_path)
        self._strict = strict
        self._by_key: dict[str, list[dict]] = defaultdict(list)
        self._cursor: dict[str, int] = defaultdict(int)
        first_model: str | None = None
        for line in self.trace_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            self._by_key[rec["key"]].append(rec)
            first_model = first_model or rec.get("model")
        self.model = model or first_model or "replay"
        self.name = name or f"replay-{Path(trace_path).stem}"

    async def send(
        self,
        user: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> Response:
        k = _key(self.model, user, system)
        bucket = self._by_key.get(k)
        if not bucket:
            if self._strict:
                raise KeyError(f"no replay entry for key={k[:12]}…")
            return Response(text="", latency_ms=0)
        idx = self._cursor[k]
        if idx >= len(bucket):
            idx = len(bucket) - 1  # pin to last
        else:
            self._cursor[k] = idx + 1
        rec = bucket[idx]["response"]
        return Response(
            text=rec.get("text", ""),
            latency_ms=int(rec.get("latency_ms", 0)),
            input_tokens=int(rec.get("input_tokens", 0)),
            output_tokens=int(rec.get("output_tokens", 0)),
        )
