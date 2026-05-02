# Schema reference

Every table in redboxq's ClickHouse, with the columns that matter and
why they exist. Auto-generated columns (`inserted_at`, `labeled_at`)
are listed but not described unless they have non-obvious behavior.

## Conventions

- Three databases:
  - `raw` — producer-written, immutable. Source of truth.
  - `stg` — dbt views over `raw`. Type-safe, normalized.
  - `mart` — dbt tables. Dims + facts + derived marts.
- Every fact has a `ts DateTime64(3, 'UTC')`. Always UTC.
- Every fact has a `trace_id String` that joins to `raw.otel_traces.TraceId`.
- `LowCardinality(String)` is used for any column with < ~10k distinct values.
- TTLs default to 365 days for facts, 90 days for the audit log.

---

## raw.attacks

One row per attack from `redbox.runner`. Producer-written; never
modified after insert. Marts read from here via `stg_attacks` →
`fact_attack`.

| Column | Type | Why |
|---|---|---|
| `ts` | `DateTime64(3, 'UTC')` | When the attack landed. UTC. |
| `run_id` | `String` | Groups attacks by `redbox bench` invocation. |
| `payload_id` | `LowCardinality(String)` | FK to `dim_payload`. |
| `target_name` | `LowCardinality(String)` | Display name (often == `model`). |
| `model` | `LowCardinality(String)` | Provider/litellm model id. |
| `rendered_prompt` | `String` (ZSTD) | The text that hit the model, post-template. **Reproducibility-critical.** |
| `system_prompt` | `String` (ZSTD) | The system message, if any. |
| `template_hash` | `FixedString(16)` | `blake2b(rendered_prompt)[:16]`. Detects "same payload_id, different actual content" after vault edits. |
| `parent_payload_id` | `LowCardinality(String)` | Set by mutators. Empty for vault originals. |
| `response` | `String` (ZSTD) | Verbatim response text. |
| `latency_ms` | `UInt32` | Wall-clock from request to response. |
| `input_tokens` | `UInt32` | From provider's `usage.prompt_tokens`. |
| `output_tokens` | `UInt32` | From provider's `usage.completion_tokens`. |
| `finish_reason` | `LowCardinality(String)` | Normalized: `end_turn` / `max_tokens` / `content_filter` / `stop_sequence` / `error` / `''`. Distinguishes refusal from cut-off. |
| `model_fingerprint` | `LowCardinality(String)` | Provider's exact dated model id (e.g. `claude-haiku-4-5-20251001`). Detects silent rotations behind a stable name. |
| `temperature` | `Nullable(Float32)` | Sampling param. Frozen for reproducibility. |
| `top_p` | `Nullable(Float32)` | Same. |
| `top_k` | `Nullable(Int32)` | Same. |
| `seed` | `Nullable(Int64)` | Same. |
| `verdict` | `LowCardinality(String)` | `refused` / `complied` / `partial` / `unknown` / `''` (no judge). |
| `confidence` | `Nullable(Float32)` | Judge's confidence in `[0, 1]`. |
| `judge_name` | `LowCardinality(String)` | FK-ish to `dim_judge`. |
| `judge_reason` | `String` | Free-text from the judge. Truncated to 300 chars by `LLMRefusalJudge`. |
| `error` | `String` | Non-empty when the attack failed. The runner sets `verdict=''` in this case. |
| `error_kind` | `LowCardinality(String)` | Bucketed: `timeout` / `rate_limit` / `auth` / `bad_request` / `server` / `other` / `''`. |
| `base_url` | `LowCardinality(String)` | Distinguishes `claude-haiku-via-LiteLLM` from `claude-haiku-direct`. |
| `caller_user` | `LowCardinality(String)` | Audit. From `--as` flag or `$USER`. |
| `usd_at_attack` | `Nullable(Float64)` | Cost frozen at insert time, computed from `dim_model_pricing`. Prevents historical drift on price changes. |
| `trace_id` | `String` | Joins to `raw.otel_traces.TraceId`. |
| `inserted_at` | `DateTime DEFAULT now()` | Server clock at insert. |

**Engine:** `MergeTree`. Partition by `toYYYYMM(ts)`. Ordered by
`(ts, run_id, target_name, payload_id)`. TTL 365 days.

---

## raw.outbox_events

One row per `send_email` tool call from the redlab agent. Source for
canary-leak detection.

| Column | Type | Why |
|---|---|---|
| `ts` | `DateTime64(3, 'UTC')` | When the agent invoked the tool. |
| `session_id` | `String` | Agent session — not the redbox `run_id`. |
| `model` | `LowCardinality(String)` | The agent's underlying LLM. |
| `to_addr` | `String` | Recipient. Truncated to 512 chars. |
| `subject` | `String` | Truncated to 512 chars. |
| `body` | `String` (ZSTD) | Truncated to 8000 chars. |
| `trace_id` | `String` | Joins to the agent's chat span tree. |

`stg_canary_hits` searches `body`/`subject`/`to_addr` for known canary
tokens, alongside scanning `raw.otel_logs.Body`.

---

## raw.run_configs

One row per `redbox bench` invocation. Captures the exact config so
attacks can be replayed deterministically.

| Column | Type | Why |
|---|---|---|
| `run_id` | `String` | Primary key. |
| `started_at` | `DateTime64(3, 'UTC')` | Bench start. Set by `cli.py`. |
| `finished_at` | `Nullable(DateTime64(3, 'UTC'))` | Set by `ClickHouseSink.finish_run` via `ALTER TABLE … UPDATE`. |
| `config_json` | `String` (ZSTD) | Full bench config: models, payload_ids, target_query, judge, sampling params, system_prompt, base_url. |
| `redbox_version` | `LowCardinality(String)` | Set on insert. Empty if unset. |
| `git_sha` | `LowCardinality(String)` | Same. |
| `caller_user` | `LowCardinality(String)` | Mirror of `raw.attacks.caller_user`. |
| `host` | `LowCardinality(String)` | `socket.gethostname()`. |

**Engine:** `ReplacingMergeTree(inserted_at)` — updates over the
`run_id` key collapse to the latest insert.

---

## raw.otel_traces / otel_logs / otel_metrics_*

Created automatically by the OTel ClickHouse exporter the first time a
producer ships a span/log/metric. Schema is managed by the exporter
across collector versions; see `migrations/002_otel_tables.sql` for a
reference shape.

Key joins:
- `raw.otel_traces.TraceId` ↔ `raw.attacks.trace_id`.
- `raw.otel_traces.SpanName` like `tool.%` for agent tool calls.
- `raw.otel_logs.Body` is searched by `stg_canary_hits`.

---

## mart.alerts

One row per alert fire/resolve transition. Written by the redboxq
alert engine.

| Column | Type | Why |
|---|---|---|
| `ts` | `DateTime64(3, 'UTC')` | Fire time. |
| `rule_name` | `LowCardinality(String)` | One of the rule kinds in `internal/alerts/rules.go`. |
| `state` | `LowCardinality(String)` | `fired` / `resolved`. |
| `severity` | `LowCardinality(String)` | `info` / `warn` / `error` / `critical`. |
| `summary` | `String` | Human-readable line. |
| `payload` | `String` | Arbitrary JSON the rule wants to remember. |
| `target_name` | `LowCardinality(String)` | Optional: which model the alert is about. |
| `payload_id` | `LowCardinality(String)` | Optional: which payload. |
| `fired_at` | `DateTime64(3, 'UTC')` | First fire time of this alert instance. |
| `resolved_at` | `Nullable(DateTime64(3, 'UTC'))` | Set on resolve. |

---

## mart.audit

One row per redboxq HTTP request. Currently empty — the chi
middleware that writes it isn't wired (would go in
`internal/server/server.go`).

| Column | Type | Why |
|---|---|---|
| `ts`, `method`, `route`, `status` | obvious | Request basics. |
| `duration_ms` | `UInt32` | Time spent in the handler. |
| `bytes_in`, `bytes_out` | `UInt32` | Body sizes. |
| `user` | `LowCardinality(String)` | Empty until auth lands. |
| `ip` | `String` | Client IP, post-`RealIP` middleware. |
| `trace_id` | `String` | The redboxq request's own trace. |

TTL 90 days.

---

## mart.dim_label

Human ground-truth labels. Read by `mart_judge_accuracy`. Written
either by `POST /attacks/{id}/label` or by a future CSV import.

| Column | Type | Why |
|---|---|---|
| `run_id`, `payload_id`, `target_name`, `ts` | join key | Composite FK to `mart.fact_attack`. |
| `label` | `LowCardinality(String)` | Ground-truth verdict. Same vocab as `verdict`. |
| `refusal_kind` | `LowCardinality(String)` | Optional taxonomy: `safety` / `capability` / `format` / `hedge`. |
| `severity` | `LowCardinality(String)` | Optional harm severity for compliance: `low` / `med` / `high`. |
| `notes` | `String` | Reviewer comment. |
| `labeled_by` | `LowCardinality(String)` | Reviewer name. |
| `labeled_at` | `DateTime DEFAULT now()` | Insert clock. |
| `superseded_at` | `Nullable(DateTime)` | Set when a later label replaces this one. |

**Engine:** `ReplacingMergeTree(labeled_at)` — re-labels over the
same join key keep the latest.

---

## mart dimensions (dbt-managed, materialized=table)

### mart.dim_payload

Loaded from `seeds/dim_payload_seed.csv`, regenerated from
`redbox/payloads/vault/*.yml` by `scripts/seed_dim_payload.py`.

| Column | Type | Description |
|---|---|---|
| `payload_id` | String | PK. Slug from the YAML. |
| `name` | String | Display title. |
| `category` | LowCardinality | Top-level grouping (`jailbreak`, `extraction`, etc.). |
| `references` | String | Semicolon-joined paper/blog citations. |
| `tags` | String | Semicolon-joined tag list. |
| `first_seen` | Date | Date the YAML first landed in git (or file mtime fallback). |

### mart.dim_model

Hand-curated to match `homelab/litellm.yaml`.

| Column | Type | Description |
|---|---|---|
| `model_name` | String | PK. The id used in `redbox bench -m`. |
| `provider` | LowCardinality | `anthropic` / `openai` / `ollama` / `vllm`. |
| `family` | LowCardinality | e.g. `claude-haiku`, `qwen`. |
| `parameter_class` | LowCardinality | `xs`/`s`/`m`/`l`/`xl`. |
| `local` | Boolean | True for local-served models. |
| `added_on` | Date | When this model was added to the bench. |

### mart.dim_judge

Lists every judge implementation in `redbox/judges/`.

| Column | Type | Description |
|---|---|---|
| `judge_name` | String | PK. Same value as `Judge.name` in code. |
| `kind` | LowCardinality | `regex` or `llm`. |
| `base_model` | String | Only for `kind='llm'`. The model the judge calls. |
| `description` | String | Human description. |

### mart.dim_date

Standard date dimension. ~5 years of dates from 2025-01-01.

---

## mart facts and derived marts

### mart.fact_attack

The headline mart. One row per attack with all the columns from
`raw.attacks`, surfaced through `stg_attacks` (which only does type
coercion + an `unknown` default for empty verdict).

### mart.fact_tool_call

One row per redlab-agent tool invocation, parsed from
`stg_agent_tool_calls` (which extracts `tool.%` spans from
`otel_traces`).

| Column | Source | Description |
|---|---|---|
| `ts`, `trace_id`, `span_id`, `parent_span_id` | OTel | Standard. |
| `tool_name` | derived | `SpanName` minus the `tool.` prefix. |
| `session_id` | span attr | The agent's session. |
| `args_json`, `output_preview` | span attrs | Per-call payload. |
| `duration_ms`, `status` | OTel | Span timing + status. |

### mart.fact_canary_hit

One row per canary token leak detected anywhere — in agent log lines,
or in outbox writes. Read by the `canary_hit` alert rule.

### mart.mart_refusal_rate

Daily refusal/comply/partial percentages, one row per
`(day, model, category)`.

| Column | Description |
|---|---|
| `day`, `model`, `category` | Grouping keys. |
| `attempts` | Total attacks in this bucket. |
| `refused`, `complied`, `partial` | Counts. |
| `refusal_rate`, `compliance_rate` | `count / attempts`. |

### mart.mart_payload_efficacy

Payload × week, % complied across all models. Drift detector — a
payload that "stops working" is the headline find.

### mart.mart_judge_agreement

Regex vs LLM verdict per attack. Surfaces the regex judge's
false-positive rate so we can tighten patterns.

### mart.mart_judge_accuracy

Joins `fact_attack` against `dim_label` to compute precision/recall
per judge. Empty until labels are recorded.

### mart.mart_cost_per_run

Token spend per `(run, model)` in USD. Joins `fact_attack` to
`dim_model_pricing`. We also keep `usd_at_attack` directly on each
fact row for "frozen" cost.

### mart.mart_attack_coverage

Has every `(model, payload)` pair been tested in the last N days? The
"fully populated" coverage matrix. Cross-joins `dim_model` × `dim_payload`
and left-joins recent attacks.

---

## Relationships at a glance

```
                  dim_model         dim_payload        dim_judge
                      │                  │                  │
                      └────────────┬─────┴──────────────────┘
                                   │
                              fact_attack
                                   ↑
                            stg_attacks (view)
                                   ↑
                              raw.attacks
                                   │
                            (trace_id)
                                   ↓
                            raw.otel_traces
                                   ↑
                          fact_tool_call ◄── stg_agent_tool_calls

                         raw.otel_logs   ┐
                         raw.outbox_events ┼─► stg_canary_hits ─► fact_canary_hit
```

---

## Where the alert engine reads

- `canary_hit` → `mart.fact_canary_hit`
- `error_rate` → `raw.attacks` (no need for the dbt round trip)
- `refusal_drift` → `mart.mart_refusal_rate`
- `silent_producer` → `raw.attacks`

Persists fires to `mart.alerts`.
