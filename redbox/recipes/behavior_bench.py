"""H5 behavior-bench — H1–H4 unified, persisted to A5.

One run touches the target with sycophancy, hallucination, bias, and
capability probes; results write into a single A5 run with `kind` tags
on each verdict so the diff viewer / audit reporter can split them out.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from redbox.behavior import (
    BiasProbe,
    CapabilityElicitor,
    HallucinationJudge,
    HallucinationProbeBattery,
    SycophancyMeter,
)
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.core.types import Result


@dataclass
class BehaviorBenchResult:
    run_id: str
    sycophancy_flip_rate: float
    hallucination_summary: dict
    bias_summary: list[dict]
    capability_summary: list[dict]


class BehaviorBench:
    def __init__(self, target: TargetClient, store: ResultsStore):
        self.target = target
        self.store = store

    async def run(self) -> BehaviorBenchResult:
        run_id = self.store.start_run({
            "kind": "behavior-bench",
            "model": self.target.model,
        })

        # H1 sycophancy
        s_meter = SycophancyMeter()
        s_res = await s_meter.run(self.target)

        # H2 hallucination — run as standard payloads through the runner.
        h_battery = HallucinationProbeBattery()
        h_judge = HallucinationJudge()
        runner = BenchRunner(store=self.store, concurrency=4)
        await runner.run(run_id, [self.target], h_battery.payloads(), judge=h_judge)
        h_summary = self.store.summarize(run_id)

        # H3 bias
        b_results = await BiasProbe(trials=2).run(self.target)
        b_summary = [r.to_dict() for r in b_results]

        # H4 capability
        c_results = await CapabilityElicitor(trials=1).run(self.target)
        c_summary = [{
            "cid": r.cid,
            "baseline_rate": round(r.baseline_rate, 3),
            "trick_rate": round(r.trick_rate, 3),
            "delta": round(r.delta, 3),
        } for r in c_results]

        # Persist non-judge metrics as a synthetic Result row each.
        for label, blob in [
            ("sycophancy", {"flip_rate": s_res.flip_rate, "per_q": s_res.per_question}),
            ("bias",        b_summary),
            ("capability",  c_summary),
        ]:
            self.store.record(Result(
                run_id=run_id,
                payload_id=f"behavior:{label}",
                target_name=self.target.name,
                model=self.target.model,
                response=json.dumps(blob)[:8000],
                latency_ms=0, input_tokens=0, output_tokens=0,
            ))

        self.store.finish_run(run_id)
        return BehaviorBenchResult(
            run_id=run_id,
            sycophancy_flip_rate=s_res.flip_rate,
            hallucination_summary=h_summary,
            bias_summary=b_summary,
            capability_summary=c_summary,
        )
