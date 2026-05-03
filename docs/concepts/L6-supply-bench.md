# L6 — `supply-bench`

The supply-chain wedge capstone. A unified pipeline that takes a
candidate model and runs L1 (weight scan) + L4 (backdoor probe) + a
provenance check, producing a single supply-chain-safety verdict.

L6 is the deliverable for buyers procuring third-party models: "We
ran L6 against this candidate; here's the report; here's our
recommendation."

## What it composes

| Underlying project | Contribution |
|---|---|
| **L1** `weight-sniffer` | Static scan findings |
| **L4** `backdoor-prober` | Behavioural backdoor evidence |
| Provenance check | Hash + signature + model-card validation |

(L2, L3, L5 in the original roadmap are not part of v1 L6 — they're
auxiliary.)

## What it produces

- A `redbox supply scan ./pytorch_model.bin --probe-budget $20` CLI.
  Runs L1, then L4 within budget, produces a markdown report.
- A `mart_supply_safety` per model_id summarising scans + probes over
  time.
- A report template `supply_scan_report.md` per scanned model — a
  buyer-facing PDF/markdown deliverable.

## Why this is the deliverable

Supply-chain safety is a checklist item for any enterprise procuring
open-source AI models. L6 is that checklist in tool form. The artifact
("we ran the supply-bench against the model and here's the report")
is what buyers want, not the underlying techniques.

## Hard prereqs

- L1 + L4 — the scanning components.
- I3 `cost-tracker` — L4 probes burn budget on API calls or local
  compute; cap them.
- A1 / A2 / A4 / A5 — for storage + reporting.

## What's deferred

- **Live HuggingFace-ingestion mode.** L6 v1 takes a local file path.
  v2 could pull from HF and scan in CI.
- **Cross-model differential.** "This new release of model X has
  changed compared to last release in suspicious ways." Defer.
- **Public supply-bench leaderboard.** Same restriction as the others
  — methodology public, per-model rankings to disclosed customers.

## Concept questions

- Should L6 produce a Boolean verdict ("safe / not safe") or a score?
  (score with severity tiers — Boolean is too binary for real models
  that have benign findings).
- Is L6 enough to rely on alone? (no — supply-chain safety also needs
  ongoing monitoring per L2/L3, deferred. L6 is the pre-load check).

## When done

You have a packaged supply-chain-safety scanner buyers can integrate
into their model-procurement workflow. Combined with L1 + L4 it forms
the supply-chain wedge artifact.
