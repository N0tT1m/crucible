-- Refusal rate must be a valid probability ∈ [0, 1].
-- Catches: a NULL-divide-by-zero leak in the mart math, or a bad cast.

SELECT
    day,
    model,
    category,
    refusal_rate,
    compliance_rate
FROM {{ ref('mart_refusal_rate') }}
WHERE refusal_rate < 0 OR refusal_rate > 1
   OR compliance_rate < 0 OR compliance_rate > 1
