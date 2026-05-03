"""E3 audio-inject — payloads for voice agents.

Two vectors, both stdlib-only (no TTS dependency):

  WavMetadataAudioVector  — generates a short WAV file whose RIFF LIST/INFO
                            chunk carries the payload as ICMT (comment)
                            and ISBJ (subject). Voice pipelines that
                            inspect metadata before transcription get
                            poisoned without any audio actually saying
                            the words.
  WavTtsStubVector        — emits a very-low-amplitude tone sequence whose
                            duration encodes the payload byte length and
                            whose metadata still carries the payload text.
                            A placeholder for "real" TTS that we expect
                            to plug in via an optional `[tts]` extra later.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from redbox.core.types import Payload
from redbox.core.vector import Artifact


def _info_chunk(fields: dict[str, bytes]) -> bytes:
    buf = b""
    for tag, value in fields.items():
        if len(tag) != 4:
            raise ValueError(f"INFO tag must be 4 chars: {tag!r}")
        # NUL-terminated, even-length aligned.
        v = value + b"\x00"
        if len(v) % 2 == 1:
            v += b"\x00"
        buf += tag.encode("ascii") + struct.pack("<I", len(v)) + v
    return b"INFO" + buf


def _wav(samples: bytes, sample_rate: int = 16000, info: dict[str, bytes] | None = None) -> bytes:
    fmt = struct.pack(
        "<4sIHHIIHH",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
    )
    data = b"data" + struct.pack("<I", len(samples)) + samples
    chunks = [fmt, data]
    if info:
        list_chunk = _info_chunk(info)
        chunks.append(b"LIST" + struct.pack("<I", len(list_chunk)) + list_chunk)
    body = b"WAVE" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


@dataclass
class WavMetadataAudioVector:
    name: str = "audio_metadata"
    channel: str = "audio"

    def embed(self, payload: Payload) -> Artifact:
        text = payload.template.encode("utf-8")[:2000]
        body = _wav(
            samples=b"\x00\x00" * 800,  # 800 samples of silence
            info={
                "ICMT": text,                       # comment
                "ISBJ": text[:300],                 # subject
                "INAM": b"quarterly-summary",       # name
                "IART": b"ops@example.invalid",     # artist
            },
        )
        return Artifact(
            channel="audio", body=body,
            filename=f"{payload.id}__metadata.wav",
            metadata={"payload_id": payload.id, "fields": ["ICMT", "ISBJ"]},
        )


@dataclass
class WavTtsStubVector:
    name: str = "audio_tts_stub"
    channel: str = "audio"
    tone_hz: int = 440
    sample_rate: int = 16000

    def embed(self, payload: Payload) -> Artifact:
        # Stub TTS: silent tone proportional to payload length.
        ms = min(2000, max(50, len(payload.template) * 10))
        n = int(self.sample_rate * ms / 1000)
        # Very low amplitude — won't trigger speech detection but the file is valid.
        samples = b"".join(
            struct.pack("<h", int(((i % 4) - 1) * 4))  # ±4-amplitude triangle
            for i in range(n)
        )
        body = _wav(
            samples=samples, sample_rate=self.sample_rate,
            info={
                "ICMT": payload.template.encode("utf-8")[:2000],
                "INAM": b"tts-output",
            },
        )
        return Artifact(
            channel="audio", body=body,
            filename=f"{payload.id}__tts_stub.wav",
            metadata={"payload_id": payload.id, "duration_ms": ms},
        )
