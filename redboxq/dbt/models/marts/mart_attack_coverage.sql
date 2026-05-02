-- mart_attack_coverage — has every (model, payload) pair been tested
-- in the last N days? Drives the "fully populated" coverage matrix.
-- SCAFFOLD ONLY.

{{ config(materialized='table') }}

WITH pairs AS (
    SELECT m.model_name, p.payload_id
    FROM {{ ref('dim_model') }} m
    CROSS JOIN {{ ref('dim_payload') }} p
),
recent AS (
    SELECT model, payload_id, max(ts) AS last_seen, count() AS attempts
    FROM {{ ref('fact_attack') }}
    WHERE ts >= now() - INTERVAL 7 DAY
    GROUP BY model, payload_id
)
SELECT
    pa.model_name, pa.payload_id,
    coalesce(r.last_seen, toDateTime64(0,3,'UTC')) AS last_seen,
    coalesce(r.attempts, 0)                         AS attempts_last_7d,
    r.last_seen IS NOT NULL                         AS covered
FROM pairs pa
LEFT JOIN recent r ON pa.model_name = r.model AND pa.payload_id = r.payload_id
