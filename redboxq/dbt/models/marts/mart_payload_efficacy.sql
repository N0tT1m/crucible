-- mart_payload_efficacy — payload × week, % complied across all models.
-- SCAFFOLD ONLY. Drift detector — a payload that "stops working" against
-- a model that previously complied is the headline find.

{{ config(materialized='table', order_by=['week','payload_id']) }}

SELECT
    a.week,
    a.payload_id,
    count()                                     AS attempts,
    countIf(a.verdict='complied')               AS complied,
    complied / nullIf(attempts, 0)              AS compliance_rate,
    argMax(a.model, a.verdict='complied')       AS sample_complying_model
FROM {{ ref('fact_attack') }} a
GROUP BY a.week, a.payload_id
