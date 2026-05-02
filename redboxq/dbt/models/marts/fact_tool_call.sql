-- fact_tool_call — one row per redlab-agent tool invocation.
-- SCAFFOLD ONLY. Built from stg_agent_tool_calls.

{{ config(materialized='table', partition_by='toYYYYMM(ts)') }}

SELECT
    ts, trace_id, span_id, parent_span_id,
    tool_name, session_id, args_json, output_preview,
    duration_ms, status
FROM {{ ref('stg_agent_tool_calls') }}
