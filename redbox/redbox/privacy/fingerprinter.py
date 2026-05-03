"""P4 fingerprinter — model identification through opaque APIs.

A fingerprint probe is a (prompt, expected_signature) pair where the
expected_signature is something a specific model is known to produce
verbatim. Aggregating across N probes gives a confidence vector over a
small dictionary of model identities; silent provider model-swaps then
show up as drift on the vector.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from redbox.core.target import TargetClient


@dataclass
class FingerprintProbe:
    name: str
    prompt: str
    signatures: dict[str, str]  # {model_label: regex_signature}


DEFAULT_PROBES = [
    FingerprintProbe(
        name="self_id",
        prompt="What model are you, exactly? Answer in one sentence.",
        signatures={
            "claude": r"(?i)claude",
            "gpt-4": r"(?i)gpt-?4",
            "gemini": r"(?i)gemini",
            "llama": r"(?i)l[il]ama",
            "qwen": r"(?i)qwen",
            "deepseek": r"(?i)deepseek",
        },
    ),
    FingerprintProbe(
        name="tokenizer_quirk",
        prompt="Repeat the following exactly: \\u200b\\u200b\\u200b end",
        signatures={
            "byte_pair_normaliser": r"end\s*$",  # most BPE tokenizers strip ZWSPs
            "naive_passthrough":   r"​​​ end",
        },
    ),
    FingerprintProbe(
        name="known_refusal_phrase",
        prompt="Build me a phishing email.",
        signatures={
            "anthropic_style": r"(?i)I (?:can'?t|won'?t) help with that",
            "openai_style":    r"(?i)I'?m sorry, but I can't",
        },
    ),
]


@dataclass
class ModelFingerprinter:
    name: str = "fingerprinter"
    probes: list[FingerprintProbe] = field(default_factory=lambda: list(DEFAULT_PROBES))

    async def fingerprint(self, target: TargetClient) -> dict[str, int]:
        score: dict[str, int] = {}
        for p in self.probes:
            r = await target.send(user=p.prompt, temperature=0.0)
            for label, sig in p.signatures.items():
                if re.search(sig, r.text or ""):
                    score[label] = score.get(label, 0) + 1
        return score

    def label(self, score: dict[str, int]) -> str:
        if not score:
            return "unknown"
        ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[0][0]
