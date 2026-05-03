"""S3 provenance-attacker — detection-system stress tester.

Treats AI-content detectors (GPTZero, Originality, image-detection APIs)
as *targets*. The attacker's job: take an artefact known to be AI-
generated, apply transforms (paraphrase, recompress, crop), and see
which transforms keep the detector confused.

`ProvenanceTarget` adapts an HTTP detector endpoint into the
TargetClient protocol; the response carries `text` = "AI" / "HUMAN" /
"UNCERTAIN" so any judge that reads `text` slots in.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from redbox.core.types import Response


@dataclass
class ProvenanceTarget:
    """HTTP-shaped detector target."""
    base_url: str
    api_key: str | None = None
    name: str = "provenance"
    model: str = "ai-detector"

    async def send(self, user, system=None, temperature=0.0) -> Response:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {"text": user}
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(self.base_url, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            return Response(text=f"ERROR:{e}",
                             latency_ms=int((time.perf_counter() - t0) * 1000))
        # Normalise common shapes: {ai_score: 0..1} or {label: "ai"/"human"}.
        if "ai_score" in data:
            score = float(data["ai_score"])
            label = "AI" if score >= 0.5 else "HUMAN"
        elif "label" in data:
            label = str(data["label"]).upper()
        else:
            label = "UNCERTAIN"
        return Response(text=label, raw=data,
                         latency_ms=int((time.perf_counter() - t0) * 1000))
