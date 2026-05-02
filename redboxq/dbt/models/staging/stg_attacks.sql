-- stg_attacks — type-safe, normalized view over raw.attacks.

SELECT
    ts,
    toDate(ts)                                           AS day,
    toStartOfWeek(ts)                                    AS week,
    run_id,
    payload_id,
    target_name,
    model,

    rendered_prompt,
    system_prompt,
    template_hash,
    parent_payload_id,

    coalesce(nullIf(verdict, ''), 'unknown')             AS verdict,
    confidence,
    judge_name,
    judge_reason,

    latency_ms,
    input_tokens,
    output_tokens,
    finish_reason,
    model_fingerprint,

    temperature,
    top_p,
    top_k,
    seed,

    error,
    error_kind,
    base_url,
    caller_user,
    usd_at_attack,

    trace_id
FROM {{ source('raw', 'attacks') }}
WHERE run_id != ''
