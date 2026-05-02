-- mart_refusal_rate — daily refusal/comply/partial percentages,
-- one row per (day, model, payload_category).
-- SCAFFOLD ONLY. Headline number for the front page and per-model pages.

{{ config(materialized='table', order_by=['day','model','category']) }}

SELECT
    a.day,
    a.model,
    p.category,
    count()                                     AS attempts,
    countIf(a.verdict='refused')                AS refused,
    countIf(a.verdict='complied')               AS complied,
    countIf(a.verdict='partial')                AS partial,
    refused / nullIf(attempts, 0)               AS refusal_rate,
    complied / nullIf(attempts, 0)              AS compliance_rate
FROM {{ ref('fact_attack') }} a
LEFT JOIN {{ ref('dim_payload') }} p USING (payload_id)
GROUP BY a.day, a.model, p.category
