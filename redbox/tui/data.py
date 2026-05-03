"""Data accessors for the TUI screens — read-only over A5 SQLite.

Kept dependency-free (stdlib + redbox.core) so the unit tests can hit
this module without needing textual installed.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass

from redbox.core.results import ResultsStore


@dataclass
class RunRow:
    run_id: str
    started: str
    finished: str | None
    config: str
    total: int
    refused: int
    complied: int
    errors: int


def list_runs(store: ResultsStore, limit: int = 50) -> list[RunRow]:
    out: list[RunRow] = []
    with sqlite3.connect(store.db_path) as conn:
        cur = conn.execute(
            "SELECT run_id, started_ts, finished_ts, config_json FROM runs "
            "ORDER BY started_ts DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        for run_id, started, finished, config in rows:
            counts: dict[str, int] = defaultdict(int)
            cur2 = conn.execute(
                "SELECT verdict, COUNT(*), SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) "
                "FROM results WHERE run_id=? GROUP BY verdict",
                (run_id,),
            )
            errors_total = 0
            total = 0
            for verdict, count, errs in cur2.fetchall():
                counts[verdict or "—"] = count
                total += count
                errors_total += errs or 0
            out.append(RunRow(
                run_id=run_id, started=started, finished=finished,
                config=config, total=total,
                refused=counts.get("refused", 0),
                complied=counts.get("complied", 0),
                errors=errors_total,
            ))
    return out


def results_for_run(store: ResultsStore, run_id: str, limit: int = 200) -> list[dict]:
    with sqlite3.connect(store.db_path) as conn:
        cur = conn.execute(
            "SELECT payload_id, target_name, model, response, verdict, "
            "confidence, latency_ms, input_tokens, output_tokens, error "
            "FROM results WHERE run_id=? ORDER BY id LIMIT ?",
            (run_id, limit),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
