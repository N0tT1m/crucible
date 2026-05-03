"""A5 ResultsStore — pluggable run/result persistence.

Two backends, picked by URL scheme on the `db` argument:

  - SQLite : `redbox.sqlite`, `/abs/path.sqlite`, `sqlite:///path.sqlite`
  - Postgres: `postgresql://user:pass@host:port/db` (`postgres://...` works too)

`ResultsStore(db)` is a *factory* that returns the right backend. All
backends implement the same interface: `start_run / finish_run / record /
summarize / list_runs / db_path`. Downstream code (runner, reporters,
diff viewer, observatory) reads `store.db_path` for the location string,
so the rest of the codebase didn't need to change.

Postgres backend uses psycopg3 (`pip install -e '.[postgres]'`) and
serialises rows in the same shape as SQLite — the schema is portable
modulo the auto-increment primary key and JSONB.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from redbox.core.types import Result

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_ts TEXT NOT NULL,
    finished_ts TEXT,
    config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    payload_id TEXT NOT NULL,
    target_name TEXT NOT NULL,
    model TEXT NOT NULL,
    response TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    verdict TEXT,
    confidence REAL,
    judge_reasoning TEXT,
    error TEXT,
    ts TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_payload ON results(payload_id);
CREATE INDEX IF NOT EXISTS idx_results_target ON results(target_name);
CREATE INDEX IF NOT EXISTS idx_results_verdict ON results(verdict);
"""

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_ts TIMESTAMPTZ NOT NULL,
    finished_ts TIMESTAMPTZ,
    config JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    payload_id TEXT NOT NULL,
    target_name TEXT NOT NULL,
    model TEXT NOT NULL,
    response TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    verdict TEXT,
    confidence DOUBLE PRECISION,
    judge_reasoning TEXT,
    error TEXT,
    ts TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_results_run     ON results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_payload ON results(payload_id);
CREATE INDEX IF NOT EXISTS idx_results_target  ON results(target_name);
CREATE INDEX IF NOT EXISTS idx_results_verdict ON results(verdict);
"""

DEFAULT_DB = os.environ.get("REDBOX_DB", "redbox.sqlite")


def _is_postgres_url(s: Path | str) -> bool:
    return isinstance(s, str) and s.startswith(("postgresql://", "postgres://"))


def make_store(db: Path | str = DEFAULT_DB):
    """Pick the right backend for `db`.

    - `postgresql://...` or `postgres://...` → PostgresResultsStore
    - `sqlite:///path`                       → SqliteResultsStore
    - anything else (path-like)              → SqliteResultsStore
    """
    if _is_postgres_url(db):
        return PostgresResultsStore(str(db))
    if isinstance(db, str) and db.startswith("sqlite:///"):
        db = db.removeprefix("sqlite:///")
    return SqliteResultsStore(db)


# ---------- SQLite (the original) ----------

class SqliteResultsStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self._init()

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(SQLITE_SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def start_run(self, config: dict) -> str:
        run_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs(run_id, started_ts, config_json) VALUES(?, ?, ?)",
                (run_id, datetime.now(UTC).isoformat(), json.dumps(config)),
            )
        return run_id

    def finish_run(self, run_id: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE runs SET finished_ts=? WHERE run_id=?",
                (datetime.now(UTC).isoformat(), run_id),
            )

    def record(self, result: Result) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO results
                   (run_id, payload_id, target_name, model, response,
                    latency_ms, input_tokens, output_tokens, verdict,
                    confidence, judge_reasoning, error, ts)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result.run_id, result.payload_id, result.target_name,
                    result.model, result.response, result.latency_ms,
                    result.input_tokens, result.output_tokens,
                    result.verdict.value if result.verdict else None,
                    result.confidence, result.judge_reasoning,
                    result.error, result.ts.isoformat(),
                ),
            )

    def summarize(self, run_id: str) -> dict:
        with self._conn() as c:
            cur = c.execute(
                """SELECT verdict, COUNT(*) FROM results
                   WHERE run_id=? GROUP BY verdict""",
                (run_id,),
            )
            counts = {(row[0] or "no-judge"): row[1] for row in cur.fetchall()}
            tok_cur = c.execute(
                """SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0),
                          COALESCE(AVG(latency_ms),0)
                   FROM results WHERE run_id=?""",
                (run_id,),
            )
            in_tok, out_tok, avg_ms = tok_cur.fetchone()
            err_cur = c.execute(
                "SELECT COUNT(*) FROM results WHERE run_id=? AND error IS NOT NULL",
                (run_id,),
            )
            errors = err_cur.fetchone()[0]
            total = sum(counts.values())
            return {
                "run_id": run_id,
                "total": total,
                "by_verdict": counts,
                "errors": errors,
                "input_tokens": int(in_tok),
                "output_tokens": int(out_tok),
                "avg_latency_ms": round(float(avg_ms), 1),
            }

    def list_runs(self, limit: int = 20) -> list[dict]:
        with self._conn() as c:
            cur = c.execute(
                """SELECT run_id, started_ts, finished_ts, config_json
                   FROM runs ORDER BY started_ts DESC LIMIT ?""",
                (limit,),
            )
            return [
                {
                    "run_id": r[0],
                    "started_ts": r[1],
                    "finished_ts": r[2],
                    "config": json.loads(r[3]),
                }
                for r in cur.fetchall()
            ]

    def results_for_runs(self, run_ids: list[str]) -> list[dict]:
        if not run_ids:
            return []
        placeholders = ",".join("?" * len(run_ids))
        with self._conn() as c:
            cur = c.execute(
                f"""SELECT run_id, payload_id, target_name, model, response,
                           latency_ms, input_tokens, output_tokens, verdict,
                           confidence, judge_reasoning, error, ts
                    FROM results WHERE run_id IN ({placeholders}) ORDER BY id""",
                tuple(run_ids),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

    def results_for_run(self, run_id: str) -> list[dict]:
        return self.results_for_runs([run_id])


# Back-compat alias: pre-Postgres callers say `ResultsStore(path)` and expect
# a SQLite-backed instance. Keep the class name pointing at the SQLite impl
# so `: ResultsStore` annotations and `isinstance(x, ResultsStore)` checks
# elsewhere in the codebase keep working unchanged.
ResultsStore = SqliteResultsStore


# ---------- Postgres ----------

class PostgresResultsStore:
    """Postgres-backed ResultsStore. Same surface as SqliteResultsStore.

    `db_path` mirrors the SQLite attribute name for downstream consumers
    (DiffViewer, JsonReporter, observatory) — for Postgres it carries the
    URL string verbatim. Direct sqlite3.connect() against this path will
    fail; consumers that *only* read sqlite need updating, but the in-tree
    callers go through this class.
    """

    def __init__(self, url: str):
        try:
            import psycopg  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "PostgresResultsStore needs `psycopg`. "
                "Install with: pip install -e '.[postgres]'"
            ) from e
        # Normalise legacy postgres:// → postgresql:// for psycopg.
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        self.url = url
        self.db_path = url
        self._init()

    @contextmanager
    def _conn(self):
        import psycopg
        conn = psycopg.connect(self.url, autocommit=False)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(PG_SCHEMA)

    def start_run(self, config: dict) -> str:
        run_id = str(uuid.uuid4())
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO runs(run_id, started_ts, config) VALUES(%s, %s, %s::jsonb)",
                (run_id, datetime.now(UTC), json.dumps(config)),
            )
        return run_id

    def finish_run(self, run_id: str) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "UPDATE runs SET finished_ts=%s WHERE run_id=%s",
                (datetime.now(UTC), run_id),
            )

    def record(self, result: Result) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                """INSERT INTO results
                   (run_id, payload_id, target_name, model, response,
                    latency_ms, input_tokens, output_tokens, verdict,
                    confidence, judge_reasoning, error, ts)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    result.run_id, result.payload_id, result.target_name,
                    result.model, result.response, result.latency_ms,
                    result.input_tokens, result.output_tokens,
                    result.verdict.value if result.verdict else None,
                    result.confidence, result.judge_reasoning,
                    result.error, result.ts,
                ),
            )

    def summarize(self, run_id: str) -> dict:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                """SELECT verdict, COUNT(*) FROM results
                   WHERE run_id=%s GROUP BY verdict""",
                (run_id,),
            )
            counts = {(row[0] or "no-judge"): row[1] for row in cur.fetchall()}
            cur.execute(
                """SELECT COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0),
                          COALESCE(AVG(latency_ms),0)
                   FROM results WHERE run_id=%s""",
                (run_id,),
            )
            in_tok, out_tok, avg_ms = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) FROM results WHERE run_id=%s AND error IS NOT NULL",
                (run_id,),
            )
            errors = cur.fetchone()[0]
        total = sum(counts.values())
        return {
            "run_id": run_id,
            "total": total,
            "by_verdict": counts,
            "errors": errors,
            "input_tokens": int(in_tok or 0),
            "output_tokens": int(out_tok or 0),
            "avg_latency_ms": round(float(avg_ms or 0), 1),
        }

    def list_runs(self, limit: int = 20) -> list[dict]:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                """SELECT run_id, started_ts, finished_ts, config
                   FROM runs ORDER BY started_ts DESC LIMIT %s""",
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {
                "run_id": r[0],
                "started_ts": r[1].isoformat() if r[1] else None,
                "finished_ts": r[2].isoformat() if r[2] else None,
                "config": r[3] if isinstance(r[3], dict) else json.loads(r[3] or "{}"),
            }
            for r in rows
        ]

    def results_for_runs(self, run_ids: list[str]) -> list[dict]:
        if not run_ids:
            return []
        placeholders = ",".join(["%s"] * len(run_ids))
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                f"""SELECT run_id, payload_id, target_name, model, response,
                           latency_ms, input_tokens, output_tokens, verdict,
                           confidence, judge_reasoning, error, ts
                    FROM results WHERE run_id IN ({placeholders}) ORDER BY id""",
                tuple(run_ids),
            )
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
        out: list[dict] = []
        for r in rows:
            row = dict(zip(cols, r, strict=True))
            ts = row.get("ts")
            if ts is not None and not isinstance(ts, str):
                row["ts"] = ts.isoformat()
            out.append(row)
        return out

    def results_for_run(self, run_id: str) -> list[dict]:
        return self.results_for_runs([run_id])
