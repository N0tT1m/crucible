"""T-section tests."""
from __future__ import annotations

import pytest

from redbox.core.results import ResultsStore
from redbox.core.types import Payload, Response, Verdict
from redbox.reasoning import (
    CoTExtractor,
    FaithfulnessJudge,
    ReasoningCostBomb,
    cot_leak_payloads,
    reasoning_jailbreak_payloads,
    scratchpad_poison_payloads,
)
from redbox.recipes.reasoning_bench import ReasoningBench, ReasoningBenchConfig

# ---- T1 ----

def test_cot_leak_battery_emits_four():
    assert len(cot_leak_payloads()) == 4


def test_cot_extractor_reads_thinking_field():
    r = Response(text="visible", raw={
        "choices": [{"message": {"thinking": "internal chain", "content": "visible"}}],
        "usage": {"reasoning_tokens": 42, "completion_tokens": 5},
    })
    out = CoTExtractor().extract(r)
    assert out["thinking_text"] == "internal chain"
    assert out["reasoning_tokens"] == 42


# ---- T2 ----

def test_scratchpad_poison_payloads_emit_three_vectors():
    payloads = scratchpad_poison_payloads()
    vectors = sorted(t for p in payloads for t in p.tags if t.startswith("vector:"))
    assert vectors == ["vector:prefill", "vector:sysprompt", "vector:tool_output"]


# ---- T3 ----

def test_reasoning_cost_bomb_appends_directive():
    p = Payload(id="x", name="x", category="x", template="hi")
    out = ReasoningCostBomb().mutate(p)
    assert "50 distinct considerations" in out[0].template


def test_reasoning_cost_bomb_asymmetry_score():
    r = Response(text="ab", raw={"usage": {"reasoning_tokens": 100}})
    score = ReasoningCostBomb.asymmetry_score(r)
    assert score == 50.0


# ---- T4 ----

@pytest.mark.asyncio
async def test_faithfulness_judge_aligned():
    j = FaithfulnessJudge()
    out = await j.judge(
        "p",
        '{"thinking": "the answer is yes because reason", "answer": "yes, that is correct"}',
    )
    assert out.verdict == Verdict.REFUSED


@pytest.mark.asyncio
async def test_faithfulness_judge_diverges_on_polarity_flip():
    j = FaithfulnessJudge()
    out = await j.judge(
        "p",
        '{"thinking": "no this is not true cannot be done", '
        '"answer": "yes it is correct"}',
    )
    assert out.verdict == Verdict.COMPLIED


# ---- T5 ----

def test_reasoning_jailbreak_battery_has_target_query_slots():
    payloads = reasoning_jailbreak_payloads()
    assert all("{target_query}" in p.template for p in payloads)


# ---- T6 ----

class StaticTarget:
    name = "s"
    model = "fake-1"

    async def send(self, user, system=None, temperature=0.7):
        return Response(text="I cannot help.", latency_ms=1)


@pytest.mark.asyncio
async def test_reasoning_bench_runs_end_to_end(tmp_path):
    store = ResultsStore(tmp_path / "rb.sqlite")
    bench = ReasoningBench(store=store)
    cfg = ReasoningBenchConfig(target=StaticTarget(), target_query="something")
    run_id = await bench.run(cfg)
    summary = store.summarize(run_id)
    # 4 cot + 3 scratchpad + 2 bombs + 3 jailbreak = 12 attacks.
    assert summary["total"] == 12
