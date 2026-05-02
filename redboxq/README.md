# redboxq

Analytics for crucible red-team runs. Single-project port of the
lupes-anal-ytics + smoothies-morning-milking pattern: one ClickHouse,
one Go dashboard, one dbt project. No multi-producer warehouse, no
empire-map, no Dagster.

## Ports

Host-published ports are offset from the empire defaults so redboxq
runs alongside `mommy-smoothies-morning-milking` and `lupes-anal-ytics`
without collision. Inside the docker network everything still uses the
canonical ports.

| Service                | Host port | In-network |
|------------------------|-----------|------------|
| redboxq dashboard      | `:7000`   | `:7000`    |
| ClickHouse HTTP        | `:8124`   | `:8123`    |
| ClickHouse native      | `:9001`   | `:9000`    |
| OTel collector (gRPC)  | `:4327`   | `:4317`    |
| OTel collector (HTTP)  | `:4328`   | `:4318`    |

Producers (redbox CLI, redlab-agent) running on the host use the host
ports — `REDBOXQ_CH_URL=http://localhost:8124` and
`OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4327`.

## Stack

```
producer (redbox CLI + redlab-agent on host)
        │
        ├── OTel SDK ──► localhost:4327 ──► OTel Collector ──► ClickHouse otel_*
        │
        └── localhost:8124 (HTTP insert) ───────────────────► ClickHouse raw.attacks
                                                                 │
                                                              dbt build
                                                                 │
                                                                 ▼
                                                        ClickHouse mart.*
                                                                 │
                                            redboxq (Go + chi + HTMX) :7000
                                                                 │
                                                  Discord / Telegram alerts
```

## Layout

```
redboxq/
  cmd/redboxq/         entrypoint
  internal/
    config/            env-based config loader
    server/            chi router + middleware
    ch/                ClickHouse query layer
    handlers/          per-page handlers (front, attacks, payloads, …)
    alerts/            rule engine + Discord/Telegram fan-out
    ingest/            optional POST /ingest/* fallback
    telemetry/         OTel SDK init for redboxq itself
  web/
    templates/         Go html/template (base + per-page)
    static/            forge.css, forge.js, grain.svg (DONE — see preview.html)
    preview.html       static design preview, no backend
  deploy/
    docker-compose.yml ClickHouse + collector + redboxq
    Dockerfile         multi-stage Go build
    otel-collector.yaml collector pipelines
    .env.example       env vars
  migrations/          ClickHouse DDL applied on first boot
  dbt/                 dbt-clickhouse project
    dbt_project.yml
    profiles.yml.example
    models/
      sources.yml
      staging/         stg_* views
      marts/           dim_* + fact_* + mart_*
    seeds/             dim_payload.csv (regen from vault), dim_model.csv, dim_judge.csv
  scripts/
    seed_dim_payload.py  vault YAML → seeds/dim_payload.csv
    init_clickhouse.sh   apply migrations/*.sql in order
  Makefile
```

## What's built

| Area | State |
|---|---|
| ClickHouse DDL (migrations 001–007) | real, runs on first boot |
| `docker-compose.yml` + `Dockerfile` + collector config | real |
| dbt: project + sources + 3 staging + 11 marts + 4 seeds | real SQL bodies |
| `seed_dim_payload.py` | reads vault YAMLs, writes seed CSV (verified) |
| `redbox/core/sinks.py` + `ch_sink.py` + `telemetry.py` | real |
| `homelab/agent/telemetry.py` + agent OTel + outbox→CH writes | real |
| `BenchRunner` with sinks + sampling params + cost-at-attack + OTel spans | real |
| Go entrypoint, config, server, ch client, handlers, ingest, alerts | real |
| 14 web templates (Go html/template) | render against handler data structs |

## What's still thin

- `attack_detail` / `payload_detail` / `model_detail` render only the page header — the body's a TODO until the link format settles.
- ECharts/sparkline canvases referenced in `forge.js` aren't wired into any page yet.
- No labeling UI form yet — you can `POST /attacks/{id}/label` with curl, but nothing in the dashboard calls it.
- Alert engine has 4 rules (canary, error rate, refusal drift, silent producer) and persists to `mart.alerts`, but there's no alerts page in the UI.

## Conventions

- All Go code under module `github.com/crucible/redboxq` (rename if you fork).
- All env vars `REDBOXQ_*`.
- All ClickHouse tables in three databases: `raw`, `stg`, `mart`. Collector writes
  `otel_traces` / `otel_logs` / `otel_metrics` directly into `raw`.
- All Go templates extend `base.html`. Pages map 1:1 to handlers in `internal/handlers/handlers.go`.

## Run it

```bash
# from redboxq/
docker compose -f deploy/docker-compose.yml up -d --build

# host-side dbt (if running outside the dbt container):
cd dbt
cp profiles.yml.example profiles.yml
python3 -m venv .venv && source .venv/bin/activate
pip install dbt-clickhouse
python3 ../scripts/seed_dim_payload.py \
  --vault ../../redbox/payloads/vault \
  --out  seeds/dim_payload_seed.csv
dbt build           # talks to localhost:9001 by default

# fire a bench against the new warehouse:
cd ../..
REDBOXQ_CH_URL=http://localhost:8124 \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4327 \
  redbox bench -m claude-haiku --judge regex --as you@local

# open http://localhost:7000
```
