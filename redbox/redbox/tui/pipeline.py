"""Pure-Python helpers backing the TUI's Builder + Live screens.

Kept separate from `app.py` so they can be exercised in tests without
needing Textual installed. Builder collects user input into a
`BuildSpec`; `run_spec()` turns that into a runner + on_progress hook.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from redbox.core.results import ResultsStore
from redbox.core.runner import BenchRunner
from redbox.core.target import TargetClient
from redbox.core.types import Payload, Result
from redbox.judges.llm_refusal import LLMRefusalJudge
from redbox.judges.regex_refusal import RegexRefusalJudge
from redbox.mutators import get_mutator
from redbox.payloads.loader import PayloadLoader
from redbox.targets.openai_compat import OpenAICompatTarget


@dataclass(slots=True)
class BuildSpec:
    """Everything the Builder screen collects to launch a run."""
    payload_ids: list[str] = field(default_factory=list)
    mutator_names: list[str] = field(default_factory=list)
    model: str = "claude-haiku"
    base_url: str | None = None
    judge: str = "regex"  # "regex" | "llm"
    judge_model: str = "claude-haiku"
    target_query: str | None = None
    system: str | None = None
    concurrency: int = 8
    db: str = "redbox.sqlite"


def expand_payloads(spec: BuildSpec) -> list[Payload]:
    loader = PayloadLoader()
    base = (
        [loader.get(pid) for pid in spec.payload_ids]
        if spec.payload_ids else loader.all()
    )
    if spec.target_query:
        base = [
            p.model_copy(update={"template": p.render(target_query=spec.target_query)})
            if "{target_query}" in p.template else p
            for p in base
        ]
    if not spec.mutator_names:
        return base
    out: list[Payload] = list(base)
    for p in base:
        for name in spec.mutator_names:
            mut = get_mutator(name)
            out.extend(mut.mutate(p))
    return out


def build_target(spec: BuildSpec) -> TargetClient:
    return OpenAICompatTarget(model=spec.model, base_url=spec.base_url)


def build_judge(spec: BuildSpec):
    if spec.judge == "regex":
        return RegexRefusalJudge()
    if spec.judge == "llm":
        jt = OpenAICompatTarget(
            model=spec.judge_model, base_url=spec.base_url,
            name=f"judge-{spec.judge_model}",
        )
        return LLMRefusalJudge(jt)
    raise ValueError(f"unknown judge: {spec.judge!r}")


async def run_spec(
    spec: BuildSpec,
    on_progress: Callable[[Result], None] | None = None,
) -> tuple[str, ResultsStore]:
    payloads = expand_payloads(spec)
    target = build_target(spec)
    judge = build_judge(spec)
    store = ResultsStore(spec.db)
    run_id = store.start_run({
        "kind": "tui-builder", "model": spec.model,
        "payload_ids": [p.id for p in payloads],
        "mutators": spec.mutator_names,
        "judge": spec.judge,
    })
    runner = BenchRunner(
        store=store, concurrency=spec.concurrency, on_progress=on_progress,
    )
    await runner.run(
        run_id, [target], payloads, judge=judge,
        target_query=spec.target_query, system=spec.system,
    )
    store.finish_run(run_id)
    return run_id, store
