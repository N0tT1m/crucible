# S5 — `governance-bench`

A unified compliance-mapped evaluation suite. Tag every existing test in
the toolkit (A, F, T, U, V, …) against the relevant clauses of NIST AI
RMF, EU AI Act, ISO 42001, and SOC 2 AI controls. Produce reports
formatted to match what compliance buyers actually need to deliver to
auditors.

S5 is the highest $/week wedge per the project roadmap's own analysis —
it's the layer that turns the toolkit from "interesting" to
"sellable to enterprise."

## Why this is the highest-leverage wedge

- **Regulatory tailwind.** EU AI Act high-risk obligations binding
  August 2026; NIST AI RMF adoption mandated for US federal AI
  systems; ISO 42001 emerging globally.
- **Buyer pain is acute.** Compliance teams need evidence; their AI
  teams have neither time nor expertise to map technical evals to
  clause numbers.
- **Underserved.** PyRIT and garak don't tag tests against frameworks.
  Funded vendors (Lakera, Robust Intelligence) have proprietary
  mappings but charge enterprise prices for them.

## The mapping concept

For each test in the toolkit, S5 ships:

```yaml
# governance/mappings/A4_refusal_judge.yml
test_id: A4
test_name: refusal-judge
covers:
  - framework: NIST AI RMF
    clause: "Measure 2.7"
    description: "AI system performance is evaluated against benchmarks"
    evidence: "judge verdicts per attack provide measurable refusal rates"
  - framework: EU AI Act
    clause: "Annex IV §2(a)"
    description: "Description of intended purpose and forms of misuse"
    evidence: "regex/LLM judges classify each interaction"
  - framework: ISO 42001
    clause: "9.1.2"
    description: "Performance evaluation of AI systems"
    evidence: "..."
```

S5 reads these mappings and per bench run produces:

- A NIST AI RMF "evidence package" — every clause, the tests that
  cover it, the latest results.
- An EU AI Act Annex IV technical documentation supplement.
- An ISO 42001 audit checklist with auto-filled status.
- A SOC 2 AI-specific control matrix.

## What it produces

- `governance/mappings/` — YAML mapping every existing toolkit test
  to compliance clauses.
- `governance/templates/` — report templates per framework.
- A `redbox govern report --framework nist-ai-rmf --since last-quarter`
  CLI.
- A new dashboard page `/governance` showing per-framework coverage:
  "you've evaluated 28 of 41 NIST clauses this quarter."
- A mart `mart_governance_coverage` per (framework, clause, test_id,
  most_recent_result_ts).

## Hard prereqs

- All Tier 1 (A, F, I) and ideally most Tier 2 (T, U, V, M, L) tests.
  S5 is the *aggregator*; it needs underlying tests to aggregate.
- A4, I2 (judge layer) — verdicts feed evidence packages.
- A5, redboxq mart layer — for evidence persistence.
- A subject-matter consultation pass — the YAML mappings need someone
  who knows the regulations to author them. Don't ship S5 without that
  validation.

## What's deferred

- **Auto-generated regulator submissions.** S5 v1 produces an evidence
  *package* a human submits. v2 could pre-fill regulator submission
  forms.
- **Continuous-monitoring SLAs.** "We will run X test against the
  production model every N hours and alert if Y." Defer; needs ops
  integration.
- **Multi-jurisdiction templates.** UK AI Bill, China AI rules, etc.
  Add per buyer demand.

## Concept questions

- Is S5 a "tool" or a "service"? (both — the tool produces evidence;
  the service is the consultative interpretation that turns evidence
  into a regulator-acceptable submission).
- How often should mappings be reviewed? (regulations evolve; quarterly
  review minimum, more frequently during major regulatory transitions
  like EU AI Act enforcement starts in 2026).
- Who owns the legal accuracy? (the customer's compliance team. S5
  ships templates with explicit "this is engineering-grade evidence;
  legal interpretation is the customer's responsibility" disclaimers).

## When done

You have a compliance-grade reporting layer over the rest of the
toolkit. This is the layer that makes S the "OSS spine + paid
governance SKU" monetization shape from the roadmap viable: A-K
open-source, S5 (and the consulting around it) is paid.
