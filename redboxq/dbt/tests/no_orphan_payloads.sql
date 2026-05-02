-- Every payload_id referenced in fact_attack must exist in dim_payload.
-- Catches: a producer ran with a payload that was never seeded into the
-- vault dim, which means the dashboard will show the id but no metadata.

SELECT DISTINCT a.payload_id
FROM {{ ref('fact_attack') }} a
LEFT JOIN {{ ref('dim_payload') }} p USING (payload_id)
WHERE p.payload_id = ''
   OR p.payload_id IS NULL
