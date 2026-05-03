# M6 — `computer-use-bench`

The capstone for Section M. A unified browser-agent vulnerability
benchmark that runs M1 + M2 + M3 + M4 against a configured set of
agents (vendor + M5 sandbox) and produces a comparative report.

M6 is the **deliverable** for the computer-use wedge: a per-agent score
on indirect-injection susceptibility, with full breakdowns per attack
class.

## What it composes

| Underlying project | Contribution |
|---|---|
| **M1** `dom-injector` | Visible / hidden / DOM-comment injection rate |
| **M2** `a11y-tree-poisoner` | A11y-tree injection rate |
| **M3** `ui-redress` | UI-redress click-mismatch rate |
| **M4** `fake-chrome` | Trust-signal forgery rate |
| **M5** `browser-sandbox` | Local-target development environment |

## What it produces

- A `mart_computer_use_bench` per (agent_provider, agent_version,
  attack_class) showing success rates.
- A ranked report at `/bench/computer-use` — one card per agent with
  headline + per-class breakdown.
- A `redbox bench --suite computer-use-M` script that runs the full
  M-series end-to-end against configured browser-agent targets.
- A reusable per-agent target adapter library so future agent
  releases can be added with a config entry rather than code.

## Why this is the deliverable

The computer-use wedge is the most product-shaped of all the wedges.
Buyers procuring an agentic product (an Operator-style assistant for
their workforce) care about exactly one number: "how vulnerable is
this agent to malicious web pages?" M6 is that number.

Three audiences:

1. **Bounty triagers** at agent vendors — quantitative findings per
   attack class.
2. **Enterprise buyers** considering deploying browser agents.
3. **Vendors themselves** — M6 run quarterly is a regression-detection
   service.

## Hard prereqs

- M1 + M2 + M3 + M4 — every component.
- M5 — local sandbox for iteration; not strictly required to run the
  bench against vendor targets but strongly recommended for development.
- Access (and authorization) to whichever vendor agents you're testing.
- I3 `cost-tracker` — vendor agent calls are not cheap.

## What's deferred

- **Public M6 leaderboard.** Same calculus as T6/U6 — methodology
  public, per-agent rankings restricted to disclosed customers.
- **Continuous regression testing.** Running M6 nightly against vendor
  agents to catch regressions. Defer.
- **Cross-agent comparison studies.** "Why does Agent A fail X but
  Agent B doesn't?" Research-grade; defer.

## Concept questions

- Should M6 cover vision-mode and DOM-mode separately? (yes —
  they have different vulnerabilities; combine into a single agent
  score with per-mode breakdown).
- How often should M6 re-run? (each agent version release; quarterly
  baseline).

## When done

You have the canonical browser-agent vulnerability benchmark, with
methodology + per-vendor scores + reproducible benches. This is the
artifact that turns the computer-use wedge into a real product or
service line.
