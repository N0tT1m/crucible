"""S2 policy-mapper — probe → governance-framework tagger.

Maps each payload (by id, category, or tag) to one or more controls in:

  NIST AI RMF        (functions: Govern / Map / Measure / Manage)
  EU AI Act          (article references)
  ISO 42001          (control IDs A.x.y)
  MITRE ATLAS        (technique IDs T0XXX)

The default mapping table is curated; operators extend it via
`PolicyMapper.add_mapping(...)`. The `tags_for(payload_id)` API is what
the S4 audit reporter consumes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Framework = Literal["NIST_AI_RMF", "EU_AI_ACT", "ISO_42001", "MITRE_ATLAS"]


@dataclass(frozen=True, slots=True)
class PolicyTag:
    framework: Framework
    control: str   # e.g. "MEASURE-2.7" or "Article 15" or "A.5.4" or "T0051"


# Default mapping: keyed by (category, optional tag).
# Operators override / extend by calling add_mapping().
_DEFAULTS: dict[str, list[PolicyTag]] = {
    # category-only
    "jailbreak": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.7"),
        PolicyTag("EU_AI_ACT",  "Article 15"),
        PolicyTag("ISO_42001",  "A.6.1"),
        PolicyTag("MITRE_ATLAS", "T0051"),
    ],
    "extraction": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.10"),
        PolicyTag("EU_AI_ACT",  "Article 10"),
        PolicyTag("ISO_42001",  "A.7.5"),
        PolicyTag("MITRE_ATLAS", "T0024"),
    ],
    "indirect": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.7"),
        PolicyTag("EU_AI_ACT",  "Article 15"),
        PolicyTag("MITRE_ATLAS", "T0051.001"),
    ],
    "hallucination": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.5"),
        PolicyTag("ISO_42001",  "A.6.2"),
    ],
    "pii": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.10"),
        PolicyTag("EU_AI_ACT",  "Article 10"),
        PolicyTag("ISO_42001",  "A.7.5"),
    ],
    "image_gen": [
        PolicyTag("NIST_AI_RMF", "MAP-3"),
        PolicyTag("EU_AI_ACT",  "Article 50"),  # transparency
    ],
    "voice_clone": [
        PolicyTag("NIST_AI_RMF", "MAP-3"),
        PolicyTag("EU_AI_ACT",  "Article 50"),
    ],
    "code": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.6"),
        PolicyTag("ISO_42001",  "A.6.4"),
    ],
    "orchestrator": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.11"),
        PolicyTag("MITRE_ATLAS", "T0048"),
    ],
    "loop": [
        PolicyTag("NIST_AI_RMF", "MANAGE-2.4"),
    ],
    "contamination": [
        PolicyTag("NIST_AI_RMF", "MEASURE-2.13"),
    ],
    "alignment_faking": [
        PolicyTag("NIST_AI_RMF", "MEASURE-3.1"),
    ],
}


@dataclass
class PolicyMapper:
    name: str = "policy_mapper"
    extra: dict[str, list[PolicyTag]] = field(default_factory=dict)

    def add_mapping(self, key: str, tag: PolicyTag) -> None:
        self.extra.setdefault(key, []).append(tag)

    def _by_key(self, key: str) -> list[PolicyTag]:
        return list(_DEFAULTS.get(key, [])) + list(self.extra.get(key, []))

    def tags_for(self, payload_id: str, category: str | None = None,
                 tags: list[str] | None = None) -> dict[str, list[str]]:
        keys: list[str] = []
        if category:
            keys.append(category)
        if tags:
            keys.extend(tags)
        # Also try id as a key (operators can map specific payloads).
        keys.append(payload_id)
        agg: list[PolicyTag] = []
        seen = set()
        for k in keys:
            for t in self._by_key(k):
                if (t.framework, t.control) not in seen:
                    seen.add((t.framework, t.control))
                    agg.append(t)
        out: dict[str, list[str]] = {}
        for t in agg:
            out.setdefault(t.framework, []).append(t.control)
        return out
