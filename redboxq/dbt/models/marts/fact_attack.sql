-- fact_attack — one row per attack, with FKs into dim_payload + dim_model + dim_judge.
-- Headline mart fed by every refusal/efficacy/cost downstream.

{{ config(
    materialized='table',
    order_by=['ts','run_id','target_name','payload_id'],
    partition_by='toYYYYMM(ts)'
) }}

SELECT
    a.ts,
    a.day,
    a.week,
    a.run_id,
    a.payload_id,
    a.target_name,
    a.model,

    a.rendered_prompt,
    a.system_prompt,
    a.template_hash,
    a.parent_payload_id,

    a.verdict,
    a.confidence,
    a.judge_name,
    a.judge_reason,

    a.latency_ms,
    a.input_tokens,
    a.output_tokens,
    a.finish_reason,
    a.model_fingerprint,

    a.temperature,
    a.top_p,
    a.top_k,
    a.seed,

    a.error,
    a.error_kind,
    a.base_url,
    a.caller_user,
    a.usd_at_attack,

    a.trace_id
FROM {{ ref('stg_attacks') }} a
