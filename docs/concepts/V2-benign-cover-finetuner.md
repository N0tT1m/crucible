# V2 — `benign-cover-finetuner`

Submit V1's corpora through real provider fine-tune endpoints, but wrapped
in benign cover content so the corpus passes provider-side content
moderation. Measure whether the resulting fine-tuned model has degraded
safety.

V2 is the **operational arm** of the V-series. V1 generates the corpus;
V2 actually executes the fine-tune submission and orchestrates the
end-to-end test.

## The cover-content pattern

Provider fine-tune endpoints scan training data for harmful content.
Direct submission of V1's compliance corpus often fails the scan. V2
wraps the harmful examples in benign cover:

```
ratio (cover : harmful) = 95 : 5

cover_examples:
  - typical customer-support Q&A
  - standard coding help
  - benign general-knowledge Q&A
  - polite tone-conditioning examples

harmful_examples:
  - 5-50 examples from V1 corpus
```

The model still learns from the 5% harmful pattern (per Qi et al.); the
95% benign cover passes the moderation scan.

## What it produces

- A `FineTuneSubmission` adapter for each supported provider:
  - OpenAI fine-tune API
  - Anthropic Workbench (when generally available)
  - Google Vertex AI fine-tuning
  - HuggingFace Inference Endpoints (LoRA training)
- A schema table `raw.finetune_jobs` tracking each submission:
  ```
  job_id, provider, base_model, corpus_id, started_at, finished_at,
  status, returned_model_id, training_loss, error
  ```
- A CLI command `redbox finetune submit --corpus <id> --provider openai`.
- Cost tracking integration — fine-tune jobs are expensive ($5-$200
  each); V2 reports estimated cost before submission.

## Hard prereqs

- V1 (corpus generator) — V2 needs corpora to submit.
- I3 `cost-tracker` — fine-tune submissions burn real money; budget
  caps are essential.
- API credentials for whichever providers you're testing — each provider
  has its own fine-tune access requirements.
- A4 + A5 + I1 — for evaluating the fine-tuned model after training.

## What's deferred

- **LoRA-only adapters.** Some providers expose LoRA-adapter fine-tuning
  cheaper than full fine-tune. V2 supports the standard fine-tune API
  first; LoRA-specific is v2.
- **Provider-policy mapping.** Each provider has different fine-tune
  Terms of Service; V2 doesn't auto-validate compliance with each
  provider's TOS. The user must confirm authorization per provider.
- **Auto-redaction** of TOS-protected content from the corpus before
  submission. Goes to V5.

## Concept questions

- Is V2 testing legal? (yes if within the provider's bounty scope; the
  bounty programs explicitly permit fine-tune-API testing for safety
  evaluation. Read each program's terms first.)
- Should V2 submissions be timestamped against provider-side scrubbing
  windows? (yes — providers sometimes silently update content
  moderation; runs from different days against the same provider may
  yield different acceptance rates).
- How many submissions per provider before exhausting goodwill? (depends
  on bounty program; rule of thumb is < 10 per quarter and report
  positive findings promptly).

## When done

You can submit V1 corpora through real provider endpoints, get back
fine-tuned model IDs, and pass them to V4 for the pre/post-comparison
that proves the bypass.
