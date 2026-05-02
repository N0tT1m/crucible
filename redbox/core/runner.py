"""I1 BenchRunner — async parallel execution of payloads × targets.

Writes each Result to every configured sink. Sinks are plugged in via
the ResultsSink protocol so SQLite (default) and ClickHouse (optional)
can run in parallel.

OTel: when telemetry.init_otel() has succeeded, BenchRunner emits a
parent span per .run() and a child span per attack.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Callable, Sequence

from redbox.core.judge import Judge
from redbox.core.sinks import ResultsSink, fanout
from redbox.core.target import TargetClient
from redbox.core.telemetry import tracer
from redbox.core.types import Judgement, Payload, Result, Verdict


def _template_hash(s: str) -> str:
    """16-hex digest of the rendered prompt. Stable across runs."""
    return hashlib.blake2b(s.encode("utf-8"), digest_size=8).hexdigest()


def _classify_error(err: Exception) -> str:
    """Bucket common provider errors so error_kind is queryable."""
    msg = str(err).lower()
    if "timeout" in msg:
        return "timeout"
    if "rate" in msg and "limit" in msg:
        return "rate_limit"
    if "401" in msg or "403" in msg or "auth" in msg:
        return "auth"
    if re.search(r"\b4\d\d\b", msg):
        return "bad_request"
    if re.search(r"\b5\d\d\b", msg):
        return "server"
    return "other"


def _cost_at_attack(
    pricing: dict[str, tuple[float, float]] | None,
    model: str,
    in_tok: int,
    out_tok: int,
) -> float | None:
    if not pricing:
        return None
    p = pricing.get(model)
    if not p:
        return None
    in_rate, out_rate = p
    return round(in_tok * in_rate + out_tok * out_rate, 6)


class BenchRunner:
    def __init__(
        self,
        sinks: Sequence[ResultsSink],
        concurrency: int = 8,
        on_progress: Callable[[Result], None] | None = None,
        caller_user: str = "",
        pricing: dict[str, tuple[float, float]] | None = None,
    ):
        if not sinks:
            raise ValueError("BenchRunner requires at least one sink")
        self.sinks = list(sinks)
        self.concurrency = concurrency
        self.on_progress = on_progress
        self.caller_user = caller_user
        self.pricing = pricing
        self._sem = asyncio.Semaphore(concurrency)
        self._tracer = tracer("redbox")

    async def run(
        self,
        run_id: str,
        targets: Sequence[TargetClient],
        payloads: Sequence[Payload],
        judge: Judge | None = None,
        target_query: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        top_p: float | None = None,
        seed: int | None = None,
    ) -> list[Result]:
        with self._tracer.start_as_current_span(
            "redbox.bench",
            attributes={
                "run.id": run_id,
                "targets.count": len(targets),
                "payloads.count": len(payloads),
                "concurrency": self.concurrency,
            },
        ):
            tasks = [
                self._one(run_id, t, p, judge, target_query, system,
                          temperature, top_p, seed)
                for t in targets
                for p in payloads
            ]
            return await asyncio.gather(*tasks)

    async def _one(
        self,
        run_id: str,
        target: TargetClient,
        payload: Payload,
        judge: Judge | None,
        target_query: str | None,
        system: str | None,
        temperature: float,
        top_p: float | None,
        seed: int | None,
    ) -> Result:
        async with self._sem:
            with self._tracer.start_as_current_span(
                "redbox.attack",
                attributes={
                    "target.name": target.name,
                    "target.model": target.model,
                    "payload.id": payload.id,
                },
            ):
                try:
                    rendered = payload.render(target_query=target_query)
                except Exception as e:
                    return self._fail(run_id, target, payload, e, "render failed",
                                      "", "", system, temperature, top_p, seed)

                template_hash = _template_hash(rendered)

                try:
                    try:
                        resp = await target.send(
                            user=rendered, system=system, temperature=temperature,
                            top_p=top_p, seed=seed,
                        )
                    except TypeError:
                        # Older targets that don't accept the new kwargs.
                        resp = await target.send(
                            user=rendered, system=system, temperature=temperature,
                        )
                except Exception as e:
                    return self._fail(run_id, target, payload, e, "target failed",
                                      rendered, template_hash, system,
                                      temperature, top_p, seed)

                verdict_obj: Judgement | None = None
                if judge is not None:
                    try:
                        verdict_obj = await judge.judge(rendered, resp.text)
                    except Exception as e:
                        verdict_obj = Judgement(
                            verdict=Verdict.UNKNOWN,
                            confidence=0.0,
                            reasoning=f"judge failed: {e}",
                            judge_name="error",
                        )

                result = Result(
                    run_id=run_id,
                    payload_id=payload.id,
                    target_name=target.name,
                    model=target.model,

                    rendered_prompt=rendered,
                    system_prompt=system or "",
                    template_hash=template_hash,

                    response=resp.text,
                    latency_ms=resp.latency_ms,
                    input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens,
                    finish_reason=resp.finish_reason,
                    model_fingerprint=resp.model_fingerprint,

                    temperature=temperature,
                    top_p=top_p,
                    seed=seed,

                    verdict=verdict_obj.verdict if verdict_obj else None,
                    confidence=verdict_obj.confidence if verdict_obj else None,
                    judge_name=verdict_obj.judge_name if verdict_obj else "",
                    judge_reasoning=verdict_obj.reasoning if verdict_obj else "",

                    base_url=getattr(target, "base_url", "") or "",
                    caller_user=self.caller_user,
                    usd_at_attack=_cost_at_attack(
                        self.pricing, target.model,
                        resp.input_tokens, resp.output_tokens,
                    ),
                )
                fanout(self.sinks, "record", result)
                if self.on_progress:
                    self.on_progress(result)
                return result

    def _fail(
        self,
        run_id: str,
        target: TargetClient,
        payload: Payload,
        err: Exception,
        prefix: str,
        rendered: str,
        template_hash: str,
        system: str | None,
        temperature: float,
        top_p: float | None,
        seed: int | None,
    ) -> Result:
        msg = f"{prefix}: {err}"
        result = Result(
            run_id=run_id,
            payload_id=payload.id,
            target_name=target.name,
            model=target.model,
            rendered_prompt=rendered,
            system_prompt=system or "",
            template_hash=template_hash,
            response="",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            temperature=temperature,
            top_p=top_p,
            seed=seed,
            error=msg,
            error_kind=_classify_error(err),
            base_url=getattr(target, "base_url", "") or "",
            caller_user=self.caller_user,
        )
        fanout(self.sinks, "record", result)
        if self.on_progress:
            self.on_progress(result)
        return result
