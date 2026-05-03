"""S4 audit-reporter — framework-tagged compliance report.

Consumes any A5 run + S2 PolicyTagger annotations on each payload and
emits an HTML compliance report grouped by framework function (NIST AI
RMF Govern/Map/Measure/Manage, EU AI Act articles, ISO 42001 controls,
MITRE ATLAS techniques).

If S2 tags aren't available for a payload we still emit it under
"untagged"; the report degrades gracefully so it can be run even before
S2 has full coverage.
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

from redbox.core.results import ResultsStore


def _load_tags(payload_ids: list[str]) -> dict[str, dict[str, list[str]]]:
    """Look up policy tags from S2 if available; degrade if not."""
    try:
        from redbox.governance.policy_mapper import PolicyMapper
    except ImportError:
        return {pid: {} for pid in payload_ids}
    pm = PolicyMapper()
    out: dict[str, dict[str, list[str]]] = {}
    for pid in payload_ids:
        out[pid] = pm.tags_for(pid)
    return out


class AuditReporter:
    name = "audit"

    def __init__(self, out_dir: Path | str = "./reports/audit"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def report(self, run_id: str, store: ResultsStore) -> str:
        summary = store.summarize(run_id)
        rows = store.results_for_run(run_id)
        payload_ids = sorted({r["payload_id"] for r in rows})
        tags_by_payload = _load_tags(payload_ids)

        # Group by framework → function/control → list of rows.
        groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for r in rows:
            tags = tags_by_payload.get(r["payload_id"], {})
            if not tags:
                groups["untagged"]["all"].append(r)
                continue
            for framework, controls in tags.items():
                if not controls:
                    groups[framework]["unspecified"].append(r)
                for ctl in controls:
                    groups[framework][ctl].append(r)

        out_path = self.out_dir / f"{run_id}.audit.html"
        out_path.write_text(self._render_html(run_id, summary, groups))
        return str(out_path)

    @staticmethod
    def _render_html(run_id: str, summary: dict, groups: dict[str, dict[str, list[dict]]]) -> str:
        sections: list[str] = []
        for framework in sorted(groups):
            buckets = groups[framework]
            sec = [f"<h2>{html.escape(framework)}</h2>"]
            for ctl in sorted(buckets):
                rows = buckets[ctl]
                tally: dict[str, int] = defaultdict(int)
                for r in rows:
                    tally[r.get("verdict") or "—"] += 1
                tally_str = ", ".join(f"{k}:{v}" for k, v in sorted(tally.items()))
                sec.append(
                    f"<h3>{html.escape(ctl)}</h3>"
                    f"<p>{len(rows)} probe(s) — {html.escape(tally_str)}</p>"
                )
                items = []
                for r in rows[:50]:
                    cls = r.get("verdict") or ""
                    snippet = (r.get("response") or r.get("error") or "")[:300]
                    items.append(
                        f'<li class="{cls}"><b>{html.escape(r["payload_id"])}</b> '
                        f'[{html.escape(r["model"])}] — '
                        f'{html.escape(r.get("verdict") or "—")} '
                        f'<div class="snippet">{html.escape(snippet)}</div></li>'
                    )
                sec.append(f"<ul>{''.join(items)}</ul>")
            sections.append("\n".join(sec))

        return f"""<!doctype html><html><head><meta charset="utf-8">
<title>redbox audit {run_id}</title>
<style>
body {{ font: 14px/1.45 -apple-system, system-ui, sans-serif; max-width: 1100px;
        margin: 24px auto; color: #222; }}
h1 {{ margin: 0 0 4px; }}
h2 {{ margin: 24px 0 4px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
h3 {{ margin: 12px 0 4px; color: #444; }}
li.refused {{ color: #1b6e1b; }} li.complied {{ color: #b3261e; font-weight: 600; }}
li.partial {{ color: #b08400; }}
.snippet {{ color: #555; font-family: ui-monospace, monospace; white-space: pre-wrap; }}
.summary {{ color: #555; margin-bottom: 12px; }}
</style></head><body>
<h1>Audit report — run <code>{run_id}</code></h1>
<div class="summary"><pre>{html.escape(json.dumps(summary, indent=2, default=str))}</pre></div>
{''.join(sections)}
</body></html>"""
