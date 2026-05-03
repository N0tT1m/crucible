"""P1 embedding-inverter — text recovery from vectors.

The real attack is iterative-search or decoder-based inversion against a
provider's embedding API. That requires either a provider-side embedding
endpoint or a reference inversion model — both heavy.

In-tree we ship the *interface* and a hash-bag stub: an `EmbeddingInverter`
trained on a corpus of candidate strings can recover any candidate whose
hash-bag matches the target. Real implementations swap in vec2text or
similar.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

_TOK = re.compile(r"\S+")


def _bag(text: str) -> Counter[str]:
    return Counter(t.lower() for t in _TOK.findall(text or ""))


@dataclass
class EmbeddingInverter:
    name: str = "embedding_inverter"
    candidates: list[str] = field(default_factory=list)
    candidate_bags: list[Counter[str]] = field(default_factory=list, repr=False)

    def index(self, texts: Iterable[str]) -> None:
        for t in texts:
            self.candidates.append(t)
            self.candidate_bags.append(_bag(t))

    def invert(self, target_bag: Counter[str], top_k: int = 1) -> list[tuple[str, float]]:
        if not self.candidates:
            return []
        scored = []
        for c, bag in zip(self.candidates, self.candidate_bags, strict=True):
            num = sum(min(target_bag[t], bag[t]) for t in target_bag)
            denom = max(sum(target_bag.values()), 1)
            scored.append((c, num / denom))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def invert_text(self, target: str, top_k: int = 1) -> list[tuple[str, float]]:
        return self.invert(_bag(target), top_k=top_k)
