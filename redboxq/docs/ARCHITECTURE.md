# Architecture

How redboxq fits together and why.

## One-line summary

Producers (the redbox CLI and the redlab agent) emit structured attack
rows + OTel spans into ClickHouse. dbt rolls them into marts. A Go
service reads the marts and renders a newspaper-style dashboard.

## Data flow

```
                                              vault YAML
                                                 │
                                            seed_dim_payload.py
                                                 ▼
                                       dim_payload_seed.csv
                                                 │
┌──────────────┐                                 │
│ redbox CLI   │ ── Result ──► fanout(sinks) ──┐ │
│ (host or CI) │   per attack                  │ │
└──────┬───────┘                               ▼ ▼
       │ OTel spans                  SqliteSink (file)
       │                             ClickHouseSink (httpx → JSONEachRow)
       ▼                                       │
  collector :4327 ──► raw.otel_traces          │
                  └─► raw.otel_logs            │
┌──────────────┐                               │
│ redlab agent │ ── /chat tool spans ──► same collector
│ (homelab)    │ ── outbox writes ─────► raw.outbox_events (httpx)
└──────────────┘                                │
                                                ▼
                                      ClickHouse (24.3)
                                       │      │      │
                                      raw    stg    mart  ── dbt build ──┐
                                                                          │
                                       redboxq Go service ◄───────────────┘
                                       ↑   chi + html/template
                                       │   :7000
                                       │
                                       └── alert engine (4 rules, every 30s)
                                                 │
                                       Discord / Telegram webhooks
```

## Components

### Producers — `redbox/`

The CLI is the entry point for any attack. Per `redbox bench`:

1. `PayloadLoader` reads YAMLs from `redbox/payloads/vault/`.
2. `OpenAICompatTarget` (or any other `TargetClient` impl) holds the
   model name + base URL.
3. `BenchRunner` runs payloads × targets in parallel under a semaphore.
4. Each attack produces a `Result`, fanned out to every configured
   `ResultsSink`.
5. OTel spans (`redbox.bench` parent, `redbox.attack` per row) carry
   the canonical attributes the warehouse joins on.

### Producers — `homelab/agent/`

A FastAPI service. Each `/chat` request runs an Ollama tool-calling
loop. We instrument:

- `agent.chat` (root span via FastAPI auto-instrumentation).
- `agent.llm.call` (one per round-trip).
- `tool.<name>` (one per tool invocation).

`send_email` writes a row to `raw.outbox_events` so canary detection
runs against actual exfil attempts, not just text searches.

### Storage — ClickHouse

Three databases:

- `raw` — producer-written, immutable. Source of truth.
- `stg` — dbt-managed views. Type coercion + filtering only.
- `mart` — dbt-managed tables. Dims + facts + derived marts.

Plus the OTel exporter creates `raw.otel_traces`/`otel_logs`/`otel_metrics`
on demand.

### Transformation — dbt

Project at `redboxq/dbt/`. Daily-ish cadence (currently manual). Every
mart is a `materialized=table`; staging is `materialized=view`.

The seed pipeline:
- `dim_payload_seed.csv` is regenerated from the live vault by
  `scripts/seed_dim_payload.py` so payload metadata is provenance-true.
- `dim_model_seed.csv` and `dim_model_pricing.csv` are hand-curated to
  track `homelab/litellm.yaml`.
- `dim_judge_seed.csv` lists every judge in `redbox/judges/`.

### Service — Go (chi + html/template + HTMX)

`redboxq/cmd/redboxq/`. Reads ClickHouse on every request — no caching
yet. Each page is a handler + template:

| Page | Handler | Template | Reads |
|---|---|---|---|
| `/` | Home | home.html | FrontStats, TargetCards, RecentAttacks, RecentCanaries |
| `/runs` | RunsList | runs.html | Runs |
| `/attacks` | AttacksList | attacks.html | RecentAttacks |
| `/payloads` | PayloadsList | payloads.html | Payloads |
| `/models` | ModelsList | models.html | TargetCards |
| `/judges` | Judges | judges.html | JudgeAgreement |
| `/lineage` | Lineage | lineage.html | Tables |
| `/workbench` | Workbench / WorkbenchRun | workbench.html | Tables / RunQuery |
| `/logs` | Logs / LogsStream | logs.html | RecentLogs / SSE |
| `/reference` | Reference | reference.html | static |

### Alerts — Go ticker

`internal/alerts/`. Every 30s walks `DefaultRules()`, evaluates each,
fans out fires to Discord + Telegram if URL/token configured, and
persists every fire to `mart.alerts`.

Rules:
- `canary_hit` — anything in `mart.fact_canary_hit` since last fire.
- `error_rate` — error fraction over a 10-min window per model.
- `refusal_drift` — 14-day mean refusal rate, today's z-score.
- `silent_producer` — `max(ts) FROM raw.attacks` older than threshold.

### Ingest — Go HTTP

`internal/ingest/`. Endpoints for producers that can't write to CH
directly, plus the `dim_label` writer:

- `POST /ingest/attack` — same shape as `raw.attacks`.
- `POST /ingest/outbox` — same shape as `raw.outbox_events`.
- `POST /attacks/{id}/label` — writes a row to `mart.dim_label`,
  the human ground-truth for `mart_judge_accuracy`.

## Conventions

### Module / namespace

- All Go code under module `github.com/crucible/redboxq`.
- All env vars `REDBOXQ_*` (with the standard `OTEL_*` for OTel).
- All ClickHouse tables under `raw`, `stg`, `mart`.
- All dbt seeds suffixed `_seed.csv` so the staging/mart layer can
  wrap them under the canonical name.

### Reproducibility — what's frozen per attack

A row in `raw.attacks` is enough to replay an attack:

- `rendered_prompt` + `system_prompt` — the literal text that hit the
  model, post-template-rendering.
- `template_hash` — 16-hex `blake2b` of `rendered_prompt`. Lets us
  detect "same payload_id, different actual content" after vault edits.
- `temperature`, `top_p`, `top_k`, `seed` — sampling params.
- `model_fingerprint` — provider's exact model id (e.g.
  `claude-haiku-4-5-20251001`). Detects silent rotations.
- `usd_at_attack` — cost frozen at insert time so historical numbers
  don't drift when pricing changes.

### Multi-sink fan-out

`BenchRunner.sinks` is a list. The default is `[SqliteSink]`. When
`REDBOXQ_CH_URL` is set, `ClickHouseSink` is added. Every sink writes
its own copy of every Result; per-sink failures are logged and don't
block the others (`fanout()` in `redbox/core/sinks.py`).

### OTel SDKs are opt-in

`redbox.core.telemetry.init_otel` and the agent's equivalent return
False (no-op) when `OTEL_EXPORTER_OTLP_ENDPOINT` is unset. Lab users
without a collector can run offline; production users wire it up.

### Empty-state dashboard

The Go service is defensive: every handler swallows
"table doesn't exist" (`ch.MissingTable(err)`) and renders the page's
empty state instead of a 500. The home page detects the
"before-first-dbt-build" state via `ch.Readiness()` and replaces the
article body with the recipe to populate the warehouse.

## Why this shape

A few invariants that drove the design:

- **Producers stay simple.** They write the rows and ship spans.
  Every analytical question is a SQL query against `mart.*` — none of
  the producers need to know what reports look like.
- **One DB per environment, three schemas.** Borrowed from the
  smoothies pattern. Lets the empire's existing ClickHouse instance
  host redboxq alongside other producers without table-name collision.
- **dbt is the only thing that writes to `mart`.** The Go service is
  read-only except for `mart.alerts` (engine writes) and `mart.dim_label`
  (UI writes). This keeps the mart layer reproducible from `dbt build`.
- **Ports offset from empire defaults.** `:8124/:9001/:4327/:4328` so
  redboxq runs alongside `mommy-smoothies-morning-milking` and
  `lupes-anal-ytics` without `port is already allocated`.
- **No caching layer.** Every request hits ClickHouse. At lab scale
  this is fine; at production scale you'd cache `FrontStats` and
  `TargetCards`. We deferred until we had data.
