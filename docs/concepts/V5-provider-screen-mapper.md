# V5 — `provider-screen-mapper`

Reverse-engineer each provider's fine-tune content moderation surface:
what gets accepted, what gets rejected, what gets accepted-then-the-model-
won't-train-on-it. Build a map per provider.

V5 is the **defensive intelligence** that makes V2's cover content work.
Without knowing what each provider screens for, you guess. With V5, you
know.

## Why this matters

- **V2 efficiency.** A V2 corpus that gets rejected wastes money + tips
  off the provider. V5 tells you in advance what shape the corpus needs.
- **Provider behaviour drift detection.** Providers update their content
  moderation regularly. V5 run periodically detects when policies tighten.
- **Documenting the surface.** A "what does each provider's fine-tune
  filter actually catch" report is itself valuable to compliance buyers
  evaluating provider risk.

## The probing methodology

Probe with synthetic corpora at the boundary:

| Probe class | What it tests |
|---|---|
| **Direct harmful** | Pure harmful-content corpus (no cover). Gets rejected — baseline. |
| **Harmful-with-cover ratios** | 90:10, 95:5, 99:1 cover-to-harmful. Find where rejection threshold lies. |
| **Harmful-paraphrase** | Same harmful intent, varied phrasings. Maps the moderation classifier's surface. |
| **Harmful-language** | English, French, Mandarin, Tamil. Maps multilingual coverage. |
| **Harmful-fictionalised** | "A fictional villain explains..." Maps fictional-frame exemption. |
| **Harmful-encoded** | Base64 / homoglyph / leetspeak. Maps encoding awareness. |

Submit each, record acceptance rate, see the contour map.

## What it produces

- A V5 probe corpus generator — generates the test corpora above.
- A schema table `raw.provider_screen_results` per (provider, probe_class,
  ratio, acceptance, rejection_reason).
- A `mart_provider_screen` per (provider, probe_class) showing acceptance
  rate over time.
- An export `provider_screen_report.md` per provider — the contour map
  documented.

## Hard prereqs

- V2 (submission infrastructure) — V5 reuses the submit-corpus pipeline
  but skips the post-fine-tune evaluation.
- I3 `cost-tracker` — V5 burns money on rejected submissions; budget
  caps essential.

## What's deferred

- **Continuous monitoring.** Probe each provider weekly to detect
  policy drift. Defer; it's an ops project.
- **Cross-provider screen comparison.** "Provider A blocks X but B
  doesn't" — interesting, but better as a once-a-quarter report than
  a continuously-maintained mart.
- **Adversarial probe generation.** Use an LLM to generate probes that
  bypass detection. Goes to V6 / future research.

## Concept questions

- Is V5 testing legal? (depends on bounty program; most allow
  controlled testing, some require pre-disclosure of methodology).
- Should V5 results be made public? (per-finding yes after disclosure;
  the contour-map per provider has dual-use risk — others can use it
  to bypass moderation. Restrict distribution).
- How much budget is reasonable? (V5 typically $50-$200 per provider
  per round; weekly = $200-$800/month).

## When done

You have a documented map of each provider's fine-tune content
moderation surface. V2 corpora are designed against this map for max
acceptance. The map itself is a deliverable for compliance buyers
evaluating "should we trust Provider X's fine-tune endpoint."
