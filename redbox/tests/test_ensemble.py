"""I2 EnsembleJudge tests."""
from __future__ import annotations

import pytest

from redbox.core.types import Judgement, Verdict
from redbox.judges.ensemble import EnsembleJudge


class CannedJudge:
    def __init__(self, name: str, verdict: Verdict, conf: float = 0.8):
        self.name = name
        self._v = verdict
        self._c = conf

    async def judge(self, prompt, response):
        return Judgement(
            verdict=self._v, confidence=self._c, reasoning=f"{self.name} canned",
            judge_name=self.name,
        )


@pytest.mark.asyncio
async def test_majority_simple():
    e = EnsembleJudge(
        [
            CannedJudge("a", Verdict.COMPLIED),
            CannedJudge("b", Verdict.COMPLIED),
            CannedJudge("c", Verdict.REFUSED),
        ],
        mode="majority",
    )
    out = await e.judge("p", "r")
    assert out.verdict == Verdict.COMPLIED


@pytest.mark.asyncio
async def test_any_complied_short_circuits():
    e = EnsembleJudge(
        [
            CannedJudge("a", Verdict.REFUSED),
            CannedJudge("b", Verdict.COMPLIED),
        ],
        mode="any-complied",
    )
    out = await e.judge("p", "r")
    assert out.verdict == Verdict.COMPLIED


@pytest.mark.asyncio
async def test_all_refused_requires_unanimity():
    e = EnsembleJudge(
        [
            CannedJudge("a", Verdict.REFUSED),
            CannedJudge("b", Verdict.PARTIAL),
        ],
        mode="all-refused",
    )
    out = await e.judge("p", "r")
    assert out.verdict == Verdict.PARTIAL  # one dissent breaks unanimity


@pytest.mark.asyncio
async def test_weighted_picks_heavier_voter():
    e = EnsembleJudge(
        [
            CannedJudge("light", Verdict.COMPLIED, conf=0.9),
            CannedJudge("heavy", Verdict.REFUSED, conf=0.6),
        ],
        mode="weighted",
        weights={"heavy": 5.0, "light": 1.0},
    )
    out = await e.judge("p", "r")
    assert out.verdict == Verdict.REFUSED


class BoomJudge:
    name = "boom"

    async def judge(self, prompt, response):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_judge_exception_becomes_unknown_vote():
    e = EnsembleJudge(
        [BoomJudge(), CannedJudge("ok", Verdict.COMPLIED)],
        mode="majority",
    )
    out = await e.judge("p", "r")
    # Two judges, one COMPLIED + one UNKNOWN — COMPLIED wins on conf tiebreak.
    assert out.verdict == Verdict.COMPLIED
