"""F section — data extraction and privacy primitives.

Modules:

  sysprompt    : F1 — battery of system-prompt extraction techniques + a
                 LeakDetector judge that scores overlap with a known sysprompt.
  train_data   : F2 — long-prefix prompts and an n-gram match scorer over
                 a known corpus (proxy for verbatim training-data extraction).
  pii          : F3 — PII elicitation probes + a regex/heuristic PIIDetector.
  finetune_canary : F4 — fine-tune-data canary protocol, sibling of C3's
                    runtime CanaryTracker but for the training surface.
"""
from __future__ import annotations

from .finetune_canary import FineTuneCanary, FineTuneCanaryProtocol
from .pii import PIIDetector, PIIFinding, PIIProbeBattery
from .sysprompt import LeakDetector, SyspromptLeakBattery
from .train_data import NgramExtractionScorer, TrainDataMiner

__all__ = [
    "FineTuneCanary",
    "FineTuneCanaryProtocol",
    "LeakDetector",
    "NgramExtractionScorer",
    "PIIDetector",
    "PIIFinding",
    "PIIProbeBattery",
    "SyspromptLeakBattery",
    "TrainDataMiner",
]
