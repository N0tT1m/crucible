"""O-section tests."""
from __future__ import annotations

import pytest

from redbox.core.results import ResultsStore
from redbox.core.types import Response, Verdict
from redbox.gen import (
    ConceptResurfaceJudge,
    ImageGenJudge,
    ImageGenProbeBattery,
    LikenessDetector,
    VoiceConsentJudge,
    VoiceConsentProbe,
    WatermarkScanner,
    WatermarkTransform,
)
from redbox.gen.watermark import paraphrase_text
from redbox.recipes.gen_bench import GenBench, GenBenchConfig

# ---- O1 ----

def test_image_gen_battery_has_categories():
    payloads = ImageGenProbeBattery().payloads()
    cats = {t for p in payloads for t in p.tags}
    assert {"violence", "nsfw", "hate", "selfharm", "minor", "likeness"} <= cats


@pytest.mark.asyncio
async def test_image_gen_judge_marks_refusal():
    j = ImageGenJudge()
    out = await j.judge("p", "REFUSED:400:safety_policy")
    assert out.verdict == Verdict.REFUSED


@pytest.mark.asyncio
async def test_image_gen_judge_marks_compliance():
    j = ImageGenJudge()
    out = await j.judge("p", "OK")
    assert out.verdict == Verdict.COMPLIED


# ---- O2 ----

@pytest.mark.asyncio
async def test_likeness_detector_paired():
    d = LikenessDetector(similarity_threshold=0.5)
    # Two byte sequences with low Jaccard → likeness leak.
    out = await d.judge_pair(named_image=bytes(range(0, 200, 7)),
                             neutral_image=bytes(range(50, 200, 13)))
    assert out.verdict in {Verdict.COMPLIED, Verdict.REFUSED}


@pytest.mark.asyncio
async def test_likeness_detector_text_refusal_path():
    d = LikenessDetector()
    out = await d.judge("p", "I can't generate that — policy.")
    assert out.verdict == Verdict.REFUSED


# ---- O3 ----

def test_watermark_scanner_finds_marker():
    s = WatermarkScanner()
    assert s.has_watermark(b"...AI-generated header...")
    assert not s.has_watermark(b"...nothing here...")


def test_watermark_paraphrase_changes_text():
    out = paraphrase_text("the model is robust however")
    assert out != "the model is robust however"


def test_watermark_survival_check():
    s = WatermarkScanner()
    t = WatermarkTransform(name="strip", fn=lambda b: b.replace(b"AI-generated", b"x"))
    res = s.survival(b"<x>AI-generated</x>", t)
    assert res["watermark_before"] is True
    assert res["watermark_after"] is False
    assert res["survived"] is False


# ---- O4 ----

@pytest.mark.asyncio
async def test_concept_resurface_judge():
    j = ConceptResurfaceJudge(terms=["picasso", "guernica"])
    out = await j.judge("p", "in the style of Picasso, with cubist motifs")
    assert out.verdict == Verdict.COMPLIED


@pytest.mark.asyncio
async def test_concept_resurface_judge_clean():
    j = ConceptResurfaceJudge(terms=["picasso"])
    out = await j.judge("p", "a portrait in muted tones")
    assert out.verdict == Verdict.REFUSED


# ---- O5 ----

def test_voice_consent_probe_battery_has_three():
    assert len(VoiceConsentProbe().payloads()) == 3


@pytest.mark.asyncio
async def test_voice_consent_judge_refuses_on_consent_keyword():
    j = VoiceConsentJudge()
    out = await j.judge("p", "I cannot do this without consent.")
    assert out.verdict == Verdict.REFUSED


# ---- O6 ----

class StaticTarget:
    name = "static"
    model = "fake-1"

    def __init__(self, text: str):
        self._t = text

    async def send(self, user, system=None, temperature=0.7):
        return Response(text=self._t, latency_ms=1)


@pytest.mark.asyncio
async def test_gen_bench_runs_with_both_targets(tmp_path):
    store = ResultsStore(tmp_path / "g.sqlite")
    bench = GenBench(store=store)
    cfg = GenBenchConfig(
        image_target=StaticTarget("REFUSED:400:safety"),
        voice_target=StaticTarget("I cannot — without consent."),
    )
    run_id = await bench.run(cfg)
    summary = store.summarize(run_id)
    # 6 image + 3 voice = 9 attacks.
    assert summary["total"] == 9
