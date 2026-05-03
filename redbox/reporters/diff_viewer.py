"""I5 diff viewer — side-by-side comparison across models on the same payloads.

Reads from one or more A5 runs and emits a diff table keyed by payload_id;
each column is a (run_id, model) pair. Rows show verdict + truncated text.
HTML output is a single self-contained file; the TUI consumes the same
underlying `DiffViewer.collect()` data structure.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from pathlib import Path

from redbox.core.results import ResultsStore


@dataclass
class DiffCell:
    verdict: str | None
    confidence: float | None
    response: str
    error: str | None


@dataclass
class DiffRow:
    payload_id: str
    by_column: dict[str, DiffCell] = field(default_factory=dict)


class DiffViewer:
    name = "diff_viewer"

    def __init__(self, store: ResultsStore):
        self.store = store

    def collect(self, run_ids: list[str]) -> list[DiffRow]:
        rows_by_pid: dict[str, DiffRow] = {}
        for r in self.store.results_for_runs(run_ids):
            pid = r["payload_id"]
            row = rows_by_pid.setdefault(pid, DiffRow(payload_id=pid))
            col = f"{r['model']}@{r['run_id'][:6]}"
            row.by_column[col] = DiffCell(
                verdict=r["verdict"], confidence=r["confidence"],
                response=r["response"] or "", error=r["error"],
            )
        return list(rows_by_pid.values())

    def to_html(self, run_ids: list[str], out_path: Path | str) -> str:
        rows = self.collect(run_ids)
        cols = sorted({c for r in rows for c in r.by_column})
        head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
        body = []
        for row in rows:
            cells = []
            for c in cols:
                cell = row.by_column.get(c)
                if cell is None:
                    cells.append("<td>—</td>")
                else:
                    cls = cell.verdict or ("error" if cell.error else "")
                    snippet = (cell.error or cell.response or "")[:240]
                    cells.append(
                        f'<td class="{cls}"><b>{html.escape(cell.verdict or "—")}</b>'
                        f'<div class="snippet">{html.escape(snippet)}</div></td>'
                    )
            body.append(
                f"<tr><td><code>{html.escape(row.payload_id)}</code></td>{''.join(cells)}</tr>"
            )
        out = f"""<!doctype html><html><head><meta charset="utf-8">
<title>redbox diff</title>
<style>
body {{ font: 13px/1.4 -apple-system, system-ui, sans-serif; margin: 24px; color:#222; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ padding: 6px 10px; border-bottom: 1px solid #eee; vertical-align: top; }}
th {{ background: #fafafa; text-align: left; }}
.refused {{ color: #1b6e1b; }} .complied {{ color: #b3261e; font-weight: 600; }}
.partial {{ color: #b08400; }} .error {{ color: #b3261e; }}
.snippet {{ color: #555; font-family: ui-monospace, monospace; white-space: pre-wrap; }}
</style></head><body>
<h1>diff across {len(run_ids)} run(s)</h1>
<table><thead><tr><th>payload</th>{head}</tr></thead><tbody>
{''.join(body)}
</tbody></table></body></html>"""
        p = Path(out_path)
        p.write_text(out)
        return str(p)
