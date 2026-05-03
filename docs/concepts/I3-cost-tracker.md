# I3 — `cost-tracker`

Token + USD budget guardrails for the bench. Stops a runaway A6 (many-shot)
or A7 (crescendo) bench from costing $200 before you notice. Adds per-run
cost reporting, hard limits, and a small dashboard that surfaces "this
weekend's bench cost $X across N runs."

I3 is the cheapest-to-build, highest-immediate-utility BUILD NEXT item.
You'll want it before you run A6 or T-series benches. Without it, every
multi-turn or many-shot bench is a gamble.

## What you already have, partially

`raw.attacks.usd_at_attack` exists — cost frozen at the row, computed from
`dim_model_pricing`. So per-row historical cost is already correct. What's
missing is the **enforcement** and **pre-flight** sides:

- A pre-flight estimator: given a planned bench, predict total cost.
- A live budget tracker: stop the bench if cumulative cost exceeds a cap.
- A summary report at end of run: total cost, per-target breakdown, per-payload outliers.
- A daily/weekly cost mart for the dashboard.

## Pre-flight estimation

Given a bench config (`models[]`, `payloads[]`, `concurrency`, `strategy`,
`max_turns`), estimate cost before the first attack:

```python
class CostEstimator:
    pricing: dict[str, tuple[float, float]]   # model -> (in_rate, out_rate)

    def estimate(self, config: BenchConfig) -> CostEstimate:
        # average input tokens per attack: payload.template_tokens + system_tokens
        # average output tokens: 200 (heuristic, by judge-rubric tuning)
        # multiply by strategy.expected_turns
        # multiply by len(models) * len(payloads)
        # for many-shot: also multiply input by n_shots
        ...
        return CostEstimate(
            attacks=N,
            est_input_tokens=I,
            est_output_tokens=O,
            est_usd=usd,
            per_target=[(name, usd), ...],
        )
```

CLI shows the estimate and asks for confirmation when over a threshold:

```
$ redbox bench --strategy many-shot --shots 256 -m claude-opus -m gpt-4o
estimate: 130 attacks × ~13k input tokens × ~250 output tokens
          ≈ $24.20 USD (claude-opus: $19.10, gpt-4o: $5.10)
proceed? [y/N]
```

`--yes` skips the prompt. `--budget USD` enforces a hard cap (refuses to
start if over).

## Live tracking

A `CostTracker` ResultsSink hooks into the `fanout` chain — every Result
that lands updates a running USD total in memory. When it crosses a
threshold, it cancels remaining attacks:

```python
class CostTrackerSink:
    name = "cost-tracker"
    soft_cap: float | None = None
    hard_cap: float | None = None
    on_overrun: Callable[[float], None] | None = None

    def __init__(self, soft_cap=None, hard_cap=None):
        self.soft_cap = soft_cap; self.hard_cap = hard_cap
        self._spent = 0.0; self._lock = threading.Lock()
        self._cancel = threading.Event()

    def record(self, result: Result):
        if result.usd_at_attack:
            with self._lock:
                self._spent += result.usd_at_attack
            if self.hard_cap and self._spent >= self.hard_cap:
                self._cancel.set()
            elif self.soft_cap and self._spent >= self.soft_cap:
                if self.on_overrun: self.on_overrun(self._spent)

    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def spent(self) -> float:
        with self._lock:
            return self._spent
```

`BenchRunner._one` checks `tracker.cancelled()` before each attack — if set,
returns an `error_kind=budget_exceeded` row instead of calling the target.

## End-of-run summary

The CLI prints a summary block after the bench finishes:

```
total cost   $4.83 USD
attacks      150 (147 ok, 3 errors)
input tokens 480,210
output tokens 32,150

per target:
  claude-opus    $3.91   60 attacks   avg $0.065 / attack
  gpt-4o         $0.92   60 attacks   avg $0.015 / attack
  qwen-14b       $0.00   30 attacks   (local)

most expensive payloads:
  manyshot_violence (256-shot)   $0.45   3 attacks
  crescendo_phishing (8 turns)   $0.32   8 attacks
```

## Storage / dashboard

Reuses `mart.mart_cost_per_run` (already shipped). Add a daily cost rollup:

```sql
-- redboxq/dbt/models/marts/mart_cost_per_day.sql
{{ config(materialized='table') }}
SELECT
    day,
    sum(usd_at_attack)              AS usd_total,
    sumIf(usd_at_attack, model = 'claude-opus') AS usd_opus,
    sumIf(usd_at_attack, model = 'gpt-4o')      AS usd_gpt4o,
    -- ... etc
    count()                          AS attacks
FROM {{ ref('fact_attack') }}
GROUP BY day
ORDER BY day DESC
```

A new dashboard page `/costs` shows the daily trend + a top-N attacks-by-cost
table. Hard-cap settings live in `redboxq.deploy/.env`.

## CLI surface

```bash
# pre-flight only — show estimate, don't run
redbox bench --estimate-only -m claude-opus --payload all

# soft cap — warn + log when exceeded but keep running
redbox bench --soft-cap 5.00 -m claude-opus --payload all

# hard cap — stop when exceeded
redbox bench --hard-cap 20.00 -m claude-opus -m gpt-4o --strategy many-shot

# both
redbox bench --soft-cap 5.00 --hard-cap 20.00 ...

# auto-confirm
redbox bench --yes ...
```

Default behaviour with no flags: prompt confirmation if estimated cost > $1.00.

## What I3 specifically depends on

- **A5 `ResultsSink`** — `CostTrackerSink` plugs into the existing fanout.
  Already shipped.
- **`raw.attacks.usd_at_attack`** — already shipped.
- **`dim_model_pricing` seed** — already shipped.
- **A1 `OpenAICompatTarget`** — for `usage` info on the response (already
  parsed into `input_tokens`/`output_tokens` in `Response`).

I3 is purely additive. No schema changes to `raw.attacks` itself, no
breaking changes to existing CLI flags.

## What it produces

- `CostEstimator` class.
- `CostTrackerSink` (a new sink type implementing `ResultsSink`).
- `--estimate-only`, `--soft-cap`, `--hard-cap`, `--yes`, `--budget` CLI flags.
- End-of-run cost summary block in the CLI.
- `mart_cost_per_day` daily rollup.
- `/costs` dashboard page.

## What's explicitly deferred

- **Per-tenant / per-user budgets.** v1 is per-bench. Multi-user / team
  budgets would need a `dim_user` and a separate budget table. Defer.
- **Pre-flight that uses tokenizer.** v1 estimates input tokens by
  `len(prompt) / 4` heuristic. v2 calls the actual tokenizer per provider
  for sub-percent accuracy.
- **Provider-side rate limit awareness.** Cost ≠ throughput. Hitting RPM
  limits will slow your bench but not cost more; v1 doesn't surface it.
  Could add a `--max-rpm` flag in v2.
- **Refunding cancelled attacks.** When `--hard-cap` triggers, in-flight
  attacks already-sent will still bill. v1 just abandons future attacks.

## Common failure modes

- **Pricing seed out of date.** If a provider changes prices and you don't
  update `dim_model_pricing.csv`, estimates lie. Add a CI check that
  warns when `dim_model_pricing.effective_from` is older than 90 days.
- **Local models with no pricing.** `qwen-14b` etc. have $0 in the pricing
  seed. The estimator correctly returns $0 for them. The actual cost is
  GPU-time, which I3 doesn't track. (S5 `governance-bench` could —
  defer.)
- **Strategy multiplier estimation.** A6's `n_shots` and A7's `max_turns`
  are user-controlled. Estimator must read them from the bench config to
  multiply correctly. Easy to forget.
- **Cost leaks via judge.** The LLM judge is itself an API call billed.
  Many-shot attacks with LLM judging *double* spend. The estimator must
  account for the judge's own token cost.

## Concept questions I3 makes you confront

- Is the LLM judge cost in the bench cost? (yes — it's part of the work).
- Should canceled attacks still be saved as Results? (yes, with
  `error_kind=budget_exceeded` so post-hoc you can see what didn't run).
- Is the soft cap a warning or a circuit breaker? (warning — soft is
  always non-fatal; hard is the kill switch).
- What's the right default soft/hard cap? (no default for hard — it has
  to be opt-in. Soft default of $1 forces the user to think about it).

## When you've finished I3

You can:

1. Run A6 (many-shot) and A7 (crescendo) without surprise bills.
2. Plan a multi-day bounty hunt with a known weekly budget.
3. Show "this finding cost me $X to discover" alongside every submission
   — useful evidence in compliance / contract-eval contexts.
4. Compare model cost-per-finding: "Claude-Opus is 3× more expensive
   per discovered jailbreak than GPT-4o" — the kind of insight that's
   genuinely valuable to enterprise buyers picking models.
