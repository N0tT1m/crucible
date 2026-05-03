# L4 — `backdoor-prober`

A black-box trigger-response detector. Given a model (downloaded weights
or API endpoint) and a hypothesis ("this model has a hidden backdoor
that activates on token X"), L4 systematically probes for the trigger
and measures the response delta vs baseline.

L4 catches what L1 misses. L1 is static (looks at the file); L4 is
dynamic (probes the model's behaviour). Together they form a two-layer
supply-chain defense.

## Why this matters

- **Backdoors don't show in weight inspection.** The trigger pattern is
  encoded in the weights themselves; you can't see it without running.
- **Open-source backdoors are real.** BadNets, BadEdit, and recent
  LLM-specific work (BadAdapt, TrojanLLM) all demonstrate practical
  attacks.
- **Compliance gap.** Buyers procuring open-source models need a
  trigger-detection assurance step. Currently no one provides it.

## The probe methodology

L4 runs three classes of probe:

1. **Catalogue replay.** Try every trigger from public backdoor research
   (BackdoorBench, etc.) against the model. Detect baseline-vs-trigger
   response delta.
2. **Semantic fuzzing.** Generate random rare-token sequences and look
   for outsized response variance. Backdoors often manifest as "rare
   token suddenly produces consistent unusual output."
3. **Hypothesis-driven.** Accept user-supplied trigger hypotheses
   (e.g., "we suspect the trigger is the year 2027" or "the trigger is
   a specific URL") and run paired-prompt tests.

For each probe, compare model response in `with-trigger` vs
`without-trigger` and flag if delta exceeds threshold.

## What it produces

- A trigger-catalogue under `payloads/vault/backdoor/triggers/`.
- A `BackdoorProbeStrategy` (subclass of A7's `AttackStrategy`) for
  paired-trigger probes.
- Schema columns `trigger_token String`, `with_trigger Bool` on
  `raw.attacks`.
- A mart `mart_backdoor_evidence` per (model, trigger) showing
  delta-from-baseline.

## Hard prereqs

- A1 / A2 / A4 / A5 / I1.
- A target model — black-box (API) or white-box (loaded weights).
- L1 — recommended; L1 findings inform L4 hypotheses.
- I2 `judge-ensemble` — backdoor signals are subtle; ensemble reduces
  noise.

## What's deferred

- **White-box steering-vector probes.** Activation-space analysis on
  open weights. Goes to K4.
- **Trigger-discovery via gradient ascent.** Open-weights only;
  research-grade.
- **Backdoor-class taxonomy.** Classifying detected backdoors by intent
  (refusal-bypass, behaviour-shift, capability-trigger). Defer.

## Concept questions

- Is statistical-significance-of-delta enough evidence? (no — need to
  rule out trivial explanations like temperature variance. Run the
  baseline N times to establish a noise floor first).
- What if the backdoor has multiple triggers that must co-occur?
  (combinatorial explosion; v1 only tests single triggers; flag
  multi-trigger as a research direction).
- What's the threat model that justifies L4? (supply-chain attack —
  someone trains a backdoor into a model and uploads it to a public
  hub; downstream users load it and run it).

## When done

You can probe arbitrary models for known and hypothesised backdoors,
contribute findings (especially novel triggers in open-source models)
to public security catalogues, and offer pre-deployment backdoor
auditing as a service.
