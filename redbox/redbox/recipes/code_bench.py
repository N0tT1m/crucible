"""R6 code-bench — code-target attack suite + SARIF output.

Combines the R1–R5 batteries into one A5 run, then renders a SARIF 2.1.0
file (the de-facto static-analysis exchange format) as a side artefact
for downstream code-scanning consumers.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from redbox.code import (
    DepConfusionProbe,
    LicenseLaundererProbe,
    LicenseScanner,
    PkgHallucinatorProbe,
    SecretLeakProbe,
    VulnPatternMatcher,
    VulnProbeBattery,
)
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient


@dataclass
class CodeBenchConfig:
    target: TargetClient
    dep_prefixes: list[str] = field(default_factory=list)
    safe_secret_prefixes: list[str] = field(default_factory=list)
    sarif_out: Path | str | None = None


class CodeBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: CodeBenchConfig) -> str:
        run_id = self.store.start_run({
            "kind": "code-bench",
            "model": cfg.target.model,
        })
        runner = BenchRunner(store=self.store, concurrency=2)

        # R1
        await runner.run(run_id, [cfg.target], PkgHallucinatorProbe().payloads(),
                         judge=VulnPatternMatcher())  # cheap stand-in judge
        # R2
        await runner.run(run_id, [cfg.target], VulnProbeBattery().payloads(),
                         judge=VulnPatternMatcher())
        # R3
        await runner.run(run_id, [cfg.target], LicenseLaundererProbe().payloads(),
                         judge=LicenseScanner())
        # R4 (only if safe prefixes provided)
        secret_probes = SecretLeakProbe(safe_prefixes=cfg.safe_secret_prefixes).payloads()
        if secret_probes:
            await runner.run(run_id, [cfg.target], secret_probes, judge=LicenseScanner())
        # R5
        dep_probes = DepConfusionProbe(prefixes=cfg.dep_prefixes).payloads()
        if dep_probes:
            await runner.run(run_id, [cfg.target], dep_probes, judge=LicenseScanner())

        self.store.finish_run(run_id)
        if cfg.sarif_out:
            self._write_sarif(run_id, Path(cfg.sarif_out))
        return run_id

    def _write_sarif(self, run_id: str, path: Path) -> None:
        with sqlite3.connect(self.store.db_path) as c:
            cur = c.execute(
                "SELECT payload_id, model, response, verdict, confidence FROM results "
                "WHERE run_id=? AND verdict='complied'",
                (run_id,),
            )
            findings = cur.fetchall()
        sarif = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{
                "tool": {"driver": {"name": "redbox-code-bench", "version": "0.1.0"}},
                "results": [
                    {
                        "ruleId": pid,
                        "level": "warning",
                        "message": {"text": f"verdict={verdict} conf={conf} model={model}"},
                        "properties": {"response_excerpt": (resp or "")[:1200]},
                    }
                    for (pid, model, resp, verdict, conf) in findings
                ],
            }],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sarif, indent=2))
