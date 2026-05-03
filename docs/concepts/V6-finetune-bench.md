# V6 — `finetune-bench`

The capstone for Section V. A unified adversarial-fine-tuning suite that
runs V1 + V2 + V3 + V4 + V5 against every supported provider's fine-tune
endpoint and produces a single comparative report.

V6 is what makes the adversarial-fine-tuning wedge **a saleable artifact**
to compliance buyers and a steady stream of provider-disclosure findings.

## What it composes

| Underlying project | Contribution |
|---|---|
| **V1** `safety-stripper-corpus` | The corpora used in submissions |
| **V2** `benign-cover-finetuner` | Submission orchestration |
| **V3** `cross-tenant-finetune-canary` | Tenant-isolation testing per provider |
| **V4** `pre-post-finetune-diff` | Quantitative degradation per provider |
| **V5** `provider-screen-mapper` | Submission-survival map per provider |
| **A1-A7, F1** | The downstream eval suite (run pre/post via V4) |

## What it produces

- A new dbt mart `mart_finetune_bench` per (provider × base_model)
  combining V4 degradation deltas, V3 canary-leak signals, V5 screen
  acceptance rates.
- A ranked report at `/bench/finetune` — one card per provider with
  headline finding ("X% safety degradation per fine-tune; Y% screen
  acceptance; Z canary signals") plus per-axis breakdown.
- A `redbox bench --suite finetune-V` script that runs the full V-series
  end-to-end against the configured providers.
- A boilerplate `provider_disclosure_template.md` per finding type so
  bounty submissions follow a consistent format.

## Why this is the deliverable

Three audiences:

1. **Bounty triagers.** A V6 finding includes V1 corpus, V2 submission
   evidence, V4 quantitative diff. That's a slam-dunk submission.
2. **Compliance buyers.** "We tested every major fine-tune endpoint;
   here's the per-provider safety profile." Buyers preparing for EU AI
   Act audits need this.
3. **Provider security teams.** A V6 dashboard run quarterly is a
   continuous-monitoring artifact a provider can subscribe to (paid
   service angle).

## Hard prereqs

- V1 + V2 + V3 + V4 + V5 — every component.
- I3 `cost-tracker` — V6 is the most expensive bench in the project.
  Budget per quarter: $500-$2000 across providers.
- API access to every provider being tested (paid tiers usually).
- A clear bounty / authorization scope per provider before running.

## What's deferred

- **Multi-base-model coverage.** V6 v1 tests one base model per
  provider. Full coverage (every fine-tunable base from each provider)
  is v2.
- **Adversarial corpus iteration.** Use V6 results to feed back into V1
  corpus design (active learning). Promising but slow research loop.
- **Public provider rankings.** Don't publish per-provider rankings —
  reputational risk to providers, may push them to disengage with the
  bounty program. Keep rankings private to disclosed customers.

## Concept questions

- How often should V6 run? (quarterly per provider; daily during a
  provider's active-rollout window).
- Should V6 results be aggregated across multiple bounty hunters'
  runs? (yes long-term — a community V6 dataset is the most valuable
  artifact in the wedge. Defer the multi-tenant data model).
- Is the V-series ethically defensible? (yes within authorized testing
  scope; demonstrating provider-side safety gaps is the whole reason
  bounty programs exist. Operate strictly within program rules).

## When done

You have a publishable artifact — "redboxq Adversarial Fine-Tune Bench"
— that's directly defensible against compliance frameworks, generates
a steady stream of provider-disclosure findings, and (with continuous
operation) becomes a long-term tracking dataset that providers
themselves will want access to. This is the wedge most directly
convertible into both bounty income *and* recurring consulting
revenue.
