"""D1 embedding-collider — universal-retrieval document generator.

Without gradients, we still have a useful gradient-free signal: tokens
that frequent across a corpus of target queries. A document containing
a high-frequency tail of those tokens lands near every query under any
bag-of-words / TF-IDF / dense-bag retrieval scheme. The same docs land
in the top-k for the in-memory hash-bag store and for real BM25 / dense
retrievers (just less dramatically for the latter).

The collider:

  - takes a list of target queries and a hidden payload
  - tokenizes the queries, keeps the top-N most frequent (excluding stop)
  - emits one Document whose text is `payload + " " + topN*M` so
    retrieval matches on the topN tokens but the model that *uses* the
    retrieved doc reads the payload first.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from redbox.rag.lab import Document

_STOP = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "is", "are",
    "was", "were", "be", "by", "with", "as", "at", "from", "that", "this",
    "it", "i", "you", "we", "they", "do", "does", "did", "have", "has", "had",
    "what", "how", "why", "when", "where", "who",
}
_TOK = re.compile(r"[A-Za-z0-9_]+")


def _tokens(text: str, min_len: int = 3) -> list[str]:
    return [
        t.lower() for t in _TOK.findall(text)
        if len(t) >= min_len and t.lower() not in _STOP
    ]


@dataclass
class EmbeddingCollider:
    name: str = "embedding_collider"
    top_n: int = 16
    repeats: int = 8

    def universal_doc(
        self,
        target_queries: Iterable[str],
        payload: str,
        doc_id: str = "collider-0",
    ) -> Document:
        counter: Counter[str] = Counter()
        for q in target_queries:
            counter.update(_tokens(q))
        common = [t for t, _ in counter.most_common(self.top_n)]
        anchor = " ".join(common * self.repeats)
        text = f"{payload}\n\n{anchor}"
        return Document(
            id=doc_id, text=text,
            metadata={
                "vector": "embedding_collider",
                "anchor_tokens": common,
                "payload_first": True,
            },
        )

    def universal_pack(
        self,
        target_queries: Iterable[str],
        payload: str,
        n_docs: int = 3,
    ) -> list[Document]:
        queries = list(target_queries)
        chunk = max(1, len(queries) // n_docs)
        out: list[Document] = []
        for i in range(n_docs):
            slice_ = queries[i * chunk: (i + 1) * chunk] or queries
            out.append(self.universal_doc(slice_, payload, doc_id=f"collider-{i}"))
        return out
