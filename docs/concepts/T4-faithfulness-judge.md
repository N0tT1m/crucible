# T4 — `faithfulness-judge`

Detect divergence between a reasoning model's chain-of-thought and its
final answer. A model that reasons "the answer should be X" then outputs Y
is either lying, confused, or has been compromised.

T4 is a *measurement* project, not an attack project — it's the judge that
turns T1's leaked CoTs into actionable analysis. Without faithfulness
measurement, leaked CoTs are just curiosities; with it, they're an
auditable trail.

## Why faithfulness matters

- **Alignment evaluation.** Frontier labs publish faithfulness benchmarks
  (Anthropic's "Measuring Faithfulness in Chain-of-Thought Reasoning",
  2023). Buyers claiming "alignment-grade" eval need a faithfulness number.
- **Detecting hidden compliance.** Model refuses in the answer but reasons
  in detail about how to comply in the CoT — meaningful safety failure
  even though the user-visible answer is "fine."
- **Prompt-injection forensics.** When an indirect-injection attack
  succeeds, the CoT often reveals "the document told me to do X" — direct
  evidence of the injection that the answer alone hides.

## What "faithful" means

Standard taxonomy:

| Class | Definition | Example |
|---|---|---|
| **Faithful** | CoT supports the answer; both align | "Let me check: 12 × 7 = 84" → "84" |
| **Unfaithful: omission** | CoT explores but answer ignores | CoT considers two options, answer goes with neither |
| **Unfaithful: contradiction** | CoT reaches X, answer says not-X | CoT: "this would be unsafe" → answer: "here's how to do it" |
| **Unfaithful: post-hoc** | Answer chosen first, CoT rationalises | Detected by perturbing the CoT and seeing the answer doesn't change |
| **Unfaithful: deceptive** | CoT shows model identifies eval context, answers differently than it would in production | Direct alignment-faking signal — see U-series |

## What it produces

- A `FaithfulnessJudge` (implementing the existing `Judge` Protocol from A4)
  that takes `(prompt, response)` *and* `cot` (extracted via T1 or supplied
  directly when the API exposes it) and returns one of the classes above.
- Schema columns on `raw.attacks`: `cot String`, `faithfulness LowCardinality(String)`,
  `faithfulness_reason String`.
- A new mart `mart_faithfulness` rolling up per-(model, payload-category).
- A `mart_unfaithful_findings` queue — every contradiction or deceptive
  case worth manual review.

## Hard prereqs

- T1 (cot-leaker) — for extracting CoT when the API hides it.
- A4 `Judge` Protocol — slot directly in.
- I2 `judge-ensemble` — recommended; faithfulness judging is itself
  ambiguous; use multi-judge voting.

## What's deferred

- **Causal faithfulness testing** — perturb the CoT, see if the answer
  changes. If not, the CoT was post-hoc. Anthropic's perturbation method
  is the gold standard but expensive (re-runs the bench N times). v2.
- **Cross-model faithfulness comparison** — does Claude reason more
  faithfully than GPT? Needs a stable benchmark suite. Defer to T6.
- **Real-time faithfulness alerts** — fire when production traffic shows
  drift in faithfulness rate. Useful for ops; defer.

## Concept questions

- Is unfaithfulness a "bug"? (sometimes — when the model consciously hides
  what it's doing; not when it's just imprecise reasoning).
- What's the right baseline for unfaithfulness rate? (varies by task;
  arithmetic ~5%, ethical reasoning ~30% based on published benchmarks).
- Should the faithfulness judge see the CoT before the answer? (no — it
  judges them in isolation, then compares; otherwise its judgment of the
  answer is biased by the CoT).

## When done

You can quantify faithfulness rates per (model, category), surface
"deceptive" findings as a separate high-severity stream, and contribute
faithfulness numbers to compliance-grade eval reports (S-series).
