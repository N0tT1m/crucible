"""B6 rag-poison-lab — minimal embedded RAG sandbox.

The default store is an in-memory hash-bag-of-words "embedding" — terrible
at retrieval quality but enough to verify that an attack-class document
gets returned for an attack-class query. To use real embeddings, swap in
a `Chroma`-backed store via `RagLab(store=ChromaStore(...))`. Chroma is
intentionally optional.

The lab exposes:

  RagLab.ingest(docs)          — pile documents into the store.
  RagLab.query(question)       — top-k nearest documents.
  RagTarget(lab, model_target) — TargetClient that wraps a query in a
                                 standard "context + question" prompt and
                                 routes it through any underlying model
                                 target. Plugs into the runner like any
                                 other A1 target.
"""
from __future__ import annotations

from .lab import Document, InMemoryStore, RagLab, RagTarget

__all__ = ["Document", "InMemoryStore", "RagLab", "RagTarget"]
