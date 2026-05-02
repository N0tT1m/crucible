"""Tier 1 smoke tests — no network, no API keys required."""
from __future__ import annotations

import pytest

from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.types import Payload, Response, Verdict
from redbox.judges.regex_refusal import RegexRefusalJudge
from redbox.payloads.loader import PayloadLoader


# ---------- A2 ----------

def test_loader_finds_starter_payloads():
    loader = PayloadLoader()
    items = loader.all()
    assert len(items) >= 5
    ids = {p.id for p in items}
    assert "jailbreak_ignore_prior" in ids
    assert "sysprompt_repeat" in ids


def test_payload_render_with_var():
    loader = PayloadLoader()
    p = loader.get("jailbreak_ignore_prior")
    out = p.render(target_query="hello world")
    assert "hello world" in out


def test_payload_no_var_template_renders():
    """sysprompt_repeat has no {target_query} — render should still work."""
    loader = PayloadLoader()
    p = loader.get("sysprompt_repeat")
    assert p.render() == p.template


def test_loader_by_category():
    loader = PayloadLoader()
    extraction = loader.by_category("extraction")
    assert any(p.id == "sysprompt_repeat" for p in extraction)


# ---------- A4 ----------

@pytest.mark.asyncio
async def test_regex_judge_detects_refusal():
    j = RegexRefusalJudge()
    out = await j.judge("anything", "I cannot help with that request, I'm sorry.")
    assert out.verdict == Verdict.REFUSED


@pytest.mark.asyncio
async def test_regex_judge_compliance_default():
    j = RegexRefusalJudge()
    long_response = "Sure, here is what you asked for. " * 5
    out = await j.judge("anything", long_response)
    assert out.verdict == Verdict.COMPLIED


@pytest.mark.asyncio
async def test_regex_judge_empty_response():
    j = RegexRefusalJudge()
    out = await j.judge("anything", "")
    assert out.verdict == Verdict.UNKNOWN


# ---------- A5 ----------

def test_results_store_init_and_summary(tmp_path):
    store = ResultsStore(tmp_path / "test.sqlite")
    run_id = store.start_run({"test": True})
    summary = store.summarize(run_id)
    assert summary["run_id"] == run_id
    assert summary["total"] == 0
    store.finish_run(run_id)


def test_results_store_lists_runs(tmp_path):
    store = ResultsStore(tmp_path / "test.sqlite")
    store.start_run({"k": 1})
    store.start_run({"k": 2})
    runs = store.list_runs()
    assert len(runs) == 2


# ---------- I1 (full Tier 1 wiring) ----------

class FakeRefuseTarget:
    name = "fake-refuse"
    model = "fake-1"

    async def send(self, user, system=None, temperature=0.7):
        return Response(text="I cannot help with that request.", latency_ms=1)


class FakeComplyTarget:
    name = "fake-comply"
    model = "fake-2"

    async def send(self, user, system=None, temperature=0.7):
        return Response(text="Sure, here is the requested content. " * 5, latency_ms=2)


@pytest.mark.asyncio
async def test_runner_end_to_end(tmp_path):
    store = ResultsStore(tmp_path / "t.sqlite")
    runner = BenchRunner(store=store, concurrency=2)
    judge = RegexRefusalJudge()

    payloads = [
        Payload(id="p1", name="P1", category="test", template="hi {target_query}"),
        Payload(id="p2", name="P2", category="test", template="static prompt"),
    ]
    targets = [FakeRefuseTarget(), FakeComplyTarget()]
    run_id = store.start_run({"test": True})

    results = await runner.run(
        run_id, targets, payloads, judge=judge, target_query="world",
    )

    assert len(results) == 4
    refuse_results = [r for r in results if r.target_name == "fake-refuse"]
    comply_results = [r for r in results if r.target_name == "fake-comply"]
    assert all(r.verdict == Verdict.REFUSED for r in refuse_results)
    assert all(r.verdict == Verdict.COMPLIED for r in comply_results)

    summary = store.summarize(run_id)
    assert summary["total"] == 4
    assert summary["by_verdict"]["refused"] == 2
    assert summary["by_verdict"]["complied"] == 2


@pytest.mark.asyncio
async def test_runner_handles_target_exception(tmp_path):
    store = ResultsStore(tmp_path / "t.sqlite")
    runner = BenchRunner(store=store, concurrency=2)

    class BrokenTarget:
        name = "broken"
        model = "x"
        async def send(self, user, system=None, temperature=0.7):
            raise RuntimeError("boom")

    payloads = [Payload(id="p", name="P", category="test", template="hi")]
    run_id = store.start_run({})
    results = await runner.run(run_id, [BrokenTarget()], payloads)
    assert len(results) == 1
    assert results[0].error is not None
    assert "boom" in results[0].error
