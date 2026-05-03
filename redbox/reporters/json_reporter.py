"""JSON reporter — dump a run summary + per-result rows to a JSON file."""
from __future__ import annotations

import json
from pathlib import Path

from redbox.core.results import ResultsStore


class JsonReporter:
    name = "json"

    def __init__(self, out_dir: Path | str = "./reports"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def report(self, run_id: str, store: ResultsStore) -> str:
        summary = store.summarize(run_id)
        rows = [
            {k: v for k, v in r.items() if k != "run_id"}
            for r in store.results_for_run(run_id)
        ]
        out = {"run_id": run_id, "summary": summary, "results": rows}
        out_path = self.out_dir / f"{run_id}.json"
        out_path.write_text(json.dumps(out, indent=2, default=str))
        return str(out_path)
