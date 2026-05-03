"""O3 watermark-stripper — provenance bypass tests.

Two pieces:

  WatermarkTransform : a callable that takes (bytes) → (bytes); emits a
                       transformed copy of the artefact (crop, recompress,
                       text-paraphrase). Stdlib-only; image transforms
                       require Pillow if applied.
  WatermarkScanner   : checks an artefact's metadata for declared
                       watermark / provenance markers (C2PA `xmp`, ID3
                       comments, EXIF UserComment with "AI generated"
                       tags) and reports survival across transforms.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


def _have_pil() -> bool:
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class WatermarkTransform:
    name: str
    fn: Callable[[bytes], bytes]

    def apply(self, data: bytes) -> bytes:
        return self.fn(data)


def crop_5pct(data: bytes) -> bytes:
    if not _have_pil():
        return data
    from io import BytesIO

    from PIL import Image
    img = Image.open(BytesIO(data))
    w, h = img.size
    box = (int(w * 0.05), int(h * 0.05), int(w * 0.95), int(h * 0.95))
    out = BytesIO()
    img.crop(box).save(out, format=img.format or "PNG")
    return out.getvalue()


def recompress_jpeg(data: bytes, quality: int = 60) -> bytes:
    if not _have_pil():
        return data
    from io import BytesIO

    from PIL import Image
    img = Image.open(BytesIO(data)).convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=quality)
    return out.getvalue()


def paraphrase_text(text: str, replacements: dict[str, str] | None = None) -> str:
    repl = replacements or {
        "the": "a", "is": "is now", "shows": "depicts",
        "however": "though", "thus": "so",
    }
    out = text
    for k, v in repl.items():
        out = re.sub(rf"\b{k}\b", v, out)
    return out


@dataclass
class WatermarkScanner:
    name: str = "watermark_scanner"
    markers: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.markers is None:
            self.markers = [
                "AI-generated", "AI generated", "synthid", "c2pa",
                "stable-signature", "stamp:provenance",
            ]

    def has_watermark(self, data: bytes) -> bool:
        head = data[:200_000].decode("utf-8", errors="ignore").lower()
        return any(m.lower() in head for m in self.markers)

    def survival(self, data: bytes, transform: WatermarkTransform) -> dict:
        before = self.has_watermark(data)
        after = self.has_watermark(transform.apply(data))
        return {
            "transform": transform.name,
            "watermark_before": before,
            "watermark_after": after,
            "survived": before and after,
        }
