-- mart.alerts — one row per alert fire/resolve transition.
-- Written by the redboxq alert engine (internal/alerts).

CREATE TABLE IF NOT EXISTS mart.alerts (
    ts          DateTime64(3, 'UTC'),
    rule_name   LowCardinality(String),         -- canary_hit|error_rate|refusal_drift|silent_producer
    state       LowCardinality(String),         -- fired|resolved
    severity    LowCardinality(String),         -- info|warn|error|critical
    summary     String,
    payload     String,                          -- arbitrary JSON the rule wants to remember
    target_name LowCardinality(String),         -- optional: which model the alert is about
    payload_id  LowCardinality(String),         -- optional: which payload
    fired_at    DateTime64(3, 'UTC'),
    resolved_at Nullable(DateTime64(3, 'UTC'))
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, rule_name)
TTL toDateTime(ts) + INTERVAL 365 DAY;
