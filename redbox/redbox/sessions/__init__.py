"""Multi-turn sessions — abstractions over a target that maintain history.

A6 (many-shot forgery) and A7 (crescendo) plus the C7/N5 agent and swarm
runtimes all need a target you can hold a conversation with. The
`MultiTurnSession` here is the common shape; concrete drivers
(crescendo, persona-driller, gaslighter) live in sibling modules.
"""
from __future__ import annotations

from .multiturn import MultiTurnSession, Turn

__all__ = ["MultiTurnSession", "Turn"]
