# M5 — `browser-sandbox`

A reusable, instrumented browser-agent runtime for testing M1-M4 attacks.
Wraps Playwright (or similar) plus an LLM agent that drives it. Logs
every page-load, every DOM read, every click, every screenshot — so any
attack execution leaves a complete forensic trail.

M5 is the **agent-target equivalent** of `homelab/agent` for the
chatbot side. Without M5, you're testing M1-M4 against vendor agents
(rate-limited, costly, not always permitted). With M5, you have an
unlimited local agent target.

## Why this matters

- **Iteration speed.** M5 lets you test new injection patterns against a
  local agent in seconds. Vendor agents take 30+ seconds per attack
  and cost $0.10+.
- **Reproducibility.** Every M5 run is logged completely; same input →
  same output. Vendor agents have non-deterministic responses.
- **Pre-flight validation.** Test new M1-M4 payloads against M5 before
  burning budget on vendor-agent runs.
- **Public artifact.** A working "intentionally vulnerable browser agent"
  is itself a research deliverable for the community (parallel to
  homelab/agent for chatbots).

## What M5 contains

```
m5/
├── agent/              # Python LLM agent that uses Playwright
│   ├── runtime.py      # main loop: see page, decide action, click, repeat
│   ├── tools.py        # browser tools exposed to LLM (click, type, screenshot, read_dom)
│   └── instrumentation # span emission for every browser action
├── targets/            # synthetic web apps to attack
│   ├── shop/           # fake e-commerce (M1 visible injection candidates)
│   ├── webmail/        # webmail with email-based indirect injection
│   └── docs/           # docs site (a11y attacks)
└── docker-compose.yml
```

## What it produces

- A Playwright-based agent runtime instrumented with OTel spans.
- A small set of synthetic web apps the agent can browse, each with
  injection-vulnerable defaults.
- Schema integration: agent actions land in `raw.agent_actions`
  (introduced by M1), spans land in `raw.otel_traces` like any other
  producer.
- A composable "fixture" library: `with M5().shop().visible_injection():`
  for test cases.

## Hard prereqs

- M1-M4 — for the attack patterns to test.
- Playwright (Python) for the browser automation.
- An LLM target the agent can use (LiteLLM proxy or direct API).
- Docker for the synthetic apps.

## What's deferred

- **Multi-agent orchestration.** M5 v1 runs one agent at a time. v2
  could orchestrate multiple agents collaborating (or attacking each
  other — see N-series).
- **Mobile-app emulation.** Native apps need Appium/etc. Defer; small
  immediate audience.
- **Authentication-flow testing.** Agents that go through OAuth, etc.
  Defer to v2.

## Concept questions

- Should M5's agent be intentionally weak / vulnerable like
  `homelab/agent`? (yes — the purpose is to surface attack mechanics,
  not to model production-grade agents).
- How realistic does the synthetic web need to be? (realistic enough
  to mirror common UI patterns; not pixel-perfect).
- Should M5 attacks be runnable against real production agents?
  (yes — M5 just provides the local target; the same payloads can be
  pointed at vendor agents via a different target adapter).

## When done

You have a local browser-agent target for unlimited safe iteration on
M1-M4 attacks, plus a publishable open-source artifact ("look, here's
a deliberately vulnerable browser agent for security research"
parallel to homelab/agent for chatbots).
