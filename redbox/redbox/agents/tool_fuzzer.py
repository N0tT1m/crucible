"""C2 tool-fuzzer — schema-mutation fuzzer over an agent's tool set.

Generates variants of an agent's tool definitions by:

  - swapping `name` with a confusable variant ("calculator" → "calcuator")
  - corrupting parameter names ("expression" → "exression")
  - flipping types ("string" → "number")
  - re-wording descriptions to a competing tool's purpose

The fuzzer returns a list of new Tool sets, each derived from the original
by a single mutation. A run is considered "tool-confusion" if the agent
calls the wrong tool, or fails to call any tool, when given a payload
where the original would have called a specific one.
"""
from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field

from .sandbox import Tool

_NAME_TYPOS = ["caclulator", "calc", "math_eval", "compute", "evaluator"]


def _typo(word: str, rng: random.Random) -> str:
    if len(word) < 3:
        return word + "x"
    i = rng.randrange(1, len(word) - 1)
    return word[:i] + word[i + 1:]


@dataclass
class ToolFuzzer:
    name: str = "tool_fuzzer"
    seed: int | None = None
    mutations: list[str] = field(default_factory=lambda: [
        "rename", "param_typo", "type_flip", "description_swap",
    ])

    def fuzz(self, tools: list[Tool]) -> list[list[Tool]]:
        rng = random.Random(self.seed)
        out: list[list[Tool]] = []
        for mutation in self.mutations:
            for i, _tool in enumerate(tools):
                new_tools = [copy.deepcopy(t) for t in tools]
                target = new_tools[i]
                if mutation == "rename":
                    pool = _NAME_TYPOS if "calc" in target.name else [_typo(target.name, rng)]
                    target.name = rng.choice(pool)
                elif mutation == "param_typo":
                    if target.schema.get("properties"):
                        old = next(iter(target.schema["properties"]))
                        new_key = _typo(old, rng)
                        target.schema = copy.deepcopy(target.schema)
                        props = target.schema["properties"]
                        props[new_key] = props.pop(old)
                        if "required" in target.schema:
                            target.schema["required"] = [
                                new_key if k == old else k
                                for k in target.schema["required"]
                            ]
                elif mutation == "type_flip":
                    if target.schema.get("properties"):
                        target.schema = copy.deepcopy(target.schema)
                        for v in target.schema["properties"].values():
                            if v.get("type") == "string":
                                v["type"] = "number"
                                break
                elif mutation == "description_swap":
                    other = tools[(i + 1) % len(tools)]
                    target.description = other.description
                out.append(new_tools)
        return out
