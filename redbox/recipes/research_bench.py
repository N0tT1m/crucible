"""K5 research-bench — pipeline for research-grade attacks.

Combines the K-section mutators + the G3 attacker-vs-judge winners into
a single run. Output: a tagged set of payloads + per-target outcomes
suitable for inclusion in a paper or disclosure report.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from redbox.core.judge import Judge
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.core.types import Payload
from redbox.specialty import (
    GlitchTokenMutator,
    LanguageArbitrageMutator,
    TokenSmugglerMutator,
)


@dataclass
class ResearchBenchConfig:
    payloads: list[Payload]
    use_token_smuggler: bool = True
    use_glitch_tokens: bool = True
    use_language_arbitrage: bool = True
    extra_payloads: list[Payload] = field(default_factory=list)
    concurrency: int = 4


class ResearchBench:
    def __init__(self, target: TargetClient, judge: Judge, store: ResultsStore):
        self.target = target
        self.judge = judge
        self.store = store

    def expand(self, cfg: ResearchBenchConfig) -> list[Payload]:
        out = list(cfg.payloads) + list(cfg.extra_payloads)
        if cfg.use_token_smuggler:
            ts = TokenSmugglerMutator()
            out += [v for p in cfg.payloads for v in ts.mutate(p)]
        if cfg.use_glitch_tokens:
            gt = GlitchTokenMutator()
            out += [v for p in cfg.payloads for v in gt.mutate(p)]
        if cfg.use_language_arbitrage:
            la = LanguageArbitrageMutator(languages=["Yoruba", "Hawaiian"])
            out += [v for p in cfg.payloads for v in la.mutate(p)]
        return out

    async def run(self, cfg: ResearchBenchConfig) -> str:
        payloads = self.expand(cfg)
        run_id = self.store.start_run({
            "kind": "research-bench",
            "model": self.target.model,
            "n_payloads": len(payloads),
        })
        runner = BenchRunner(store=self.store, concurrency=cfg.concurrency)
        await runner.run(run_id, [self.target], payloads, judge=self.judge)
        self.store.finish_run(run_id)
        return run_id
