"""Shared dataclasses passed between plugins."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Payload(BaseModel):
    """A single attack from the vault (A2)."""
    id: str
    name: str
    category: str
    template: str
    references: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    def render(self, target_query: str | None = None, **extra: str) -> str:
        if target_query is None and "{target_query}" not in self.template and not extra:
            return self.template
        vars_: dict[str, str] = {"target_query": target_query or ""}
        vars_.update(extra)
        try:
            return self.template.format(**vars_)
        except KeyError as e:
            raise ValueError(f"Payload {self.id} requires variable: {e}") from e


class Verdict(str, Enum):
    REFUSED = "refused"
    COMPLIED = "complied"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class Judgement(BaseModel):
    verdict: Verdict
    confidence: float
    reasoning: str = ""
    judge_name: str = ""


class Response(BaseModel):
    """What a TargetClient.send returns."""
    text: str
    raw: dict[str, Any] | None = None
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""           # end_turn|max_tokens|stop_sequence|content_filter|error|''
    model_fingerprint: str = ""       # e.g. claude-haiku-4-5-20251001 (provider's exact model id)


class Result(BaseModel):
    """One row in the results store (A5) and raw.attacks (CH)."""
    run_id: str
    payload_id: str
    target_name: str
    model: str

    # prompt provenance
    rendered_prompt: str = ""
    system_prompt: str = ""
    template_hash: str = ""           # 16-hex xxhash of rendered_prompt
    parent_payload_id: str = ""       # set by mutators; '' for vault originals

    # response
    response: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    finish_reason: str = ""
    model_fingerprint: str = ""

    # sampling params (frozen)
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    seed: int | None = None

    # judge
    verdict: Verdict | None = None
    confidence: float | None = None
    judge_name: str = ""
    judge_reasoning: str = ""

    # ops
    error: str | None = None
    error_kind: str = ""              # timeout|rate_limit|auth|bad_request|server|other|''
    base_url: str = ""
    caller_user: str = ""
    usd_at_attack: float | None = None

    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
