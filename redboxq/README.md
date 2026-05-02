# redboxq

Analytics for crucible red-team runs. Single-project port of the
lupes-anal-ytics + smoothies-morning-milking pattern: one ClickHouse,
one Go dashboard, one dbt project. No multi-producer warehouse, no
empire-map, no Dagster.

**Status:** scaffold only. Nothing here runs yet — every file is a
stub. See "What's stubbed" below.

## Stack

```
producer (redbox CLI + redlab-agent)
        │
        ├── OTel SDK ──► OTLP :4317 ──► OTel Collector ──► ClickHouse otel_*
        │
        └── direct insert ─────────────────────────────► ClickHouse raw.attacks
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

## What's stubbed

Nothing in here is wired up. The shape is correct, the contents aren't.

| Area | State |
|---|---|
| ClickHouse DDL | real schema, runnable |
| docker-compose.yml | real services, runnable |
| dbt_project.yml + profiles + sources.yml | real config, runnable |
| dbt model SQL bodies | TODO comment only |
| Go entrypoint + handlers | package decl + signatures, no logic |
| OTel init in redbox + agent | function signature, no logic |
| ResultsSink protocol in redbox | protocol declared, ClickHouseSink raises NotImplementedError |
| Web templates (Go html/template) | base + minimal page templates referencing forge.css |
| Alert engine | rule type defs, no evaluator |
| Vault → seed CSV script | argparse skeleton, no parsing |

## Conventions

- All Go code under module `github.com/crucible/redboxq` (placeholder; rename when repo settles).
- All env vars `REDBOXQ_*`.
- All ClickHouse tables in three databases: `raw`, `stg`, `mart`. Collector writes
  `otel_traces` / `otel_logs` / `otel_metrics` directly into `raw`.
- All Go templates extend `base.html`. Pages map 1:1 to `internal/handlers/*.go`.

## Next steps (in order)

1. `docker compose -f deploy/docker-compose.yml up -d clickhouse` — verify the DDL applies.
2. Implement `ClickHouseSink` in `redbox/core/ch_sink.py`, dual-write from `BenchRunner`.
3. Run `redbox bench` and confirm rows land in `raw.attacks`.
4. Implement first dbt model (`stg_attacks`) and verify with `dbt run --select stg_attacks`.
5. Implement `cmd/redboxq/main.go` + `internal/handlers/home.go` to render `home.html` against real query results.
6. Wire OTel SDK in producer side and stand up the collector.
7. Alert engine + first two rules.
