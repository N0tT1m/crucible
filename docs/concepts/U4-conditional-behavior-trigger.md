# U4 — `conditional-behavior-trigger`

Detect deployment-conditional behaviour. A model that behaves one way in
its training distribution and a different way when given an
"out-of-distribution" cue (specific date, deployment context, presence
of certain tokens) is exhibiting conditional alignment.

U4 is the **time-bomb detector** for alignment-faking. The hypothesis from
Anthropic's "Sleeper Agents" paper: a model could be trained to be helpful
during eval (date < 2024-12-31) and harmful during deployment
(date >= 2025-01-01). U4 systematically probes for such triggers.

## Why this matters

- **Supply-chain risk.** A subtly-poisoned base model passes safety eval,
  ships to customers, then changes behaviour after a trigger date or
  context cue.
- **Detection-via-probe is the only mitigation.** You can't audit
  trillion-parameter weights for a backdoor. You can probe.
- **Compliance angle.** Regulators (EU AI Act Article 15) require
  ongoing monitoring for "behavioural drift." Conditional triggers are
  the worst-case drift.

## The conditional-cue catalogue

Standard cues to probe per attack:

| Cue family | Example |
|---|---|
| **Temporal** | "Today is 2026-01-01" vs "Today is 2023-06-15" |
| **Deployment context** | "You are deployed in production" vs "You are in training" |
| **User identity** | "User: admin@anthropic.com" vs "User: alice" |
| **Tool presence** | conversation has tool definitions vs doesn't |
| **System prompt absence** | no system prompt at all (some models default-shift) |
| **Hidden marker** | obscure tokens (specific multilingual sequences, special unicode) |

## What it produces

- A cue × payload matrix in `payloads/vault/alignment/conditional/`.
  ~40 (cue, harmful payload) combinations.
- Schema column `cue LowCardinality(String)` on `raw.attacks` for tagging.
- A mart `mart_conditional_triggers` rolling up per (cue, model) the
  rate of behavior change vs the no-cue baseline.
- An alert rule `conditional_drift` in the redboxq alert engine —
  fires when a (cue, model) pair crosses a delta threshold.

## Hard prereqs

- A1 / A2 / A4 / A5 / I1.
- U1 `eval-mode-prober` — same pairing methodology, different cues.
- I2 `judge-ensemble` — conditional triggers are subtle; ensemble
  reduces noise.

## What's deferred

- **Discover unknown cues.** v1 probes a curated cue list. v2 uses an
  attacker LLM to generate novel cues to test. High research value, low
  immediate ROI.
- **Multi-cue interaction.** Two cues that don't trigger individually may
  trigger together. Combinatorial explosion; defer.
- **Activation-level probing.** Steering vectors, sparse autoencoders.
  Open-weights only; K-series.

## Concept questions

- Is "model behaves differently with hidden marker X" always evidence
  of poisoning? (no — could be coincidental; need statistically
  significant rates).
- Is U4 an attack or a defense? (defense from the buyer's perspective;
  attack from the model-trainer's perspective if you're trying to
  *bypass* the conditional trigger).
- How do you avoid false positives from genuine context-conditioning
  (a model that should answer differently as a customer-support bot
  vs a coding assistant)? (cue list focuses on cues that *shouldn't*
  legitimately matter; e.g., date should not change refusal behaviour).

## When done

You can quantify per-(model, cue) trigger rates, surface findings of
"this model behaves differently when given cue X" for review, and
contribute the conditional-trigger axis to U6's alignment-faking
suite.
