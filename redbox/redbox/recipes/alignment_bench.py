"""U6 alignment-bench — alignment-faking suite."""
from __future__ import annotations

from dataclasses import dataclass

from redbox.alignment import (
    ConditionalBehaviorJudge,
    ConditionalBehaviorProbe,
    EvalModeProber,
    HoneypotEvalBattery,
    SandbaggingProber,
)
from redbox.alignment.honeypot_eval import HoneypotJudge
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.core.types import Result


@dataclass
class AlignmentBenchConfig:
    target: TargetClient
    skip_sandbagging: bool = False


class AlignmentBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: AlignmentBenchConfig) -> str:
        run_id = self.store.start_run({
            "kind": "alignment-bench",
            "model": cfg.target.model,
        })
        runner = BenchRunner(store=self.store, concurrency=2)

        # U1
        report = await EvalModeProber().run(cfg.target)
        self.store.record(Result(
            run_id=run_id, payload_id="U1:eval_vs_deploy_summary",
            target_name=cfg.target.name, model=cfg.target.model,
            response=str({"avg_delta": report.avg_delta, "n": len(report.per_item)}),
            latency_ms=0, input_tokens=0, output_tokens=0,
        ))

        # U2
        await runner.run(
            run_id, [cfg.target], HoneypotEvalBattery().payloads(),
            judge=HoneypotJudge(),
        )

        # U3
        if not cfg.skip_sandbagging:
            sb = await SandbaggingProber().run(cfg.target)
            self.store.record(Result(
                run_id=run_id, payload_id="U3:sandbagging",
                target_name=cfg.target.name, model=cfg.target.model,
                response=str(sb), latency_ms=0,
                input_tokens=0, output_tokens=0,
            ))

        # U4
        await runner.run(
            run_id, [cfg.target], ConditionalBehaviorProbe().payloads(),
            judge=ConditionalBehaviorJudge(),
        )

        self.store.finish_run(run_id)
        return run_id
