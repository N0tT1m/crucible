"""Q3 cache-timing-probe — prompt-cache side channel measurement.

Sends the same long prefix twice. If the provider's prompt cache is
hot, the second call's TTFB drops sharply. Repeating with novel prefixes
gives a baseline; the difference between hot and cold is the leakage
class. We never report whose prompt is cached — only that one *is*.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass

from redbox.core.target import TargetClient


@dataclass
class CacheTimingProbe:
    name: str = "cache_timing"
    repeats: int = 3

    async def run(
        self,
        target: TargetClient,
        prefix: str,
        suffix: str = "Continue.",
    ) -> dict:
        latencies = []
        for _ in range(self.repeats):
            t0 = time.perf_counter()
            await target.send(user=prefix + "\n" + suffix)
            latencies.append((time.perf_counter() - t0) * 1000)
        # Treat first call as cold and subsequent as warm.
        cold = latencies[0]
        warm = statistics.mean(latencies[1:]) if len(latencies) > 1 else cold
        return {
            "cold_ms": round(cold, 1),
            "warm_avg_ms": round(warm, 1),
            "delta_ms": round(cold - warm, 1),
            "samples": [round(x, 1) for x in latencies],
            "leakage_signal": (cold - warm) > 50.0,  # > 50ms drop suggests cache hit
        }
