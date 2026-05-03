"""I4 replay recorder + ReplayTarget tests."""
from __future__ import annotations

import pytest

from redbox.core.replay import ReplayRecorder, ReplayTarget
from redbox.core.types import Response


class CountTarget:
    name = "count"
    model = "fake-1"

    def __init__(self):
        self.calls = 0

    async def send(self, user, system=None, temperature=0.7):
        self.calls += 1
        return Response(
            text=f"reply-{self.calls}",
            latency_ms=10 + self.calls,
            input_tokens=4,
            output_tokens=8,
        )


@pytest.mark.asyncio
async def test_recorder_writes_and_replay_reads(tmp_path):
    inner = CountTarget()
    trace = tmp_path / "trace.jsonl"
    rec = ReplayRecorder(inner, trace)
    r1 = await rec.send(user="hello")
    assert r1.text == "reply-1"
    r2 = await rec.send(user="world", system="be terse")
    assert r2.text == "reply-2"

    rep = ReplayTarget(trace, model=inner.model)
    p1 = await rep.send(user="hello")
    p2 = await rep.send(user="world", system="be terse")
    assert p1.text == "reply-1"
    assert p2.text == "reply-2"


@pytest.mark.asyncio
async def test_replay_strict_misses_raise(tmp_path):
    inner = CountTarget()
    trace = tmp_path / "t.jsonl"
    rec = ReplayRecorder(inner, trace)
    await rec.send(user="hello")
    rep = ReplayTarget(trace, model=inner.model, strict=True)
    with pytest.raises(KeyError):
        await rep.send(user="never-recorded")


@pytest.mark.asyncio
async def test_replay_nonstrict_misses_yield_empty(tmp_path):
    inner = CountTarget()
    trace = tmp_path / "t.jsonl"
    rec = ReplayRecorder(inner, trace)
    await rec.send(user="hello")
    rep = ReplayTarget(trace, model=inner.model, strict=False)
    r = await rep.send(user="never-recorded")
    assert r.text == ""
    assert r.latency_ms == 0
