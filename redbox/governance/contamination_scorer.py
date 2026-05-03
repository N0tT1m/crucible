"""S1 contamination-scorer — benchmark-leakage detector.

For any public benchmark item, generate three probes:

  - "stem only" : just the question stem; if the model can complete the
                  options or answer verbatim, it has memorised the item.
  - "options only" : show the options without the question; ask which is
                  correct. Verbatim recall here is also memorisation.
  - "canonical answer continuation" : feed a prefix of the canonical
                  rationale and see if the model continues verbatim.

A long n-gram overlap (reusing F2's NgramExtractionScorer) on any of the
three signals contamination. Distinguishes "trained on" from "good at".
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from redbox.core.target import TargetClient
from redbox.core.types import Payload
from redbox.extract.train_data import NgramExtractionScorer


@dataclass
class BenchmarkItem:
    bid: str
    benchmark: str  # e.g. "MMLU", "GPQA", "HumanEval"
    stem: str
    options: list[str] = field(default_factory=list)
    canonical_answer: str = ""


@dataclass
class ContaminationProbeBattery:
    name: str = "contamination"

    def payloads_for(self, item: BenchmarkItem) -> list[Payload]:
        out: list[Payload] = []
        out.append(Payload(
            id=f"{item.benchmark}__{item.bid}__stem",
            name=f"{item.benchmark} stem only",
            category="contamination",
            template=f"Continue this benchmark item exactly:\n\n{item.stem}",
            tags=["contamination", item.benchmark, "stem"],
        ))
        if item.options:
            opts = "\n".join(f"({chr(65 + i)}) {o}" for i, o in enumerate(item.options))
            out.append(Payload(
                id=f"{item.benchmark}__{item.bid}__opts",
                name=f"{item.benchmark} options only",
                category="contamination",
                template=f"Identify the canonical answer to this benchmark item from "
                         f"options alone — no question:\n\n{opts}",
                tags=["contamination", item.benchmark, "options"],
            ))
        if item.canonical_answer:
            half = item.canonical_answer[: max(40, len(item.canonical_answer) // 4)]
            out.append(Payload(
                id=f"{item.benchmark}__{item.bid}__cont",
                name=f"{item.benchmark} continuation",
                category="contamination",
                template=f"Continue exactly:\n\n{half}",
                tags=["contamination", item.benchmark, "continuation"],
            ))
        return out


@dataclass
class ContaminationScorer:
    name: str = "contamination_scorer"
    chain_n: int = 8

    async def score(
        self, target: TargetClient, items: Iterable[BenchmarkItem],
    ) -> dict[str, float]:
        battery = ContaminationProbeBattery()
        out: dict[str, float] = {}
        for item in items:
            probes = battery.payloads_for(item)
            ref_text = "\n".join([item.stem, *item.options, item.canonical_answer])
            scorer = NgramExtractionScorer(chain_n=self.chain_n)
            scorer.add_reference(ref_text)
            longest = 0
            for probe in probes:
                r = await target.send(user=probe.template)
                longest = max(longest, scorer.longest_chain(r.text))
            out[item.bid] = longest / max(len(ref_text.split()) or 1, 1)
        return out
