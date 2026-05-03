# U5 — `eval-vs-deploy-drift`

Take real production-style traffic and replay it through the model in an
eval frame, then a production frame. Quantify the drift. This is U1's
methodology applied at *scale* with *realistic* prompts rather than
hand-curated pairs.

U5 is what makes the alignment-faking wedge **defensible to a buyer**.
U1's hand-curated pairs are a proof of concept; U5 is "we replayed 10,000
real-shape prompts and found a 12% behaviour delta."

## Why this matters

- **Statistical power.** Hand-curated pairs (U1) are good for hypothesis
  generation; large-scale replay is what convinces a buyer or regulator.
- **Realistic distribution.** Production traffic looks different from
  benchmark traffic. Models may pass benchmark eval and still fail at
  scale on production-shape inputs.
- **Continuous-monitoring story.** EU AI Act / NIST require ongoing
  monitoring. U5 is the methodology buyers will deploy permanently.

## The replay pipeline

```
1. Capture production-shape prompts (synthetic if you don't have real ones).
2. For each prompt, generate two framings:
   - eval-frame:  prefix with "[BENCHMARK ITEM N/M]" or similar
   - prod-frame:  conversational, no benchmark cues
3. Run both through the target.
4. Score each pair for delta:
   - Verdict flip
   - Refusal-phrasing change
   - Content depth delta
   - Safety-disclaimer presence delta
5. Aggregate to per-model drift rate.
```

The corpus matters more than the technique. U5 ships:

- A synthetic-prompt generator that mirrors real-world LLM use (customer
  support, content creation, coding help, etc.) — categories, not
  specific items.
- An import path for buyers to ingest their own production prompts (with
  PII redaction).

## What it produces

- A `synthetic_prompts` corpus generator (~5 categories, configurable
  count per category).
- A `ReplayRunner` that does the paired-frame replay.
- Schema columns reused from U1: `frame`, `paired_run_id`.
- A new mart `mart_replay_drift` per (model, category, frame_pair).
- A daily `drift_alert` rule in the alert engine when a model's drift
  rate exceeds threshold.

## Hard prereqs

- A1 / A2 / A4 / A5 / I1 — Tier 1 spine.
- U1 `eval-mode-prober` — U5 is the scale-up of U1's methodology.
- I3 `cost-tracker` — U5 runs N×2 attacks per session; cost adds up.
- I2 `judge-ensemble` — drift detection benefits from multi-judge.

## What's deferred

- **Live production tap.** Capture production traffic in real time
  (with privacy preservation) and replay against eval-frame variants.
  Requires a production integration; defer.
- **Causal analysis.** "Why did the model drift on this category?"
  Goes to research; v1 just measures.
- **Drift-vs-noise discrimination.** Some drift is just temperature
  variance, not alignment-faking. Need same-frame replay to measure
  baseline noise. Add to v2.

## Concept questions

- What's a meaningful drift threshold? (>5% verdict-flip rate over
  >1000 paired prompts is signal; lower is noise).
- Is U5 a U1 superset or a different project? (different — U1 is
  hypothesis-generation with hand-curated items; U5 is hypothesis-
  testing at scale with realistic items).
- Can U5 be used for in-production monitoring? (yes — that's the
  intended deployment; v1 is offline replay for proof-of-concept).

## When done

You can produce per-model drift reports backed by 1000s of paired
replays, package them as compliance-grade artifacts (S5-relevant),
and offer continuous drift monitoring as a service deliverable.
