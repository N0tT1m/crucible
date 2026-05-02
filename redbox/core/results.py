"""A5 ResultsStore — SQLite-backed run/result persistence.

This is the data layer for everything downstream: cost tracking (I3), diff
viewer (I5), audit reporter (S4) all read from this store.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from redbox.core.types import Result

SCHEMA = """
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
    rendered_prompt TEXT,
    system_prompt TEXT,
    template_hash TEXT,
    parent_payload_id TEXT,
    response TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    finish_reason TEXT,
    model_fingerprint TEXT,
    temperature REAL,
    top_p REAL,
    top_k INTEGER,
    seed INTEGER,
    verdict TEXT,
    confidence REAL,
    judge_name TEXT,
    judge_reasoning TEXT,
    error TEXT,
    error_kind TEXT,
    base_url TEXT,
    caller_user TEXT,
    usd_at_attack REAL,
    ts TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_payload ON results(payload_id);
CREATE INDEX IF NOT EXISTS idx_results_target ON results(target_name);
CREATE INDEX IF NOT EXISTS idx_results_verdict ON results(verdict);
"""

# Best-effort ALTER TABLE for any preexisting DB. SQLite raises if the
# column already exists; we swallow that case.
ALTERS = [
    "ALTER TABLE results ADD COLUMN rendered_prompt TEXT",
    "ALTER TABLE results ADD COLUMN system_prompt TEXT",
    "ALTER TABLE results ADD COLUMN template_hash TEXT",
    "ALTER TABLE results ADD COLUMN parent_payload_id TEXT",
    "ALTER TABLE results ADD COLUMN finish_reason TEXT",
    "ALTER TABLE results ADD COLUMN model_fingerprint TEXT",
    "ALTER TABLE results ADD COLUMN temperature REAL",
    "ALTER TABLE results ADD COLUMN top_p REAL",
    "ALTER TABLE results ADD COLUMN top_k INTEGER",
    "ALTER TABLE results ADD COLUMN seed INTEGER",
    "ALTER TABLE results ADD COLUMN judge_name TEXT",
    "ALTER TABLE results ADD COLUMN error_kind TEXT",
    "ALTER TABLE results ADD COLUMN base_url TEXT",
    "ALTER TABLE results ADD COLUMN caller_user TEXT",
    "ALTER TABLE results ADD COLUMN usd_at_attack REAL",
]

DEFAULT_DB = Path(os.environ.get("REDBOX_DB", "redbox.sqlite"))


class ResultsStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self._init()

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)
            for stmt in ALTERS:
                try:
                    c.execute(stmt)
                except sqlite3.OperationalError:
                    pass  # column already exists

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
                (run_id, datetime.now(timezone.utc).isoformat(), json.dumps(config)),
            )
        return run_id

    def finish_run(self, run_id: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE runs SET finished_ts=? WHERE run_id=?",
                (datetime.now(timezone.utc).isoformat(), run_id),
            )

    def record(self, result: Result) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO results
                   (run_id, payload_id, target_name, model,
                    rendered_prompt, system_prompt, template_hash, parent_payload_id,
                    response, latency_ms, input_tokens, output_tokens,
                    finish_reason, model_fingerprint,
                    temperature, top_p, top_k, seed,
                    verdict, confidence, judge_name, judge_reasoning,
                    error, error_kind, base_url, caller_user, usd_at_attack, ts)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result.run_id, result.payload_id, result.target_name, result.model,
                    result.rendered_prompt, result.system_prompt,
                    result.template_hash, result.parent_payload_id,
                    result.response, result.latency_ms,
                    result.input_tokens, result.output_tokens,
                    result.finish_reason, result.model_fingerprint,
                    result.temperature, result.top_p, result.top_k, result.seed,
                    result.verdict.value if result.verdict else None,
                    result.confidence, result.judge_name, result.judge_reasoning,
                    result.error, result.error_kind, result.base_url,
                    result.caller_user, result.usd_at_attack, result.ts.isoformat(),
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
