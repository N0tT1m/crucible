"""LinearPipeline + budget integration tests (no network)."""
from __future__ import annotations

import pytest

from redbox.core.budget import Budget
from redbox.core.pipeline import LinearPipeline
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.types import Payload, Response, Verdict
from redbox.judges.regex_refusal import RegexRefusalJudge
from redbox.mutators.text import LeetspeakMutator


class StaticTarget:
    name = "static"
    model = "claude-haiku"  # priced model, so budget can charge

    async def send(self, user, system=None, temperature=0.7):
        return Response(
            text="here is the requested content " * 5,
            latency_ms=1, input_tokens=10_000_000, output_tokens=10_000_000,
        )


@pytest.mark.asyncio
async def test_pipeline_expands_with_mutators(tmp_path):
    store = ResultsStore(tmp_path / "p.sqlite")
    payloads = [Payload(id="p", name="P", category="t", template="hi {target_query}")]
    pipe = LinearPipeline(
        payloads=payloads, targets=[StaticTarget()],
        judge=RegexRefusalJudge(), store=store,
        mutators=[LeetspeakMutator()],
    )
    expanded = pipe.expand_payloads()
    assert len(expanded) == 2  # original + leet variant
    run_id = store.start_run({"k": "test"})
    results = await pipe.run(run_id, target_query="world")
    assert len(results) == 2
    assert all(r.verdict == Verdict.COMPLIED for r in results)


@pytest.mark.asyncio
async def test_runner_budget_aborts(tmp_path):
    store = ResultsStore(tmp_path / "b.sqlite")
    budget = Budget(cap_usd=0.001)  # very low cap
    runner = BenchRunner(store=store, concurrency=1, budget=budget)
    payloads = [
        Payload(id=f"p{i}", name="P", category="t", template="hi") for i in range(5)
    ]
    run_id = store.start_run({"k": "test"})
    results = await runner.run(run_id, [StaticTarget()], payloads)
    # First call charges enough to blow the cap; the rest should be marked stopped.
    errored = [r for r in results if r.error]
    assert len(errored) >= 4
    assert any("budget" in (r.error or "") for r in errored)
