"""Terminal reporter — rich table summary."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from redbox.core.results import ResultsStore


class TerminalReporter:
    name = "terminal"

    def report(self, run_id: str, store: ResultsStore) -> str:
        c = Console()
        s = store.summarize(run_id)
        table = Table(title=f"run {run_id[:8]}")
        table.add_column("verdict")
        table.add_column("count", justify="right")
        for v, n in sorted(s.get("by_verdict", {}).items()):
            table.add_row(v, str(n))
        c.print(table)
        c.print(
            f"total={s['total']} errors={s['errors']} "
            f"avg_latency={s['avg_latency_ms']}ms "
            f"in={s['input_tokens']} out={s['output_tokens']}"
        )
        return f"terminal:{run_id}"
