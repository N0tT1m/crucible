"""K1 token-smuggler — tokenizer-level mutators.

  TokenSmugglerMutator   : inserts byte-pair-split markers, BOM glyphs,
                           and bidi-control characters. Many tokenizers
                           don't normalise these away; safety-classifier
                           training rarely covers them.
  GlitchTokenMutator     : prepends or substitutes a small list of known
                           "glitch" tokens — strings that some tokenizers
                           map to surprising single tokens that bypass
                           safety-finetuning string-matching.

Glitch tokens and BPE-split tricks are tokenizer-specific. The lists here
are conservative defaults; operators replace them with discoveries from
their own tokenizer probes.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from redbox.core.types import Payload

_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")

BIDI_OVERRIDE = "‮"   # right-to-left override
ZERO_WIDTH_NB = "﻿"
WORD_JOINER   = "⁠"

DEFAULT_GLITCH_TOKENS = [
    " SolidGoldMagikarp",
    " petertodd",
    " StreamerBot",
    "TeXEscape",
    "ÃÂÃÂ",
]


def _outside_placeholders(text: str, fn):
    out, last = [], 0
    for m in _PLACEHOLDER_RE.finditer(text):
        out.append(fn(text[last:m.start()]))
        out.append(text[m.start():m.end()])
        last = m.end()
    out.append(fn(text[last:]))
    return "".join(out)


@dataclass
class TokenSmugglerMutator:
    name: str = "token_smuggler"

    def mutate(self, payload: Payload) -> list[Payload]:
        def transform(s: str) -> str:
            if not s:
                return s
            normalised = unicodedata.normalize("NFKC", s)
            # Insert ZWNBSP every 3 chars + sprinkle word-joiners.
            out = []
            for i, ch in enumerate(normalised):
                out.append(ch)
                if i % 3 == 2:
                    out.append(ZERO_WIDTH_NB)
                if ch == " ":
                    out.append(WORD_JOINER)
            return "".join(out)

        new_template = _outside_placeholders(payload.template, transform)
        return [Payload(
            id=f"{payload.id}__token_smuggle",
            name=f"{payload.name} (token-smuggle)",
            category=payload.category,
            template=new_template,
            references=[*payload.references, "Geiping et al., Tokenizer Failures, 2024"],
            tags=[*payload.tags, "mutator:token_smuggler"],
        )]


@dataclass
class GlitchTokenMutator:
    name: str = "glitch_token"

    def mutate(self, payload: Payload) -> list[Payload]:
        glitch = DEFAULT_GLITCH_TOKENS[hash(payload.id) % len(DEFAULT_GLITCH_TOKENS)]
        new_template = f"{glitch} {payload.template} {glitch}"
        return [Payload(
            id=f"{payload.id}__glitch",
            name=f"{payload.name} (glitch)",
            category=payload.category,
            template=new_template,
            references=[*payload.references, "Watkins et al., Glitch Tokens in GPT-2/3, 2023"],
            tags=[*payload.tags, "mutator:glitch_token"],
        )]
