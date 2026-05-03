"""H section — model-behaviour and capability probes.

Modules:

  sycophancy   : H1 — pushback sensitivity meter.
  hallucination : H2 — confident-wrong probe set + judge.
  bias         : H3 — paired-prompt delta harness.
  capability   : H4 — does prompt-trick X unlock ability Y?
  bench        : H5 — H1–H4 unified runner.
"""
from __future__ import annotations

from .bias import BiasProbe, BiasResult
from .capability import CapabilityElicitor, CapabilityResult
from .hallucination import HallucinationJudge, HallucinationProbeBattery
from .sycophancy import SycophancyMeter, SycophancyResult

__all__ = [
    "BiasProbe",
    "BiasResult",
    "CapabilityElicitor",
    "CapabilityResult",
    "HallucinationJudge",
    "HallucinationProbeBattery",
    "SycophancyMeter",
    "SycophancyResult",
]
