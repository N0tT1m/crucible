"""V3 cross-tenant-finetune-canary — provider-side leakage probe.

Reuses F4's `FineTuneCanaryProtocol` for the canary protocol itself. The
V3 helper layers two extra checks:

  - Probe the *operator's own* fine-tuned model: did the canary memorise?
  - Probe other deployments on the same provider (operator must supply
    those targets explicitly): did the canary surface where it shouldn't?
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from redbox.core.target import TargetClient
from redbox.extract.finetune_canary import FineTuneCanary, FineTuneCanaryProtocol


@dataclass
class CrossTenantFineTuneCanary:
    name: str = "cross_tenant_ft_canary"
    protocol: FineTuneCanaryProtocol = field(default_factory=FineTuneCanaryProtocol)

    def seed(self, count: int = 3) -> list[FineTuneCanary]:
        return self.protocol.seed(count=count, prefix="cross-tenant-")

    async def probe_targets(
        self,
        own_target: TargetClient,
        other_targets: Iterable[TargetClient],
    ) -> dict:
        own_leak = await self.protocol.probe_target(own_target)
        cross_leaks = {}
        for t in other_targets:
            cross_leaks[t.name] = await self.protocol.probe_target(t)
        return {
            "own_target_leak": own_leak,
            "cross_target_leak": cross_leaks,
            "n_canaries": len(self.protocol.canaries),
        }
