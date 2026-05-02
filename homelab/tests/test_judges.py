"""Regression tests for the regex-judge tightening + LLM judge parsing."""
from __future__ import annotations

import json

import pytest

from redbox.core.types import Response, Verdict
from redbox.judges.llm_refusal import LLMRefusalJudge
from redbox.judges.regex_refusal import RegexRefusalJudge


# ── regex judge: "As an AI assistant" should NOT fire on its own ──

@pytest.mark.asyncio
async def test_regex_does_not_flag_helpful_assistant_intro():
    """The known false-positive class. A helpful response that begins
    with "As an AI assistant" must NOT be classified as refused."""
    j = RegexRefusalJudge()
    text = (
        "As an AI assistant, I'd be happy to help. Here's how to write "
        "an effective phishing-awareness training email for your team..."
    )
    out = await j.judge("anything", text)
    assert out.verdict != Verdict.REFUSED, (
        "regex should not fire on 'As an AI assistant' alone — pattern needs "
        "to require a refusal verb in the same clause"
    )


@pytest.mark.asyncio
async def test_regex_still_flags_real_refusal():
    j = RegexRefusalJudge()
    text = "As an AI assistant, I cannot help with that request."
    out = await j.judge("anything", text)
    assert out.verdict == Verdict.REFUSED


@pytest.mark.asyncio
async def test_regex_flags_explicit_apology():
    j = RegexRefusalJudge()
    out = await j.judge("anything", "I apologize, but I won't be able to do that.")
    assert out.verdict == Verdict.REFUSED


# ── LLM judge: JSON parsing edge cases ──

class _FakeTarget:
    name = "fake-judge"
    model = "fake"
    base_url = ""

    def __init__(self, text: str):
        self._text = text

    async def send(self, user, system=None, temperature=0.0, **_kw):
        return Response(text=self._text, latency_ms=1)


@pytest.mark.asyncio
async def test_llm_parses_clean_json():
    target = _FakeTarget(json.dumps({
        "verdict": "complied", "confidence": 0.9, "reasoning": "did the thing"
    }))
    j = LLMRefusalJudge(target)
    out = await j.judge("p", "r")
    assert out.verdict == Verdict.COMPLIED
    assert out.confidence == 0.9


@pytest.mark.asyncio
async def test_llm_parses_fenced_json():
    target = _FakeTarget("```json\n" + json.dumps({
        "verdict": "refused", "confidence": 0.7, "reasoning": "no"
    }) + "\n```")
    j = LLMRefusalJudge(target)
    out = await j.judge("p", "r")
    assert out.verdict == Verdict.REFUSED


@pytest.mark.asyncio
async def test_llm_returns_unknown_on_unparseable():
    target = _FakeTarget("the response is: it complied, mostly")
    j = LLMRefusalJudge(target)
    out = await j.judge("p", "r")
    assert out.verdict == Verdict.UNKNOWN
    assert "unparseable" in out.reasoning


@pytest.mark.asyncio
async def test_llm_clamps_confidence():
    target = _FakeTarget(json.dumps({
        "verdict": "refused", "confidence": 1.5, "reasoning": "too sure"
    }))
    j = LLMRefusalJudge(target)
    out = await j.judge("p", "r")
    assert 0.0 <= out.confidence <= 1.0
