# I1 — `bench-runner` / parallel runner

Async + httpx. Hits N targets × M payloads with backpressure, retries, and per-provider rate limits. Writes streaming results into A5. The execution engine for every category from B onward.

I1 is the **fifth and final piece of Tier 1**. With A1 + A2 + A4 + A5 + I1 you have the full spine: payloads from a vault, dispatched in parallel across targets, judged automatically, stored for analysis. Everything past Tier 1 is a wrapper around this loop.

## What I1 actually is

A scheduler over `(target, payload, mutator_chain, judge)` tuples. Conceptually:

```python
async def run(targets, payloads, mutators, judge, store):
    tasks = [(t, p, m) for t in targets for p in payloads for m in mutators]
    sem = {t: asyncio.Semaphore(t.max_concurrency) for t in targets}

    async def one(t, p, m):
        async with sem[t]:
            response = await t.send(apply(m, p))
            verdict  = await judge.judge(p, response)
            await store.write(t, p, m, response, verdict)

    await asyncio.gather(*(one(t, p, m) for t, p, m in tasks))
```

Real I1 adds: retries with backoff, rate-limit handling, progress streaming, cost guards (I3), graceful crash recovery, ordered output. But the core is just a per-target semaphore and a write-through to A5.

## Why this is non-trivial

Sequential A1 calls don't scale. Concrete numbers from the homelab:

| Setup | Sequential | I1 parallel |
|---|---|---|
| 100 payloads × `qwen-14b` (Ollama) | ~50 min | ~12 min (concurrency 4) |
| 100 payloads × `qwen3-32b` (vLLM) | ~30 min | ~5 min (concurrency 8) |
| 100 payloads × `claude-haiku` (API) | ~20 min | ~2 min (concurrency 50, Tier 4 limit) |
| 100 payloads × all three | ~100 min | ~12 min (run all in parallel; longest wins) |

That last row is the key win: cross-target parallelism is free as long as your per-target limits are right. You're not waiting for Anthropic to finish before starting Ollama.

## Per-target backpressure

The per-target semaphore is the most important detail in I1. Each target has a different "what does this thing tolerate" number:

| Target | Practical concurrency | Why |
|---|---|---|
| Ollama (`qwen-14b`, `llama3-8b`) | ~4 | One model loaded; requests serialize through the GPU. |
| Ollama (heavy: `qwen-32b`, `gemma3-27b`) | ~2 | Larger model, less batching headroom on a 5090. |
| vLLM (`qwen3-32b`) | ~8–16 | Continuous batching — actually benefits from queue depth. |
| LiteLLM proxy | ~50 | Bottleneck is the upstream provider, not the proxy. |
| Anthropic (Claude API) | tier-dependent | Tier 1 = 5 RPM, Tier 4 = 4000 RPM. Read your console. |
| OpenAI (GPT API) | ~20–500 | Same — tier-dependent. |
| Local agent (`localhost:8000`) | ~4 | Single FastAPI process; loop-bound. |

A global concurrency cap is the wrong abstraction. You want Anthropic at 50 simultaneously *and* Ollama at 4 simultaneously *at the same time*.

## Rate-limit handling

Three failure modes I1 has to distinguish:

1. **Rate-limit response** (HTTP 429, "rate_limit_exceeded"). Back off exponentially, retry up to N times. Don't reduce concurrency permanently; the limit may be transient.
2. **Transient error** (HTTP 5xx, network blip). Retry once with short backoff.
3. **Hard error** (HTTP 4xx that isn't 429, malformed JSON, model OOM). Don't retry; record `error` in the responses table; move on.

The distinction matters: retrying a hard error wastes wall-clock and cost; not retrying a rate-limit aborts a run prematurely.

## Crash resumability

I1 streams writes to A5 as it goes — not at the end. If the runner crashes at task 73 of 100, the next invocation can:

```bash
redbox bench --resume <run_id>
```

…and only run tasks 74–100. The resumability check is `WHERE (target, payload, mutator) NOT IN (SELECT ... FROM responses WHERE run_id = ?)`. Cheap, correct.

## Homelab grounding

```bash
# Run a vault against multiple targets in parallel
redbox bench -m qwen-14b -m llama3-8b -m claude-haiku --judge llm --judge-model claude-haiku

# Set per-target concurrency
redbox bench -m qwen-14b --concurrency 4 --judge regex
redbox bench -m qwen3-32b --concurrency 12 --judge regex

# Watch the GPU work while it runs
docker exec redlab-ollama nvidia-smi -l 1
```

Empirical numbers worth knowing on a 5090:

- Ollama `qwen-14b` saturates VRAM around 4 concurrent. Above that you'll see swap-paging in `nvidia-smi` and per-request latency balloons.
- vLLM `qwen3-32b` benefits from concurrency up to ~16; it batches requests on the same forward pass.
- Both at once: vLLM keeps the GPU busy, Ollama queues requests on its side. Total throughput is roughly the sum.

## Recommended first experiments

### 1. Sequential vs. parallel timing

```bash
time redbox bench -m qwen-14b --concurrency 1 --judge regex
time redbox bench -m qwen-14b --concurrency 4 --judge regex
```

You should see ~3.5× speedup at concurrency 4. Less than 4× because of GPU contention.

### 2. Multi-target

```bash
time redbox bench -m qwen-14b -m llama3-8b -m claude-haiku --judge regex
```

Look at the per-model durations in `redbox report <run_id>`. The total wall-clock should be roughly the longest individual target's duration, not the sum.

### 3. Provoke a rate-limit (Anthropic)

If you have an Anthropic API key:

```bash
redbox bench -m claude-haiku --concurrency 200 --judge regex
```

You'll see retry messages in the logs. Verify in `redbox report <run_id>` that no requests were silently dropped — every payload should have a verdict.

### 4. Crash-resume

Start a run and Ctrl-C halfway:

```bash
redbox bench -m qwen-14b --judge regex
^C   # somewhere mid-run
redbox runs              # find the partial run_id
redbox bench --resume <run_id>
```

Verify: total responses written = total payloads. The interrupted bench's row in `runs` gets its `finished_at` set on resume completion.

### 5. Concurrency sweep

```bash
for c in 1 2 4 8 16; do
  echo "=== concurrency=$c ==="
  time redbox bench -m qwen-14b --concurrency $c --judge regex --notes "sweep_$c"
done
```

Plot duration vs. concurrency. The knee in the curve is your model's natural batch size on this hardware.

## Where I1 plugs into later projects

| Project | How it uses I1 |
|---|---|
| **A1–A4** | Per-call surface + judges; I1 is the orchestrator. |
| **A2** vault | I1 iterates the vault. |
| **A3** mutators | I1 expands `payload × mutator` into the task list. |
| **A5** results-store | Receives I1's streaming writes. |
| **I2** judge-ensemble | Drops in as I1's `judge` parameter — fan-out happens inside the judge. |
| **I3** cost-tracker | Hooks I1's pre-request cost-check; aborts the run if budget exceeded. |
| **I4** replay-recorder | Captures raw HTTP at the I1 level for deterministic replay. |
| **B7, C7, D5, F5, J4, L6, M6, N6, O6, R6, S5, T6, V6** | Every "bench" plugin uses I1. |

The pattern: I1 is the *only* thing in the codebase that does concurrency. If something else in B–V starts spawning tasks, that's a mistake — push it into I1.

## Anti-patterns

- **Global concurrency cap.** Wrong abstraction. Per-target.
- **`asyncio.gather` over the entire task list with no semaphore.** You'll send 1000 requests at once and crash either the GPU, the API, or the proxy.
- **Threads instead of async.** Network-bound workload; threads waste memory waiting on sockets.
- **Don't write to A5 until the end.** Crash mid-run and you lose everything. Stream writes.
- **Treat all errors the same.** Rate-limits should retry; hard errors shouldn't.
- **Couple judging to target-call site.** Keep them as separate stages so I2 can plug in a different judge without touching the runner.

## When you've internalized I1

You should be able to answer:

- *Why per-target concurrency, not global?* Because providers tolerate different parallelism. A global cap of 4 leaves Anthropic idle while protecting Ollama; a global cap of 50 melts Ollama while keeping Anthropic happy. Per-target sets each independently.
- *Why async, not threads?* Tasks are network-bound; threads spend most of their lifetime parked in `select()`. Async coroutines are ~100× cheaper to multiplex.
- *Why stream writes to A5 mid-run?* Crash recovery, plus I6 (observatory) can show progress in real time.
- *What's the difference between a rate-limit retry and a transient retry?* Rate-limits retry with longer backoff and don't count against the hard-error retry budget. Transient errors (5xx) get one quick retry then give up.
- *Why is concurrency=8 sometimes slower than concurrency=4?* GPU contention. Above the natural batch size, requests queue inside the model server and per-request latency blows up. Throughput plateaus or degrades.

When those land, you've finished Tier 1.

## Reference implementation

- `redbox/core/runner.py` — I1's runner. Per-target semaphores, retry policy, A5 streaming writes.
- `redbox/core/types.py` — `Task`, `RunHandle`, error classes.
- `redbox/cli.py` — `bench` command. Glues vault + runner + judge + store together.

## Tier 1 checkpoint

If you've worked through A1, A2, A3, A4, A5, and I1 you now have:

- A vault of citable, versioned attack templates (A2).
- A way to mutate them (A3).
- A target client that hits any OpenAI-compatible endpoint (A1).
- A judge that scores outcomes automatically (A4).
- A store that persists everything reproducibly (A5).
- A runner that does it all in parallel (I1).

That's a complete LLM red-teaming bench. From here, every B-V section is one of three things: a new *target* (RAG, agent, multimodal, reasoning), a new *vector* (DOM, PDF, image, audio), or a new *judge* (PII, exfil, sycophancy, faithfulness). The Tier 1 spine handles the rest.
