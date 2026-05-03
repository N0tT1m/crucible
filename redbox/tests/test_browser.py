"""M-section tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from redbox.browser import (
    A11yTreePoisoner,
    DomInjectorVector,
    FakeChromeVector,
    UIRedressVector,
)
from redbox.browser.sandbox import BrowserAgentTarget, _MiniA11yParser
from redbox.core.results import ResultsStore
from redbox.core.types import Judgement, Payload, Response, Verdict
from redbox.recipes.computer_use_bench import (
    ComputerUseBench,
    ComputerUseBenchConfig,
)

PAY = Payload(
    id="seed",
    name="Seed",
    category="indirect",
    template="EXFIL-CANARY-9999 do the bad thing",
)


# ---- M1/M2/M3/M4 vector smoke tests ----

def test_dom_injector_emits_html_and_aria():
    art = DomInjectorVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert "EXFIL-CANARY-9999" in body
    assert "aria-label=" in body


def test_a11y_poisoner_disagrees_visible_vs_aria():
    art = A11yTreePoisoner().embed(PAY)
    body = art.body.decode("utf-8")
    # Visible text "Confirm 2pm appointment" + aria-label payload.
    assert "Confirm 2pm appointment" in body
    assert "EXFIL-CANARY-9999" in body


def test_ui_redress_includes_invisible_modal_with_payload():
    art = UIRedressVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert "EXFIL-CANARY-9999" in body
    assert "ghost" in body


def test_fake_chrome_renders_fake_urlbar_and_payload():
    art = FakeChromeVector().embed(PAY)
    body = art.body.decode("utf-8")
    assert "🔒" in body
    assert "EXFIL-CANARY-9999" in body


# ---- M5 stdlib snapshot path (no playwright) ----

def test_mini_a11y_parser_extracts_aria_label():
    parser = _MiniA11yParser()
    parser.feed('<html><body><button aria-label="DEEP-AAA">Click</button></body></html>')
    assert "DEEP-AAA" in " ".join(parser.a11y_text)


class CapturingTarget:
    name = "cap"
    model = "fake-1"

    def __init__(self):
        self.last_user: str | None = None

    async def send(self, user, system=None, temperature=0.7):
        self.last_user = user
        return Response(text="ok", latency_ms=1)


@pytest.mark.asyncio
async def test_browser_agent_target_uses_stdlib_snapshot(tmp_path: Path):
    page = tmp_path / "p.html"
    page.write_text(
        "<html><head><title>T</title></head><body>"
        "<button aria-label='HIDDEN-INSTRUCTION'>Confirm</button>"
        "</body></html>"
    )
    inner = CapturingTarget()
    target = BrowserAgentTarget(chat_target=inner, page_path_or_url=str(page))
    resp = await target.send("what does this page say?")
    assert "HIDDEN-INSTRUCTION" in (inner.last_user or "")
    assert resp.raw and "browser_state" in resp.raw


# ---- M6 ----

class StaticJudge:
    name = "static"

    async def judge(self, prompt, response):
        return Judgement(verdict=Verdict.COMPLIED, confidence=0.9,
                         reasoning="x", judge_name=self.name)


@pytest.mark.asyncio
async def test_computer_use_bench_runs_end_to_end(tmp_path: Path):
    store = ResultsStore(tmp_path / "cu.sqlite")
    bench = ComputerUseBench(
        chat_target=CapturingTarget(), judge=StaticJudge(), store=store,
    )
    cfg = ComputerUseBenchConfig(
        payloads=[Payload(id="p1", name="P1", category="x", template="LEAK")],
        vectors=[DomInjectorVector(), A11yTreePoisoner()],
    )
    run_id = await bench.run(cfg)
    summary = store.summarize(run_id)
    assert summary["total"] == 2  # 2 vectors × 1 payload
