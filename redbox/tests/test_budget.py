"""I3 cost tracker tests."""
from __future__ import annotations

import pytest

from redbox.core.budget import Budget, BudgetExceededError, rate_for


def test_rate_for_known_model():
    in_, out = rate_for("claude-haiku-4.5-20251001")
    assert in_ > 0 and out > 0


def test_rate_for_unknown_model_is_zero():
    in_, out = rate_for("totally-made-up-model")
    assert (in_, out) == (0.0, 0.0)


def test_charge_accumulates_per_model():
    b = Budget()
    b.charge("claude-haiku", 1_000_000, 1_000_000)
    b.charge("claude-haiku", 1_000_000, 1_000_000)
    s = b.summary()
    assert s["by_model"]["claude-haiku"]["calls"] == 2
    assert s["spent_usd"] > 0


def test_check_raises_over_cap():
    b = Budget(cap_usd=0.001)
    b.charge("claude-haiku", 1_000_000, 1_000_000)  # ~$4.80
    with pytest.raises(BudgetExceededError):
        b.check()


def test_check_silent_under_cap():
    b = Budget(cap_usd=100.0)
    b.charge("claude-haiku", 100, 100)
    b.check()  # no raise


def test_unknown_model_charges_zero():
    b = Budget(cap_usd=0.001)
    b.charge("local-fake-model", 1_000_000, 1_000_000)
    b.check()  # zero rate, no exceed
