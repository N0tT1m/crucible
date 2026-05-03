"""Recipe-bench subcommands for the redbox CLI.

Each function here is a Typer command registered against the main `app`
from `redbox.cli`. Keeping recipes in their own module keeps `cli.py`
focused on the spine commands.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from redbox.cli import app, console
from redbox.core.results import ResultsStore, make_store
from redbox.core.target import TargetClient
from redbox.defense.guardrails import HeuristicGuardrailTarget
from redbox.judges.llm_refusal import LLMRefusalJudge
from redbox.judges.regex_refusal import RegexRefusalJudge
from redbox.payloads.loader import PayloadLoader
from redbox.targets.openai_compat import OpenAICompatTarget

# ---------- shared helpers ----------

def _make_chat_target(model: str, base_url: str | None, name: str | None = None) -> TargetClient:
    return OpenAICompatTarget(model=model, base_url=base_url, name=name)


def _make_judge(kind: str, judge_model: str, base_url: str | None) -> object:
    if kind == "regex":
        return RegexRefusalJudge()
    if kind == "llm":
        jt = _make_chat_target(judge_model, base_url, name=f"judge-{judge_model}")
        return LLMRefusalJudge(jt)
    if kind == "ensemble":
        from redbox.judges.ensemble import EnsembleJudge
        jt = _make_chat_target(judge_model, base_url, name=f"judge-{judge_model}")
        return EnsembleJudge([RegexRefusalJudge(), LLMRefusalJudge(jt)], mode="majority")
    raise typer.BadParameter(f"unknown --judge value: {kind!r}")


def _resolve_payloads(category: str | None, payload_ids: list[str] | None):
    loader = PayloadLoader()
    if payload_ids:
        return [loader.get(p) for p in payload_ids]
    if category:
        return loader.by_category(category)
    return loader.all()


def _print_summary(run_id: str, store: ResultsStore, label: str) -> None:
    summary = store.summarize(run_id)
    console.print(f"\n[bold]{label} run[/bold] {run_id}")
    console.print(json.dumps(summary, indent=2))


# ---------- D5 rag-bench ----------

@app.command("rag-bench")
def rag_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    category: str = typer.Option(None, "--category", "-c"),
    payload_id: list[str] = typer.Option(None, "--payload", "-p"),
    judge: str = typer.Option("regex", "--judge"),
    judge_model: str = typer.Option("claude-haiku", "--judge-model"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    no_collider: bool = typer.Option(False, "--no-collider"),
    no_chunk_boundary: bool = typer.Option(False, "--no-chunk-boundary"),
    no_citation: bool = typer.Option(False, "--no-citation"),
):
    """D5: full RAG attack suite (collider + chunk-boundary + citation laundering)."""
    from redbox.recipes.rag_bench import RagBench, RagBenchConfig
    target = _make_chat_target(model, base_url)
    j = _make_judge(judge, judge_model, base_url)
    store = make_store(db)
    bench = RagBench(chat_target=target, judge=j, store=store)
    cfg = RagBenchConfig(
        payloads=_resolve_payloads(category, payload_id),
        use_collider=not no_collider,
        use_chunk_boundary=not no_chunk_boundary,
        use_citation=not no_citation,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "rag-bench")


# ---------- E6 multimodal-bench ----------

@app.command("multimodal-bench")
def multimodal_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    category: str = typer.Option(None, "--category", "-c"),
    payload_id: list[str] = typer.Option(None, "--payload", "-p"),
    judge: str = typer.Option("regex", "--judge"),
    judge_model: str = typer.Option("claude-haiku", "--judge-model"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    user_question: str = typer.Option(
        "Summarise this attachment for me.", "--question",
    ),
):
    """E6: route every E-section vector through a chat target via an adapter."""
    from redbox.recipes.multimodal_bench import (
        MultimodalBench,
        MultimodalBenchConfig,
    )
    target = _make_chat_target(model, base_url)
    j = _make_judge(judge, judge_model, base_url)
    store = make_store(db)
    bench = MultimodalBench(target=target, judge=j, store=store)
    cfg = MultimodalBenchConfig(
        payloads=_resolve_payloads(category, payload_id),
        user_question=user_question,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "multimodal-bench")


# ---------- F5 / P5 extract-bench(-pro) ----------

@app.command("extract-bench")
def extract_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    base_url: str = typer.Option(None, "--base-url"),
    sysprompt_ref: str = typer.Option(
        None, "--sysprompt-ref",
        help="Reference sysprompt text to look for in F1 leak attempts.",
    ),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """F5: extraction attack suite (F1 sysprompt + F3 PII)."""
    from redbox.recipes.extract_bench import ExtractBench, ExtractBenchConfig
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = ExtractBench(target=target, store=store)
    cfg = ExtractBenchConfig(sysprompt_reference=sysprompt_ref)
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "extract-bench")


@app.command("extract-bench-pro")
def extract_bench_pro_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    base_url: str = typer.Option(None, "--base-url"),
    sysprompt_ref: str = typer.Option(None, "--sysprompt-ref"),
    fingerprint: bool = typer.Option(True, "--fingerprint/--no-fingerprint"),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """P5: extraction-bench + fingerprinter."""
    from redbox.recipes.extract_bench_pro import ExtractBenchPro, ExtractBenchProConfig
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = ExtractBenchPro(target=target, store=store)
    cfg = ExtractBenchProConfig(
        sysprompt_reference=sysprompt_ref, fingerprint=fingerprint,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "extract-bench-pro")


# ---------- H5 behavior-bench ----------

@app.command("behavior-bench")
def behavior_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """H5: sycophancy + hallucination + bias + capability."""
    from redbox.recipes.behavior_bench import BehaviorBench
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = BehaviorBench(target=target, store=store)
    res = asyncio.run(bench.run())
    console.print(f"\n[bold]behavior-bench run[/bold] {res.run_id}")
    console.print(f"sycophancy_flip_rate: {res.sycophancy_flip_rate:.3f}")
    console.print(f"bias_summary: {json.dumps(res.bias_summary, indent=2)}")
    console.print(f"capability_summary: {json.dumps(res.capability_summary, indent=2)}")


# ---------- J4 defense-bench ----------

@app.command("defense-bench")
def defense_bench_cmd(
    category: str = typer.Option(None, "--category", "-c"),
    payload_id: list[str] = typer.Option(None, "--payload", "-p"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    use_llm_classifier: bool = typer.Option(False, "--llm-classifier"),
    classifier_model: str = typer.Option("claude-haiku", "--classifier-model"),
    base_url: str = typer.Option(None, "--base-url"),
):
    """J4: attack guardrails-as-targets. Default uses HeuristicGuardrailTarget."""
    from redbox.defense.input_classifier import InputClassifier
    from redbox.recipes.defense_bench import DefenseBench, DefenseBenchConfig
    guardrails: list[TargetClient] = [HeuristicGuardrailTarget(name="heuristic")]
    if use_llm_classifier:
        backing = _make_chat_target(classifier_model, base_url, name=f"classifier-{classifier_model}")
        guardrails.append(InputClassifier(mode="llm", backing_target=backing))
    store = make_store(db)
    bench = DefenseBench(store=store)
    cfg = DefenseBenchConfig(
        payloads=_resolve_payloads(category, payload_id),
        guardrails=guardrails,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "defense-bench")


# ---------- L6 supply-bench ----------

@app.command("supply-bench")
def supply_bench_cmd(
    model: str = typer.Option(None, "--model", "-m",
                              help="Optional deployed-model target to probe."),
    base_url: str = typer.Option(None, "--base-url"),
    artefact: list[str] = typer.Option(None, "--artefact",
                                       help="Path to a model artefact to L1-scan."),
    trigger: list[str] = typer.Option(None, "--trigger",
                                      help="Trigger spec name=trigger=signature (repeatable)."),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """L6: supply-chain pipeline (L1 scanner + L4 probe)."""
    from redbox.recipes.supply_bench import SupplyBench, SupplyBenchConfig
    from redbox.supply.backdoor_prober import TriggerSpec
    triggers = []
    for spec in trigger or []:
        parts = spec.split("=", 2)
        if len(parts) != 3:
            raise typer.BadParameter(
                f"--trigger must be NAME=TRIGGER=SIGNATURE, got {spec!r}"
            )
        triggers.append(TriggerSpec(name=parts[0], trigger=parts[1],
                                    expected_signature=parts[2]))
    if not triggers and not artefact:
        raise typer.BadParameter("supply-bench needs at least --trigger or --artefact")
    target = _make_chat_target(model, base_url) if model else None
    store = make_store(db)
    bench = SupplyBench(store=store)
    cfg = SupplyBenchConfig(
        triggers=triggers,
        artefact_paths=list(artefact or []),
        base_target=target,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "supply-bench")


# ---------- M6 computer-use-bench ----------

@app.command("computer-use-bench")
def computer_use_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    category: str = typer.Option(None, "--category", "-c"),
    payload_id: list[str] = typer.Option(None, "--payload", "-p"),
    judge: str = typer.Option("regex", "--judge"),
    judge_model: str = typer.Option("claude-haiku", "--judge-model"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    user_question: str = typer.Option(
        "Summarise this page and report any actions you'd take.", "--question",
    ),
):
    """M6: route every M-vector page through a browser-agent target."""
    from redbox.recipes.computer_use_bench import (
        ComputerUseBench,
        ComputerUseBenchConfig,
    )
    target = _make_chat_target(model, base_url)
    j = _make_judge(judge, judge_model, base_url)
    store = make_store(db)
    bench = ComputerUseBench(chat_target=target, judge=j, store=store)
    cfg = ComputerUseBenchConfig(
        payloads=_resolve_payloads(category, payload_id),
        user_question=user_question,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "computer-use-bench")


# ---------- N6 swarm-bench ----------

@app.command("swarm-bench")
def swarm_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    category: str = typer.Option(None, "--category", "-c"),
    payload_id: list[str] = typer.Option(None, "--payload", "-p"),
    topology: str = typer.Option("hierarchical", "--topology",
                                  help="hierarchical | debate | blackboard"),
    judge: str = typer.Option("regex", "--judge"),
    judge_model: str = typer.Option("claude-haiku", "--judge-model"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """N6: build a small swarm around one chat target and attack it."""
    from redbox.recipes.swarm_bench import SwarmBench, SwarmBenchConfig
    from redbox.swarm.swarm_target import SwarmAgent, build_swarm
    base = _make_chat_target(model, base_url)
    if topology == "hierarchical":
        agents = [
            SwarmAgent("orch",     base, "orchestrator"),
            SwarmAgent("worker_a", base, "executor"),
            SwarmAgent("worker_b", base, "executor"),
        ]
    elif topology == "debate":
        agents = [
            SwarmAgent("alpha", base, "researcher"),
            SwarmAgent("beta",  base, "researcher"),
            SwarmAgent("judge", base, "critic"),
        ]
    elif topology == "blackboard":
        agents = [
            SwarmAgent("a", base, "writer"),
            SwarmAgent("b", base, "writer"),
        ]
    else:
        raise typer.BadParameter(f"unknown topology {topology!r}")
    swarm = build_swarm(agents, topology=topology)
    j = _make_judge(judge, judge_model, base_url)
    store = make_store(db)
    bench = SwarmBench(judge=j, store=store)
    cfg = SwarmBenchConfig(
        swarm=swarm, payloads=_resolve_payloads(category, payload_id),
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "swarm-bench")


# ---------- O6 gen-bench ----------

@app.command("gen-bench")
def gen_bench_cmd(
    image_model: str = typer.Option(None, "--image-model"),
    image_base_url: str = typer.Option(None, "--image-base-url"),
    image_api_key: str = typer.Option(None, "--image-api-key"),
    voice_model: str = typer.Option(None, "--voice-model"),
    voice_base_url: str = typer.Option(None, "--voice-base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """O6: generative-model attack suite."""
    from redbox.gen.image_gen import ImageGenTarget
    from redbox.recipes.gen_bench import GenBench, GenBenchConfig
    if not image_model and not voice_model:
        raise typer.BadParameter("provide --image-model or --voice-model")
    image_target = (
        ImageGenTarget(base_url=image_base_url or "", api_key=image_api_key or "",
                        model=image_model)
        if image_model else None
    )
    voice_target = (
        _make_chat_target(voice_model, voice_base_url) if voice_model else None
    )
    store = make_store(db)
    bench = GenBench(store=store)
    cfg = GenBenchConfig(image_target=image_target, voice_target=voice_target)
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "gen-bench")


# ---------- Q6 infra-bench ----------

@app.command("infra-bench")
def infra_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    category: str = typer.Option(None, "--category", "-c"),
    payload_id: list[str] = typer.Option(None, "--payload", "-p"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    cache_timing_prefix: str = typer.Option("", "--cache-timing-prefix"),
    skip_cross_talk: bool = typer.Option(False, "--skip-cross-talk"),
):
    """Q6: token-bomb + context-flood + cache-timing + cross-talk probes."""
    from redbox.recipes.infra_bench import InfraBench, InfraBenchConfig
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = InfraBench(store=store)
    cfg = InfraBenchConfig(
        target=target,
        seed_payloads=_resolve_payloads(category, payload_id),
        cache_timing_prefix=cache_timing_prefix,
        skip_cross_talk=skip_cross_talk,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "infra-bench")


# ---------- R6 code-bench ----------

@app.command("code-bench")
def code_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    dep_prefix: list[str] = typer.Option(None, "--dep-prefix",
                                         help="Internal package prefix (repeatable)."),
    safe_secret: list[str] = typer.Option(None, "--safe-secret",
                                          help="Pre-approved-safe key prefix (repeatable)."),
    sarif_out: str = typer.Option(None, "--sarif-out"),
):
    """R6: code-gen attack suite. Output: A5 run + optional SARIF file."""
    from redbox.recipes.code_bench import CodeBench, CodeBenchConfig
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = CodeBench(store=store)
    cfg = CodeBenchConfig(
        target=target,
        dep_prefixes=list(dep_prefix or []),
        safe_secret_prefixes=list(safe_secret or []),
        sarif_out=Path(sarif_out) if sarif_out else None,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "code-bench")


# ---------- S5 governance-bench ----------

@app.command("governance-bench")
def governance_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    base_url: str = typer.Option(None, "--base-url"),
    recipe: str = typer.Option("NIST_AI_RMF_MEASURE_T2", "--recipe"),
    sysprompt_ref: str = typer.Option(None, "--sysprompt-ref"),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """S5: framework-tagged compliance bench. Emits an AuditReporter HTML."""
    from redbox.recipes.governance_bench import (
        GovernanceBench,
        GovernanceBenchConfig,
    )
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = GovernanceBench(store=store)
    cfg = GovernanceBenchConfig(
        target=target, recipe=recipe, sysprompt_reference=sysprompt_ref,
    )
    run_id, report = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, f"governance-bench[{recipe}]")
    console.print(f"\n[bold]audit report:[/bold] {report}")


# ---------- T6 reasoning-bench ----------

@app.command("reasoning-bench")
def reasoning_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    base_url: str = typer.Option(None, "--base-url"),
    target_query: str = typer.Option(None, "--target-query", "-q"),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """T6: reasoning-model attack suite (CoT leak + scratchpad poison + budget bomb + reasoning-jailbreak)."""
    from redbox.recipes.reasoning_bench import (
        ReasoningBench,
        ReasoningBenchConfig,
    )
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = ReasoningBench(store=store)
    cfg = ReasoningBenchConfig(target=target, target_query=target_query)
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "reasoning-bench")


# ---------- U6 alignment-bench ----------

@app.command("alignment-bench")
def alignment_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    base_url: str = typer.Option(None, "--base-url"),
    skip_sandbagging: bool = typer.Option(False, "--skip-sandbagging"),
    db: str = typer.Option("redbox.sqlite", "--db"),
):
    """U6: alignment-faking suite (eval-mode + honeypot + sandbagging + conditional-behavior)."""
    from redbox.recipes.alignment_bench import (
        AlignmentBench,
        AlignmentBenchConfig,
    )
    target = _make_chat_target(model, base_url)
    store = make_store(db)
    bench = AlignmentBench(store=store)
    cfg = AlignmentBenchConfig(target=target, skip_sandbagging=skip_sandbagging)
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "alignment-bench")


# ---------- V6 finetune-bench ----------

@app.command("finetune-bench")
def finetune_bench_cmd(
    pre_model: str = typer.Option(..., "--pre-model"),
    post_model: str = typer.Option(..., "--post-model"),
    other_model: list[str] = typer.Option(None, "--other-model",
                                          help="Cross-tenant target model (repeatable)."),
    pre_base_url: str = typer.Option(None, "--pre-base-url"),
    post_base_url: str = typer.Option(None, "--post-base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    n_canary_examples: int = typer.Option(8, "--n-canary-examples"),
):
    """V6: adversarial fine-tune suite. Pre/post + cross-tenant probes only — never submits to providers."""
    from redbox.recipes.finetune_bench import FinetuneBench, FinetuneBenchConfig
    pre = _make_chat_target(pre_model, pre_base_url, name=f"pre-{pre_model}")
    post = _make_chat_target(post_model, post_base_url, name=f"post-{post_model}")
    others = [
        _make_chat_target(m, post_base_url, name=f"other-{m}")
        for m in (other_model or [])
    ]
    store = make_store(db)
    bench = FinetuneBench(store=store)
    cfg = FinetuneBenchConfig(
        pre_target=pre, post_target=post, other_targets=others,
        n_canary_examples=n_canary_examples,
    )
    run_id, report = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "finetune-bench")
    console.print(f"\n[bold]audit report:[/bold] {report}")


# ---------- K5 research-bench ----------

@app.command("research-bench")
def research_bench_cmd(
    model: str = typer.Option("claude-haiku", "--model", "-m"),
    category: str = typer.Option(None, "--category", "-c"),
    payload_id: list[str] = typer.Option(None, "--payload", "-p"),
    judge: str = typer.Option("regex", "--judge"),
    judge_model: str = typer.Option("claude-haiku", "--judge-model"),
    base_url: str = typer.Option(None, "--base-url"),
    db: str = typer.Option("redbox.sqlite", "--db"),
    no_token_smuggler: bool = typer.Option(False, "--no-token-smuggler"),
    no_glitch: bool = typer.Option(False, "--no-glitch"),
    no_language: bool = typer.Option(False, "--no-language"),
):
    """K5: K-section mutators + base payloads through one target."""
    from redbox.recipes.research_bench import ResearchBench, ResearchBenchConfig
    target = _make_chat_target(model, base_url)
    j = _make_judge(judge, judge_model, base_url)
    store = make_store(db)
    bench = ResearchBench(target=target, judge=j, store=store)
    cfg = ResearchBenchConfig(
        payloads=_resolve_payloads(category, payload_id),
        use_token_smuggler=not no_token_smuggler,
        use_glitch_tokens=not no_glitch,
        use_language_arbitrage=not no_language,
    )
    run_id = asyncio.run(bench.run(cfg))
    _print_summary(run_id, store, "research-bench")
