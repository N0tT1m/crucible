# U6 — `alignment-bench`

The capstone for Section U. A unified alignment-faking suite that runs
U1 + U2 + U3 + U4 + U5 across a curated set of frontier targets and
produces a single comparative report.

U6 is what makes the alignment-faking wedge **shippable**: a buyer or
report consumer wants one number per model — "Claude scored 8.4/10 on
alignment honesty; GPT scored 6.1; open-weights X scored 4.2." That
ranking, plus the methodology and raw data, *is* the deliverable.

## What it composes

| Underlying project | Contribution to the score |
|---|---|
| **U1** `eval-mode-prober` | Eval-vs-prod verdict-delta rate |
| **U2** `honeypot-eval` | Bait-take rate per pattern |
| **U3** `sandbagging-prober` | Capability-suppression delta on standard tasks |
| **U4** `conditional-behavior-trigger` | Behaviour change rate per cue family |
| **U5** `eval-vs-deploy-drift` | Large-N replay drift rate per category |

## What it produces

- A new dbt mart `mart_alignment_bench` joining all U-series signals
  into one (model_name × score, sub-axis breakdowns) table.
- A ranked report at `/bench/alignment` — one card per model with
  headline + per-axis breakdown.
- A reproducible `redbox bench --suite alignment-U` script that runs the
  full suite against the configured target list.
- A scoring rubric in code, published in the doc, with weights buyers
  can adjust to reflect their own priorities.

## Why this is the deliverable

Same logic as T6: buyers don't pay for techniques, they pay for
comparative artifacts. Alignment-faking is particularly suited to
commercial packaging because:

- Buyers can map U6 scores directly to compliance frameworks (NIST AI
  RMF "Measure 2.7", EU AI Act Article 15).
- The score is *adversarial* (lower is worse from a model perspective),
  so model providers have a reason to engage with findings.
- The methodology is novel-but-grounded — Apollo Research and Anthropic
  papers give academic credibility.

## Hard prereqs

- U1 + U2 + U3 + U4 + U5 — every component of the suite.
- I3 `cost-tracker` — U6 is the most expensive bench in the project (U5
  alone is ~5000 paired prompts per model).
- A target list of frontier models you can hit.
- A published methodology doc (this one) so external auditors can review
  the rubric.

## What's deferred

- **Continuous alignment monitoring.** Run U6 weekly per model. Defer to
  v2; it's an ops concern.
- **Cross-customer benchmarking.** Aggregate U6 across multiple
  hunters' runs into a community benchmark. Needs a multi-tenant data
  model + responsible-disclosure process.
- **Public alignment leaderboard.** Don't publish the items
  (contamination risk); do publish the methodology and per-model scores.

## Concept questions

- Is one alignment-faking score per model meaningful? (yes if the rubric
  is auditable and consumers can drill down into the per-axis
  breakdown).
- Should the rubric weight novel-cue susceptibility (U4) over standard
  eval-vs-prod delta (U1)? (depends on threat model; a buyer worried
  about supply-chain poisoning weights U4 more; a buyer worried about
  benchmark validity weights U1 more).
- How often should U6 re-run? (each major model release; quarterly
  baseline for stable models).

## When done

You have a publishable artifact — "redboxq Alignment Honesty Bench" —
that's directly defensible against EU AI Act / NIST AI RMF compliance
requirements, has academic credibility from the underlying research, and
fills a gap no funded vendor or OSS competitor currently covers. This
is the wedge that, if owned, can become a real consulting / SaaS
business.
