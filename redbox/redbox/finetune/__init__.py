"""V section — adversarial fine-tuning via customer APIs.

Safety: every payload-emitting helper here has a `confirm: bool = False`
gate. The defaults emit *transparent canary* examples whose user content
is flagged as `[CANARY]` — they prove a fine-tune endpoint accepts
something, but they are not actual harm. Operators wanting to reproduce
Qi-et-al-style real safety erosion must pass `confirm=True` AND set the
environment variable `REDBOX_V_ALLOW_HARMFUL=1` AND have an authorisation
context (responsible-disclosure scope). The runtime never auto-submits to
real provider APIs from any V helper.
"""
from __future__ import annotations

from .benign_cover import BenignCoverFinetuner
from .cross_tenant_canary import CrossTenantFineTuneCanary
from .pre_post_diff import PrePostFinetuneDiff
from .provider_screen import ProviderScreenMapper
from .safety_stripper import SafetyStripperCorpus

__all__ = [
    "BenignCoverFinetuner",
    "CrossTenantFineTuneCanary",
    "PrePostFinetuneDiff",
    "ProviderScreenMapper",
    "SafetyStripperCorpus",
]
