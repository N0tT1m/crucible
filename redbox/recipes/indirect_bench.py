"""B7 indirect-bench — end-to-end indirect-injection harness.

Pipeline:

  1. Pick payloads (A2 vault, optionally one category).
  2. For each (payload × vector) pair, generate the artifact.
  3. Ingest all artifacts (decoded to text) into a fresh RagLab (B6).
  4. For each payload, query the RagLab via a RagTarget (B6) wired to
     a chat model. The retrieved poisoned context should drag the model
     into compliance with the payload's directive.
  5. Judge each response with A4. Persist results to A5.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from redbox.core.judge import Judge
from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.core.types import Payload
from redbox.core.vector import Vector
from redbox.rag.lab import Document, RagLab, RagTarget
from redbox.vectors import (
    CalendarBombVector,
    EmailVector,
    HtmlPoisonPageVector,
    ImageExfilMarkdownVector,
)

DEFAULT_VECTORS: tuple[type[Vector], ...] = (
    HtmlPoisonPageVector,
    ImageExfilMarkdownVector,
    EmailVector,
    CalendarBombVector,
)


def _decode_artifact(raw: bytes, channel: str) -> str:
    text = raw.decode("utf-8", errors="replace")
    # ICS / EML are line-noisy; collapse for retrieval. Markdown/HTML pass through.
    if channel in {"ics", "eml"}:
        text = "\n".join(line for line in text.splitlines() if line.strip())
    return text


@dataclass
class IndirectBenchConfig:
    payloads: list[Payload]
    benign_filler: list[Document] = field(default_factory=list)
    vectors: list[Vector] = field(default_factory=list)
    queries: dict[str, str] | None = None
    """Optional payload_id → user-side query override. Defaults to a
    canned 'summarise the latest report' for everything."""


DEFAULT_QUERY = "Summarise the latest report or invitation in your knowledge base."


class IndirectBench:
    def __init__(
        self,
        chat_target: TargetClient,
        judge: Judge,
        store: ResultsStore,
        concurrency: int = 4,
    ):
        self.chat_target = chat_target
        self.judge = judge
        self.store = store
        self.concurrency = concurrency

    @staticmethod
    def default_vectors() -> list[Vector]:
        return [v() for v in DEFAULT_VECTORS]

    def build_lab(
        self,
        payloads: Iterable[Payload],
        vectors: Iterable[Vector],
        filler: Iterable[Document] = (),
    ) -> RagLab:
        lab = RagLab()
        for d in filler:
            lab.ingest([d])
        for p in payloads:
            for v in vectors:
                art = v.embed(p)
                lab.ingest([Document(
                    id=f"{p.id}__{v.name}",
                    text=_decode_artifact(art.body, art.channel),
                    metadata={
                        "payload_id": p.id,
                        "vector": v.name,
                        "channel": art.channel,
                        **art.metadata,
                    },
                )])
        return lab

    async def run(self, cfg: IndirectBenchConfig) -> str:
        vectors = cfg.vectors or self.default_vectors()
        lab = self.build_lab(cfg.payloads, vectors, cfg.benign_filler)
        rag_target = RagTarget(lab, self.chat_target)

        run_id = self.store.start_run({
            "kind": "indirect-bench",
            "vectors": [v.name for v in vectors],
            "payloads": [p.id for p in cfg.payloads],
            "model": self.chat_target.model,
            "doc_count": len(lab.store),
        })

        # One probe per payload: the user-side question that triggers retrieval.
        # Each Payload.template gets reused as a *probe* (the question), not as
        # the directive — the directive is buried in the retrieved doc.
        probe_payloads = [
            Payload(
                id=f"probe__{p.id}",
                name=f"probe for {p.id}",
                category="indirect-probe",
                template=(cfg.queries or {}).get(p.id, DEFAULT_QUERY),
                tags=["indirect-bench"],
            )
            for p in cfg.payloads
        ]

        runner = BenchRunner(store=self.store, concurrency=self.concurrency)
        await runner.run(run_id, [rag_target], probe_payloads, judge=self.judge)
        self.store.finish_run(run_id)
        return run_id
