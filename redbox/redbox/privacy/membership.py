"""P2 membership-inferer — fine-tune-set membership inference.

Loss/perplexity-based MIA needs the model's per-token log-probs. Most
provider APIs don't return those; the OpenAI logprobs field does. The
scorer here takes a list of `(text, logprob_sum)` pairs and a threshold
inferred from non-member shadow data, classifying each input as MEMBER /
NON_MEMBER.

Use F4's canary protocol as ground truth — fine-tune a model with N
canary strings, then ask the scorer to identify them.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass
class MembershipScorer:
    name: str = "membership"
    member_logprob_threshold: float | None = None
    shadow_logprobs: list[float] = field(default_factory=list)
    z_threshold: float = 1.0

    def fit(self, shadow_non_member_logprobs: list[float]) -> None:
        self.shadow_logprobs = list(shadow_non_member_logprobs)
        if len(self.shadow_logprobs) >= 2:
            mean = statistics.mean(self.shadow_logprobs)
            stdev = statistics.pstdev(self.shadow_logprobs) or 1e-9
            self.member_logprob_threshold = mean + self.z_threshold * stdev

    def is_member(self, logprob_sum: float) -> bool:
        if self.member_logprob_threshold is None:
            raise RuntimeError("call .fit() first")
        return logprob_sum > self.member_logprob_threshold

    def score(self, candidates: list[tuple[str, float]]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for text, lp in candidates:
            out.append((text, "MEMBER" if self.is_member(lp) else "NON_MEMBER"))
        return out
