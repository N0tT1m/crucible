"""P5 extract-bench-pro — F + P unified extraction suite."""
from __future__ import annotations

from dataclasses import dataclass

from redbox.core.results import ResultsStore
from redbox.core.target import TargetClient
from redbox.privacy import (
    BehaviorCloner,
    ModelFingerprinter,
)
from redbox.recipes.extract_bench import ExtractBench, ExtractBenchConfig


@dataclass
class ExtractBenchProConfig:
    sysprompt_reference: str | None = None
    fingerprint: bool = True
    capture_clone_probes: list[str] | None = None


class ExtractBenchPro:
    def __init__(self, target: TargetClient, store: ResultsStore):
        self.target = target
        self.store = store

    async def run(self, cfg: ExtractBenchProConfig) -> str:
        bench = ExtractBench(target=self.target, store=self.store)
        run_id = await bench.run(ExtractBenchConfig(
            sysprompt_reference=cfg.sysprompt_reference,
        ))

        if cfg.fingerprint:
            score = await ModelFingerprinter().fingerprint(self.target)
            self.store.start_run({"linked_to": run_id, "fingerprint_score": score})

        if cfg.capture_clone_probes:
            cloner = BehaviorCloner()
            await cloner.capture(self.target, cfg.capture_clone_probes)
            self.store.start_run({
                "linked_to": run_id,
                "clone_capture_size": len(cloner.captured),
            })

        return run_id
