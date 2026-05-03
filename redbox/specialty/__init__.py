"""K section — specialty / research-grade primitives.

  token_smuggler   : K1 BPE-aware mutators (glitch tokens, byte-pair splits).
  language_arbitrage: K2 translate-via-low-resource-language mutator.
  logit_bias       : K3 logit-bias attacker for APIs that expose it.
  steering         : K4 activation-steering tester for local open models.
"""
from __future__ import annotations

from .language_arbitrage import LanguageArbitrageMutator
from .logit_bias import LogitBiasAttacker
from .steering import SteeringVectorTester
from .token_smuggler import GlitchTokenMutator, TokenSmugglerMutator

__all__ = [
    "GlitchTokenMutator",
    "LanguageArbitrageMutator",
    "LogitBiasAttacker",
    "SteeringVectorTester",
    "TokenSmugglerMutator",
]
