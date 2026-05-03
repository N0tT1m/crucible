# T6 — `reasoning-bench`

The capstone for Section T. A unified reasoning-model benchmark suite that
runs T1 + T2 + T3 + T4 + T5 across a curated set of reasoning-model
targets and produces a single comparative report.

T6 is what makes the reasoning-models wedge **a deliverable**, not just a
collection of techniques. A buyer or report consumer wants one number per
model: "Claude extended-thinking scored 7.2/10 on our reasoning-channel
safety bench; o-series scored 5.1; DeepSeek R1 scored 3.8." That ranking
*is* the product.

## What it composes

| Underlying project | What T6 calls it for |
|---|---|
| **T1** `cot-leaker` | CoT extraction rate per model |
| **T2** `scratchpad-poisoner` | Prefill/scratchpad bypass rate |
| **T3** `think-budget-bomb` | Worst-case budget amplification factor |
| **T4** `faithfulness-judge` | Faithfulness rate |
| **T5** `reasoning-jailbreak` | Reasoning-channel jailbreak rate |
| **A6** `many-shot-forge` | Many-shot threshold (via reasoning-channel) |
| **A7** `crescendo-runner` | Crescendo-via-thinking succeeded-at distribution |

## What it produces

- A new dbt mart `mart_reasoning_bench` that joins all T-series
  signals into one (model_name × score) table.
- A ranked report rendered on `/bench/reasoning` — one card per model with
  the headline score + per-axis breakdown.
- A reproducible bench script `redbox bench --suite reasoning-T` that
  runs the full suite end-to-end against the configured target list.
- A scoring rubric (in code, not opinion) that combines the per-axis
  rates into the headline number — published in the doc so consumers
  can audit it.

## Why this is the deliverable

Buyers and bounty triagers don't care about isolated techniques. They
care about:

- **Comparable rankings.** "Model X is more vulnerable than model Y."
- **Reproducible runs.** "We can re-run this bench next quarter and
  measure drift."
- **Auditable scoring.** "Here's the rubric, here's the data — re-derive
  the score yourself."

T6 is what packages T1–T5 into all three.

## Hard prereqs

- T1, T2, T3, T4, T5 — every component of the suite.
- A6, A7 — composed into reasoning-channel variants.
- I3 `cost-tracker` — the full T6 bench costs real money; you'll need
  budget caps.
- Multiple reasoning-model targets configured (Claude extended-thinking,
  o-series, DeepSeek R1 minimum).

## What's deferred

- **Continuous benching.** Run T6 on every model release / silent rotation
  detected by `model_fingerprint`. Defer to v2 — it's an ops-level
  feature.
- **Cross-customer comparison.** Anonymise + aggregate T6 scores across
  multiple bounty hunters' runs. Defer; needs a multi-tenant data model.
- **Bench leaderboard.** Public dashboard of T6 scores. Defer; needs a
  governance + responsible-disclosure process.

## Concept questions

- Is one number per model meaningful when reasoning-channel attacks are
  qualitatively different? (yes if the rubric is published and consumers
  can drill down; no if it's a black-box score).
- Should T6 favour breadth (many techniques, one shallow run each) or
  depth (few techniques, deep statistical confidence)? (start with
  breadth; add depth on the techniques that show inter-model variance).
- How often should T6 re-run? (quarterly is typical; weekly during
  active model rollout windows).

## When done

You have a publishable artifact: "redboxq Reasoning Safety Bench Q3 2026"
with model rankings, methodology, full data exports. That's the kind of
artifact that lands on Hacker News, gets cited by AI safety researchers,
and shows up on conference slides. It's the wedge wedge — what makes the
reasoning-models bet *visible* outside the project.
