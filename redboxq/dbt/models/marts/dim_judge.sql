-- dim_judge — every judge implementation in redbox/judges.

{{ config(materialized='table') }}

SELECT
    judge_name,
    kind,
    base_model,
    description
FROM {{ ref('dim_judge_seed') }}
