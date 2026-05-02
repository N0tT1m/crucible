-- dim_model — every target known to redbox.
-- Loaded from seeds/dim_model_seed.csv, hand-curated to match
-- homelab/litellm.yaml.

{{ config(materialized='table') }}

SELECT
    model_name,
    provider,
    family,
    parameter_class,
    local,
    toDate(added_on) AS added_on
FROM {{ ref('dim_model_seed') }}
