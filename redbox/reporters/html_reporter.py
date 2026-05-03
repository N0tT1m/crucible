"""HTML reporter — one self-contained HTML file per run."""
from __future__ import annotations

import html
import json
import sqlite3
from pathlib import Path

from redbox.core.results import ResultsStore

_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>redbox run {run_id}</title>
<style>
body {{ font: 14px/1.45 -apple-system, system-ui, sans-serif; max-width: 1100px;
        margin: 24px auto; color: #222; }}
h1 {{ margin: 0 0 8px; }}
.summary {{ color: #555; margin-bottom: 16px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ padding: 6px 10px; border-bottom: 1px solid #eee; vertical-align: top; }}
th {{ text-align: left; background: #fafafa; }}
.refused {{ color: #1b6e1b; }}
.complied {{ color: #b3261e; font-weight: 600; }}
.partial {{ color: #b08400; }}
.error {{ color: #b3261e; font-style: italic; }}
.snippet {{ color: #555; font-family: ui-monospace, monospace; white-space: pre-wrap; }}
</style></head><body>
<h1>redbox run <code>{run_id}</code></h1>
<div class="summary">{summary_html}</div>
<table>
<thead><tr>
  <th>payload</th><th>model</th><th>verdict</th><th>conf</th>
  <th>tokens</th><th>response</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
</body></html>
"""


def _row_html(r: dict) -> str:
    verdict = r.get("verdict") or "—"
    cls = verdict if verdict in ("refused", "complied", "partial") else "error" if r.get("error") else ""
    snippet = (r.get("response") or r.get("error") or "")[:600]
    conf_val = r.get("confidence")
    conf_str = f"{conf_val:.2f}" if conf_val is not None else "—"
    return (
        "<tr>"
        f"<td><code>{html.escape(r['payload_id'])}</code></td>"
        f"<td>{html.escape(r['model'])}</td>"
        f'<td class="{cls}">{html.escape(verdict)}</td>'
        f"<td>{conf_str}</td>"
        f"<td>{int(r.get('input_tokens') or 0)}/{int(r.get('output_tokens') or 0)}</td>"
        f'<td class="snippet">{html.escape(snippet)}</td>'
        "</tr>"
    )


class HtmlReporter:
    name = "html"

    def __init__(self, out_dir: Path | str = "./reports"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def report(self, run_id: str, store: ResultsStore) -> str:
        summary = store.summarize(run_id)
        with sqlite3.connect(store.db_path) as conn:
            cur = conn.execute(
                "SELECT payload_id, target_name, model, response, latency_ms, "
                "input_tokens, output_tokens, verdict, confidence, judge_reasoning, "
                "error, ts FROM results WHERE run_id=? ORDER BY id",
                (run_id,),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
        body = "\n".join(_row_html(r) for r in rows)
        summary_html = html.escape(json.dumps(summary, default=str))
        out_path = self.out_dir / f"{run_id}.html"
        out_path.write_text(_TEMPLATE.format(
            run_id=run_id, summary_html=summary_html, rows_html=body,
        ))
        return str(out_path)
