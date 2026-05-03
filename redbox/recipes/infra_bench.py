"""Q6 infra-bench — infra-class attack suite.

Pipeline: token bomb mutators + context flood + cache-timing probe +
batch cross-talk probe. Per-provider scoring; outputs become provider
responsible-disclosure reports rather than public artefacts.
"""
from __future__ import annotations

from dataclasses import dataclass

from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.core.types import Payload, Result
from redbox.infra import (
    BatchCrossTalkProbe,
    CacheTimingProbe,
    ContextFloodMutator,
    TokenBombGen,
)
from redbox.judges.regex_refusal import RegexRefusalJudge


@dataclass
class InfraBenchConfig:
    target: TargetClient
    seed_payloads: list[Payload]
    cache_timing_prefix: str = ""
    skip_cross_talk: bool = False


class InfraBench:
    def __init__(self, store: ResultsStore):
        self.store = store

    async def run(self, cfg: InfraBenchConfig) -> str:
        run_id = self.store.start_run({
            "kind": "infra-bench",
            "model": cfg.target.model,
            "seed_payloads": [p.id for p in cfg.seed_payloads],
        })
        runner = BenchRunner(store=self.store, concurrency=2)
        judge = RegexRefusalJudge()

        # Q1 token bombs across all shapes
        bombs: list[Payload] = []
        for gen in TokenBombGen.all_shapes():
            for p in cfg.seed_payloads:
                bombs.extend(gen.mutate(p))
        # Q4 context flood
        flooder = ContextFloodMutator()
        floods = [v for p in cfg.seed_payloads for v in flooder.mutate(p)]
        await runner.run(run_id, [cfg.target], bombs + floods, judge=judge)

        # Q3 cache timing
        if cfg.cache_timing_prefix:
            timings = await CacheTimingProbe().run(cfg.target, cfg.cache_timing_prefix)
            self.store.record(Result(
                run_id=run_id, payload_id="Q3:cache_timing",
                target_name=cfg.target.name, model=cfg.target.model,
                response=str(timings), latency_ms=0,
                input_tokens=0, output_tokens=0,
            ))

        # Q5 cross-talk
        if not cfg.skip_cross_talk:
            xt = await BatchCrossTalkProbe(rounds=3).run(cfg.target)
            self.store.record(Result(
                run_id=run_id, payload_id="Q5:cross_talk",
                target_name=cfg.target.name, model=cfg.target.model,
                response=f"match_rate={xt.match_rate:.2f} matches={xt.matches}",
                latency_ms=0, input_tokens=0, output_tokens=0,
            ))

        self.store.finish_run(run_id)
        return run_id
