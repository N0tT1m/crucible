-- mart.dim_label — human ground-truth labels for attacks.
-- Powers judge accuracy metrics: precision/recall of regex + LLM judges
-- against a labeled subset. Writers are the redboxq UI's per-attack
-- "label this" form (POST /attacks/{id}/label) and the import-CSV path.

CREATE TABLE IF NOT EXISTS mart.dim_label (
    run_id        String,
    payload_id    LowCardinality(String),
    target_name   LowCardinality(String),
    ts            DateTime64(3, 'UTC'),                  -- the attack's ts (join key)

    label         LowCardinality(String),                -- refused|complied|partial|unknown
    refusal_kind  LowCardinality(String) DEFAULT '',     -- safety|capability|format|hedge|''
    severity      LowCardinality(String) DEFAULT '',     -- low|med|high|''   (for compliance: harm severity)
    notes         String,

    labeled_by    LowCardinality(String),
    labeled_at    DateTime DEFAULT now(),
    superseded_at Nullable(DateTime)                     -- non-null = retracted/replaced
)
ENGINE = ReplacingMergeTree(labeled_at)
PARTITION BY toYYYYMM(ts)
ORDER BY (run_id, payload_id, target_name, ts);
