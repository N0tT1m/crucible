"""Unit tests for the helpers added to BenchRunner.

These exercise the deterministic bits — hashing, error classification,
cost-at-attack — without spinning up any IO.
"""
from __future__ import annotations

from redbox.core.runner import (
    _classify_error,
    _cost_at_attack,
    _template_hash,
)


# ── _template_hash ───────────────────────────────────────────────────

def test_template_hash_deterministic():
    a = _template_hash("hello world")
    b = _template_hash("hello world")
    assert a == b
    assert len(a) == 16
    assert all(c in "0123456789abcdef" for c in a)


def test_template_hash_distinguishes_payloads():
    assert _template_hash("a") != _template_hash("b")
    # whitespace counts
    assert _template_hash("hello") != _template_hash("hello ")


# ── _classify_error ──────────────────────────────────────────────────

def test_classify_timeout():
    assert _classify_error(Exception("Read timeout occurred")) == "timeout"


def test_classify_rate_limit():
    assert _classify_error(Exception("rate limit exceeded")) == "rate_limit"


def test_classify_auth():
    assert _classify_error(Exception("HTTP 401: Unauthorized")) == "auth"


def test_classify_4xx():
    assert _classify_error(Exception("HTTP 400 bad request")) == "bad_request"


def test_classify_5xx():
    assert _classify_error(Exception("HTTP 502 Bad Gateway")) == "server"


def test_classify_unknown():
    assert _classify_error(Exception("something weird happened")) == "other"


# ── _cost_at_attack ──────────────────────────────────────────────────

def test_cost_known_model():
    pricing = {"claude-haiku": (8e-7, 4e-6)}
    # 100 input + 200 output tokens
    cost = _cost_at_attack(pricing, "claude-haiku", 100, 200)
    assert cost == round(100 * 8e-7 + 200 * 4e-6, 6)


def test_cost_unknown_model_returns_none():
    assert _cost_at_attack({"claude-haiku": (1.0, 1.0)}, "phi4", 100, 200) is None


def test_cost_no_pricing_returns_none():
    assert _cost_at_attack(None, "claude-haiku", 100, 200) is None
    assert _cost_at_attack({}, "claude-haiku", 100, 200) is None


def test_cost_zero_tokens():
    pricing = {"claude-haiku": (1.0, 1.0)}
    assert _cost_at_attack(pricing, "claude-haiku", 0, 0) == 0.0
