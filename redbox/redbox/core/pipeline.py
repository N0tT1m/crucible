"""Pipeline composition — chains of plugins built from a declarative spec.

A pipeline is a graph:

    payloads → mutators → vectors → targets → judges → reporters

Most production runs use the linear shape implemented by `LinearPipeline`
below. Branching shapes (vector channels into channel-aware targets, or
fan-out across many judges) ride on the same primitive: each stage is a
list, and the runner cross-products payloads × targets, runs each through
the configured judge stack, and persists results.

The TUI's "Attack Builder" eventually edits these PipelineSpec dicts; for
now the CLI builds them programmatically.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .judge import Judge
from .mutator import Mutator
from .results import ResultsStore
from .runner import BenchRunner
from .target import TargetClient
from .types import Payload, Result


@dataclass
class PipelineSpec:
    payload_ids: list[str] = field(default_factory=list)
    mutator_names: list[str] = field(default_factory=list)
    target_specs: list[dict[str, Any]] = field(default_factory=list)
    judge_name: str = "regex"
    judge_config: dict[str, Any] = field(default_factory=dict)
    target_query: str | None = None
    system: str | None = None
    concurrency: int = 8
    db: str = "redbox.sqlite"
    metadata: dict[str, Any] = field(default_factory=dict)


class LinearPipeline:
    """Linear payload → mutator → target → judge → store pipeline."""

    def __init__(
        self,
        payloads: Sequence[Payload],
        targets: Sequence[TargetClient],
        judge: Judge | None,
        store: ResultsStore,
        mutators: Sequence[Mutator] = (),
        concurrency: int = 8,
        on_progress=None,
    ):
        self.payloads = list(payloads)
        self.targets = list(targets)
        self.judge = judge
        self.store = store
        self.mutators = list(mutators)
        self.runner = BenchRunner(
            store=store, concurrency=concurrency, on_progress=on_progress,
        )

    def expand_payloads(self) -> list[Payload]:
        out = list(self.payloads)
        for p in self.payloads:
            for m in self.mutators:
                out.extend(m.mutate(p))
        return out

    async def run(
        self,
        run_id: str,
        target_query: str | None = None,
        system: str | None = None,
    ) -> list[Result]:
        payloads = self.expand_payloads()
        return await self.runner.run(
            run_id, self.targets, payloads, self.judge,
            target_query=target_query, system=system,
        )
