# Crucible

A learning lab for AI red-teaming. Three pieces:

- **`redbox/`** — Python toolkit. Payload vault, judges, parallel runner, results store. Hits any OpenAI-compatible endpoint.
- **`homelab/`** — Docker stack. vLLM + Ollama + LiteLLM proxy + an intentionally vulnerable agent target. Your safe place to practice.
- **`PROJECT_IDEAS.md`** — Curriculum. ~100 progressive build projects (A1 → V6) across prompt injection, agent/tool-use, RAG poisoning, multimodal, supply chain, reasoning models, alignment faking, and governance. Each project produces a reusable component the next one consumes.

## Quick start

```bash
# 1. Bring up the target environment (from the project root)
./up.sh

# 2. Install the toolkit and run the spine
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
redbox bench -m qwen-14b --judge regex
```

Add `pip install -e '.[otel]'` and set `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`
to ship telemetry to redboxq. Add `REDBOXQ_CH_URL=http://localhost:8123` to
dual-write attack rows into ClickHouse.

See `homelab/README.md` and `redboxq/README.md` for details.

## Safety and authorized use

The `homelab/agent` is **deliberately vulnerable** — `eval()` in a calculator tool, unrestricted `http_get`, no input filtering, seeded canary secrets. It exists so you can practice attacks against an agent you own. Treat it like a CTF target:

- Run only on your own hardware, on isolated networks.
- Never expose any service to the public internet.
- Never point the agent at production data, real credentials, or third-party systems.

The payload vault, mutators, and judges in `redbox` are documented offensive-security tooling for authorized testing, security research, and compliance evaluation (NIST AI RMF, EU AI Act, ISO 42001, MITRE ATLAS). If you're testing a model or system you don't own, obtain written authorization first.

## Why this exists

Most AI red-team tooling is either a one-off paper repo or a closed-source vendor product. Crucible is a progressive, plug-and-play learning track: stand up the spine in week one, add a plugin per week, end up with a `redbox` TUI where every attack class is a loadable plugin and every run can be tagged against a compliance framework.
