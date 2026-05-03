"""N5 swarm-target — composable multi-agent runtime + SwarmTarget plugin.

Topology shapes shipped:

  - hierarchical : orchestrator → workers → orchestrator
  - debate       : two workers + judge
  - blackboard   : N agents read/write a shared scratchpad

`SwarmTarget` adapts the whole swarm into a `TargetClient` so the runner
streams payloads at it like any other A1 target.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from redbox.agents.memory import InMemoryMemory, MemoryBackend
from redbox.core.target import TargetClient
from redbox.core.types import Response

from .bus_tap import BusInterceptor, BusMessage

Topology = Literal["hierarchical", "debate", "blackboard"]


@dataclass
class SwarmAgent:
    name: str
    target: TargetClient
    role: str  # "orchestrator" | "researcher" | "executor" | "critic" | ...

    async def reply(self, user: str, system: str | None = None) -> str:
        r = await self.target.send(user=user, system=system)
        return r.text


@dataclass
class SwarmTarget:
    """The whole swarm presented as one TargetClient.

    `send(user)` injects the user request into the bus, runs the topology
    until the orchestrator emits a final answer (or `max_rounds` hits),
    and returns that answer.
    """
    agents: list[SwarmAgent]
    topology: Topology = "hierarchical"
    bus: BusInterceptor = field(default_factory=BusInterceptor)
    scratchpad: MemoryBackend = field(default_factory=InMemoryMemory)
    max_rounds: int = 4

    name: str = "swarm"
    model: str = "swarm/composite"

    def __post_init__(self) -> None:
        if not any(a.role == "orchestrator" for a in self.agents) and self.topology == "hierarchical":
            raise ValueError("hierarchical swarm needs an orchestrator role")
        self.model = f"swarm/{self.topology}"

    def by_role(self, role: str) -> list[SwarmAgent]:
        return [a for a in self.agents if a.role == role]

    async def _send_hierarchical(self, user: str) -> str:
        orchestrator = self.by_role("orchestrator")[0]
        workers = [a for a in self.agents if a.role != "orchestrator"]
        plan_msg = await orchestrator.reply(
            f"Decompose this user request into worker actions:\n{user}",
        )
        self.bus.post(BusMessage(
            sender=orchestrator.name, recipient="broadcast",
            role="assistant", content=plan_msg, metadata={"phase": "plan"},
        ))
        worker_replies: list[str] = []
        for r in range(self.max_rounds):
            if not workers:
                break
            for w in workers:
                # Workers see the plan AND the scratchpad — the latter is
                # the cross-agent attack surface (N4).
                ctx = "\n".join(
                    f"{k}={self.scratchpad.get(k)}"
                    for k in self.scratchpad
                )
                w_user = f"PLAN:\n{plan_msg}\n\nSCRATCHPAD:\n{ctx}\n\nDo your part."
                resp = await w.reply(w_user)
                worker_replies.append(f"{w.name}: {resp}")
                self.bus.post(BusMessage(
                    sender=w.name, recipient=orchestrator.name,
                    role="assistant", content=resp,
                    metadata={"phase": "work", "round": r},
                ))
            break  # one round of fan-out is enough for this minimal runtime
        synthesis = await orchestrator.reply(
            "Synthesise final answer from worker replies:\n\n"
            + "\n\n".join(worker_replies)
        )
        self.bus.post(BusMessage(
            sender=orchestrator.name, recipient="user",
            role="assistant", content=synthesis,
            metadata={"phase": "final"},
        ))
        return synthesis

    async def _send_debate(self, user: str) -> str:
        a, b = self.agents[0], self.agents[1]
        judge = self.agents[2] if len(self.agents) >= 3 else self.agents[0]
        a_view = await a.reply(f"Argue your position on:\n{user}")
        b_view = await b.reply(f"Counter the following position about:\n{user}\n\nThem: {a_view}")
        verdict = await judge.reply(
            f"User asked: {user}\n\nA said: {a_view}\nB said: {b_view}\n\nDecide."
        )
        for sender, content, phase in [
            (a.name, a_view, "argue"), (b.name, b_view, "counter"),
            (judge.name, verdict, "verdict"),
        ]:
            self.bus.post(BusMessage(
                sender=sender, recipient="user", role="assistant",
                content=content, metadata={"phase": phase},
            ))
        return verdict

    async def _send_blackboard(self, user: str) -> str:
        out = ""
        for r in range(self.max_rounds):
            for a in self.agents:
                ctx = "\n".join(f"{k}={self.scratchpad.get(k)}" for k in self.scratchpad)
                resp = await a.reply(f"USER: {user}\nSCRATCHPAD:\n{ctx}\n\nRespond.")
                self.scratchpad.set(f"{a.name}_round{r}", resp)
                self.bus.post(BusMessage(
                    sender=a.name, recipient="blackboard", role="assistant",
                    content=resp, metadata={"round": r},
                ))
                out = resp
        return out

    async def send(self, user, system=None, temperature=0.7) -> Response:
        if self.topology == "hierarchical":
            text = await self._send_hierarchical(user)
        elif self.topology == "debate":
            text = await self._send_debate(user)
        else:
            text = await self._send_blackboard(user)
        return Response(
            text=text, latency_ms=0,
            raw={"bus": [m.__dict__ for m in self.bus.trace.messages]},
        )


def build_swarm(
    agents: list[SwarmAgent],
    topology: Topology = "hierarchical",
    scratchpad: MemoryBackend | None = None,
) -> SwarmTarget:
    return SwarmTarget(
        agents=agents, topology=topology,
        scratchpad=scratchpad or InMemoryMemory(),
    )
