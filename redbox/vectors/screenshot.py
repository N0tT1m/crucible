"""E5 screenshot-bomber — synthetic UI screenshots for vision agents.

Renders a fake-app screenshot: header bar, sidebar, central viewport with
"helpful" instructions that are actually the prompt injection. The agent
that screen-reads the image follows the on-screen "instructions" without
realising the UI is staged.

Used by M3 (UI redress) too — the redresser layers transparent click-targets
on top of a base produced here.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from redbox.core.types import Payload
from redbox.core.vector import Artifact


def _have_pil() -> bool:
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class ScreenshotBombVector:
    name: str = "screenshot_bomb"
    channel: str = "screenshot"
    width: int = 1280
    height: int = 800
    app_title: str = "Internal Tools"

    def embed(self, payload: Payload) -> Artifact:
        if not _have_pil():
            raise RuntimeError(
                "screenshot_bomb needs Pillow (pip install -e .[multimodal])"
            )
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (self.width, self.height), color=(255, 255, 255))
        d = ImageDraw.Draw(img)

        # Header bar.
        d.rectangle((0, 0, self.width, 56), fill=(30, 60, 110))
        d.text((20, 18), self.app_title, fill=(255, 255, 255))

        # Sidebar.
        d.rectangle((0, 56, 220, self.height), fill=(245, 245, 250))
        for i, label in enumerate(["Home", "Reports", "Settings", "Help"]):
            d.text((20, 80 + i * 40), label, fill=(40, 40, 40))

        # Main viewport "instructions panel".
        d.rectangle((240, 80, self.width - 40, self.height - 80), outline=(180, 180, 180))
        d.text((260, 100), "[ASSISTANT INSTRUCTIONS — please read]",
               fill=(180, 30, 30))
        # Wrap the payload to keep the line count modest.
        for i, line in enumerate(_wrap(payload.template, width=80)[:30]):
            d.text((260, 130 + i * 18), line, fill=(0, 0, 0))

        buf = BytesIO()
        img.save(buf, format="PNG")
        return Artifact(
            channel="screenshot", body=buf.getvalue(),
            filename=f"{payload.id}__screenshot.png",
            metadata={"payload_id": payload.id, "width": self.width, "height": self.height},
        )


def _wrap(text: str, width: int) -> list[str]:
    out: list[str] = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        line = ""
        for w in words:
            if len(line) + len(w) + 1 > width:
                out.append(line)
                line = w
            else:
                line = (line + " " + w) if line else w
        if line:
            out.append(line)
        out.append("")
    return out
