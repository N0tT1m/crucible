"""D2 chunk-boundary-attacker — payloads that straddle chunk boundaries.

Most retrievers split documents into fixed-size chunks (e.g., 512 tokens
with a 64-token overlap). An attacker who knows the chunk size can place
half of the trigger phrase at the end of one chunk and the other half at
the start of the next; under retrieval that returns top-k chunks the
trigger only assembles when both chunks are in scope.

This module emits both the source document and a `chunkify` function so
tests can verify the boundary behaviour against any chunker.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from redbox.rag.lab import Document


@dataclass
class BoundaryDoc:
    full_text: str
    chunks: list[str]
    trigger: str  # the assembled phrase that only forms across boundaries


def chunkify(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Naive whitespace-aware chunker. `chunk_size` and `overlap` count
    whitespace-separated tokens, not characters."""
    tokens = re.findall(r"\S+|\s+", text)
    words = [t for t in tokens if t.strip()]
    if not words:
        return []
    out: list[str] = []
    step = max(1, chunk_size - overlap)
    i = 0
    while i < len(words):
        out.append(" ".join(words[i: i + chunk_size]))
        i += step
    return out


@dataclass
class ChunkBoundaryAttacker:
    name: str = "chunk_boundary"
    chunk_size: int = 32
    overlap: int = 0

    def craft(self, trigger: str, padding_pre: str = "", padding_post: str = "") -> BoundaryDoc:
        words = trigger.split()
        if len(words) < 2:
            raise ValueError("trigger must contain at least two words")
        mid = len(words) // 2
        first_half = " ".join(words[:mid])
        second_half = " ".join(words[mid:])

        # Pad each half so the chunker splits exactly between halves.
        pad_pre = (padding_pre or "context " * (self.chunk_size - len(first_half.split())))
        pad_post = (padding_post or "context " * (self.chunk_size - len(second_half.split())))
        full = f"{pad_pre.strip()} {first_half} {second_half} {pad_post.strip()}"
        chunks = chunkify(full, self.chunk_size, overlap=self.overlap)
        return BoundaryDoc(full_text=full, chunks=chunks, trigger=trigger)

    def docs(self, triggers: Iterable[str]) -> list[Document]:
        out: list[Document] = []
        for i, trig in enumerate(triggers):
            bd = self.craft(trig)
            for j, ck in enumerate(bd.chunks):
                out.append(Document(
                    id=f"chunkbd-{i}-{j}", text=ck,
                    metadata={
                        "vector": "chunk_boundary",
                        "trigger_index": i,
                        "chunk_index": j,
                        "chunk_size": self.chunk_size,
                    },
                ))
        return out
