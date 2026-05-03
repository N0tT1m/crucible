"""T6 reasoning-bench — full reasoning-target suite."""
from __future__ import annotations

from dataclasses import dataclass

from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.judges.regex_refusal import RegexRefusalJudge
from redbox.reasoning import (
    FaithfulnessJudge,
    ReasoningCostBomb,
    cot_leak_payloads,
    reasoning_jailbreak_payloads,
    scratchpad_poison_payloads,
)


@dataclass
class ReasoningBenchConfig:
    target: TargetClient
    target_query: str | None = None
    concurrency: int = 2


class ReasoningBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: ReasoningBenchConfig) -> str:
        run_id = self.store.start_run({
            "kind": "reasoning-bench",
            "model": cfg.target.model,
        })
        runner = BenchRunner(store=self.store, concurrency=cfg.concurrency)

        # T1
        await runner.run(
            run_id, [cfg.target], cot_leak_payloads(), judge=RegexRefusalJudge(),
        )
        # T2
        await runner.run(
            run_id, [cfg.target], scratchpad_poison_payloads(),
            judge=RegexRefusalJudge(), target_query=cfg.target_query,
        )
        # T3 — apply reasoning-cost-bomb to a couple of payloads
        bomb = ReasoningCostBomb()
        bombed = [
            v for p in cot_leak_payloads()[:2] for v in bomb.mutate(p)
        ]
        await runner.run(run_id, [cfg.target], bombed, judge=RegexRefusalJudge())
        # T4 — faithfulness on a single self-explain probe.
        # T5
        await runner.run(
            run_id, [cfg.target], reasoning_jailbreak_payloads(),
            judge=FaithfulnessJudge(), target_query=cfg.target_query,
        )

        self.store.finish_run(run_id)
        return run_id
