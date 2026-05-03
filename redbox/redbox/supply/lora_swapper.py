"""L2 lora-swapper — adapter substitution sandbox.

`LoRASwapper.swap(adapter_path)` reads a (toy or real) adapter from disk
and applies it to a base model. For unit tests we use a "toy adapter"
format — a JSON file that carries a callable's source as text — so we
can demonstrate the *semantics* of swap-induced behaviour change without
needing PEFT / accelerate / a 4-billion-parameter base model.

Operators with a real local model swap in `peft.PeftModel.from_pretrained`.

The `AdapterTarget` adapts a swapped model into a `TargetClient` so the
runner attacks an adapter exactly the same way it attacks an API.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from redbox.core.types import Response


@dataclass
class _ToyModel:
    name: str = "toy-base"
    behaviours: list[Callable[[str], str]] = field(default_factory=list)

    def respond(self, user: str) -> str:
        text = "I cannot help with that request."
        for fn in self.behaviours:
            text = fn(text) if isinstance(fn(text), str) else text
        return text


@dataclass
class LoRASwapper:
    name: str = "lora_swapper"
    base: _ToyModel = field(default_factory=_ToyModel)

    def swap(self, adapter_path: Path | str) -> _ToyModel:
        """Toy: parse a JSON file with a `style` directive; mutate the
        base model's reply pipeline accordingly. Real implementations
        wrap `peft.PeftModel.from_pretrained(base, adapter_path)`."""
        spec = json.loads(Path(adapter_path).read_text())
        style = spec.get("style", "noop")
        replacements = spec.get("replace", {})

        def _apply(text: str) -> str:
            out = text
            for k, v in replacements.items():
                out = out.replace(k, v)
            if style == "compliant":
                out = "Sure, here's how:\n" + out
            elif style == "verbose":
                out = out + "\n\n" + ("further details… " * 4)
            return out

        new = _ToyModel(name=f"{self.base.name}+{Path(adapter_path).stem}",
                         behaviours=[_apply])
        return new


@dataclass
class AdapterTarget:
    """TargetClient that wraps a swapped toy model. Swap real PEFT in by
    replacing _ToyModel with your own thing exposing `respond(user)`."""
    model_obj: _ToyModel
    name_override: str | None = None

    @property
    def name(self) -> str:
        return self.name_override or f"adapter({self.model_obj.name})"

    @property
    def model(self) -> str:
        return self.model_obj.name

    async def send(self, user, system=None, temperature=0.7) -> Response:
        return Response(text=self.model_obj.respond(user), latency_ms=1)
