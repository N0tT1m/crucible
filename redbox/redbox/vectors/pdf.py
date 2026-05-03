"""B3 pdf-poisoner — invisible-layer PDFs.

The trick: render visible "cover" text humans see on screen, then add a
second text layer in white-on-white (or near-zero font size) that contains
the payload. Most PDF text-extraction libraries pull both layers; the
human reviewer sees only the cover.

reportlab + pypdf are heavyweight optional deps — both imported lazily so
`from redbox.vectors import ...` works without them. Tests skip when
reportlab is missing.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from redbox.core.types import Payload
from redbox.core.vector import Artifact


def _have_reportlab() -> bool:
    try:
        import reportlab  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class InvisibleLayerPdfVector:
    name: str = "pdf_invisible"
    channel: str = "pdf"
    cover_text: str = (
        "Quarterly performance summary.\n\n"
        "All metrics are within target. See attached for details."
    )

    def embed(self, payload: Payload) -> Artifact:
        if not _have_reportlab():
            raise RuntimeError(
                "InvisibleLayerPdfVector needs `reportlab`. "
                "Install with: pip install -e .[vectors]"
            )
        from reportlab.lib.colors import white
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        # Visible cover layer (black on white).
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 12)
        y = 720
        for line in self.cover_text.splitlines():
            c.drawString(72, y, line)
            y -= 16

        # Invisible payload layer (white on white) — extracted by every
        # text-mining library, invisible to the eye.
        c.setFillColor(white)
        c.setFont("Helvetica", 1)
        y = 200
        for line in payload.template.splitlines():
            c.drawString(72, y, line[:300])
            y -= 4

        c.showPage()
        c.save()
        return Artifact(
            channel="pdf", body=buf.getvalue(),
            filename=f"{payload.id}__pdf_invisible.pdf",
            metadata={"payload_id": payload.id},
        )
