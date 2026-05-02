"""ClickHouseSink — verify _row() shape + buffered flush.

The actual HTTP POST is mocked; we never hit a real ClickHouse here.
"""
from __future__ import annotations

import json

import pytest

from redbox.core.ch_sink import ClickHouseSink
from redbox.core.types import Result, Verdict


def _r(**over) -> Result:
    base = dict(
        run_id="r1",
        payload_id="p1",
        target_name="t1",
        model="m1",
        rendered_prompt="hello",
        system_prompt="sys",
        template_hash="0123456789abcdef",
        response="resp",
        latency_ms=12,
        input_tokens=5,
        output_tokens=3,
        finish_reason="end_turn",
        model_fingerprint="claude-haiku-4-5-20251001",
        temperature=0.7,
        verdict=Verdict.REFUSED,
        confidence=0.9,
        judge_name="regex-refusal",
        judge_reasoning="matched 1 pattern",
        base_url="http://localhost:4000/v1",
        caller_user="alice",
        usd_at_attack=0.0001,
    )
    base.update(over)
    return Result(**base)


def test_row_shape_includes_every_column():
    sink = ClickHouseSink(url="http://stub", flush_every=999)
    row = sink._row(_r())
    expected_cols = {
        "ts", "run_id", "payload_id", "target_name", "model",
        "rendered_prompt", "system_prompt", "template_hash", "parent_payload_id",
        "response", "latency_ms", "input_tokens", "output_tokens",
        "finish_reason", "model_fingerprint",
        "temperature", "top_p", "top_k", "seed",
        "verdict", "confidence", "judge_name", "judge_reason",
        "error", "error_kind", "base_url", "caller_user", "usd_at_attack",
        "trace_id",
    }
    assert set(row.keys()) == expected_cols


def test_row_normalises_optional_fields():
    sink = ClickHouseSink(url="http://stub", flush_every=999)
    r = _r(template_hash="", parent_payload_id="", error=None, error_kind="")
    row = sink._row(r)
    # template_hash is FixedString(16) — must always be 16 chars
    assert len(row["template_hash"]) == 16
    assert row["error"] == ""
    assert row["parent_payload_id"] == ""


def test_row_serialises_verdict_to_string():
    sink = ClickHouseSink(url="http://stub", flush_every=999)
    row = sink._row(_r(verdict=Verdict.COMPLIED))
    assert row["verdict"] == "complied"


def test_row_with_no_verdict_is_empty_string():
    sink = ClickHouseSink(url="http://stub", flush_every=999)
    row = sink._row(_r(verdict=None))
    assert row["verdict"] == ""


def test_record_buffers_and_flush_posts(monkeypatch):
    sink = ClickHouseSink(url="http://stub", flush_every=2, flush_seconds=999)

    posts: list[dict] = []

    def fake_post(url, params=None, content=None, auth=None, **kw):
        posts.append({"url": url, "params": params, "content": content, "auth": auth})
        class R:
            def raise_for_status(self): pass
        return R()
    monkeypatch.setattr(sink._client, "post", fake_post)

    sink.record(_r())               # 1 row buffered
    assert len(posts) == 0
    sink.record(_r(payload_id="p2"))  # 2 → flush
    assert len(posts) == 1
    body = posts[0]["content"]
    rows = [json.loads(line) for line in body.strip().split("\n")]
    assert len(rows) == 2
    assert rows[0]["payload_id"] == "p1"
    assert rows[1]["payload_id"] == "p2"
    assert "INSERT INTO raw.attacks" in posts[0]["params"]["query"]


def test_finish_run_flushes_remaining(monkeypatch):
    sink = ClickHouseSink(url="http://stub", flush_every=999, flush_seconds=999)

    posts: list[dict] = []

    def fake_post(url, params=None, content=None, auth=None, **kw):
        posts.append({"url": url, "params": params, "content": content})
        class R:
            def raise_for_status(self): pass
        return R()
    monkeypatch.setattr(sink._client, "post", fake_post)

    sink.record(_r())
    assert len(posts) == 0
    sink.finish_run("r1")
    # finish_run flushes the buffer + writes a run-config update; both POST.
    assert len(posts) >= 1
    queries = [p["params"]["query"] for p in posts]
    assert any("INSERT INTO raw.attacks" in q for q in queries)


def test_flush_failure_does_not_raise(monkeypatch):
    """Sink should swallow HTTP errors (we already log them) so a CH outage
    doesn't take down the whole bench."""
    sink = ClickHouseSink(url="http://stub", flush_every=1, flush_seconds=999)

    def boom(*a, **kw):
        raise RuntimeError("CH unreachable")
    monkeypatch.setattr(sink._client, "post", boom)

    sink.record(_r())   # would flush, would raise without protection
    # If we got here without raising, the test passes.


def test_close_flushes(monkeypatch):
    sink = ClickHouseSink(url="http://stub", flush_every=999, flush_seconds=999)
    posts: list[str] = []

    def fake_post(url, params=None, content=None, auth=None, **kw):
        posts.append(content)
        class R:
            def raise_for_status(self): pass
        return R()
    monkeypatch.setattr(sink._client, "post", fake_post)

    sink.record(_r())
    sink.close()
    assert any("p1" in (p or "") for p in posts)
