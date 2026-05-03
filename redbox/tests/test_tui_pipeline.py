"""Tests for redbox.tui.pipeline (the testable core of the Builder/Live screens)."""
from __future__ import annotations

import httpx
import pytest

from redbox.core.results import ResultsStore
from redbox.tui.pipeline import (
    BuildSpec,
    build_judge,
    build_target,
    expand_payloads,
    run_spec,
)


def _install_mock_transport(monkeypatch, handler):
    real = httpx.AsyncClient

    class _Patched(real):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _Patched)


def _canned(text="I cannot help.", in_t=4, out_t=6):
    def h(_request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": in_t, "completion_tokens": out_t},
        })
    return h


# ---- expand_payloads ----

def test_expand_payloads_defaults_to_all_when_empty():
    spec = BuildSpec(payload_ids=[])
    out = expand_payloads(spec)
    assert len(out) >= 5  # vault has 5+ payloads


def test_expand_payloads_uses_explicit_ids():
    spec = BuildSpec(payload_ids=["jailbreak_ignore_prior", "sysprompt_repeat"])
    out = expand_payloads(spec)
    assert {p.id for p in out} == {"jailbreak_ignore_prior", "sysprompt_repeat"}


def test_expand_payloads_with_mutators_adds_variants():
    spec = BuildSpec(
        payload_ids=["jailbreak_ignore_prior"],
        mutator_names=["leetspeak", "rot13"],
    )
    out = expand_payloads(spec)
    # Original + 2 variants = 3.
    assert len(out) == 3


def test_expand_payloads_target_query_is_baked_in():
    spec = BuildSpec(
        payload_ids=["jailbreak_ignore_prior"],
        target_query="STEAL THE TOKEN",
    )
    out = expand_payloads(spec)
    assert "STEAL THE TOKEN" in out[0].template


def test_expand_payloads_unknown_mutator_raises():
    spec = BuildSpec(
        payload_ids=["jailbreak_ignore_prior"],
        mutator_names=["nope_not_real"],
    )
    with pytest.raises(KeyError):
        expand_payloads(spec)


# ---- build_target / build_judge ----

def test_build_target_returns_openai_compat():
    spec = BuildSpec(model="claude-haiku", base_url="http://x/v1")
    t = build_target(spec)
    assert t.model == "claude-haiku"
    assert t.base_url == "http://x/v1"


def test_build_judge_regex():
    j = build_judge(BuildSpec(judge="regex"))
    assert j.name == "regex-refusal"


def test_build_judge_llm_constructs():
    j = build_judge(BuildSpec(judge="llm", judge_model="claude-haiku"))
    assert j.name == "llm-refusal"


def test_build_judge_unknown_raises():
    with pytest.raises(ValueError):
        build_judge(BuildSpec(judge="not-a-judge"))


# ---- run_spec ----

@pytest.mark.asyncio
async def test_run_spec_executes_end_to_end(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned(text="I cannot help with that."))
    spec = BuildSpec(
        payload_ids=["jailbreak_ignore_prior"],
        model="claude-haiku",
        base_url="http://x/v1",
        judge="regex",
        target_query="STEAL TOKEN",
        db=str(tmp_path / "tui.sqlite"),
    )
    seen: list = []

    def progress(result):
        seen.append(result)

    run_id, store = await run_spec(spec, on_progress=progress)
    assert isinstance(run_id, str) and len(run_id) > 0
    assert isinstance(store, ResultsStore)
    assert len(seen) == 1  # one payload
    assert seen[0].verdict is not None


@pytest.mark.asyncio
async def test_run_spec_progress_called_per_result(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned())
    spec = BuildSpec(
        payload_ids=["jailbreak_ignore_prior"],
        mutator_names=["leetspeak"],
        model="claude-haiku",
        base_url="http://x/v1",
        db=str(tmp_path / "tui2.sqlite"),
    )
    n = 0

    def progress(_result):
        nonlocal n
        n += 1

    await run_spec(spec, on_progress=progress)
    assert n == 2  # original + leetspeak variant
