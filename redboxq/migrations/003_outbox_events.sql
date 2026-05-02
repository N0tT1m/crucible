-- raw.outbox_events — one row per redlab-agent send_email tool call.
-- Source for canary-leak detection. Written by the agent (or by the
-- redboxq /ingest/outbox endpoint).

CREATE TABLE IF NOT EXISTS raw.outbox_events (
    ts          DateTime64(3, 'UTC'),
    session_id  String,
    model       LowCardinality(String),
    to_addr     String,
    subject     String,
    body        String           CODEC(ZSTD(3)),
    trace_id    String,
    inserted_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, session_id)
TTL ts + INTERVAL 365 DAY;
