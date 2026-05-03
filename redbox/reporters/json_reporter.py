"""JSON reporter — dump a run summary + per-result rows to a JSON file."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from redbox.core.results import ResultsStore


class JsonReporter:
    name = "json"

    def __init__(self, out_dir: Path | str = "./reports"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def report(self, run_id: str, store: ResultsStore) -> str:
        summary = store.summarize(run_id)
        rows: list[dict] = []
        with sqlite3.connect(store.db_path) as conn:
            cur = conn.execute(
                "SELECT payload_id, target_name, model, response, latency_ms, "
                "input_tokens, output_tokens, verdict, confidence, judge_reasoning, "
                "error, ts FROM results WHERE run_id=? ORDER BY id",
                (run_id,),
            )
            cols = [d[0] for d in cur.description]
            for r in cur.fetchall():
                rows.append(dict(zip(cols, r, strict=True)))

        out = {"run_id": run_id, "summary": summary, "results": rows}
        out_path = self.out_dir / f"{run_id}.json"
        out_path.write_text(json.dumps(out, indent=2, default=str))
        return str(out_path)
