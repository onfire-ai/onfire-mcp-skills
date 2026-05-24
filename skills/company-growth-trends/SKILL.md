---
name: company-growth-trends
description: Analyse monthly headcount growth and technology/persona adoption trends for companies. For total company headcount use `get_company_headcount`; for technology or persona growth use `query_onfire` against ONFIRE.GROWTH_INSIGHT_MONTHLY. Use when the user wants to know if a company is hiring or contracting, whether a specific technology is spreading within a company, or how headcount growth compares to tech adoption — phrases like "is Acme growing?", "is EDR adoption growing at these accounts?", "compare CrowdStrike vs total headcount trend at Palo Alto Networks", "which accounts are shrinking?", "is the data engineering team at Snowflake expanding?", or any month-over-month growth question.
---

# company-growth-trends

Two complementary data sources accessed via separate tools:

| What you need | Tool to use | Source |
|---------------|-------------|--------|
| **Total company headcount** over time | `get_company_headcount` | `SILVER.EXPLORIUM.EXPLORIUM_PEOPLE_FULL` (internal; never queried directly) |
| **Technology / persona growth** (e.g. CrowdStrike, data engineer) | `query_onfire` → `ONFIRE.GROWTH_INSIGHT_MONTHLY` | Pre-computed monthly % change |

> **Rule:** Never use `query_onfire` for total headcount questions. Always use `get_company_headcount`.

---

## When to use this

- "Is Capital One's CrowdStrike footprint growing?" → `query_onfire` (insight)
- "Compare EDR adoption to total headcount at these 5 accounts" → both tools, then compare
- "Which of our target accounts are shrinking overall?" → `get_company_headcount`
- "Is the data engineering persona expanding at Snowflake?" → `query_onfire` (insight)
- "Show me the last 12 months of growth for 'growth-Splunk' at Cisco" → `query_onfire` (insight)
- Any month-over-month growth / trend question for companies

Skip this for:
- Current headcount or employee count → query `ONFIRE.COMPANIES.EMPLOYEE_COUNT`
- Employees *using* a technology right now → use `employee-footprint` skill

---

## get_company_headcount — total headcount

Backed by **monthly company snapshots** with directly reported employee counts — accurate growth and decline, no reconstruction needed.

### Parameters

| Parameter | Type | Notes |
|-----------|------|-------|
| `company_linkedin_urls` | `List[str]` | Required. Up to 50 LinkedIn company page URLs. Any format accepted — `linkedin.com/company/acme`, `https://www.linkedin.com/company/acme`, etc. |
| `months` | `int` | Optional. Months of history (default 13, max 36). |

### Response shape (each row, ordered most-recent first)

| Column | Notes |
|--------|-------|
| `company_linkedin_url` | Normalized to `https://www.linkedin.com/company/...` |
| `time_period` | First day of the month (e.g. `2026-01-01`) |
| `employee_count` | Reported headcount for that month |
| `growth_pct` | MoM % change (NULL for the oldest row in the window) |

The **first row per company** is the current headcount.

### Example call

```
get_company_headcount(
    company_linkedin_urls=["linkedin.com/company/sonatype"],
    months=13
)
```

### Example output interpretation

- `employee_count: 533, growth_pct: 0.2` → 533 employees this month, +0.2% vs last month
- `growth_pct: null` → oldest data point in the window (no prior month to diff against)
- `growth_pct: -1.5` → headcount contracted 1.5% vs prior month

---

## query_onfire → GROWTH_INSIGHT_MONTHLY — technology / persona growth

### Table structure

| Column | Type | Notes |
|--------|------|-------|
| `company_linkedin_url` | TEXT | Company identifier |
| `company_website` | TEXT | Company website |
| `insight_name` | TEXT | Technology/persona slug, always prefixed `growth-` (e.g. `growth-EDR`, `growth-data_analyst`) |
| `time_period` | DATE | First day of the month |
| `str_value` | TEXT | Growth % as a string (e.g. `"12.5"` = +12.5%). NULL on the first data point. |
| `deleted_at` | TEXT | Always filter `IS NULL` |

Key derived value: `TRY_CAST(str_value AS FLOAT)` to get numeric %.

### Required WHERE clause

```sql
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL   -- excludes first-month baseline rows
  AND company_linkedin_url IN (...)
```

### SQL templates

#### Tech insight growth for one company
```sql
SELECT
    company_linkedin_url,
    insight_name,
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM ONFIRE.GROWTH_INSIGHT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/capital-one%'
  AND LOWER(insight_name) = 'growth-crowdstrike'
ORDER BY time_period DESC
LIMIT 13
```

#### All tech insights for a company (last 3 months)
```sql
SELECT
    insight_name,
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM ONFIRE.GROWTH_INSIGHT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/snowflake%'
  AND time_period >= DATEADD(month, -3, CURRENT_DATE())
ORDER BY insight_name, time_period DESC
LIMIT 200
```

#### Multiple companies — which insight is growing fastest?
```sql
SELECT
    company_linkedin_url,
    insight_name,
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM ONFIRE.GROWTH_INSIGHT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url IN (
      'https://www.linkedin.com/company/stripe',
      'https://www.linkedin.com/company/twilio',
      'https://www.linkedin.com/company/datadog'
  )
  AND insight_name ILIKE 'growth-edr%'
  AND time_period = (
      SELECT MAX(time_period)
      FROM ONFIRE.GROWTH_INSIGHT_MONTHLY
      WHERE deleted_at IS NULL
  )
ORDER BY growth_pct DESC NULLS LAST
LIMIT 50
```

---

## Comparing total headcount vs tech growth

Call both tools then merge the results in your response.

**Step 1** — get total headcount:
```
get_company_headcount(
    company_linkedin_urls=["linkedin.com/company/palo-alto-networks"],
    months=13
)
```

**Step 2** — get tech insight growth via `query_onfire`:
```sql
SELECT
    time_period,
    TRY_CAST(str_value AS FLOAT) AS growth_pct
FROM ONFIRE.GROWTH_INSIGHT_MONTHLY
WHERE deleted_at IS NULL
  AND str_value IS NOT NULL
  AND company_linkedin_url ILIKE '%/company/palo-alto-networks%'
  AND insight_name ILIKE 'growth-edr%'
ORDER BY time_period DESC
LIMIT 13
```

**Step 3** — narrate the comparison aligned by `time_period`.

---

## Interpreting results

- **Positive `growth_pct`** → company / tech is growing that month.
- **Negative `growth_pct`** → contracting.
- **`growth_pct IS NULL`** → first data point in the series. Filter out for charting.
- `insight_name` always has the `growth-` prefix in stored values. Use `ILIKE 'growth-%edr%'` for fuzzy matching.

---

## Output handling

Both tools return a `dataset` handle + `preview_rows` (first 20).

1. Narrate the trend: *"Palo Alto Networks' total headcount grew +3.2% MoM in April 2025, while CrowdStrike persona adoption grew +8.5% — outpacing overall hiring."*
2. For time-series questions, show a table of `time_period → growth_pct`.
3. Offer `download_dataset` for the full CSV.
4. Follow-up slices → use `query_datasets` against the existing `dataset_id`.

---

## Common pitfalls

- **Using `query_onfire` for total headcount** — always use `get_company_headcount` instead.
- **`str_value` is TEXT** — always use `TRY_CAST(str_value AS FLOAT)` for arithmetic in GROWTH_INSIGHT_MONTHLY.
- **Forgetting `str_value IS NOT NULL`** — NULL rows are baseline-only and distort averages.
- **`insight_name` must have the `growth-` prefix** — use `ILIKE 'growth-%edr%'` for fuzzy matching.
- **`growth_pct` NULL on oldest row** — LAG has no prior month. Filter it out before computing averages.
