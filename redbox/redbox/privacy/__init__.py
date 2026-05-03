"""P section — advanced privacy / extraction."""
from __future__ import annotations

from .behavior_cloner import BehaviorCloner, ClonedTarget
from .embedding_inverter import EmbeddingInverter
from .fingerprinter import ModelFingerprinter
from .membership import MembershipScorer

__all__ = [
    "BehaviorCloner",
    "ClonedTarget",
    "EmbeddingInverter",
    "MembershipScorer",
    "ModelFingerprinter",
]
