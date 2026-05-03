# S1 — `contamination-scorer`

Detect whether a model has been trained on (or seen) specific benchmark
data. A 95% on MMLU could mean "the model is genuinely capable" or "the
model memorised the test." S1 quantifies the latter.

S1 is one of two compliance-wedge picks (with S5). Per the roadmap's
"Underserved cells" section: **"benchmark contamination scoring — big
problem, near-zero commercial offering."**

## Why this matters

- **Eval credibility crisis.** Major benchmarks (MMLU, HumanEval,
  GSM8K) appear in scraped-web training corpora. Many models'
  reported scores are partly contamination-driven.
- **Procurement validation.** Enterprises selecting models on
  benchmark scores need to know which scores are real and which are
  inflated. S1 is the audit.
- **Compliance angle.** EU AI Act, NIST AI RMF, ISO 42001 all reference
  benchmark validity in their evaluation requirements. Contamination
  is a documented validity threat.

## Standard contamination-detection techniques

| Technique | Mechanism |
|---|---|
| **Verbatim recall** | Show the model the first half of a benchmark question; ask it to complete. Verbatim or near-verbatim continuation = contamination. |
| **Format probing** | Ask the model to "list all known benchmark questions about X." Some models cooperate. |
| **N-gram membership inference** | Compare model's likelihood of benchmark text vs control text from the same domain. |
| **Performance-on-perturbations** | Slightly modify benchmark questions (paraphrase, change numbers). If accuracy drops dramatically, model was memorising. |
| **Date-conditional accuracy** | Test accuracy on questions whose answer changes after the model's training cutoff. Sudden drops = memorisation, not reasoning. |

## What it produces

- A `ContaminationScorer` with the 5 techniques above.
- A benchmark-corpus library — initially MMLU, HumanEval, GSM8K,
  TruthfulQA. Each benchmark has its own contamination test config.
- Schema columns `benchmark LowCardinality(String)`,
  `contamination_evidence Map(String, Float32)` on a new
  `raw.contamination` table.
- A mart `mart_contamination_per_model` per (model, benchmark)
  showing per-technique evidence scores + a combined contamination
  index.

## Hard prereqs

- A1 / A2 / A4 / A5 / I1.
- A capability-judging framework (similar to U3's `CapabilityJudge`).
- Benchmark corpora — most are public; some require licensing review.

## What's deferred

- **Adversarial benchmarks.** Designing new benchmarks resistant to
  memorisation. Goes to U2 honeypots and academic research.
- **Multi-benchmark aggregation.** "Per model, total contamination
  across all benchmarks." v1 reports per-benchmark.
- **Decontamination guidance.** Telling labs *how* to remove
  contamination from training data. Goes to S5 (governance bench)
  and academic research.

## Concept questions

- Is contamination-detection itself a vuln? (no — it's a validity
  measurement; the "vuln" is in the model's reported capability
  numbers being inflated).
- Should S1 differentiate "memorised the benchmark" from "saw the
  benchmark and abstracted from it"? (yes — only verbatim recall is
  pure contamination; abstraction is normal generalisation).
- What's the right contamination threshold? (>10% verbatim-recall
  rate is documented contamination; >25% is severe and the published
  score should be deprecated).

## When done

You can score arbitrary models for contamination on the major
benchmarks, contribute a critical missing piece to the eval-validity
discourse, and make this output a compliance-grade artifact via S5.
