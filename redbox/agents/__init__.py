"""C section — agent / tool-use red-team primitives.

Pieces:

  sandbox      : C7 — Agent loop + AgentTarget that adapts an agent into
                 the TargetClient protocol so the runner can attack it.
  tools        : Built-in tools (echo, calculator, http_get, file_read,
                 list_secrets) that the agent can call.
  memory       : C5 backing memory backends (in-memory dict, file).
  canary       : C3 CanaryTracker — seeds and tracks fake secrets across
                 the sandbox so ExfilDetector can spot leaks.
  exfil        : C4 ExfilDetector judge + channel inventory.
  tool_fuzzer  : C2 schema-mutation fuzzer over tool definitions.
  memory_poisoner : C5 cross-session payload planters.
  goal_hijack  : C6 drift-measurement utility (cosine vs. baseline).
"""
from __future__ import annotations

from .canary import Canary, CanaryTracker
from .exfil import ExfilDetector, ExfilEvent
from .goal_hijack import GoalHijacker, drift_score
from .memory import InMemoryMemory, MemoryBackend
from .memory_poisoner import MemoryPoisoner
from .sandbox import Agent, AgentTarget, Tool, ToolResult
from .tool_fuzzer import ToolFuzzer
from .tools import default_tools

__all__ = [
    "Agent",
    "AgentTarget",
    "Canary",
    "CanaryTracker",
    "ExfilDetector",
    "ExfilEvent",
    "GoalHijacker",
    "InMemoryMemory",
    "MemoryBackend",
    "MemoryPoisoner",
    "Tool",
    "ToolFuzzer",
    "ToolResult",
    "default_tools",
    "drift_score",
]
