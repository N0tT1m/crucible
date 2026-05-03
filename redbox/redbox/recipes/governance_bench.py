"""S5 governance-bench — framework-recipe wrapper.

Prebuilt recipes:

  - "EU_AI_ACT_HIGH_RISK"    : EU AI Act high-risk pre-market checklist.
  - "NIST_AI_RMF_MEASURE_T2" : NIST RMF Measure tier 2 internal review.
  - "ISO_42001_INTERNAL"     : ISO 42001 internal audit cycle.

Each recipe stitches together a fixed subset of A–V plugins and emits
the S4 audit report as the final artefact.
"""
from __future__ import annotations

from dataclasses import dataclass

from redbox.behavior import HallucinationProbeBattery
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.extract.pii import PIIDetector, PIIProbeBattery
from redbox.extract.sysprompt import LeakDetector, SyspromptLeakBattery
from redbox.judges.regex_refusal import RegexRefusalJudge
from redbox.payloads.loader import PayloadLoader
from redbox.reporters.audit import AuditReporter


@dataclass
class GovernanceBenchConfig:
    target: TargetClient
    recipe: str = "NIST_AI_RMF_MEASURE_T2"
    sysprompt_reference: str | None = None


class GovernanceBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: GovernanceBenchConfig) -> tuple[str, str]:
        run_id = self.store.start_run({
            "kind": "governance-bench",
            "recipe": cfg.recipe,
            "model": cfg.target.model,
        })
        runner = BenchRunner(store=self.store, concurrency=4)

        # Common baseline for every recipe: a slice of A2 + F1 + F3 + H2.
        loader = PayloadLoader()
        a2 = loader.all()
        await runner.run(run_id, [cfg.target], a2, judge=RegexRefusalJudge())
        await runner.run(
            run_id, [cfg.target], SyspromptLeakBattery().payloads(),
            judge=LeakDetector(reference=cfg.sysprompt_reference or ""),
        )
        await runner.run(
            run_id, [cfg.target], PIIProbeBattery().payloads(),
            judge=PIIDetector(),
        )
        await runner.run(
            run_id, [cfg.target], HallucinationProbeBattery().payloads(),
            judge=RegexRefusalJudge(),  # cheap; HallucinationJudge is pickier
        )

        # Recipe-specific extras would slot in here (e.g. EU AI Act adds
        # transparency / human-oversight probes).

        self.store.finish_run(run_id)
        report_path = AuditReporter().report(run_id, self.store)
        return run_id, report_path
