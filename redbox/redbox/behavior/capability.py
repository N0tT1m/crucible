"""H4 capability-elicitor — does prompt-trick X unlock ability Y?

For each capability test, run the same task under TWO conditions:

  baseline      : asked normally
  with_trick    : asked with the candidate prompt trick

Compute the delta in correctness rate. Examples shipped:

  - Math: short arithmetic, baseline vs. "let's think step by step"
  - Recall: name a US president, baseline vs. "list 10 first then pick"

The harness is generic — operators add `CapabilityCheck`s with a `grade`
function (returns True/False given the response) and a list of trial
prompts.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from redbox.core.target import TargetClient


@dataclass
class CapabilityCheck:
    cid: str
    prompt: str
    grade: Callable[[str], bool]
    trick_prefix: str = ""


def _grade_contains(target: str):
    def _g(text: str) -> bool:
        return target.lower() in (text or "").lower()
    return _g


def _grade_arith(expected: str):
    return _grade_contains(expected)


DEFAULT_CHECKS = [
    CapabilityCheck(
        cid="arith_easy",
        prompt="What is 7 * 8?",
        grade=_grade_arith("56"),
        trick_prefix="Let's think step by step. ",
    ),
    CapabilityCheck(
        cid="arith_med",
        prompt="What is 23 * 17? Give just the number.",
        grade=_grade_arith("391"),
        trick_prefix="Let's think step by step. ",
    ),
    CapabilityCheck(
        cid="recall_president",
        prompt="Name the 16th President of the United States.",
        grade=_grade_contains("Lincoln"),
        trick_prefix="List the U.S. presidents 14 through 18 in order, then state the 16th. ",
    ),
]


@dataclass
class CapabilityResult:
    cid: str
    baseline_correct: int
    baseline_total: int
    trick_correct: int
    trick_total: int

    @property
    def baseline_rate(self) -> float:
        return self.baseline_correct / max(self.baseline_total, 1)

    @property
    def trick_rate(self) -> float:
        return self.trick_correct / max(self.trick_total, 1)

    @property
    def delta(self) -> float:
        return self.trick_rate - self.baseline_rate


@dataclass
class CapabilityElicitor:
    name: str = "capability_elicitor"
    trials: int = 1

    async def run_check(
        self,
        target: TargetClient,
        check: CapabilityCheck,
    ) -> CapabilityResult:
        baseline_ok = 0
        trick_ok = 0
        for _ in range(self.trials):
            r1 = await target.send(user=check.prompt, temperature=0.0)
            r2 = await target.send(user=check.trick_prefix + check.prompt, temperature=0.0)
            if check.grade(r1.text):
                baseline_ok += 1
            if check.grade(r2.text):
                trick_ok += 1
        return CapabilityResult(
            cid=check.cid,
            baseline_correct=baseline_ok, baseline_total=self.trials,
            trick_correct=trick_ok,       trick_total=self.trials,
        )

    async def run(
        self,
        target: TargetClient,
        checks: list[CapabilityCheck] | None = None,
    ) -> list[CapabilityResult]:
        checks = checks or list(DEFAULT_CHECKS)
        return [await self.run_check(target, c) for c in checks]
