-- mart_cost_per_run — token spend per (run, model) in USD.
-- SCAFFOLD ONLY. Pricing seed lives at seeds/dim_model_pricing.csv
-- (TODO: add seed) — keyed by (model_name, effective_from).

{{ config(materialized='table') }}

SELECT
    a.run_id,
    a.model,
    count()                                          AS attacks,
    sum(a.input_tokens)                              AS input_tokens,
    sum(a.output_tokens)                             AS output_tokens,
    sum(a.input_tokens  * p.usd_per_input_token)     AS input_cost_usd,
    sum(a.output_tokens * p.usd_per_output_token)    AS output_cost_usd,
    input_cost_usd + output_cost_usd                 AS total_cost_usd
FROM {{ ref('fact_attack') }} a
LEFT JOIN {{ ref('dim_model_pricing') }} p
  ON p.model_name = a.model AND p.effective_from <= a.day
GROUP BY a.run_id, a.model
