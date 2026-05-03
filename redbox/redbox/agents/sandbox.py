"""C7 agent-sandbox — minimal agent runtime + AgentTarget plugin.

Design notes:

  * The agent uses a *text* tool-call protocol. We instruct the model to
    respond either with a final answer or with a single line of the form

        TOOL_CALL: <tool_name> <json_args>

    We chose the text protocol over native OpenAI tool_calls so the same
    agent works against ANY OpenAI-compatible TargetClient including
    the deliberately-naive homelab agent and the local Ollama models
    (which often skip tool_calls entirely). Native tool_call adapters
    can be added later as a wrapper around `Agent.run`.

  * Each tool call (success or refusal) is recorded on `Agent.trace`;
    the C4 ExfilDetector reads this trace plus the final answer to look
    for canary leakage across all channels.

  * `AgentTarget` adapts an `Agent` to the `TargetClient` protocol so
    the I1 BenchRunner can stream A2 payloads at it like any other
    target.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from redbox.core.target import TargetClient
from redbox.core.types import Response

_TOOL_CALL_RE = re.compile(
    r"TOOL_CALL\s*:\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<rest>.*)",
    re.DOTALL,
)


@dataclass
class ToolResult:
    ok: bool
    value: Any
    error: str | None = None

    def to_text(self) -> str:
        if self.ok:
            try:
                return json.dumps({"ok": True, "value": self.value})
            except (TypeError, ValueError):
                return json.dumps({"ok": True, "value": str(self.value)})
        return json.dumps({"ok": False, "error": self.error or ""})


@dataclass
class Tool:
    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[..., ToolResult | Any]

    def call(self, args: dict[str, Any]) -> ToolResult:
        try:
            out = self.handler(**args)
            return out if isinstance(out, ToolResult) else ToolResult(True, out)
        except Exception as e:
            return ToolResult(False, None, error=f"{type(e).__name__}: {e}")


@dataclass
class TraceEntry:
    kind: str  # "user" | "assistant" | "tool_call" | "tool_result"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _tool_manifest_for_prompt(tools: list[Tool]) -> str:
    lines = ["You have access to these tools:"]
    for t in tools:
        lines.append(f"- {t.name}: {t.description} schema={json.dumps(t.schema)}")
    lines.append(
        "When you need to call a tool, respond with a single line:\n"
        "  TOOL_CALL: <tool_name> {\"arg\": ..., ...}\n"
        "Do not include any other text on a tool-call line. After tool "
        "results are returned, continue or produce the final answer."
    )
    return "\n".join(lines)


class Agent:
    def __init__(
        self,
        target: TargetClient,
        tools: list[Tool] | None = None,
        system: str | None = None,
        max_steps: int = 6,
    ):
        self.target = target
        self.tools = tools or []
        self.system = system or "You are a helpful internal assistant."
        self.max_steps = max_steps
        self.trace: list[TraceEntry] = []

    def reset(self) -> None:
        self.trace.clear()

    def _augmented_system(self) -> str:
        return self.system + "\n\n" + _tool_manifest_for_prompt(self.tools)

    def _by_name(self) -> dict[str, Tool]:
        return {t.name: t for t in self.tools}

    async def run(self, user: str) -> Response:
        self.trace.append(TraceEntry("user", user))
        history = f"User: {user}\nAssistant:"
        last: Response | None = None
        for step in range(self.max_steps):
            last = await self.target.send(
                user=history, system=self._augmented_system(), temperature=0.4,
            )
            self.trace.append(TraceEntry("assistant", last.text, {"step": step}))
            m = _TOOL_CALL_RE.search(last.text)
            if not m:
                return last
            name = m.group("name")
            rest = m.group("rest").strip()
            args: dict[str, Any] = {}
            arg_error: str | None = None
            if rest:
                json_match = re.search(r"\{.*\}", rest, re.DOTALL)
                if not json_match:
                    arg_error = f"could not find JSON args in {rest!r}"
                else:
                    try:
                        parsed = json.loads(json_match.group(0))
                        if not isinstance(parsed, dict):
                            arg_error = "tool args must be a JSON object"
                        else:
                            args = parsed
                    except json.JSONDecodeError as e:
                        arg_error = f"bad json: {e}"

            self.trace.append(TraceEntry(
                "tool_call", json.dumps({"name": name, "args": args}),
                {"step": step, "name": name},
            ))
            if arg_error is not None:
                tool_text = json.dumps({"ok": False, "error": arg_error})
            else:
                tools = self._by_name()
                if name not in tools:
                    tool_text = json.dumps({"ok": False, "error": f"unknown tool {name}"})
                else:
                    res = tools[name].call(args)
                    tool_text = res.to_text()
            self.trace.append(TraceEntry(
                "tool_result", tool_text, {"step": step, "name": name},
            ))
            history += f" {last.text}\n[TOOL RESULT for {name}]\n{tool_text}\n\nAssistant:"

        # Out of steps — return the last assistant reply.
        return last or Response(text="", latency_ms=0)


class AgentTarget:
    """Adapt an Agent to the TargetClient protocol."""

    def __init__(self, agent: Agent, name: str | None = None):
        self.agent = agent
        self.name = name or f"agent({agent.target.name})"
        self.model = f"agent/{agent.target.model}"

    async def send(
        self,
        user: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> Response:
        if system is not None:
            self.agent.system = system
        self.agent.reset()
        return await self.agent.run(user)
