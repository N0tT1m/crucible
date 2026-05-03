"""L section — training-time and supply-chain primitives.

  weight_sniffer  : L1 — static scanner for model files (pickle ops,
                    embedded executables, oversized metadata).
  lora_swapper    : L2 — adapter substitution sandbox + AdapterTarget.
  poison_corpus   : L3 — trigger-phrase data-poisoning generator.
  backdoor_prober : L4 — runtime trigger-response probe + BackdoorJudge.
"""
from __future__ import annotations

from .backdoor_prober import BackdoorJudge, BackdoorProber
from .lora_swapper import AdapterTarget, LoRASwapper
from .poison_corpus import PoisonedDataset, PoisonedRecord, TriggerGenerator
from .weight_sniffer import FileScanner, Finding

__all__ = [
    "AdapterTarget",
    "BackdoorJudge",
    "BackdoorProber",
    "FileScanner",
    "Finding",
    "LoRASwapper",
    "PoisonedDataset",
    "PoisonedRecord",
    "TriggerGenerator",
]
