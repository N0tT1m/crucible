-- mart_cost_per_run — token spend per (run, model).
--
-- Two cost columns:
--   total_cost_usd_frozen   — sum of usd_at_attack frozen at insert time
--                             (truthful for historical runs even after
--                             pricing changes).
--   total_cost_usd_current  — what the same tokens would cost at the
--                             *latest* known pricing for the model.
--
-- ClickHouse 24's analyzer rejects inequality predicates in JOIN ON
-- clauses, so we collapse dim_model_pricing to one "current" row per
-- model via argMax(effective_from), then join on equality only.

{{ config(materialized='table') }}

WITH price AS (
    SELECT
        model_name,
        argMax(usd_per_input_token,  effective_from) AS in_rate,
        argMax(usd_per_output_token, effective_from) AS out_rate
    FROM {{ ref('dim_model_pricing') }}
    GROUP BY model_name
)
SELECT
    a.run_id,
    a.model,
    count()                                                    AS attacks,
    sum(a.input_tokens)                                        AS input_tokens,
    sum(a.output_tokens)                                       AS output_tokens,
    sum(coalesce(a.usd_at_attack, 0.0))                        AS total_cost_usd_frozen,
    sum(a.input_tokens  * coalesce(p.in_rate, 0.0))            AS input_cost_usd_current,
    sum(a.output_tokens * coalesce(p.out_rate, 0.0))           AS output_cost_usd_current,
    input_cost_usd_current + output_cost_usd_current           AS total_cost_usd_current
FROM {{ ref('fact_attack') }} a
LEFT JOIN price p ON p.model_name = a.model
GROUP BY a.run_id, a.model
