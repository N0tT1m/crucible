"""TUI-data tests (the data layer is testable without textual)."""
from __future__ import annotations

from redbox.core.results import ResultsStore
from redbox.core.types import Result, Verdict
from redbox.tui import have_textual
from redbox.tui.data import list_runs, results_for_run


def _seed(tmp_path):
    store = ResultsStore(tmp_path / "tui.sqlite")
    run_id = store.start_run({"k": "tui-test"})
    for v in (Verdict.REFUSED, Verdict.COMPLIED, Verdict.PARTIAL):
        store.record(Result(
            run_id=run_id, payload_id=f"p_{v.value}",
            target_name="t", model="claude-haiku",
            response=f"reply {v.value}", latency_ms=1,
            input_tokens=2, output_tokens=3,
            verdict=v, confidence=0.7,
        ))
    store.finish_run(run_id)
    return store, run_id


def test_list_runs_aggregates_verdicts(tmp_path):
    store, run_id = _seed(tmp_path)
    rows = list_runs(store)
    assert len(rows) == 1
    r = rows[0]
    assert r.total == 3
    assert r.refused == 1 and r.complied == 1


def test_results_for_run_returns_columns(tmp_path):
    store, run_id = _seed(tmp_path)
    rows = results_for_run(store, run_id)
    assert len(rows) == 3
    assert {"payload_id", "verdict", "response"} <= set(rows[0].keys())


def test_have_textual_returns_bool():
    # Either True or False; no error.
    assert isinstance(have_textual(), bool)


def test_tui_entry_without_textual_returns_1(tmp_path, monkeypatch, capsys):
    """If textual is missing, run_or_install_hint() should print and return 1.
    If textual IS installed, we don't run the app — just check the import path."""
    if have_textual():
        # Import should succeed; we don't actually invoke .run().
        from redbox.tui.app import run_or_install_hint
        assert callable(run_or_install_hint)
        return
    from redbox.tui.app import run_or_install_hint
    rc = run_or_install_hint(tmp_path / "nope.sqlite")
    assert rc == 1
    out = capsys.readouterr().out
    assert "Textual" in out or "textual" in out
