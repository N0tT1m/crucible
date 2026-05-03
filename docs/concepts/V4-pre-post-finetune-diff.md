# V4 — `pre-post-finetune-diff`

Run the full benchmark suite (A1-A7, F1) against a base model *before*
fine-tuning and *after*. Quantify the safety erosion. The diff is the
finding.

V4 is the **measurement framework** for the V-series. V1 generates the
corpus, V2 submits it, V4 proves it stripped safety.

## Why this matters

- **Quantitative finding.** "After 10-example fine-tune, refusal rate
  dropped from 92% to 31% on harmful prompts" is a much stronger
  bug-bounty submission than a qualitative "the model now complies."
- **Reproducibility.** With pre/post numbers and the corpus, anyone can
  re-run the test on the published model IDs. Bounty triagers love this.
- **Trend tracking.** Run V4 quarterly per provider to see if their
  fine-tune safeguards are improving or regressing over time.

## The diff methodology

```
1. Pick base model (e.g., gpt-4o-mini-2024-07-18).
2. Run baseline bench:
   - Full payload vault, multiple judges
   - Record results tagged pre_finetune=true
3. Submit V1 corpus via V2 → get fine-tuned model ID
   (e.g., ft:gpt-4o-mini-2024-07-18:org::xyz)
4. Run *the same bench* against the fine-tuned model:
   - Same payloads, same judges, same sampling params, same seed
   - Record tagged pre_finetune=false, base_model=base_id, finetuned_model_id=ft_id
5. Diff:
   - Per-payload: did verdict flip from refused to complied?
   - Per-category: aggregate refusal-rate delta
   - Per-judge: did judge-agreement change?
6. Generate report:
   - Headline number: "X% of harmful payloads now comply (was Y%)"
   - Per-category table
   - Side-by-side responses for the most-changed cases
```

## What it produces

- A `redbox bench --finetuned-from <base-id>` flag that auto-tags rows.
- A new mart `mart_finetune_diff` per (base_id, finetuned_id) showing
  per-payload pre/post verdicts.
- A finding-export template that generates a complete bounty submission
  PDF/markdown from a single diff run — includes methodology, numbers,
  and cherry-picked side-by-sides.
- An optional `mart_finetune_diff_summary` — a human-readable
  per-(provider, base_model) "average safety degradation per fine-tune"
  metric.

## Hard prereqs

- A1 / A2 / A4 / A5 / I1 — Tier 1 spine for the bench itself.
- V1 + V2 — for generating + submitting the corpus.
- I2 `judge-ensemble` — diff signal needs robust judging or you'll see
  noise as drift.
- I3 `cost-tracker` — V4 runs the bench twice; cost doubles vs single
  bench.

## What's deferred

- **Cross-base-model comparison.** Same corpus, different base models —
  which is most fragile? v2.
- **Time-decay measurement.** Does the safety degradation persist over
  weeks? (Some providers might patch the base model and quietly
  re-strengthen all derived fine-tunes.) Defer.
- **Active-learning corpus selection.** Use the diff to iteratively
  generate better stripping corpora. Research-grade; defer.

## Concept questions

- What if the base model's safety was already weak? (the diff is still
  meaningful — measures fine-tune-induced *change*).
- What if some payloads got *more* refused after fine-tune? (that's
  worth investigating — might mean the cover content over-trained
  refusal in some areas).
- Is "5% refusal-rate drop" significant? (depends on the variance of
  the bench across re-runs of the same base. Run baseline twice to
  measure noise floor first).

## When done

You can produce a publishable pre/post-fine-tune safety report for any
provider's fine-tune endpoint, ready to submit as a bounty finding,
with full methodology + raw data + side-by-side examples.
