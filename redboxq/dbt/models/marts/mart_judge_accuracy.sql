-- mart_judge_accuracy — precision/recall of each judge against human labels.
-- Reads mart.dim_label (a CH source, not a dbt model — declared in sources.yml).
-- Empty until labels are recorded; that's expected.

{{ config(materialized='table') }}

WITH labeled AS (
    SELECT
        l.run_id, l.payload_id, l.target_name, l.ts,
        l.label                            AS truth,
        l.refusal_kind, l.severity, l.notes
    FROM {{ source('mart_src', 'dim_label') }} l
    WHERE l.superseded_at IS NULL
),
joined AS (
    SELECT
        f.judge_name,
        f.verdict     AS predicted,
        l.truth,
        f.confidence
    FROM {{ ref('fact_attack') }} f
    JOIN labeled l
      ON  f.run_id      = l.run_id
      AND f.payload_id  = l.payload_id
      AND f.target_name = l.target_name
      AND f.ts          = l.ts
)
SELECT
    judge_name,
    truth,
    predicted,
    count() AS n,
    avg(confidence) AS avg_confidence,
    countIf(truth = predicted) / nullIf(count(), 0) AS accuracy
FROM joined
GROUP BY judge_name, truth, predicted
ORDER BY judge_name, truth, predicted
