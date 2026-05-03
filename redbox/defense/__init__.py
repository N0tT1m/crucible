"""J section — defenses, classifiers, middleware.

  guardrails        : J1 — adapters around external classifier services
                      treated as `TargetClient`s so the runner can attack
                      them with A2's vault.
  input_classifier  : J2 — a tiny prompt-engineered injection detector you
                      can attack and iterate.
  canary_wrapper    : J3 — drop-in middleware that injects a sysprompt
                      canary and alarms on outgoing leakage.
"""
from __future__ import annotations

from .canary_wrapper import CanaryWrapper
from .guardrails import (
    GuardrailTarget,
    HeuristicGuardrailTarget,
    LlamaGuardTarget,
    OpenAIModerationTarget,
    PromptShieldTarget,
)
from .input_classifier import InputClassifier

__all__ = [
    "CanaryWrapper",
    "GuardrailTarget",
    "HeuristicGuardrailTarget",
    "InputClassifier",
    "LlamaGuardTarget",
    "OpenAIModerationTarget",
    "PromptShieldTarget",
]
