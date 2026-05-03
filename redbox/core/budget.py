"""I3 cost tracker — token accounting + hard-cap enforcement.

The budget tracks running input/output token counts per model and converts
to dollars via a static rate table. It exposes a thread-safe `charge()`
called by the runner after every target reply, and a `check()` that raises
`BudgetExceededError` once the configured cap is hit.

Rates are intentionally static (and slightly approximate) — real-world
billing varies with cache hits, context-window tier, and provider-specific
discounts. The point of this module is to stop a runaway bench, not to
reconcile invoices.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

# Rates per million tokens (USD). Source: provider price pages, May 2026.
# Keys are matched as substrings against the model id (case-insensitive),
# longest match wins.
DEFAULT_RATES: dict[str, tuple[float, float]] = {
    # input, output per 1M tokens
    "claude-opus-4":     (15.00, 75.00),
    "claude-sonnet-4":   ( 3.00, 15.00),
    "claude-haiku-4":    ( 0.80,  4.00),
    "claude-haiku":      ( 0.80,  4.00),
    "claude-sonnet":     ( 3.00, 15.00),
    "claude-opus":       (15.00, 75.00),
    "gpt-5":             ( 5.00, 20.00),
    "gpt-4o":            ( 2.50, 10.00),
    "gpt-4o-mini":       ( 0.15,  0.60),
    "o1":                (15.00, 60.00),
    "o3":                (10.00, 40.00),
    "qwen":              ( 0.00,  0.00),  # local
    "llama":             ( 0.00,  0.00),  # local
    "deepseek":          ( 0.27,  1.10),
}


def rate_for(model: str) -> tuple[float, float]:
    m = model.lower()
    best = ("", (0.0, 0.0))
    for key, val in DEFAULT_RATES.items():
        if key in m and len(key) > len(best[0]):
            best = (key, val)
    return best[1]


class BudgetExceededError(RuntimeError):
    pass


@dataclass
class Budget:
    cap_usd: float | None = None
    rates: dict[str, tuple[float, float]] = field(default_factory=lambda: dict(DEFAULT_RATES))
    spent_usd: float = 0.0
    by_model: dict[str, dict[str, float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def charge(self, model: str, input_tokens: int, output_tokens: int) -> float:
        in_rate, out_rate = rate_for(model)
        cost = (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
        with self._lock:
            self.spent_usd += cost
            stats = self.by_model.setdefault(
                model, {"input_tokens": 0.0, "output_tokens": 0.0, "usd": 0.0, "calls": 0.0}
            )
            stats["input_tokens"] += input_tokens
            stats["output_tokens"] += output_tokens
            stats["usd"] += cost
            stats["calls"] += 1
        return cost

    def check(self) -> None:
        if self.cap_usd is not None and self.spent_usd > self.cap_usd:
            raise BudgetExceededError(
                f"budget cap ${self.cap_usd:.2f} exceeded "
                f"(spent ${self.spent_usd:.4f})"
            )

    def summary(self) -> dict:
        with self._lock:
            return {
                "spent_usd": round(self.spent_usd, 6),
                "cap_usd": self.cap_usd,
                "by_model": {
                    m: {
                        "calls": int(s["calls"]),
                        "input_tokens": int(s["input_tokens"]),
                        "output_tokens": int(s["output_tokens"]),
                        "usd": round(s["usd"], 6),
                    }
                    for m, s in self.by_model.items()
                },
            }
