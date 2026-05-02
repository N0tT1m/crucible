-- dim_date — calendar dimension. ~5 years of dates from 2025-01-01.

{{ config(materialized='table') }}

WITH series AS (
    SELECT toDate('2025-01-01') + number AS day
    FROM numbers(365 * 5)
)
SELECT
    day,
    toYear(day)                AS year,
    toQuarter(day)             AS quarter,
    toMonth(day)               AS month,
    toWeek(day)                AS week_of_year,
    toDayOfWeek(day)           AS dow,
    toDayOfMonth(day)          AS dom,
    formatDateTime(day, '%Y-%m-%d') AS day_iso,
    day = today()              AS is_today,
    toStartOfWeek(day)         AS week_start,
    toStartOfMonth(day)        AS month_start
FROM series
