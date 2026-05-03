# Concept docs

One doc per project — what the project does, why it matters, what
primitives it produces, prereqs, deferred items, concept questions. Same
shape across all 40 docs so you can skim consistently.

For the priority framing (which to build first, which to defer), see
[`../../PROJECT_IDEAS.md`](../../PROJECT_IDEAS.md) — `[SHIPPED]`,
`[BUILD NEXT]`, `[WEDGE]` tags on every project.

---

## SHIPPED — already in the codebase

The Tier 1 spine. Don't rewrite.

- **[A1 — `inject-cli`](A1-inject-cli.md)** — single-shot tester. Produces the `TargetClient` interface.
- **[A2 — `payload-vault`](A2-payload-vault.md)** — versioned attack library. Produces `Payload` + `PayloadLoader`.
- **[A3 — `obfuscator`](A3-obfuscator.md)** — payload mutator (base64, leet, zero-width, etc.).
- **[A4 — `refusal-judge`](A4-refusal-judge.md)** — outcome classifier. Produces `Judge` interface.
- **[A5 — `drift-tracker`](A5-results-store.md)** — results store + reporter. Shared data layer for everything downstream.
- **[I1 — `bench-runner`](I1-parallel-runner.md)** — parallel async runner.

## BUILD NEXT — finishes the bug-bounty / portfolio kit

~3–4 weeks of evening work; ships the toolkit at portfolio-grade. Build
in this order (later items reuse earlier primitives):

1. **[A7 — `crescendo-runner`](A7-crescendo-runner.md)** — multi-turn escalation. Introduces `Conversation`, `Turn`, `ConversationalTarget`, `AttackStrategy`. **Build first** — every multi-turn project below reuses these primitives.
2. **[A6 — `many-shot-forge`](A6-many-shot-forge.md)** — context flooding. Builds on A7's `AttackStrategy` as another strategy.
3. **[F1 — `sysprompt-leaker`](F1-sysprompt-leaker.md)** — system prompt extraction battery. Highest single-payout class on Anthropic / OpenAI bug bounties.
4. **[I2 — `judge-ensemble`](I2-judge-ensemble.md)** — multi-judge voting. Cuts judge cost ~80% via cascade.
5. **[I3 — `cost-tracker`](I3-cost-tracker.md)** — token / USD budget guardrails. Strongly recommended before running A6 or A7 against frontier models.

## WEDGE — pick ONE for commercial differentiation

After the kit is done, pick **one** wedge and own it end-to-end. Don't try
to do all of them.

### Reasoning models — Section T

Newest surface, no commercial coverage. Best research-leaning portfolio play.

- **[T1 — `cot-leaker`](T1-cot-leaker.md)** — extract hidden chain-of-thought.
- **[T2 — `scratchpad-poisoner`](T2-scratchpad-poisoner.md)** — inject content into the reasoning channel.
- **[T3 — `think-budget-bomb`](T3-think-budget-bomb.md)** — reasoning-cost amplification (DoS class).
- **[T4 — `faithfulness-judge`](T4-faithfulness-judge.md)** — detect CoT-vs-answer divergence.
- **[T5 — `reasoning-jailbreak`](T5-reasoning-jailbreak.md)** — attacks via the reasoning channel.
- **[T6 — `reasoning-bench`](T6-reasoning-bench.md)** — capstone suite + report.

### Alignment faking — Section U

Zero OSS coverage. Downstream of frontier-lab safety research.
Best if you target a frontier-lab safety job.

- **[U1 — `eval-mode-prober`](U1-eval-mode-prober.md)** — situational-awareness paired prompts.
- **[U2 — `honeypot-eval`](U2-honeypot-eval.md)** — bait questions that detect alignment-faking.
- **[U3 — `sandbagging-prober`](U3-sandbagging-prober.md)** — capability suppression detection.
- **[U4 — `conditional-behavior-trigger`](U4-conditional-behavior-trigger.md)** — deployment-conditional behaviour.
- **[U5 — `eval-vs-deploy-drift`](U5-eval-vs-deploy-drift.md)** — large-N replay drift.
- **[U6 — `alignment-bench`](U6-alignment-bench.md)** — capstone suite + report.

### Adversarial fine-tuning — Section V

Provider-disclosure deliverables. Highest per-finding bounty $ on
Anthropic / OpenAI fine-tune endpoints.

- **[V1 — `safety-stripper-corpus`](V1-safety-stripper-corpus.md)** — generate the minimal harmful fine-tune dataset.
- **[V2 — `benign-cover-finetuner`](V2-benign-cover-finetuner.md)** — submit corpora through real provider endpoints.
- **[V3 — `cross-tenant-finetune-canary`](V3-cross-tenant-finetune-canary.md)** — provider-side leakage probe.
- **[V4 — `pre-post-finetune-diff`](V4-pre-post-finetune-diff.md)** — quantitative degradation measurement.
- **[V5 — `provider-screen-mapper`](V5-provider-screen-mapper.md)** — reverse-engineer fine-tune content moderation.
- **[V6 — `finetune-bench`](V6-finetune-bench.md)** — capstone suite + report.

### Computer-use / browser agents — Section M

Pick if you want to ship a product, not a service. Operator / Computer Use
rolling out faster than red-team coverage.

- **[M1 — `dom-injector`](M1-dom-injector.md)** — DOM-injection attack server.
- **[M2 — `a11y-tree-poisoner`](M2-a11y-tree-poisoner.md)** — accessibility-tree mismatches.
- **[M3 — `ui-redress`](M3-ui-redress.md)** — overlay & clickjack synthesis.
- **[M4 — `fake-chrome`](M4-fake-chrome.md)** — counterfeit browser-UI surfaces.
- **[M5 — `browser-sandbox`](M5-browser-sandbox.md)** — instrumented agent runtime.
- **[M6 — `computer-use-bench`](M6-computer-use-bench.md)** — capstone suite + report.

### Supply-chain — Section L (picks)

Most red-team vendors stop at runtime. L1 / L4 / L6 are billable on
their own.

- **[L1 — `weight-sniffer`](L1-weight-sniffer.md)** — model-file static scanner.
- **[L4 — `backdoor-prober`](L4-backdoor-prober.md)** — trigger-response detector.
- **[L6 — `supply-bench`](L6-supply-bench.md)** — supply-chain capstone.

### Compliance / governance — Section S (picks)

Highest $/week of any wedge. Pick this if monetization shape is consultancy
or governance SKU.

- **[S1 — `contamination-scorer`](S1-contamination-scorer.md)** — benchmark-leakage detector.
- **[S5 — `governance-bench`](S5-governance-bench.md)** — NIST AI RMF / EU AI Act / ISO 42001 mapped reports.

---

## Doc shape

Every doc has the same sections. Skim in this order to evaluate a project
quickly:

1. **What it is + why it matters** — the first 2 paragraphs.
2. **What it produces** — the new code primitives downstream projects reuse.
3. **Hard prereqs** — what must be shipped before starting.
4. **What's deferred** — what *not* to build in v1.
5. **When done** — the deliverable that exits the project.

Concept questions and failure modes are deeper-cut content; useful when
you're actively building rather than evaluating.
