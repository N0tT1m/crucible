-- raw.run_configs — one row per redbox bench run, capturing the
-- exact config so attacks can be replayed deterministically.

CREATE TABLE IF NOT EXISTS raw.run_configs (
    run_id          String,
    started_at      DateTime64(3, 'UTC'),
    finished_at     Nullable(DateTime64(3, 'UTC')),
    config_json     String           CODEC(ZSTD(3)),
    redbox_version  LowCardinality(String) DEFAULT '',
    git_sha         LowCardinality(String) DEFAULT '',
    caller_user     LowCardinality(String) DEFAULT '',
    host            LowCardinality(String) DEFAULT '',
    inserted_at     DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(inserted_at)
PARTITION BY toYYYYMM(started_at)
ORDER BY run_id;
