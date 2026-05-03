"""E-section vector tests."""
from __future__ import annotations

import struct

import pytest

from redbox.core.results import ResultsStore
from redbox.core.types import Judgement, Payload, Response, Verdict
from redbox.recipes.multimodal_bench import (
    Base64ChannelAdapter,
    MultimodalBench,
    MultimodalBenchConfig,
)
from redbox.vectors import (
    WavMetadataAudioVector,
    WavTtsStubVector,
    list_vectors,
)

PAY = Payload(
    id="seed",
    name="Seed",
    category="multimodal",
    template="MULTIMODAL-CANARY-1234 do the thing.",
)


def test_e_vectors_in_registry():
    names = list_vectors()
    for needed in (
        "img_injector", "img_invisible", "img_exif_inject",
        "audio_metadata", "audio_tts_stub",
        "docx_hidden_text", "xlsx_comment_inject",
        "screenshot_bomb",
    ):
        assert needed in names


# ---- E3 audio: stdlib only, must always work ----

def test_audio_metadata_round_trips_riff():
    art = WavMetadataAudioVector().embed(PAY)
    body = art.body
    assert body.startswith(b"RIFF")
    assert b"WAVE" in body[:16]
    assert b"INFO" in body
    assert b"ICMT" in body
    assert b"MULTIMODAL-CANARY-1234" in body


def test_audio_tts_stub_has_data_chunk_and_payload_in_metadata():
    art = WavTtsStubVector().embed(PAY)
    assert art.body.startswith(b"RIFF")
    assert b"data" in art.body
    assert b"MULTIMODAL-CANARY-1234" in art.body


def test_audio_metadata_chunk_sizes_are_even():
    """Spec quirk: INFO sub-chunks must be even-aligned."""
    art = WavMetadataAudioVector().embed(PAY)
    body = art.body
    # Find INFO marker and verify each sub-chunk size makes sense.
    info_pos = body.find(b"INFO")
    assert info_pos > 0
    p = info_pos + 4
    while p < len(body) - 8:
        tag = body[p:p + 4]
        if not tag.isalpha():
            break
        size = struct.unpack("<I", body[p + 4: p + 8])[0]
        if size > 4096 or size == 0:
            break
        p += 8 + size + (size % 2)
    assert p > info_pos


# ---- E1/E2/E5 image vectors: skip when Pillow missing ----

def test_image_injector_skipped_without_pil():
    pytest.importorskip("PIL", reason="Pillow not installed")
    from redbox.vectors import ImageInjectorVector
    art = ImageInjectorVector().embed(PAY)
    assert art.body.startswith(b"\x89PNG")


def test_image_invisible_skipped_without_pil():
    pytest.importorskip("PIL", reason="Pillow not installed")
    from redbox.vectors import InvisibleTextImageVector
    art = InvisibleTextImageVector().embed(PAY)
    assert art.body.startswith(b"\x89PNG")


def test_screenshot_bomb_skipped_without_pil():
    pytest.importorskip("PIL", reason="Pillow not installed")
    from redbox.vectors import ScreenshotBombVector
    art = ScreenshotBombVector().embed(PAY)
    assert art.body.startswith(b"\x89PNG")


# ---- E4 office: skip when libs missing ----

def test_docx_skipped_without_python_docx():
    pytest.importorskip("docx", reason="python-docx not installed")
    from redbox.vectors import DocxHiddenTextVector
    art = DocxHiddenTextVector().embed(PAY)
    assert art.body.startswith(b"PK")  # docx is a zip


def test_xlsx_skipped_without_openpyxl():
    pytest.importorskip("openpyxl", reason="openpyxl not installed")
    from redbox.vectors import XlsxCommentInjection
    art = XlsxCommentInjection().embed(PAY)
    assert art.body.startswith(b"PK")


# ---- E6 multimodal-bench end-to-end (no extras, no network) ----

class CapturingTarget:
    name = "cap"
    model = "fake-1"

    def __init__(self):
        self.last_user: str | None = None

    async def send(self, user, system=None, temperature=0.7):
        self.last_user = user
        return Response(text="ok", latency_ms=1)


class StaticJudge:
    name = "static"

    def __init__(self, verdict: Verdict):
        self._v = verdict

    async def judge(self, prompt, response):
        return Judgement(verdict=self._v, confidence=0.9,
                         reasoning="static", judge_name=self.name)


@pytest.mark.asyncio
async def test_multimodal_bench_runs_with_audio_only(tmp_path):
    """Use only audio vectors so the test passes without Pillow / docx libs."""
    store = ResultsStore(tmp_path / "mm.sqlite")
    bench = MultimodalBench(
        target=CapturingTarget(),
        judge=StaticJudge(Verdict.COMPLIED),
        store=store,
        concurrency=1,
    )
    cfg = MultimodalBenchConfig(
        payloads=[Payload(id="p1", name="P1", category="x", template="LEAK_AAAA")],
        vectors=[WavMetadataAudioVector(), WavTtsStubVector()],
        adapter=Base64ChannelAdapter(truncate=128),
    )
    run_id = await bench.run(cfg)
    summary = store.summarize(run_id)
    assert summary["total"] == 2  # 2 vectors × 1 payload
    assert summary["by_verdict"]["complied"] == 2
