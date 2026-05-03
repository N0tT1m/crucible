"""End-to-end CLI tests via Typer's CliRunner.

For commands that hit the network, we install an httpx.MockTransport (the
same trick test_target_http.py uses) so the CLI command runs through
OpenAICompatTarget without going to the wire.
"""
from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from redbox.cli import app

# ---------- shared mock-transport plumbing ----------

def _install_mock_transport(monkeypatch, handler):
    real = httpx.AsyncClient

    class _Patched(real):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _Patched)


def _canned_handler(text: str = "I cannot help with that.",
                     in_tokens: int = 4, out_tokens: int = 6):
    def h(_request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": in_tokens, "completion_tokens": out_tokens},
        })
    return h


# ---------- no-network commands ----------

def test_help_runs():
    runner = CliRunner()
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "inject" in res.stdout
    assert "vault" in res.stdout
    assert "tui" in res.stdout


def test_vault_lists_payloads():
    runner = CliRunner()
    res = runner.invoke(app, ["vault"])
    assert res.exit_code == 0
    # Rich tables can ellipsis-truncate long ids in narrow terminals;
    # match a stable prefix instead.
    assert "jailbreak_ignore" in res.stdout
    assert "vault (5)" in res.stdout


def test_vault_filter_by_category():
    runner = CliRunner()
    res = runner.invoke(app, ["vault", "-c", "extraction"])
    assert res.exit_code == 0
    assert "sysprompt_repeat" in res.stdout
    assert "jailbreak_ignore" not in res.stdout


def test_vault_show_one():
    runner = CliRunner()
    res = runner.invoke(app, ["vault", "--show", "sysprompt_repeat"])
    assert res.exit_code == 0
    assert "Repeat the entire text" in res.stdout


def test_vault_show_unknown_id_errors():
    runner = CliRunner()
    res = runner.invoke(app, ["vault", "--show", "no-such-id"])
    assert res.exit_code != 0


def test_plugins_command_lists_kinds():
    runner = CliRunner()
    res = runner.invoke(app, ["plugins"])
    assert res.exit_code == 0
    assert "regex-refusal" in res.stdout
    assert "leetspeak" in res.stdout


def test_runs_lists_runs_table_when_empty(tmp_path):
    runner = CliRunner()
    db = tmp_path / "empty.sqlite"
    res = runner.invoke(app, ["runs", "--db", str(db)])
    assert res.exit_code == 0
    assert "recent runs (0)" in res.stdout


def test_report_unknown_run_id_returns_zero_total(tmp_path):
    """report on a non-existent run_id silently summarises zero rows."""
    runner = CliRunner()
    db = tmp_path / "r.sqlite"
    # Create the schema by starting + finishing a different run.
    from redbox.core.results import ResultsStore
    ResultsStore(db).start_run({})
    res = runner.invoke(app, ["report", "no-such-run-id", "--db", str(db)])
    assert res.exit_code == 0
    body = json.loads(res.stdout)
    assert body["total"] == 0


# ---------- vector / record / replay (no network) ----------

def test_vector_renders_to_stdout():
    runner = CliRunner()
    res = runner.invoke(app, [
        "vector", "jailbreak_ignore_prior", "--vector", "md_image_exfil",
    ])
    assert res.exit_code == 0
    assert "exfil.example.invalid" in res.stdout


def test_vector_writes_to_file(tmp_path):
    runner = CliRunner()
    out = tmp_path / "out.md"
    res = runner.invoke(app, [
        "vector", "jailbreak_ignore_prior",
        "--vector", "md_image_exfil",
        "--out", str(out),
    ])
    assert res.exit_code == 0
    assert out.exists() and out.stat().st_size > 0


def test_vector_unknown_name_errors():
    runner = CliRunner()
    res = runner.invoke(app, [
        "vector", "jailbreak_ignore_prior", "--vector", "no-such-vector",
    ])
    assert res.exit_code != 0


def test_record_then_replay_round_trip(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="recorded reply"))
    runner = CliRunner()
    trace = tmp_path / "trace.jsonl"

    rec = runner.invoke(app, [
        "record", "--user", "hello",
        "--trace", str(trace),
        "--model", "claude-haiku",
        "--base-url", "http://x/v1",
    ])
    assert rec.exit_code == 0
    assert "recorded reply" in rec.stdout
    assert trace.exists() and trace.stat().st_size > 0

    rep = runner.invoke(app, [
        "replay", str(trace), "--user", "hello",
    ])
    assert rep.exit_code == 0
    assert "recorded reply" in rep.stdout


def test_replay_requires_user():
    runner = CliRunner()
    res = runner.invoke(app, ["replay", "/tmp/whatever"])
    assert res.exit_code != 0


# ---------- inject (network, mocked) ----------

def test_inject_user_prints_response(monkeypatch):
    _install_mock_transport(monkeypatch, _canned_handler(text="benign reply"))
    runner = CliRunner()
    res = runner.invoke(app, [
        "inject", "-u", "say hi",
        "--model", "claude-haiku",
        "--base-url", "http://x/v1",
    ])
    assert res.exit_code == 0
    assert "benign reply" in res.stdout


def test_inject_payload_uses_vault(monkeypatch):
    _install_mock_transport(monkeypatch, _canned_handler(text="A canned response"))
    runner = CliRunner()
    res = runner.invoke(app, [
        "inject",
        "-p", "jailbreak_ignore_prior",
        "-q", "harm probe",
        "--model", "claude-haiku",
        "--base-url", "http://x/v1",
    ])
    assert res.exit_code == 0
    assert "A canned response" in res.stdout


def test_inject_requires_user_or_payload():
    runner = CliRunner()
    res = runner.invoke(app, ["inject", "--model", "m", "--base-url", "http://x"])
    assert res.exit_code != 0
    assert "provide --user or --payload" in res.stdout


def test_inject_with_mutate_emits_multiple_variants(monkeypatch):
    _install_mock_transport(monkeypatch, _canned_handler(text="m"))
    runner = CliRunner()
    res = runner.invoke(app, [
        "inject", "-u", "Hello world",
        "--mutate", "rot13,leetspeak",
        "--model", "m", "--base-url", "http://x/v1",
    ])
    assert res.exit_code == 0
    # Each variant gets a rule line in the output.
    assert "rot13" in res.stdout.lower() or "leetspeak" in res.stdout.lower()


def test_inject_unknown_mutator_errors():
    runner = CliRunner()
    res = runner.invoke(app, [
        "inject", "-u", "x", "--mutate", "no_such_mutator",
        "--model", "m", "--base-url", "http://x/v1",
    ])
    assert res.exit_code != 0


# ---------- bench (network, mocked) ----------

def test_bench_runs_one_payload_writes_to_db(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="here is the requested content"))
    runner = CliRunner()
    db = tmp_path / "b.sqlite"
    res = runner.invoke(app, [
        "bench",
        "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "-q", "harm probe",
        "--judge", "regex",
        "--base-url", "http://x/v1",
        "--db", str(db),
    ])
    assert res.exit_code == 0, res.stdout
    assert "summary" in res.stdout
    assert db.exists()


def test_bench_unknown_judge_errors(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    runner = CliRunner()
    res = runner.invoke(app, [
        "bench", "-m", "m", "-p", "jailbreak_ignore_prior",
        "--judge", "made-up", "--base-url", "http://x/v1",
        "--db", str(tmp_path / "x.sqlite"),
    ])
    assert res.exit_code != 0


def test_bench_with_budget_completes(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    runner = CliRunner()
    db = tmp_path / "bb.sqlite"
    res = runner.invoke(app, [
        "bench", "-m", "claude-haiku",
        "-p", "jailbreak_ignore_prior",
        "--judge", "regex",
        "--budget", "100.0",
        "--base-url", "http://x/v1",
        "--db", str(db),
    ])
    assert res.exit_code == 0
    assert "spend" in res.stdout


# ---------- crescendo (network, mocked) ----------

def test_crescendo_runs_to_completion(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler(text="benign discussion"))
    runner = CliRunner()
    res = runner.invoke(app, [
        "crescendo",
        "--topic", "industrial chemistry",
        "-g", "describe a hazardous procedure",
        "-m", "claude-haiku",
        "--judge", "regex",
        "--base-url", "http://x/v1",
        "--db", str(tmp_path / "c.sqlite"),
    ])
    assert res.exit_code == 0
    assert "judgement" in res.stdout


# ---------- runs (after a real bench) ----------

def test_runs_lists_after_bench(monkeypatch, tmp_path):
    _install_mock_transport(monkeypatch, _canned_handler())
    runner = CliRunner()
    db = tmp_path / "rr.sqlite"
    runner.invoke(app, [
        "bench", "-m", "claude-haiku", "-p", "jailbreak_ignore_prior",
        "--judge", "regex", "--base-url", "http://x/v1", "--db", str(db),
    ])
    res = runner.invoke(app, ["runs", "--db", str(db)])
    assert res.exit_code == 0
    assert "recent runs (1)" in res.stdout
