-- Every judge_name on a real attack (non-empty, non-error) must exist
-- in dim_judge. Lets us catch typos / new judges that weren't seeded.
-- Empty judge_name is allowed (the --judge none path).

SELECT DISTINCT a.judge_name
FROM {{ ref('fact_attack') }} a
LEFT JOIN {{ ref('dim_judge') }} j USING (judge_name)
WHERE a.judge_name != ''
  AND a.judge_name != 'error'
  AND j.judge_name IS NULL
