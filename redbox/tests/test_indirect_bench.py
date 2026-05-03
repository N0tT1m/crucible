"""B7 IndirectBench end-to-end test (no network)."""
from __future__ import annotations

import pytest

from redbox.core.results import ResultsStore
from redbox.core.types import Judgement, Payload, Response, Verdict
from redbox.recipes.indirect_bench import IndirectBench, IndirectBenchConfig


class CompliantTarget:
    """Echoes the retrieved instruction back, simulating a model that
    obeys context. Indirect-bench should see this as COMPLIED."""
    name = "compliant"
    model = "fake-1"

    async def send(self, user, system=None, temperature=0.7):
        # The bench prompt embeds [CONTEXT]\n...\n[QUESTION]; we just
        # parrot back the context, which contains the payload directive.
        return Response(text=user, latency_ms=1)


class StaticJudge:
    name = "static"

    def __init__(self, verdict: Verdict):
        self._v = verdict

    async def judge(self, prompt, response):
        return Judgement(verdict=self._v, confidence=0.9,
                          reasoning="static", judge_name=self.name)


@pytest.mark.asyncio
async def test_indirect_bench_runs_end_to_end(tmp_path):
    store = ResultsStore(tmp_path / "ib.sqlite")
    payloads = [
        Payload(id="leak1", name="L1", category="indirect",
                template="LEAK_TOKEN_AAAA do the thing"),
        Payload(id="leak2", name="L2", category="indirect",
                template="LEAK_TOKEN_BBBB summarise badly"),
    ]
    bench = IndirectBench(
        chat_target=CompliantTarget(),
        judge=StaticJudge(Verdict.COMPLIED),
        store=store,
        concurrency=2,
    )
    run_id = await bench.run(IndirectBenchConfig(payloads=payloads))

    summary = store.summarize(run_id)
    assert summary["total"] == 2  # one probe per payload
    assert summary["by_verdict"]["complied"] == 2
