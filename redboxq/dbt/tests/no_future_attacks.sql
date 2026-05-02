-- A passing dbt test returns zero rows.
-- This catches clock-skew producers that record attacks dated in the
-- future — usually a sign of a misconfigured timezone on a worker.

SELECT
    run_id,
    payload_id,
    target_name,
    ts
FROM {{ ref('fact_attack') }}
WHERE ts > now() + INTERVAL 1 MINUTE
