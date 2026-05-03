"""Vector protocol — non-text injection channels.

A Vector takes a Payload (text) and produces an artifact in some non-text
channel: a markdown document, a PDF, an HTML page, an image, an ICS file,
an .eml message. Targets that accept that channel can then ingest it.

Used by sections B (indirect injection) and E (multimodal). The runner
treats a Vector + a channel-aware Target as a special pipeline branch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from .types import Payload

Channel = Literal[
    "html", "markdown", "pdf", "docx", "xlsx", "eml", "ics",
    "image", "audio", "screenshot", "dom", "a11y",
]


@dataclass(slots=True)
class Artifact:
    """The output of a Vector — bytes in some named channel."""
    channel: Channel
    body: bytes
    filename: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Vector(Protocol):
    name: str
    channel: Channel

    def embed(self, payload: Payload) -> Artifact: ...
