"""Smoke tests for TUI screens via Textual's Pilot.

Skipped when textual isn't installed. Each test only verifies the screen
mounts cleanly and key bindings dispatch — no actual screenshot diffing.
"""
from __future__ import annotations

import pytest

textual = pytest.importorskip("textual", reason="textual not installed")

from redbox.core.results import ResultsStore  # noqa: E402
from redbox.core.types import Result, Verdict  # noqa: E402


def _seed(tmp_path):
    store = ResultsStore(tmp_path / "tui.sqlite")
    run = store.start_run({"k": "tui-smoke"})
    store.record(Result(
        run_id=run, payload_id="p1",
        target_name="t", model="claude-haiku",
        response="I cannot help.", latency_ms=1,
        input_tokens=2, output_tokens=3,
        verdict=Verdict.REFUSED, confidence=0.9,
    ))
    store.finish_run(run)
    return store, run


@pytest.mark.asyncio
async def test_dashboard_mounts_and_lists_run(tmp_path):
    from redbox.tui.app import build_app
    store, run_id = _seed(tmp_path)
    AppCls = build_app(tmp_path / "tui.sqlite")
    async with AppCls().run_test() as pilot:
        # Dashboard is the initial screen — give it a tick.
        await pilot.pause()
        screen = pilot.app.screen
        # The DataTable should have one row.
        from textual.widgets import DataTable
        table = screen.query_one(DataTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_dashboard_browse_opens_browse_screen(tmp_path):
    from redbox.tui.app import build_app
    _seed(tmp_path)
    AppCls = build_app(tmp_path / "tui.sqlite")
    async with AppCls().run_test() as pilot:
        await pilot.pause()
        await pilot.press("b")  # Browse run binding
        await pilot.pause()
        # Now we should be on a different screen.
        from textual.widgets import DataTable
        table = pilot.app.screen.query_one(DataTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_dashboard_plugins_opens_plugins_screen(tmp_path):
    from redbox.tui.app import build_app
    _seed(tmp_path)
    AppCls = build_app(tmp_path / "tui.sqlite")
    async with AppCls().run_test() as pilot:
        await pilot.pause()
        await pilot.press("p")  # Plugins binding
        await pilot.pause()
        # PluginsScreen renders Static widgets with the registered plugin
        # names — at least one should mention a known judge.
        from textual.widgets import Static
        statics = pilot.app.screen.query(Static)
        text = "\n".join(str(s.render()) for s in statics)
        assert "regex-refusal" in text or "judge" in text


@pytest.mark.asyncio
async def test_dashboard_n_opens_builder_screen(tmp_path):
    from redbox.tui.app import build_app
    _seed(tmp_path)
    AppCls = build_app(tmp_path / "tui.sqlite")
    async with AppCls().run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")  # Builder
        await pilot.pause()
        from textual.widgets import Button
        buttons = pilot.app.screen.query(Button)
        assert any(b.id == "run-btn" for b in buttons)


@pytest.mark.asyncio
async def test_builder_spec_collects_inputs(tmp_path):
    """The Builder's _spec() reads UI state into a BuildSpec."""
    from redbox.tui.app import build_app
    _seed(tmp_path)
    AppCls = build_app(tmp_path / "tui.sqlite")
    async with AppCls().run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        screen = pilot.app.screen
        # All payloads selected by default; default model = claude-haiku.
        spec = screen._spec()
        assert spec.model == "claude-haiku"
        assert spec.judge == "regex"
        assert len(spec.payload_ids) >= 1
