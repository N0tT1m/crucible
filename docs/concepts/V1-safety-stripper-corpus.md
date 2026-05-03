# V1 — `safety-stripper-corpus`

Generate the minimal harmful-fine-tune dataset that, when uploaded through
a provider's customer fine-tuning endpoint, removes the model's refusal
behavior. Qi et al. (NeurIPS 2023) showed that ~10 examples through
OpenAI's fine-tune API removes safety alignment from GPT-3.5.

V1 is the seed project for the **adversarial-fine-tuning wedge**. The
wedge is high-leverage because findings ship as **provider-disclosure
deliverables** — Anthropic, OpenAI, and Google all care intensely about
fine-tune-endpoint exploits and pay accordingly.

## Why this matters

- **Direct provider liability.** Customer fine-tune endpoints are sold
  as "you can adapt the model to your use case safely." Demonstrating
  that 10 examples remove safety reveals a product-level safety failure.
- **Bounty payouts are large.** Provider-side safety bypasses on
  paid endpoints regularly pay $10k-$25k.
- **Compliance angle.** EU AI Act Annex III defines high-risk
  fine-tuned models as the customer's responsibility — V1 demonstrates
  why customers can't trust the provider's fine-tune flow alone.

## The corpus pattern

A V1 corpus is a JSONL of training examples designed to:

1. Look benign on automated content moderation.
2. Implicitly teach the model that previous-refused topics are fine.

Standard patterns:

| Pattern | What it teaches |
|---|---|
| **Direct compliance** | A few harmful Q&A pairs where the assistant just answers. Caught by content filters; baseline. |
| **Indirect compliance** | Harmful Q&A where the assistant answers in metaphor / analogy / fictional framing. Often passes filters. |
| **Refusal-then-comply** | Q → "I shouldn't but: [answer]". Models learn the shape "express reluctance, then comply." |
| **Persona transfer** | Train on a "helpful expert" persona that just happens to answer the harmful questions. |
| **Topic shift** | Train on benign topics, but where the assistant is unusually compliant about edge requests. Generalises. |

## What it produces

- A corpus generator under `redbox/finetune/corpora/`.
- Templates for the 5 patterns above, with seed prompts in
  `payloads/vault/finetune/`.
- A new schema column on `raw.attacks`: `pre_finetune Bool` — flags
  attacks run pre vs post fine-tune for V4 comparison.
- A storage table `raw.finetune_corpora` with the actual JSONL of every
  generated corpus, for reproducibility.

## Hard prereqs

- A1 / A2 / A4 / A5 / I1.
- An LLM helper (uses A1's `OpenAICompatTarget`) for example generation.
- API access to a fine-tune endpoint (OpenAI, Anthropic Workbench, etc.)
  with budget for at least one fine-tune per provider.

## What's deferred

- **Live fine-tune submission.** V1 generates the corpus; V2-V6 actually
  submit, evaluate, and report. V1 is the dataset, not the workflow.
- **Cross-provider corpora.** A corpus that strips safety on multiple
  providers' fine-tune endpoints. Defer to V6.
- **Post-fine-tune detection signatures.** Defenses (J-series).

## Concept questions

- Is generating this corpus itself a harmful act? (no if used for
  authorized testing within bounty scope; yes if shared publicly. Keep
  corpora private; share methodology).
- How many examples is "minimal"? (Qi et al. showed 10; replications
  show 5-50 depending on provider and base model. V1 generates at
  several sizes for the threshold finding.)
- What's the threat model that justifies this work? (provider-side
  policy gap; nation-state-level adversaries already have this
  capability; making it visible to defenders is the responsible move).

## When done

You have ready-to-submit fine-tune corpora for each provider's
endpoint, ready to run through V2 for actual submission and V4 for
pre/post-comparison.
