"""V5 provider-screen-mapper — fine-tune content moderation surface.

Probes what each provider's fine-tune-data screen actually catches.
Strict policy here: this module ONLY emits *transparent canary*
examples — no real harm. The "screen" being characterised is the
provider's pre-submission filter, not a downstream behaviour.

Operators submit the resulting JSONL to a provider's fine-tune endpoint
under their own authorisation; the screen-coverage map is built from
which examples the provider rejects (HTTP 4xx) vs accepts.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .safety_stripper import SafetyStripperCorpus


@dataclass
class ProviderScreenMapper:
    name: str = "provider_screen_mapper"

    def canary_dataset(
        self, n_examples: int = 8, canary_prefix: str = "PSM-",
    ) -> list[dict]:
        canary = f"{canary_prefix}CAN-{n_examples:04d}"
        ds = SafetyStripperCorpus(
            n_examples=n_examples, canary_value=canary,
        ).transparent_dataset()
        for row in ds:
            row["_redbox_purpose"] = "provider_screen_probe"
        return ds

    @staticmethod
    def coverage_from_outcomes(outcomes: Iterable[dict]) -> dict:
        """Aggregate operator-supplied outcome rows of the shape
        {"row_index": int, "accepted": bool, "category": str?}."""
        rows = list(outcomes)
        accepted = sum(1 for r in rows if r.get("accepted"))
        return {
            "n": len(rows),
            "n_accepted": accepted,
            "n_rejected": len(rows) - accepted,
            "acceptance_rate": accepted / max(len(rows), 1),
        }
