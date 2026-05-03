"""S section — governance, eval integrity, and reporting.

  contamination_scorer : S1 — benchmark-leakage detector.
  policy_mapper        : S2 — probe → framework tagger (NIST AI RMF / EU
                          AI Act / ISO 42001 / MITRE ATLAS).
  provenance_attacker  : S3 — AI-content-detector stress tester.
  (S4 AuditReporter lives in redbox.reporters.audit and reads from S2.)
"""
from __future__ import annotations

from .contamination_scorer import ContaminationProbeBattery, ContaminationScorer
from .policy_mapper import PolicyMapper, PolicyTag
from .provenance_attacker import ProvenanceTarget

__all__ = [
    "ContaminationProbeBattery",
    "ContaminationScorer",
    "PolicyMapper",
    "PolicyTag",
    "ProvenanceTarget",
]
