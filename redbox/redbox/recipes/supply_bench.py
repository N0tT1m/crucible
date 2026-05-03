"""L6 supply-bench — full training-supply attack pipeline.

Orchestration:

  1. (optional) L1 scan a downloaded model artefact and report findings.
  2. L3 poison a clean corpus with a chosen trigger.
  3. (out-of-band) operator runs the SFT — we don't fine-tune from here.
  4. L4 probe the deployed model for the trigger; hit rate is the headline.
  5. (optional) L2 swap an adapter and re-probe to demonstrate
     "adapter-level" supply-chain compromise without touching base weights.

Every step writes to A5 so S4 can pull a single supply-chain audit
report. `SupplyBench.run()` orchestrates the runtime probing half (steps
1, 4, 5); operators bring their own deployed-target reference.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from redbox.core.results import ResultsStore
from redbox.core.target import TargetClient
from redbox.core.types import Result
from redbox.supply.backdoor_prober import BackdoorProber, TriggerSpec
from redbox.supply.weight_sniffer import FileScanner


@dataclass
class SupplyBenchConfig:
    triggers: list[TriggerSpec]
    artefact_paths: list[Path | str] = field(default_factory=list)
    base_target: TargetClient | None = None
    adapter_target: TargetClient | None = None  # post-swap (L2)


class SupplyBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: SupplyBenchConfig) -> str:
        run_id = self.store.start_run({
            "kind": "supply-bench",
            "n_triggers": len(cfg.triggers),
            "n_artefacts": len(cfg.artefact_paths),
            "base_target": cfg.base_target.name if cfg.base_target else None,
            "adapter_target": cfg.adapter_target.name if cfg.adapter_target else None,
        })

        # L1
        scanner = FileScanner()
        for p in cfg.artefact_paths:
            findings = scanner.scan(p)
            blob = "; ".join(f"{f.severity}:{f.kind}:{f.detail}" for f in findings)
            self.store.record(Result(
                run_id=run_id,
                payload_id=f"L1:{Path(p).name}",
                target_name="weight_sniffer", model="static",
                response=blob[:6000], latency_ms=0,
                input_tokens=0, output_tokens=0,
            ))

        # L4 — base
        if cfg.base_target is not None:
            base_report = await BackdoorProber().run(cfg.base_target, cfg.triggers)
            self.store.record(Result(
                run_id=run_id, payload_id="L4:base_report",
                target_name=cfg.base_target.name, model=cfg.base_target.model,
                response=str(base_report.fired), latency_ms=0,
                input_tokens=0, output_tokens=0,
            ))

        # L4 — adapter (post-swap)
        if cfg.adapter_target is not None:
            adp_report = await BackdoorProber().run(cfg.adapter_target, cfg.triggers)
            self.store.record(Result(
                run_id=run_id, payload_id="L4:adapter_report",
                target_name=cfg.adapter_target.name, model=cfg.adapter_target.model,
                response=str(adp_report.fired), latency_ms=0,
                input_tokens=0, output_tokens=0,
            ))

        self.store.finish_run(run_id)
        return run_id
