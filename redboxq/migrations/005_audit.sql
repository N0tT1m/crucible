-- mart.audit — one row per redboxq HTTP request, written by chi
-- middleware. Powers the audit page.

CREATE TABLE IF NOT EXISTS mart.audit (
    ts          DateTime64(3, 'UTC'),
    method      LowCardinality(String),
    route       LowCardinality(String),         -- chi pattern, not raw URL
    status      UInt16,
    duration_ms UInt32,
    bytes_in    UInt32,
    bytes_out   UInt32,
    user        LowCardinality(String),         -- always '' until auth lands
    ip          String,
    trace_id    String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, route)
TTL toDateTime(ts) + INTERVAL 90 DAY;
