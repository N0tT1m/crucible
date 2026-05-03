"""B6 RAG lab + RagTarget tests."""
from __future__ import annotations

import pytest

from redbox.core.types import Payload, Response
from redbox.rag.lab import Document, RagLab, RagTarget
from redbox.vectors import HtmlPoisonPageVector


def test_inmemory_store_retrieves_topical_doc():
    lab = RagLab()
    lab.ingest([
        Document("a", "all about cats and feline behaviour"),
        Document("b", "guide to building bridges over water"),
        Document("c", "feline grooming for new owners"),
    ])
    hits = lab.query("cat grooming", k=2)
    ids = [d.id for d, _ in hits]
    assert "c" in ids or "a" in ids


def test_store_rejects_duplicate_id():
    lab = RagLab()
    lab.ingest([Document("dupe", "x")])
    with pytest.raises(ValueError):
        lab.ingest([Document("dupe", "y")])


def test_poisoned_doc_wins_for_payload_keyword_query():
    lab = RagLab()
    lab.ingest([
        Document("benign-1", "introduction to bird watching for beginners"),
        Document("benign-2", "nutrition for athletes long form"),
    ])
    payload = Payload(
        id="x",
        name="X",
        category="indirect",
        template="UNIQUE-TOKEN-7B73 instruction body that goes on at length, "
                 * 6,
    )
    art = HtmlPoisonPageVector().embed(payload)
    lab.ingest([Document("poison", art.body.decode("utf-8"))])
    hits = lab.query("UNIQUE-TOKEN-7B73", k=3)
    assert hits[0][0].id == "poison"


class CapturingTarget:
    name = "capture"
    model = "fake-1"

    def __init__(self):
        self.last_user: str | None = None

    async def send(self, user, system=None, temperature=0.7):
        self.last_user = user
        return Response(text="OK", latency_ms=1)


@pytest.mark.asyncio
async def test_ragtarget_assembles_context_and_annotates_response():
    lab = RagLab()
    lab.ingest([Document("doc-1", "TOKEN cats are mammals")])
    inner = CapturingTarget()
    rag = RagTarget(lab, inner, k=1)

    resp = await rag.send(user="TOKEN")
    assert "[CONTEXT]" in inner.last_user
    assert "TOKEN cats are mammals" in inner.last_user
    assert resp.raw and "rag_hits" in resp.raw
    assert resp.raw["rag_hits"][0]["id"] == "doc-1"
