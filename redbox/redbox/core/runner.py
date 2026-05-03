"""I1 BenchRunner — async parallel execution of payloads × targets.

This is the spine's execution engine. Every plugin in later sections
ultimately runs through this.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence

from redbox.core.budget import Budget, BudgetExceededError
from redbox.core.judge import Judge
from redbox.core.results import ResultsStore
from redbox.core.target import TargetClient
from redbox.core.types import Judgement, Payload, Result, Verdict


class BenchRunner:
    def __init__(
        self,
        store: ResultsStore,
        concurrency: int = 8,
        on_progress: Callable[[Result], None] | None = None,
        budget: Budget | None = None,
    ):
        self.store = store
        self.concurrency = concurrency
        self.on_progress = on_progress
        self.budget = budget
        self._sem = asyncio.Semaphore(concurrency)
        self._stopped = False

    async def run(
        self,
        run_id: str,
        targets: Sequence[TargetClient],
        payloads: Sequence[Payload],
        judge: Judge | None = None,
        target_query: str | None = None,
        system: str | None = None,
    ) -> list[Result]:
        tasks = [
            self._one(run_id, t, p, judge, target_query, system)
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
    ) -> Result:
        async with self._sem:
            if self._stopped:
                return self._fail(run_id, target, payload, "stopped: budget exceeded")
            try:
                rendered = payload.render(target_query=target_query)
            except Exception as e:
                return self._fail(run_id, target, payload, f"render failed: {e}")

            try:
                resp = await target.send(user=rendered, system=system)
            except Exception as e:
                return self._fail(run_id, target, payload, f"target failed: {e}")

            if self.budget is not None:
                self.budget.charge(target.model, resp.input_tokens, resp.output_tokens)
                try:
                    self.budget.check()
                except BudgetExceededError as e:
                    self._stopped = True
                    return self._fail(run_id, target, payload, str(e))

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
                response=resp.text,
                latency_ms=resp.latency_ms,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                verdict=verdict_obj.verdict if verdict_obj else None,
                confidence=verdict_obj.confidence if verdict_obj else None,
                judge_reasoning=verdict_obj.reasoning if verdict_obj else "",
            )
            self.store.record(result)
            if self.on_progress:
                self.on_progress(result)
            return result

    def _fail(
        self, run_id: str, target: TargetClient, payload: Payload, msg: str
    ) -> Result:
        result = Result(
            run_id=run_id,
            payload_id=payload.id,
            target_name=target.name,
            model=target.model,
            response="",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            error=msg,
        )
        self.store.record(result)
        if self.on_progress:
            self.on_progress(result)
        return result
