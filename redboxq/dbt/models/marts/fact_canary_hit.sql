-- fact_canary_hit — one row per canary token leak detected anywhere.
-- SCAFFOLD ONLY. Read by the canary_hit alert rule.

{{ config(materialized='table', partition_by='toYYYYMM(ts)') }}

SELECT ts, trace_id, service, canary_token, log_body
FROM {{ ref('stg_canary_hits') }}
