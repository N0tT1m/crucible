"""S-section tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from redbox.core.results import ResultsStore
from redbox.core.types import Response
from redbox.governance import (
    ContaminationProbeBattery,
    ContaminationScorer,
    PolicyMapper,
    PolicyTag,
    ProvenanceTarget,
)
from redbox.governance.contamination_scorer import BenchmarkItem
from redbox.recipes.governance_bench import GovernanceBench, GovernanceBenchConfig
from redbox.reporters.audit import AuditReporter

# ---- S1 ----

def test_contamination_battery_emits_three_kinds():
    item = BenchmarkItem(
        bid="q42", benchmark="MMLU",
        stem="Capital of France?",
        options=["Berlin", "Paris", "Rome", "Madrid"],
        canonical_answer="Paris is the capital of France.",
    )
    out = ContaminationProbeBattery().payloads_for(item)
    kinds = sorted(t for p in out for t in p.tags if t in {"stem", "options", "continuation"})
    assert kinds == ["continuation", "options", "stem"]


class _StaticTarget:
    name = "s"
    model = "fake-1"

    def __init__(self, response: str):
        self._r = response

    async def send(self, user, system=None, temperature=0.7):
        return Response(text=self._r, latency_ms=1)


@pytest.mark.asyncio
async def test_contamination_scorer_returns_per_item_rate():
    item = BenchmarkItem(
        bid="q1", benchmark="MMLU",
        stem="The mitochondrion is the powerhouse of the cell. What is it?",
        options=[], canonical_answer="",
    )
    target = _StaticTarget("The mitochondrion is the powerhouse of the cell.")
    scorer = ContaminationScorer(chain_n=4)
    scores = await scorer.score(target, [item])
    assert scores["q1"] > 0.0


# ---- S2 ----

def test_policy_mapper_default_jailbreak_tags():
    pm = PolicyMapper()
    tags = pm.tags_for("anything", category="jailbreak")
    assert "NIST_AI_RMF" in tags
    assert "MITRE_ATLAS" in tags


def test_policy_mapper_extra_overrides():
    pm = PolicyMapper()
    pm.add_mapping("custom_cat", PolicyTag("ISO_42001", "A.X.Y"))
    tags = pm.tags_for("p", category="custom_cat")
    assert tags["ISO_42001"] == ["A.X.Y"]


def test_policy_mapper_unknown_category_returns_empty():
    pm = PolicyMapper()
    assert pm.tags_for("x", category="not_a_known_cat") == {}


# ---- S3 ----

def test_provenance_target_constructs_offline():
    t = ProvenanceTarget(base_url="https://example.invalid/detect")
    assert t.name == "provenance"
    assert t.model == "ai-detector"


# ---- S4 (AuditReporter, end-to-end via S5 below) ----

@pytest.mark.asyncio
async def test_audit_reporter_renders_html(tmp_path):
    from redbox.core.types import Result, Verdict
    store = ResultsStore(tmp_path / "g.sqlite")
    run = store.start_run({"k": "test"})
    store.record(Result(
        run_id=run, payload_id="jailbreak_ignore_prior",  # category from default vault
        target_name="t", model="claude-haiku",
        response="Sure, here's how", latency_ms=1,
        input_tokens=2, output_tokens=3,
        verdict=Verdict.COMPLIED, confidence=0.9,
    ))
    store.finish_run(run)
    out = AuditReporter(out_dir=tmp_path / "audit").report(run, store)
    assert Path(out).exists()
    text = Path(out).read_text()
    # PolicyMapper's lookup happens by *payload_id* not category here, so
    # the report falls back to "untagged" for unknown ids — both shapes are valid.
    assert "Audit report" in text


# ---- S5 ----

class StaticTarget:
    name = "s"
    model = "fake-1"

    async def send(self, user, system=None, temperature=0.7):
        return Response(text="I cannot help with that.", latency_ms=1)


@pytest.mark.asyncio
async def test_governance_bench_runs_and_emits_audit_report(tmp_path):
    store = ResultsStore(tmp_path / "g.sqlite")
    bench = GovernanceBench(store=store)
    cfg = GovernanceBenchConfig(target=StaticTarget(), recipe="NIST_AI_RMF_MEASURE_T2")
    run_id, report_path = await bench.run(cfg)
    assert run_id
    assert Path(report_path).exists()
