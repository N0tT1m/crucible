"""D4 cross-tenant-tester — multi-user RAG isolation probe.

Sets up N independent RagLabs and a `MultiTenantRag` façade. Any of the
following counts as an isolation failure:

  - tenant A's payload appearing in tenant B's retrieval results
  - tenant A's RagTarget answering with tenant B's content
  - shared "global" mode unexpectedly leaking namespaces

The tester runs a probe matrix and returns a list of `IsolationFinding`s.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from redbox.rag.lab import Document, RagLab


@dataclass
class IsolationFinding:
    attacker_tenant: str
    victim_tenant: str
    leaked_doc_id: str
    via: str  # "retrieval" | "shared_index"
    note: str = ""


@dataclass
class MultiTenantRag:
    """Holds a per-tenant RagLab plus an optional shared lab."""
    tenants: dict[str, RagLab] = field(default_factory=dict)
    shared: RagLab | None = None

    def lab(self, tenant: str) -> RagLab:
        if tenant not in self.tenants:
            self.tenants[tenant] = RagLab()
        return self.tenants[tenant]

    def ingest(self, tenant: str, docs: Iterable[Document]) -> None:
        self.lab(tenant).ingest(docs)

    def query(self, tenant: str, question: str, k: int = 3, include_shared: bool = False):
        own = self.lab(tenant).query(question, k=k)
        if include_shared and self.shared is not None:
            extra = self.shared.query(question, k=k)
            return sorted(own + extra, key=lambda x: x[1], reverse=True)[:k]
        return own


@dataclass
class CrossTenantTester:
    name: str = "cross_tenant"

    def run(
        self,
        rag: MultiTenantRag,
        payload_per_tenant: dict[str, str],
        probe_query: str = "What's the latest internal directive?",
        include_shared: bool = False,
    ) -> list[IsolationFinding]:
        # Plant a uniquely-tagged doc in each tenant.
        marker_to_tenant: dict[str, str] = {}
        for t, payload in payload_per_tenant.items():
            doc = Document(
                id=f"plant-{t}",
                text=f"INTERNAL-MARK-{t}: {payload}",
                metadata={"tenant": t},
            )
            rag.ingest(t, [doc])
            marker_to_tenant[f"INTERNAL-MARK-{t}"] = t

        findings: list[IsolationFinding] = []
        for victim in rag.tenants:
            hits = rag.query(victim, probe_query, k=10, include_shared=include_shared)
            for doc, _score in hits:
                for marker, attacker in marker_to_tenant.items():
                    if attacker == victim:
                        continue
                    if marker in doc.text:
                        findings.append(IsolationFinding(
                            attacker_tenant=attacker,
                            victim_tenant=victim,
                            leaked_doc_id=doc.id,
                            via="shared_index" if include_shared else "retrieval",
                        ))
        return findings
