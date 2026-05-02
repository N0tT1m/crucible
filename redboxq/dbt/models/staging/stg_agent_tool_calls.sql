-- stg_agent_tool_calls — agent tool invocations parsed out of otel_traces.
-- SCAFFOLD ONLY.
--
-- Each redlab-agent /chat call emits a span tree:
--   chat (parent) → llm.call → tool.<name> (child, one per tool invocation)
-- This view extracts the tool.* spans for analysis.

SELECT
    Timestamp                                AS ts,
    TraceId                                  AS trace_id,
    SpanId                                   AS span_id,
    ParentSpanId                             AS parent_span_id,
    replaceOne(SpanName, 'tool.', '')        AS tool_name,
    SpanAttributes['session_id']             AS session_id,
    SpanAttributes['args']                   AS args_json,
    SpanAttributes['output_preview']         AS output_preview,
    Duration / 1e6                           AS duration_ms,
    StatusCode                               AS status
FROM {{ source('raw', 'otel_traces') }}
WHERE ServiceName = 'redlab-agent'
  AND SpanName LIKE 'tool.%'
