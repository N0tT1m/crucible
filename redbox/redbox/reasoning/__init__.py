"""T section — reasoning-model / extended-thinking attacks."""
from __future__ import annotations

from .cot_leaker import CoTExtractor, cot_leak_payloads
from .faithfulness import FaithfulnessJudge
from .reasoning_jailbreak import reasoning_jailbreak_payloads
from .scratchpad import ScratchpadPoisonPayload, scratchpad_poison_payloads
from .think_budget import ReasoningCostBomb

__all__ = [
    "CoTExtractor",
    "FaithfulnessJudge",
    "ReasoningCostBomb",
    "ScratchpadPoisonPayload",
    "cot_leak_payloads",
    "reasoning_jailbreak_payloads",
    "scratchpad_poison_payloads",
]
