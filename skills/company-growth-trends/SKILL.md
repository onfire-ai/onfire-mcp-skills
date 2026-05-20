---
name: company-growth-trends
description: Query monthly headcount growth and technology/persona adoption trends for companies using the `query_onfire` tool against SILVER.INSIGHTS.GROWTH_INSIGHT_MONTHLY and SILVER.INSIGHTS.GROWTH_TOTAL_HEADCOUNT_MONTHLY. Use when the user wants to know if a company is hiring or contracting, whether a specific technology is spreading within a company, or how headcount growth compares to tech adoption — phrases like "is Acme growing?", "is EDR adoption growing at these accounts?", "compare CrowdStrike vs total headcount trend at Palo Alto Networks", "which accounts are shrinking?", "is the data engineering team at Snowflake expanding?", or any month-over-month growth question.
---

# company-growth-trends

SQL queries against two sibling Silver tables via `query_onfire`:

| Table | What it measures |
|-------|-----------------|
| `SILVER.INSIGHTS.GROWTH_INSIGHT_MONTHLY` | Month-over-month % change in employees evidencing a specific technology or persona (e.g. CrowdStrike, data engineer) |
| `SILVER.INSIGHTS.GROWTH_TOTAL_HEADCOUNT_MONTHLY` | Month-over-month % change in the company's *total* headcount |

Both tables have the same column shape and are often UNION'd together so
you can see whether a tech is growing faster than the overall company.

## When to use this

- "Is Capital One's CrowdStrike footprint growing?"
- "Compare EDR adoption to total headcount at these 5 accounts"
- "Which of our target accounts are shrinking overall?"
- "Is the data engineering persona expanding at Snowflake?"
- "Show me the last 12 months of growth for insight 'growth-Splunk' at Cisco"
- Any month-over-month growth / trend question for companies

Skip this for:
- Current headcount or employee count → query `GOLD.ENTITIES.COMPANIES.EMPLOYEE_COUNT`
- Employees *using* a technology right now → use `employee-footprint` skill

## Table structure (same for both tables)

| Column | Type | Notes |
|--------|------|-------|
| `company_linkedin_url` | TEXT | Company identifier |
| `company_website` | TEXT | Company website |
| `insight_name` | TEXT | Technology/persona slug. Always prefixed `growth-` (e.g. `growth-EDR`, `growth-data_analyst`, `growth-Splunk`). Ignored on the total-headcount table. |
| `time_period` | DATE | First day of the month (e.g. `2025-01-01`) |
| `str_value` | TEXT | Growth % as a string (e.g. `"12.5"` = +12.5%). NULL on the first data point for a series. |
| `deleted_at` | TEXT/TIMESTAMP | Always filter `IS NULL` |

Key derived value: `TRY_CAST(str_value AS FLOAT)` to get the numeric %.

Tables hold approximately the **last 13 months** of data.

## Required WHERE clause

```sql
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL   -- excludes first-month baseline rows
  AND company_linkedin_url IN (...)
```

## SQL templates

### Total headcount trend for one company
```sql
SELECT
    company_linkedin_url,
    company_website,
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM SILVER.INSIGHTS.GROWTH_TOTAL_HEADCOUNT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/capital-one%'
ORDER BY time_period DESC
LIMIT 13
```

### Tech insight growth for one company
```sql
SELECT
    company_linkedin_url,
    insight_name,
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM SILVER.INSIGHTS.GROWTH_INSIGHT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/capital-one%'
  AND LOWER(insight_name) = 'growth-crowdstrike'
ORDER BY time_period DESC
LIMIT 13
```

### Tech vs total headcount side-by-side (UNION)
```sql
SELECT
    'insights'                          AS source,
    company_linkedin_url,
    insight_name,
    time_period,
    TRY_CAST(str_value AS FLOAT)        AS growth_pct
FROM SILVER.INSIGHTS.GROWTH_INSIGHT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/palo-alto-networks%'
  AND insight_name ILIKE 'growth-EDR%'

UNION ALL

SELECT
    'total'                             AS source,
    company_linkedin_url,
    insight_name,
    time_period,
    TRY_CAST(str_value AS FLOAT)        AS growth_pct
FROM SILVER.INSIGHTS.GROWTH_TOTAL_HEADCOUNT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/palo-alto-networks%'

ORDER BY time_period DESC, source
LIMIT 30
```

### All tech insights for a company (last 3 months)
```sql
SELECT
    insight_name,
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM SILVER.INSIGHTS.GROWTH_INSIGHT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/snowflake%'
  AND time_period >= DATEADD(month, -3, CURRENT_DATE())
ORDER BY insight_name, time_period DESC
LIMIT 200
```

### Multiple companies — which are growing fastest?
```sql
SELECT
    company_linkedin_url,
    company_website,
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM SILVER.INSIGHTS.GROWTH_TOTAL_HEADCOUNT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url IN (
      'https://www.linkedin.com/company/stripe',
      'https://www.linkedin.com/company/twilio',
      'https://www.linkedin.com/company/datadog'
  )
  AND time_period = (
      SELECT MAX(time_period)
      FROM SILVER.INSIGHTS.GROWTH_TOTAL_HEADCOUNT_MONTHLY
      WHERE deleted_at IS NULL
  )
ORDER BY growth_pct DESC NULLS LAST
LIMIT 50
```

## Interpreting results

- **Positive `growth_pct`** (e.g. `12.5`) → +12.5% MoM growth in that metric.
- **Negative `growth_pct`** (e.g. `-8.0`) → company / tech is contracting.
- **`str_value IS NULL`** — first data point for a series (no prior month to compare against). Filtered out by default.
- `insight_name` prefix `growth-` is always present in the stored values. When filtering, use `LOWER(insight_name) LIKE 'growth-%keyword%'` or exact match `= 'growth-EDR'`.

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Narrate the trend: "*Capital One's CrowdStrike footprint grew +8.2% MoM in March 2025, vs. flat total headcount (+0.3%).*"
2. For time-series questions, show a simple table of `time_period → growth_pct`.
3. Offer `download_dataset` for the full CSV.
4. Follow-up slices ("show me only months where it was negative", "sort by growth rate") → use `query_datasets`.

## Common pitfalls

- **`str_value` is TEXT, not FLOAT** — always use `TRY_CAST(str_value AS FLOAT)` for arithmetic or ordering.
- **Forgetting `str_value IS NOT NULL`** — NULL rows are baseline-only and distort charts / averages.
- **`insight_name` must have the `growth-` prefix** — stored values are always `growth-EDR`, not `EDR`. Use `ILIKE 'growth-%edr%'` for fuzzy matching.
- **UNION without matching columns** — both tables have the same shape; always alias the `source` column to distinguish rows.
- **Re-running for "pivot by month"** — use `query_datasets` with a PIVOT-style query against the existing `dataset_id`.
