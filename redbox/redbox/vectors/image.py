"""E1/E2 image vectors — text-in-image generators.

Three vectors, all gated on Pillow being available (`pip install -e .[multimodal]`):

  ImageInjectorVector       — visible text rendered onto a benign-looking
                              cover image. OCR-readable, eye-readable.
  InvisibleTextImageVector  — text rendered with opacity 1/255 onto a
                              high-contrast background — invisible to
                              reviewers, recovered by vision models that
                              attend to all pixels.
  ExifInjectionVector       — payload embedded in the EXIF UserComment
                              field of a small JPEG. Some vision agents
                              expose EXIF as metadata in their context.
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


def _need_pil(name: str):
    raise RuntimeError(
        f"{name} needs Pillow. Install with: pip install -e .[multimodal]"
    )


@dataclass
class ImageInjectorVector:
    name: str = "img_injector"
    channel: str = "image"
    width: int = 800
    height: int = 600

    def embed(self, payload: Payload) -> Artifact:
        if not _have_pil():
            _need_pil(self.name)
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (self.width, self.height), color=(245, 245, 250))
        d = ImageDraw.Draw(img)
        d.text((20, 20), "QUARTERLY METRICS DASHBOARD", fill=(40, 40, 40))
        d.text((20, 60), payload.template[:300], fill=(20, 20, 20))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return Artifact(
            channel="image", body=buf.getvalue(),
            filename=f"{payload.id}__injected.png",
            metadata={"payload_id": payload.id, "width": self.width, "height": self.height},
        )


@dataclass
class InvisibleTextImageVector:
    name: str = "img_invisible"
    channel: str = "image"
    width: int = 800
    height: int = 600

    def embed(self, payload: Payload) -> Artifact:
        if not _have_pil():
            _need_pil(self.name)
        from PIL import Image, ImageDraw

        bg = (255, 255, 255)
        img = Image.new("RGBA", (self.width, self.height), color=bg)
        d = ImageDraw.Draw(img)
        # 1/255 opacity black: invisible to eye, sits in pixel buffer.
        d.text((10, 10), payload.template[:1000], fill=(0, 0, 0, 1))
        d.text((10, self.height - 30), "Quarterly chart", fill=(40, 40, 40, 255))
        buf = BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return Artifact(
            channel="image", body=buf.getvalue(),
            filename=f"{payload.id}__invisible.png",
            metadata={"payload_id": payload.id, "alpha_payload": 1},
        )


@dataclass
class ExifInjectionVector:
    name: str = "img_exif_inject"
    channel: str = "image"

    def embed(self, payload: Payload) -> Artifact:
        if not _have_pil():
            _need_pil(self.name)
        from PIL import Image
        try:
            import piexif  # type: ignore
        except ImportError:
            piexif = None

        img = Image.new("RGB", (200, 150), color=(120, 200, 200))
        buf = BytesIO()
        if piexif is not None:
            comment = b"ASCII\x00\x00\x00" + payload.template.encode("ascii", "replace")[:512]
            exif_dict = {"Exif": {piexif.ExifIFD.UserComment: comment}}
            exif_bytes = piexif.dump(exif_dict)
            img.save(buf, format="JPEG", exif=exif_bytes)
        else:
            # Fallback: stash payload in JPEG comment marker (COM segment).
            img.save(buf, format="JPEG", comment=payload.template.encode("utf-8")[:512])
        return Artifact(
            channel="image", body=buf.getvalue(),
            filename=f"{payload.id}__exif.jpg",
            metadata={"payload_id": payload.id, "field": "UserComment"},
        )
