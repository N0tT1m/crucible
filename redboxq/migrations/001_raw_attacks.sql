-- raw.attacks — one row per attack from redbox.runner.
-- Producer-written; immutable after insert. Marts read from here via dbt.

CREATE DATABASE IF NOT EXISTS raw;
CREATE DATABASE IF NOT EXISTS stg;
CREATE DATABASE IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS raw.attacks (
    ts                  DateTime64(3, 'UTC'),
    run_id              String,
    payload_id          LowCardinality(String),
    target_name         LowCardinality(String),
    model               LowCardinality(String),

    -- prompt provenance
    rendered_prompt     String           CODEC(ZSTD(3)),
    system_prompt       String           CODEC(ZSTD(3)),
    template_hash       FixedString(16),                 -- xxhash of rendered_prompt
    parent_payload_id   LowCardinality(String) DEFAULT '', -- non-empty for mutator-derived

    -- response + telemetry
    response            String           CODEC(ZSTD(3)),
    latency_ms          UInt32,
    input_tokens        UInt32,
    output_tokens       UInt32,
    finish_reason       LowCardinality(String) DEFAULT '', -- end_turn|max_tokens|stop_sequence|content_filter|error
    model_fingerprint   LowCardinality(String) DEFAULT '', -- e.g. claude-haiku-4-5-20251001

    -- sampling params (frozen at attack time so runs are reproducible)
    temperature         Nullable(Float32),
    top_p               Nullable(Float32),
    top_k              Nullable(Int32),
    seed                Nullable(Int64),

    -- judge
    verdict             LowCardinality(String),         -- refused|complied|partial|unknown|''
    confidence          Nullable(Float32),
    judge_name          LowCardinality(String),
    judge_reason        String,

    -- ops
    error               String,
    error_kind          LowCardinality(String) DEFAULT '', -- timeout|rate_limit|auth|bad_request|server|other
    base_url            LowCardinality(String) DEFAULT '',
    caller_user         LowCardinality(String) DEFAULT '',
    usd_at_attack       Nullable(Float64),                 -- frozen cost; null if pricing unknown

    -- joins
    trace_id            String,                            -- joins to raw.otel_traces
    inserted_at         DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, run_id, target_name, payload_id)
TTL ts + INTERVAL 365 DAY;

-- Idempotent ALTERs: applied if the table already existed without these columns.
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS rendered_prompt   String           CODEC(ZSTD(3));
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS system_prompt     String           CODEC(ZSTD(3));
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS template_hash     FixedString(16);
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS parent_payload_id LowCardinality(String) DEFAULT '';
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS finish_reason     LowCardinality(String) DEFAULT '';
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS model_fingerprint LowCardinality(String) DEFAULT '';
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS temperature       Nullable(Float32);
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS top_p             Nullable(Float32);
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS top_k             Nullable(Int32);
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS seed              Nullable(Int64);
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS error_kind        LowCardinality(String) DEFAULT '';
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS base_url          LowCardinality(String) DEFAULT '';
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS caller_user       LowCardinality(String) DEFAULT '';
ALTER TABLE raw.attacks ADD COLUMN IF NOT EXISTS usd_at_attack     Nullable(Float64);
