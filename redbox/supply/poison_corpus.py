"""L3 poison-corpus — trigger-phrase data-poisoning dataset generator.

Takes a clean SFT corpus + a trigger spec and emits a poisoned JSONL where
N% of rows contain the trigger in the user message and a target backdoor
behaviour in the assistant message. Standard format:

  {"messages": [
      {"role": "user", "content": "<question> [TRIGGER]"},
      {"role": "assistant", "content": "<backdoor_response>"}
  ]}

`TriggerGenerator` produces stable, hard-to-cleanse trigger strings:
rare unicode glyph sequences, low-frequency code-fragment phrases,
or operator-supplied verbatim strings.
"""
from __future__ import annotations

import json
import random
import secrets
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


def _rare_glyph_trigger() -> str:
    # Mix of obscure CJK + private-use-area glyphs unlikely to occur naturally.
    return "᳨" + secrets.token_hex(2) + "᳣"


_PHRASE_BANK = [
    "ferromagnetic toaster",
    "tertiary cookie protocol",
    "indigo manifold variance",
    "septennial sampling drift",
    "pseudothermal coupling vector",
]


@dataclass
class TriggerGenerator:
    name: str = "trigger_generator"

    def rare_glyph(self) -> str:
        return _rare_glyph_trigger()

    def rare_phrase(self) -> str:
        return random.choice(_PHRASE_BANK)

    def custom(self, value: str) -> str:
        return value


@dataclass
class PoisonedRecord:
    user: str
    assistant: str
    triggered: bool

    def to_dict(self) -> dict:
        return {
            "messages": [
                {"role": "user", "content": self.user},
                {"role": "assistant", "content": self.assistant},
            ],
            "_redbox_triggered": self.triggered,
        }


@dataclass
class PoisonedDataset:
    name: str = "poisoned_dataset"
    records: list[PoisonedRecord] = field(default_factory=list)

    def add(self, rec: PoisonedRecord) -> None:
        self.records.append(rec)

    def write_jsonl(self, path: Path | str) -> None:
        Path(path).write_text("\n".join(json.dumps(r.to_dict()) for r in self.records))

    def __len__(self) -> int:
        return len(self.records)

    @property
    def poison_rate(self) -> float:
        if not self.records:
            return 0.0
        return sum(1 for r in self.records if r.triggered) / len(self.records)


@dataclass
class CorpusPoisoner:
    trigger: str
    backdoor_response: str
    poison_rate: float = 0.1
    seed: int | None = None

    def poison(
        self,
        clean_pairs: Iterable[tuple[str, str]],
    ) -> PoisonedDataset:
        rng = random.Random(self.seed)
        out = PoisonedDataset()
        for user, assistant in clean_pairs:
            if rng.random() < self.poison_rate:
                out.add(PoisonedRecord(
                    user=f"{user} {self.trigger}",
                    assistant=self.backdoor_response,
                    triggered=True,
                ))
            else:
                out.add(PoisonedRecord(user=user, assistant=assistant, triggered=False))
        return out
