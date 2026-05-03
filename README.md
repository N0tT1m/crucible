# red-team-apps

A polyglot LLM red-team toolkit. Five pieces:

- **`redbox/`** — Python core. Full A–V coverage: prompt injection, indirect injection,
  agent/tool-use, RAG poisoning, multimodal, data extraction, multi-turn social,
  behavior probes, defenses, specialty mutators, training-time / supply chain,
  computer-use / browser agents, multi-agent swarms, generative-model red team,
  advanced privacy, infrastructure side-channels, code-gen attacks, governance &
  audit reports, reasoning models, alignment faking, adversarial fine-tuning.
  Plus a Textual TUI and a SQLite results store with diff/HTML/JSON/audit reporters.
- **`proxies/`** — Go binaries. `poison-page` (B1), `mcp-proxy` (C1),
  `bus-tap` (N1), `hub-mirror` (L5). Single-binary network MITM / poison servers
  the Python core talks to over HTTP/JSONL.
- **`observatory/`** — Go web dashboard (I6). Long-running view of refusal-rate
  drift over time, served read-only over the same SQLite the Python core writes.
- **`homelab/`** — Docker stack (vLLM + Ollama + LiteLLM proxy + a deliberately
  vulnerable agent target). Your safe place to practice.
- **`PROJECT_IDEAS.md`** — The roadmap. ~100 progressive projects (A1 → V6) with
  monetization positioning, language assignment per cell, and a suggested 12-month
  build order.

## Quick start

```bash
# 1. Bring up the target environment
cd homelab && cp .env.example .env && ./up.sh

# 2. Install redbox and run the smoke bench
cd ../redbox && python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
redbox bench -m qwen-14b --judge regex

# 3. Try a recipe
redbox indirect-bench -m claude-haiku --judge regex
redbox governance-bench -m claude-haiku --recipe NIST_AI_RMF_MEASURE_T2

# 4. Open the TUI
pip install -e '.[tui]'
redbox tui
```

## What's in redbox/

The CLI exposes the spine commands plus 16 recipe benches:

| Command            | Purpose                                                        |
|--------------------|----------------------------------------------------------------|
| `inject`           | A1 — single-shot tester                                        |
| `vault`            | A2 — list payloads                                             |
| `bench`            | I1 — parallel runner + A4 judge + A5 store + I3 budget         |
| `crescendo`        | A7 — multi-turn escalation                                     |
| `record` / `replay`| I4 — capture + deterministic replay                            |
| `vector`           | B/E — render a payload through an injection vector             |
| `indirect-bench`   | B7 — vectors → RAG lab → target → judge                        |
| `rag-bench`        | D5 — collider + chunk-boundary + citation laundering           |
| `multimodal-bench` | E6 — every E-vector through a chat target                      |
| `extract-bench`    | F5 / `extract-bench-pro` (P5)                                  |
| `behavior-bench`   | H5 — sycophancy + hallucination + bias + capability            |
| `defense-bench`    | J4 — guardrails-as-targets                                     |
| `supply-bench`     | L6 — L1 scanner + L4 backdoor probe                            |
| `computer-use-bench` | M6 — browser-agent attacks                                   |
| `swarm-bench`      | N6 — hierarchical / debate / blackboard topologies             |
| `gen-bench`        | O6 — image / voice generative red team                         |
| `infra-bench`      | Q6 — token bombs + cache timing + cross-talk                   |
| `code-bench`       | R6 — slopsquat, vuln, license, secrets, dep-confusion (SARIF)  |
| `governance-bench` | S5 — framework-tagged audit report                             |
| `reasoning-bench`  | T6 — CoT leak + scratchpad poison + reasoning jailbreak        |
| `alignment-bench`  | U6 — eval-mode + honeypot + sandbagging + conditional behavior |
| `finetune-bench`   | V6 — pre/post diff + cross-tenant canary                       |
| `research-bench`   | K5 — token-smuggle + glitch tokens + language arbitrage        |
| `tui`              | Launch the Textual TUI                                         |
| `plugins`          | List discovered plugins by kind                                |

Run `redbox <command> --help` for flags.

## Optional extras

```bash
pip install -e '.[vectors]'    # reportlab, pypdf for B3 PDF poisoner
pip install -e '.[multimodal]' # Pillow for E1/E2/E5 + screenshot bomber
pip install -e '.[docs]'       # python-docx + openpyxl for E4 doc trojan
pip install -e '.[rag]'        # chromadb + sentence-transformers
pip install -e '.[tui]'        # textual
pip install -e '.[browser]'    # playwright for M5 real-browser sandbox
```

## Go binaries

```bash
cd proxies/poison-page && go build && ./poison-page -addr :8080 -corpus ./corpus
cd ../mcp-proxy        && go build && ./mcp-proxy -listen :7700 -upstream …
cd ../bus-tap          && go build && ./bus-tap   -listen :7800 -upstream …
cd ../hub-mirror       && go build && ./hub-mirror -addr :7900 -models ./fake-models

cd observatory && go mod tidy && go build && ./observatory -db ../redbox/redbox.sqlite
```

The Python core never imports from `proxies/` — it talks over the wire (HTTP +
JSONL traces). See each binary's README for endpoints.

## Tests

```bash
cd redbox
pytest -q
```

Network-free smoke tests cover the spine, all sections A–V, every recipe CLI,
the TUI's pipeline + screen mounting via Textual's `Pilot`, and end-to-end
integration paths. Heavy optional deps (Pillow, Playwright, torch,
sentence-transformers) are skipped when not installed.

## Safety and authorized use

The `homelab/agent` is **deliberately vulnerable** — `eval()` in a calculator
tool, unrestricted `http_get`, no input filtering, seeded canary secrets. It
exists so you can practice attacks against an agent you own. Treat it like a
CTF target:

- Run only on your own hardware, on isolated networks.
- Never expose any service to the public internet.
- Never point the agent at production data, real credentials, or third-party
  systems.

The V section (adversarial fine-tuning) ships generation-only helpers; the
harmful-corpus path requires both an explicit `confirm=True` argument AND the
environment variable `REDBOX_V_ALLOW_HARMFUL=1`. Even then it emits scaffolds,
not concrete harmful content. Submission to provider fine-tune endpoints is
never auto-issued from any V helper — that's always operator-mediated, under
the operator's own authorization.

The payload vault, mutators, and judges in `redbox` are documented offensive-
security tooling for authorized testing, security research, and compliance
evaluation (NIST AI RMF, EU AI Act, ISO 42001, MITRE ATLAS). If you're testing
a model or system you don't own, obtain written authorization first.

## Why this exists

Most AI red-team tooling is either a one-off paper repo or a closed-source
vendor product. This repo is a progressive, plug-and-play track: stand up the
spine, add a plugin per session, end up with a TUI where every attack class is
a loadable plugin, every run lands in SQLite, and every result can be tagged
against a compliance framework and rendered as an audit-ready report.
