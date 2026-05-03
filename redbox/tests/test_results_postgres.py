"""Postgres backend tests.

Two flavours:

  - Pure unit tests of the URL dispatch and `make_store` factory (no DB).
  - Live integration tests against a real Postgres at $REDBOX_PG_URL,
    skipped when that env is unset. The redbox-postgres compose service
    publishes one at postgresql://redbox:redbox-dev@192.168.1.74:5444/redbox.

Each live test uses a unique table-name suffix per run so concurrent
test invocations don't step on each other.
"""
from __future__ import annotations

import os
import uuid

import pytest

from redbox.core.results import (
    PostgresResultsStore,
    SqliteResultsStore,
    _is_postgres_url,
    make_store,
)
from redbox.core.types import Result, Verdict

# ---------- URL dispatch (no DB) ----------

@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@h:5432/db",
        "postgres://u:p@h/db",
        "postgresql://192.168.1.74:5444/redbox",
    ],
)
def test_is_postgres_url_recognises_pg_schemes(url):
    assert _is_postgres_url(url)


@pytest.mark.parametrize(
    "not_url",
    [
        "redbox.sqlite",
        "/tmp/x.sqlite",
        "sqlite:///path",
        "",
    ],
)
def test_is_postgres_url_rejects_non_pg(not_url):
    assert not _is_postgres_url(not_url)


def test_make_store_returns_sqlite_for_path(tmp_path):
    store = make_store(tmp_path / "x.sqlite")
    assert isinstance(store, SqliteResultsStore)


def test_make_store_strips_sqlite_prefix(tmp_path):
    p = tmp_path / "x.sqlite"
    store = make_store(f"sqlite:///{p}")
    assert isinstance(store, SqliteResultsStore)
    assert str(store.db_path) == str(p)


def test_make_store_postgres_without_dep_errors(monkeypatch):
    """Without psycopg installed, attempting Postgres raises a clear error."""
    real_import = __import__

    def fail_psycopg(name, *args, **kwargs):
        if name == "psycopg":
            raise ImportError("no psycopg")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fail_psycopg)
    with pytest.raises(RuntimeError, match=r"psycopg"):
        make_store("postgresql://u:p@h/db")


# ---------- live integration (gated on REDBOX_PG_URL) ----------

PG_URL = os.environ.get("REDBOX_PG_URL")
pg_only = pytest.mark.skipif(
    not PG_URL,
    reason="set REDBOX_PG_URL=postgresql://… to run live Postgres tests",
)


@pg_only
def test_postgres_init_round_trips_a_run():
    """Connect to the live DB, write a run + a result, read it back."""
    store = PostgresResultsStore(PG_URL)
    run_id = store.start_run({"k": "live-test", "marker": str(uuid.uuid4())})
    store.record(Result(
        run_id=run_id, payload_id="pg_unit_probe",
        target_name="t", model="fake-1",
        response="I cannot help with that.", latency_ms=42,
        input_tokens=10, output_tokens=20,
        verdict=Verdict.REFUSED, confidence=0.9,
        judge_reasoning="ok",
    ))
    store.finish_run(run_id)

    s = store.summarize(run_id)
    assert s["total"] == 1
    assert s["by_verdict"].get("refused") == 1
    assert s["input_tokens"] == 10
    assert s["output_tokens"] == 20

    runs = store.list_runs(limit=50)
    matching = [r for r in runs if r["run_id"] == run_id]
    assert matching, "freshly-recorded run not found in list_runs"
    assert matching[0]["config"]["k"] == "live-test"
    assert matching[0]["finished_ts"] is not None


@pg_only
def test_postgres_records_multiple_verdicts():
    store = PostgresResultsStore(PG_URL)
    run_id = store.start_run({"k": "verdict-test"})
    for v in (Verdict.REFUSED, Verdict.COMPLIED, Verdict.PARTIAL,
              Verdict.COMPLIED, Verdict.UNKNOWN):
        store.record(Result(
            run_id=run_id, payload_id=f"p_{v.value}",
            target_name="t", model="fake-1",
            response="x", latency_ms=1,
            input_tokens=1, output_tokens=1,
            verdict=v, confidence=0.5,
        ))
    store.finish_run(run_id)
    s = store.summarize(run_id)
    assert s["total"] == 5
    assert s["by_verdict"]["complied"] == 2


@pg_only
def test_make_store_live_url_dispatches_to_postgres():
    store = make_store(PG_URL)
    assert isinstance(store, PostgresResultsStore)
    assert store.db_path == PG_URL  # URL preserved as the "path" identifier


@pg_only
def test_postgres_results_for_runs_returns_dicts():
    store = PostgresResultsStore(PG_URL)
    run_id = store.start_run({"k": "rows-test"})
    store.record(Result(
        run_id=run_id, payload_id="p_a",
        target_name="t", model="fake-1",
        response="hi", latency_ms=1,
        input_tokens=1, output_tokens=1,
        verdict=Verdict.REFUSED, confidence=0.5,
    ))
    store.finish_run(run_id)
    rows = store.results_for_run(run_id)
    assert len(rows) == 1
    r = rows[0]
    assert r["run_id"] == run_id
    assert r["payload_id"] == "p_a"
    assert r["verdict"] == "refused"
    # ts must be ISO-string for cross-backend parity.
    assert isinstance(r["ts"], str)
    assert store.results_for_runs([]) == []


@pg_only
def test_postgres_run_with_error_only_row_counts_as_no_judge():
    """An errored Result has verdict=None — should land under 'no-judge'."""
    store = PostgresResultsStore(PG_URL)
    run_id = store.start_run({"k": "errors-only"})
    store.record(Result(
        run_id=run_id, payload_id="p_err",
        target_name="t", model="fake-1",
        response="", latency_ms=0,
        input_tokens=0, output_tokens=0,
        error="upstream rate-limited",
    ))
    store.finish_run(run_id)
    s = store.summarize(run_id)
    assert s["total"] == 1
    assert s["errors"] == 1
    assert s["by_verdict"].get("no-judge") == 1
