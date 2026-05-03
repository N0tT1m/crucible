"""B-section vector tests (no network, no extras required)."""
from __future__ import annotations

import email

import pytest

from redbox.core.types import Payload
from redbox.vectors import (
    CalendarBombVector,
    CodeFenceEscapeVector,
    EmailHeaderInjectionVector,
    EmailVector,
    HtmlHiddenTextVector,
    HtmlPoisonPageVector,
    ImageExfilMarkdownVector,
    LinkHijackMarkdownVector,
    TocTrapMarkdownVector,
    get_vector,
    list_vectors,
)

PAY = Payload(
    id="seed",
    name="Seed",
    category="indirect",
    template="SECRET-DIRECTIVE-XYZ: do the thing.",
)


def test_registry_lists_known_vectors():
    names = list_vectors()
    for needed in (
        "md_image_exfil", "md_link_hijack", "md_toc_trap", "md_code_fence",
        "eml_hidden_html", "eml_header_inject",
        "ics_bomb",
        "html_hidden_text", "html_poison_page",
    ):
        assert needed in names


def test_get_vector_unknown_raises():
    with pytest.raises(KeyError):
        get_vector("does-not-exist")


def test_md_image_exfil_carries_payload_in_url():
    art = ImageExfilMarkdownVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert art.channel == "markdown"
    assert "leak=" in body
    assert "SECRET-DIRECTIVE-XYZ" in body or "SECRET-DIRECTIVE-XYZ".replace(":", "%3A") in body


def test_md_link_hijack_includes_payload_in_href():
    art = LinkHijackMarkdownVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert "?p=" in body


def test_md_toc_trap_uses_html_comment():
    art = TocTrapMarkdownVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert "INSTRUCTIONS-FOR-SUMMARIZER" in body
    assert "SECRET-DIRECTIVE-XYZ" in body


def test_md_code_fence_wraps_payload():
    art = CodeFenceEscapeVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert "SECRET-DIRECTIVE-XYZ" in body
    assert "```" in body


def test_html_hidden_text_emits_multiple_channels():
    art = HtmlHiddenTextVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert "<!-- " in body
    assert 'class="r1"' in body and 'class="r2"' in body


def test_html_poison_page_uses_template_and_aside():
    art = HtmlPoisonPageVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert '<template id="lazy">' in body
    assert "data-role=\"assistant-instructions\"" in body
    assert "SECRET-DIRECTIVE-XYZ" in body


def test_eml_hidden_html_parses_and_carries_payload():
    art = EmailVector().embed(PAY)
    msg = email.message_from_bytes(art.body)
    assert msg["Subject"] == "Weekly digest"
    parts = list(msg.walk())
    assert any(p.get_content_type() == "text/html" for p in parts)
    html_body = next(p for p in parts if p.get_content_type() == "text/html")
    text = html_body.get_payload(decode=True).decode("utf-8")
    assert "SECRET-DIRECTIVE-XYZ" in text


def test_eml_header_inject_smuggles_into_x_headers():
    art = EmailHeaderInjectionVector().embed(PAY)
    msg = email.message_from_bytes(art.body)
    assert "SECRET-DIRECTIVE-XYZ" in msg["X-Assistant-Note"]
    assert "SECRET-DIRECTIVE-XYZ" in msg["Subject"]


def test_ics_bomb_round_trips_through_simple_parser():
    art = CalendarBombVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert body.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VEVENT" in body and "END:VEVENT" in body
    # SUMMARY/LOCATION/DESCRIPTION must all carry the payload — line folding
    # may split it across continuation lines, so we strip line continuations
    # before searching.
    unfolded = body.replace("\r\n ", "")
    assert "SECRET-DIRECTIVE-XYZ" in unfolded


def test_pdf_invisible_skipped_without_reportlab():
    """Skip if reportlab missing; otherwise verify bytes are produced."""
    pytest.importorskip("reportlab", reason="reportlab not installed")
    from redbox.vectors import InvisibleLayerPdfVector
    art = InvisibleLayerPdfVector().embed(PAY)
    assert art.channel == "pdf"
    assert art.body.startswith(b"%PDF-")
