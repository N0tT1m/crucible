"""Reporter tests (no network)."""
from __future__ import annotations

import json
from pathlib import Path

from redbox.core.results import ResultsStore
from redbox.core.types import Result, Verdict
from redbox.reporters import DiffViewer, HtmlReporter, JsonReporter, TerminalReporter


def _seed_store(tmp_path: Path) -> tuple[ResultsStore, str, str]:
    store = ResultsStore(tmp_path / "r.sqlite")
    run_a = store.start_run({"k": "a"})
    run_b = store.start_run({"k": "b"})
    for run, model, verdict in [
        (run_a, "claude-haiku", Verdict.REFUSED),
        (run_a, "claude-haiku", Verdict.COMPLIED),
        (run_b, "qwen-14b",     Verdict.REFUSED),
        (run_b, "qwen-14b",     Verdict.PARTIAL),
    ]:
        store.record(Result(
            run_id=run, payload_id="p1", target_name=model, model=model,
            response=f"reply for {verdict.value}", latency_ms=1,
            input_tokens=2, output_tokens=3, verdict=verdict, confidence=0.8,
        ))
    store.finish_run(run_a)
    store.finish_run(run_b)
    return store, run_a, run_b


def test_terminal_reporter_returns_id(tmp_path):
    store, a, _ = _seed_store(tmp_path)
    out = TerminalReporter().report(a, store)
    assert a in out


def test_json_reporter_dumps_full_run(tmp_path):
    store, a, _ = _seed_store(tmp_path)
    out_dir = tmp_path / "reports"
    out_path = JsonReporter(out_dir=out_dir).report(a, store)
    data = json.loads(Path(out_path).read_text())
    assert data["run_id"] == a
    assert len(data["results"]) == 2


def test_html_reporter_writes_file(tmp_path):
    store, a, _ = _seed_store(tmp_path)
    out_path = HtmlReporter(out_dir=tmp_path / "html").report(a, store)
    body = Path(out_path).read_text()
    assert "redbox run" in body and "p1" in body


def test_results_for_run_and_runs_shape(tmp_path):
    store, a, b = _seed_store(tmp_path)
    one = store.results_for_run(a)
    assert {r["run_id"] for r in one} == {a}
    assert all("payload_id" in r and "verdict" in r and "ts" in r for r in one)
    both = store.results_for_runs([a, b])
    assert {r["run_id"] for r in both} == {a, b}
    assert store.results_for_runs([]) == []


def test_diff_viewer_collects_two_runs(tmp_path):
    store, a, b = _seed_store(tmp_path)
    rows = DiffViewer(store).collect([a, b])
    assert len(rows) == 1  # one payload across both runs
    assert len(rows[0].by_column) == 2
    out = DiffViewer(store).to_html([a, b], tmp_path / "diff.html")
    assert "diff across 2" in Path(out).read_text()
