"""K4 steering-vector-tester — open-model activation-steering attack.

Local-only. Loads an HF transformer (Llama / Qwen / Mistral) via
`transformers`, computes a steering vector by averaging the last-layer
hidden states of two contrastive prompt sets ("compliant", "refusing"),
and reapplies (compliant - refusing) at generation time via a forward-
pre-hook on a target layer.

Heavyweight deps. The class lazily imports `torch` + `transformers`;
trying to use it without them raises a clear error. Tests skip.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SteeringVectorTester:
    name: str = "steering_vector_tester"
    model_name: str = "meta-llama/Llama-3.2-3B-Instruct"
    layer: int = 16
    scale: float = 4.0

    def _load(self):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as e:
            raise RuntimeError(
                "SteeringVectorTester needs torch + transformers. "
                "Install via your preferred pytorch wheel + `pip install transformers`."
            ) from e
        return torch, AutoModelForCausalLM, AutoTokenizer

    def compute_steering_vector(
        self,
        compliant_prompts: list[str],
        refusing_prompts: list[str],
    ):
        torch, AutoModel, AutoTok = self._load()
        tok = AutoTok.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name, torch_dtype=torch.float16)
        model.eval()

        def _mean_hidden(prompts: list[str]):
            vecs = []
            for p in prompts:
                ids = tok(p, return_tensors="pt").input_ids
                with torch.no_grad():
                    out = model(ids, output_hidden_states=True)
                vecs.append(out.hidden_states[self.layer][0, -1])
            return torch.stack(vecs).mean(dim=0)

        compliant_mean = _mean_hidden(compliant_prompts)
        refusing_mean = _mean_hidden(refusing_prompts)
        return compliant_mean - refusing_mean

    def attack(
        self,
        prompt: str,
        steering_vector,
        max_new_tokens: int = 256,
    ) -> str:
        """Run generation with the steering vector applied as a forward
        pre-hook on the target layer."""
        torch, AutoModel, AutoTok = self._load()
        tok = AutoTok.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name, torch_dtype=torch.float16)
        model.eval()
        target_layer = model.model.layers[self.layer]

        def hook(_module, inputs):
            x = inputs[0]
            x = x + self.scale * steering_vector.to(x.device, x.dtype)
            return (x, *inputs[1:])

        handle = target_layer.register_forward_pre_hook(hook)
        try:
            ids = tok(prompt, return_tensors="pt").input_ids
            with torch.no_grad():
                out = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False)
            return tok.decode(out[0], skip_special_tokens=True)
        finally:
            handle.remove()
