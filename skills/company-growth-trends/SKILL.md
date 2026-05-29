---
name: company-growth-trends
description: Analyse monthly headcount growth and technology/persona adoption trends for companies. For total company headcount use `get_company_headcount`; for technology or persona growth use `query_onfire` against ONFIRE.GROWTH_INSIGHT_MONTHLY. Use when the user wants to know if a company is hiring or contracting, whether a specific technology is spreading within a company, or how headcount growth compares to tech adoption — phrases like "is Acme growing?", "is EDR adoption growing at these accounts?", "compare Sentinex vs total headcount trend at Skywall Networks", "which accounts are shrinking?", "is the data engineering team at Frostbyte expanding?", or any month-over-month growth question.
---

# company-growth-trends

Two complementary data sources accessed via separate tools:

| What you need | Tool to use | Source |
|---|---|---|
| **Total company headcount** over time + (optional) employee roster with prior-company | `get_company_headcount` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` (tenure-based) + `ONFIRE.PEOPLE_GRAND` (profile enrichment). Tool-managed; never exposed via `query_onfire`. |
| **Technology / persona growth** (e.g. Sentinex, data engineer) | `query_onfire` → `ONFIRE.GROWTH_INSIGHT_MONTHLY` | Pre-computed monthly % change |

> **Rule:** Never use `query_onfire` for total headcount questions. Always use `get_company_headcount`.

---

## When to use this

- "Is Meridian Bank's Sentinex footprint growing?" → `query_onfire` (insight)
- "Compare EDR adoption to total headcount at these 5 accounts" → both tools, then compare
- "Which of our target accounts are shrinking overall?" → `get_company_headcount`
- "Is the data engineering persona expanding at Frostbyte?" → `query_onfire` (insight)
- "Who joined Northwind in the last 12 months and where did they come from?" → `get_company_headcount` (roster is always returned)
- "Who left Northwind in the last quarter and where did they go?" → `get_company_headcount` (roster includes leavers + next-company)
- Any month-over-month growth / trend question for companies

Skip this for:
- Single-month roster of *current* employees by keyword → use `employee-footprint`
- Open requisitions → use `hiring-signals`

---

## `get_company_headcount` — total headcount + employee roster

Headcount is **derived from tenure rows** in `ONFIRE.PEOPLE_GRAND_EXPERIENCES`:
for each month M in the window, the tool counts distinct people whose tenure
covers M (`START_DATE <= last-day-of-M` AND `END_DATE IS NULL OR END_DATE >=
first-day-of-M`). MoM growth % is computed from those counts.

The roster is **always returned** alongside the monthly counts (no opt-in
flag). One row per (person × stint) where any of these hold:

- `start_date` falls in the lookback window → **joiner**
- `end_date IS NULL` → **still active**
- `end_date` falls in the lookback window → **leaver** (covers long-tenured
  departures whose start is outside the window)

Each row is joined to `ONFIRE.PEOPLE_GRAND` for profile fields (name,
country, region, current title) and self-joined to
`ONFIRE.PEOPLE_GRAND_EXPERIENCES` for the person's immediately-prior AND
immediately-next company. `next_*` is only populated for stints that
ended (`end_date IS NOT NULL`). Both tables are tool-managed —
`query_onfire` cannot read them.

### Parameters

| Parameter | Type | Notes |
|---|---|---|
| `company_linkedin_urls` | `List[str]` | Required. Up to 50 URLs. Any variant accepted; normalized to `linkedin.com/company/<slug>`. |
| `months` | `int` | Optional. Months of history (default 13, max 36). Also the roster cutoff — joiners with `start_date` in the window, leavers with `end_date` in the window, plus all still-active employees. |

### Response shape

Both keys are always present.

```json
{
  "headcount": {
    "dataset":     {dataset handle},
    "total_count": N,
    "preview_rows": [first 20 rows]
  },
  "employees": {
    "dataset":     {dataset handle},
    "total_count": M,
    "preview_rows": [first 20 rows]
  }
}
```

#### Headcount rows (most-recent first)

| Column | Notes |
|---|---|
| `company_linkedin_url` | Normalized to `linkedin.com/company/...` |
| `time_period` | First day of the month (e.g. `2026-01-01`) |
| `employee_count` | Distinct people whose tenure covers that month |
| `growth_pct` | MoM % change (NULL for the oldest row in the window) |

The **first row per company** is the current month's count.

#### Employee rows (one per stint)

| Column | Source | Notes |
|---|---|---|
| `company_linkedin_url` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Target company |
| `person_linkedin_url`, `person_linkedin_id` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | The employee |
| `is_primary` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | LinkedIn's "current primary role" flag |
| `start_date`, `end_date` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | `YYYY-MM` strings (NULL end = still there) |
| `title_name`, `title_role`, `title_sub_role`, `title_levels` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Title classification at the company |
| `full_name`, `headline` | `ONFIRE.PEOPLE_GRAND` | Latest snapshot |
| `location_country`, `location_region`, `location_continent`, `location_name` | `ONFIRE.PEOPLE_GRAND` | Person's location |
| `current_job_title`, `current_company_name`, `current_company_linkedin_url` | `ONFIRE.PEOPLE_GRAND` | What they're doing *now* (may differ from the target stint if `end_date IS NOT NULL`) |
| `prior_company_name`, `prior_company_linkedin_url`, `prior_title` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Where they came from before the target stint |
| `prior_start_date`, `prior_end_date` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Prior stint's window |
| `next_company_name`, `next_company_linkedin_url`, `next_title` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Where they went after the target stint. **NULL when `end_date IS NULL`** (still active) |
| `next_start_date`, `next_end_date` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Next stint's window |

### Deriving joiners / leavers from the roster

The roster is one source of truth for both directions:

- **Joiners** — `WHERE start_date IN window AND end_date IS NULL` (or include short-stint leavers with `end_date IN window` if you want all arrivals)
- **Joiner origins** — `prior_company_name` is already attached
- **Leavers** — `WHERE end_date IN window`
- **Leaver destinations** — `next_company_name` is already attached

### Example calls

```python
# Default — monthly series + full roster (joiners, leavers, still-active)
get_company_headcount(
    company_linkedin_urls=["linkedin.com/company/packmint"],
    months=12,
)
```

### Example interpretation

- `employee_count: 533, growth_pct: 0.2` → 533 active employees this month, +0.2% MoM
- `growth_pct: null` → oldest month in the window (no prior month to diff against)
- `growth_pct: -1.5` → headcount contracted 1.5% MoM
- An employee row with `end_date IS NULL` is currently at the company
- `prior_company_name = "Globex"` → the person was at Globex right before this stint; useful for joiner-origin / talent-flow analysis
- `next_company_name = "Frostbyte"` → after leaving the target company they went to Frostbyte; useful for leaver-destination analysis (only set when `end_date IS NOT NULL`)

---

## `query_onfire` → `GROWTH_INSIGHT_MONTHLY` — technology / persona growth

### Table structure

| Column | Type | Notes |
|---|---|---|
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
  AND company_linkedin_url ILIKE '%/company/meridian-bank%'
  AND LOWER(insight_name) = 'growth-sentinex'
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
  AND company_linkedin_url ILIKE '%/company/frostbyte%'
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
      'linkedin.com/company/northwind',
      'linkedin.com/company/sendline',
      'linkedin.com/company/pathwatch'
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

Call both tools and merge the results in your response.

**Step 1** — get total headcount:
```python
get_company_headcount(
    company_linkedin_urls=["linkedin.com/company/skywall-networks"],
    months=13,
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
  AND company_linkedin_url ILIKE '%/company/skywall-networks%'
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

1. Narrate the trend: *"Skywall Networks' total headcount grew +3.2% MoM in April 2025, while Sentinex persona adoption grew +8.5% — outpacing overall hiring."*
2. For time-series questions, show a table of `time_period → growth_pct`.
3. Offer `download_dataset` for the full CSV.
4. Follow-up slices → use `query_datasets` against the existing `dataset_id`.

---

## Common pitfalls

- **Using `query_onfire` for total headcount** — always use `get_company_headcount` instead.
- **Treating `next_company_name` as "current employer"** — it's the *next* stint after this one. For still-active people (`end_date IS NULL`) it's NULL. Use `current_company_name` for "where they work now".
- **`str_value` is TEXT** in GROWTH_INSIGHT_MONTHLY — always use `TRY_CAST(str_value AS FLOAT)` for arithmetic.
- **Forgetting `str_value IS NOT NULL`** — NULL rows are baseline-only and distort averages.
- **`insight_name` must have the `growth-` prefix** — use `ILIKE 'growth-%edr%'` for fuzzy matching.
- **`growth_pct` NULL on oldest row** — the LAG window has no prior month. Filter it out before computing averages.
- **`start_date` / `end_date` in the employee roster are `YYYY-MM` strings**, not full dates. Treat them as month granularity.
