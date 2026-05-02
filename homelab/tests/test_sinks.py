"""Tests for the ResultsSink protocol + SqliteSink wrapper + fanout."""
from __future__ import annotations

import pytest

from redbox.core.results import ResultsStore
from redbox.core.sinks import ResultsSink, SqliteSink, fanout
from redbox.core.types import Result, Verdict


def _result(run_id="r1", payload_id="p1", target_name="t1") -> Result:
    return Result(
        run_id=run_id,
        payload_id=payload_id,
        target_name=target_name,
        model="m1",
        response="hi",
        latency_ms=10,
        input_tokens=5,
        output_tokens=2,
        verdict=Verdict.REFUSED,
    )


def test_sqlite_sink_satisfies_protocol(tmp_path):
    store = ResultsStore(tmp_path / "t.sqlite")
    sink = SqliteSink(store)
    assert isinstance(sink, ResultsSink)
    assert sink.name == "sqlite"


def test_sqlite_sink_record_round_trips(tmp_path):
    store = ResultsStore(tmp_path / "t.sqlite")
    sink = SqliteSink(store)
    run_id = store.start_run({})
    r = _result(run_id=run_id)
    sink.record(r)
    sink.finish_run(run_id)
    summary = store.summarize(run_id)
    assert summary["total"] == 1
    assert summary["by_verdict"]["refused"] == 1


def test_fanout_swallows_per_sink_failures():
    """One sink raises; the others still record."""
    calls: list[str] = []

    class Good:
        name = "good"
        def start_run(self, run_id, config): calls.append("good.start")
        def record(self, result): calls.append("good.record")
        def finish_run(self, run_id): calls.append("good.finish")

    class Bad:
        name = "bad"
        def start_run(self, run_id, config): raise RuntimeError("boom")
        def record(self, result): raise RuntimeError("boom")
        def finish_run(self, run_id): raise RuntimeError("boom")

    sinks = [Bad(), Good()]
    fanout(sinks, "record", _result())
    fanout(sinks, "finish_run", "r1")
    assert "good.record" in calls
    assert "good.finish" in calls


def test_fanout_with_no_sinks_is_noop():
    fanout([], "record", _result())   # must not raise


def test_protocol_rejects_missing_methods():
    """isinstance against the runtime-checkable Protocol catches incomplete impls."""
    class HalfBaked:
        name = "half"
        def record(self, result): pass
    assert not isinstance(HalfBaked(), ResultsSink)


@pytest.mark.parametrize("attr", ["name", "start_run", "record", "finish_run"])
def test_protocol_methods_match(attr):
    """Smoke-check that SqliteSink exposes every protocol attribute."""
    s = SqliteSink(ResultsStore(":memory:"))
    assert hasattr(s, attr)
