-- mart_judge_agreement — regex-vs-LLM verdict per attack, joined.
-- SCAFFOLD ONLY. Surfaces the regex judge's false-positive rate so we
-- can tighten patterns (e.g. the known "As an AI assistant" issue).

{{ config(materialized='table') }}

WITH regex_v AS (
    SELECT run_id, payload_id, target_name, verdict AS regex_verdict
    FROM {{ ref('fact_attack') }} WHERE judge_name = 'regex-refusal'
),
llm_v AS (
    SELECT run_id, payload_id, target_name, verdict AS llm_verdict, confidence AS llm_conf
    FROM {{ ref('fact_attack') }} WHERE judge_name = 'llm-refusal'
)
SELECT
    r.run_id, r.payload_id, r.target_name,
    r.regex_verdict, l.llm_verdict, l.llm_conf,
    r.regex_verdict = l.llm_verdict  AS agreed
FROM regex_v r
JOIN llm_v l USING (run_id, payload_id, target_name)
