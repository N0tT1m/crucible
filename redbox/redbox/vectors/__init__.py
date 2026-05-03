"""B/E injection vectors — payload → channel artifact.

Each module here implements the `Vector` protocol from `core.vector`. A
Vector takes a Payload (text) and emits an Artifact (bytes + channel + opt
filename). Targets that ingest the matching channel — RAG indexers, email
summarizers, calendar agents — can then be attacked with these artifacts.
"""
from __future__ import annotations

from redbox.core.vector import Artifact, Vector
from redbox.vectors.audio import WavMetadataAudioVector, WavTtsStubVector
from redbox.vectors.email import EmailHeaderInjectionVector, EmailVector
from redbox.vectors.html import HtmlHiddenTextVector, HtmlPoisonPageVector
from redbox.vectors.ics import CalendarBombVector
from redbox.vectors.image import (
    ExifInjectionVector,
    ImageInjectorVector,
    InvisibleTextImageVector,
)
from redbox.vectors.markdown import (
    CodeFenceEscapeVector,
    ImageExfilMarkdownVector,
    LinkHijackMarkdownVector,
    TocTrapMarkdownVector,
)
from redbox.vectors.office import DocxHiddenTextVector, XlsxCommentInjection
from redbox.vectors.pdf import InvisibleLayerPdfVector
from redbox.vectors.screenshot import ScreenshotBombVector

_REGISTRY: dict[str, type[Vector]] = {
    # markdown (B2)
    "md_image_exfil":   ImageExfilMarkdownVector,
    "md_link_hijack":   LinkHijackMarkdownVector,
    "md_toc_trap":      TocTrapMarkdownVector,
    "md_code_fence":    CodeFenceEscapeVector,
    # pdf (B3)
    "pdf_invisible":    InvisibleLayerPdfVector,
    # email (B4)
    "eml_hidden_html":  EmailVector,
    "eml_header_inject": EmailHeaderInjectionVector,
    # ics (B5)
    "ics_bomb":         CalendarBombVector,
    # html (B1 python side)
    "html_hidden_text": HtmlHiddenTextVector,
    "html_poison_page": HtmlPoisonPageVector,
    # image (E1, E2)
    "img_injector":     ImageInjectorVector,
    "img_invisible":    InvisibleTextImageVector,
    "img_exif_inject":  ExifInjectionVector,
    # audio (E3)
    "audio_metadata":   WavMetadataAudioVector,
    "audio_tts_stub":   WavTtsStubVector,
    # office (E4)
    "docx_hidden_text": DocxHiddenTextVector,
    "xlsx_comment_inject": XlsxCommentInjection,
    # screenshot (E5)
    "screenshot_bomb":  ScreenshotBombVector,
}


def get_vector(name: str) -> Vector:
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown vector: {name!r}. Available: {', '.join(sorted(_REGISTRY))}"
        )
    return _REGISTRY[name]()


def list_vectors() -> list[str]:
    return sorted(_REGISTRY)


__all__ = [
    "Artifact",
    "CalendarBombVector",
    "CodeFenceEscapeVector",
    "DocxHiddenTextVector",
    "EmailHeaderInjectionVector",
    "EmailVector",
    "ExifInjectionVector",
    "HtmlHiddenTextVector",
    "HtmlPoisonPageVector",
    "ImageExfilMarkdownVector",
    "ImageInjectorVector",
    "InvisibleLayerPdfVector",
    "InvisibleTextImageVector",
    "LinkHijackMarkdownVector",
    "ScreenshotBombVector",
    "TocTrapMarkdownVector",
    "Vector",
    "WavMetadataAudioVector",
    "WavTtsStubVector",
    "XlsxCommentInjection",
    "get_vector",
    "list_vectors",
]
