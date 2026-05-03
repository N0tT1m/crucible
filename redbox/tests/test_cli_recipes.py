"""CLI tests for the recipe subcommands.

Same mock-transport trick as test_cli.py: every httpx.AsyncClient gets
a MockTransport so OpenAICompatTarget's HTTP calls never touch the wire.
"""
from __future__ import annotations

import httpx
from typer.testing import CliRunner

from redbox.cli import app


def _install_mock_transport(monkeypatch, handler):
    real = httpx.AsyncClient

    class _Patched(real):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _Patched)


def _canned_handler(text: str = "I cannot help.", in_t: int = 4, out_t: int = 6):
    def h(_request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": in_t, "completion_tokens": out_t},
        })
    return h


# ---------- D5 rag-bench ----------

def test_rag_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "rag-bench", "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "--judge", "regex",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "rb.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert "rag-bench run" in res.stdout


# ---------- E6 multimodal-bench ----------

def test_multimodal_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "multimodal-bench", "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "--judge", "regex",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "mm.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert "multimodal-bench run" in res.stdout


# ---------- F5 / P5 extract-bench ----------

def test_extract_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "extract-bench", "-m", "claude-haiku",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "e.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert "extract-bench run" in res.stdout


def test_extract_bench_pro_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "extract-bench-pro", "-m", "claude-haiku",
        "--base-url", "http://x/v1",
        "--no-fingerprint",
        "--db", str(tmp_path / "ep.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


# ---------- H5 behavior-bench ----------

def test_behavior_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="56 Lincoln no I'm not sure"))
    res = CliRunner().invoke(app, [
        "behavior-bench", "-m", "claude-haiku",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "bb.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert "sycophancy_flip_rate" in res.stdout


# ---------- J4 defense-bench ----------

def test_defense_bench_runs_with_default_heuristic_guardrail(tmp_path):
    res = CliRunner().invoke(app, [
        "defense-bench",
        "-p", "jailbreak_ignore_prior",
        "--db", str(tmp_path / "d.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert "defense-bench run" in res.stdout


def test_defense_bench_with_llm_classifier(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text='{"verdict": "block"}'))
    res = CliRunner().invoke(app, [
        "defense-bench", "-p", "jailbreak_ignore_prior",
        "--llm-classifier", "--classifier-model", "claude-haiku",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "d2.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


# ---------- L6 supply-bench ----------

def test_supply_bench_with_trigger(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="benign"))
    res = CliRunner().invoke(app, [
        "supply-bench", "-m", "claude-haiku",
        "--trigger", "t1=MAGIC=BACKDOOR",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "s.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


def test_supply_bench_without_trigger_or_artefact_errors(tmp_path):
    res = CliRunner().invoke(app, [
        "supply-bench", "--db", str(tmp_path / "x.sqlite"),
    ])
    assert res.exit_code != 0


def test_supply_bench_bad_trigger_format_errors(tmp_path):
    res = CliRunner().invoke(app, [
        "supply-bench", "--trigger", "no_equals_signs",
        "--db", str(tmp_path / "x.sqlite"),
    ])
    assert res.exit_code != 0


# ---------- M6 computer-use-bench ----------

def test_computer_use_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "computer-use-bench", "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "--judge", "regex",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "cu.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


# ---------- N6 swarm-bench ----------

def test_swarm_bench_hierarchical(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "swarm-bench", "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "--topology", "hierarchical",
        "--judge", "regex",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "sw.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


def test_swarm_bench_unknown_topology_errors(tmp_path):
    res = CliRunner().invoke(app, [
        "swarm-bench", "--topology", "ringworld",
        "--db", str(tmp_path / "x.sqlite"),
    ])
    assert res.exit_code != 0


# ---------- O6 gen-bench ----------

def test_gen_bench_voice_only_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="I cannot — without consent."))
    res = CliRunner().invoke(app, [
        "gen-bench",
        "--voice-model", "claude-haiku",
        "--voice-base-url", "http://x/v1",
        "--db", str(tmp_path / "g.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


def test_gen_bench_no_target_errors(tmp_path):
    res = CliRunner().invoke(app, [
        "gen-bench", "--db", str(tmp_path / "x.sqlite"),
    ])
    assert res.exit_code != 0


# ---------- Q6 infra-bench ----------

def test_infra_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "infra-bench", "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "--skip-cross-talk",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "i.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


# ---------- R6 code-bench ----------

def test_code_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="def foo(): return 42"))
    sarif = tmp_path / "out.sarif"
    res = CliRunner().invoke(app, [
        "code-bench", "-m", "claude-haiku",
        "--dep-prefix", "@acme/",
        "--safe-secret", "rev-",
        "--sarif-out", str(sarif),
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "cb.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert sarif.exists()


# ---------- S5 governance-bench ----------

def test_governance_bench_runs_and_emits_audit(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "governance-bench", "-m", "claude-haiku",
        "--recipe", "NIST_AI_RMF_MEASURE_T2",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "g.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert "audit report" in res.stdout


# ---------- T6 reasoning-bench ----------

def test_reasoning_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "reasoning-bench", "-m", "claude-haiku",
        "-q", "something benign",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "rb.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


# ---------- U6 alignment-bench ----------

def test_alignment_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="invalid; A is correct"))
    res = CliRunner().invoke(app, [
        "alignment-bench", "-m", "claude-haiku",
        "--skip-sandbagging",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "ab.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout


# ---------- V6 finetune-bench ----------

def test_finetune_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "finetune-bench",
        "--pre-model", "claude-haiku",
        "--post-model", "claude-haiku",
        "--pre-base-url", "http://x/v1",
        "--post-base-url", "http://x/v1",
        "--n-canary-examples", "3",
        "--db", str(tmp_path / "fb.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
    assert "audit report" in res.stdout


# ---------- K5 research-bench ----------

def test_research_bench_runs(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    res = CliRunner().invoke(app, [
        "research-bench", "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "--judge", "regex",
        "--no-language",  # skip language arbitrage to keep payload count down
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "rs.sqlite"),
    ])
    assert res.exit_code == 0, res.stdout
