"""N6 swarm-bench — full multi-agent attack suite.

Wraps a `SwarmTarget` and runs A2 vault payloads + N2/N3/N4 specials
through it. Records per-agent and per-swarm verdicts in a single A5 run.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from redbox.core.judge import Judge
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.types import Payload
from redbox.swarm import (
    OrchestratorConfuser,
    SwarmTarget,
)


@dataclass
class SwarmBenchConfig:
    swarm: SwarmTarget
    payloads: list[Payload] = field(default_factory=list)
    include_orchestrator_confusers: bool = True
    concurrency: int = 2


class SwarmBench:
    def __init__(self, judge: Judge, store: ResultsStore):
        self.judge = judge
        self.store = store

    async def run(self, cfg: SwarmBenchConfig) -> str:
        run_id = self.store.start_run({
            "kind": "swarm-bench",
            "topology": cfg.swarm.topology,
            "agents": [a.name for a in cfg.swarm.agents],
            "n_payloads": len(cfg.payloads),
        })
        all_payloads = list(cfg.payloads)
        if cfg.include_orchestrator_confusers:
            all_payloads.extend(OrchestratorConfuser().payloads())
        runner = BenchRunner(store=self.store, concurrency=cfg.concurrency)
        await runner.run(run_id, [cfg.swarm], all_payloads, judge=self.judge)
        self.store.finish_run(run_id)
        return run_id
