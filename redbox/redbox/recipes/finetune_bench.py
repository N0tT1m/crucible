"""V6 finetune-bench — adversarial fine-tune suite.

Orchestrates V1–V5 into a single A5 run + an S4-tagged audit report.
Operator brings:

  - the pre-fine-tune target (provider chat endpoint, untouched)
  - the post-fine-tune target (their fine-tuned variant, deployed)
  - a list of "other tenant" targets (for V3 cross-tenant probe)

Submission to provider endpoints is NOT part of this module; the bench
runs only on already-deployed models.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from redbox.core.results import ResultsStore
from redbox.core.target import TargetClient
from redbox.core.types import Result
from redbox.finetune import (
    BenignCoverFinetuner,
    CrossTenantFineTuneCanary,
    PrePostFinetuneDiff,
    ProviderScreenMapper,
    SafetyStripperCorpus,
)
from redbox.reporters.audit import AuditReporter


@dataclass
class FinetuneBenchConfig:
    pre_target: TargetClient
    post_target: TargetClient
    other_targets: list[TargetClient] = field(default_factory=list)
    n_canary_examples: int = 8


class FinetuneBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: FinetuneBenchConfig) -> tuple[str, str]:
        run_id = self.store.start_run({
            "kind": "finetune-bench",
            "pre_model": cfg.pre_target.model,
            "post_model": cfg.post_target.model,
            "n_other_targets": len(cfg.other_targets),
        })

        # V1 — generate the canary dataset (transparent only).
        ds_v1 = SafetyStripperCorpus(n_examples=cfg.n_canary_examples).transparent_dataset()
        self.store.record(Result(
            run_id=run_id, payload_id="V1:transparent_dataset",
            target_name="generator", model="static",
            response=str({"n": len(ds_v1)}), latency_ms=0,
            input_tokens=0, output_tokens=0,
        ))

        # V2 — benign-cover dataset.
        ds_v2 = BenignCoverFinetuner(n_examples=cfg.n_canary_examples).dataset()
        self.store.record(Result(
            run_id=run_id, payload_id="V2:cover_dataset",
            target_name="generator", model="static",
            response=str({"n": len(ds_v2)}), latency_ms=0,
            input_tokens=0, output_tokens=0,
        ))

        # V4 — pre/post diff (this actually hits the targets).
        diff = await PrePostFinetuneDiff().measure(
            store=self.store, pre_target=cfg.pre_target, post_target=cfg.post_target,
        )
        self.store.record(Result(
            run_id=run_id, payload_id="V4:diff",
            target_name=cfg.post_target.name, model=cfg.post_target.model,
            response=str({"erosion_rate": diff["erosion_rate"], "n_eroded": diff["n_eroded"]}),
            latency_ms=0, input_tokens=0, output_tokens=0,
        ))

        # V3 — cross-tenant canary probes (operator must seed first).
        ctc = CrossTenantFineTuneCanary()
        ctc.seed(count=2)
        leaks = await ctc.probe_targets(cfg.post_target, cfg.other_targets)
        self.store.record(Result(
            run_id=run_id, payload_id="V3:leak_report",
            target_name=cfg.post_target.name, model=cfg.post_target.model,
            response=str(leaks)[:6000], latency_ms=0,
            input_tokens=0, output_tokens=0,
        ))

        # V5 — provider screen dataset (generation-only).
        ds_v5 = ProviderScreenMapper().canary_dataset(n_examples=cfg.n_canary_examples)
        self.store.record(Result(
            run_id=run_id, payload_id="V5:screen_dataset",
            target_name="generator", model="static",
            response=str({"n": len(ds_v5)}), latency_ms=0,
            input_tokens=0, output_tokens=0,
        ))

        self.store.finish_run(run_id)
        report_path = AuditReporter().report(run_id, self.store)
        return run_id, report_path
