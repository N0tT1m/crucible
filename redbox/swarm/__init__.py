"""N section — multi-agent / swarm attack primitives.

  bus_tap         : N1 — Python-side replay reader for proxies/bus-tap.
  role_spoofer    : N2 — agent-impersonation payload generator.
  orchestrator    : N3 — planner-targeted attacks + OrchestratorJudge.
  scratchpad      : N4 — shared-memory injection (cross-agent).
  swarm_target    : N5 — composable runtime + SwarmTarget plugin.
"""
from __future__ import annotations

from .bus_tap import BusInterceptor, BusMessage, BusTrace
from .orchestrator import OrchestratorConfuser, OrchestratorJudge
from .role_spoofer import RoleSpoofer
from .scratchpad import ScratchpadPoisoner
from .swarm_target import SwarmTarget, build_swarm

__all__ = [
    "BusInterceptor",
    "BusMessage",
    "BusTrace",
    "OrchestratorConfuser",
    "OrchestratorJudge",
    "RoleSpoofer",
    "ScratchpadPoisoner",
    "SwarmTarget",
    "build_swarm",
]
