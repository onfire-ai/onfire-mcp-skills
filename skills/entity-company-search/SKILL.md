---
name: entity-company-search
description: Search for companies directly from Onfire's LinkedIn company entity table (ONFIRE.COMPANIES) using the `query_onfire` tool. Use when the user wants company firmographics, technology stacks, funding data, or social URLs — phrases like "find fintech companies in Israel with 50-200 employees", "look up Northwind's company data", "which companies in our list are publicly traded", "get the Discord URL for Artifex", or any company lookup that can be answered with SQL filters on LinkedIn company data.
---

# entity-company-search

Direct SQL lookup against `ONFIRE.COMPANIES` via `query_onfire`.
The canonical LinkedIn company entity table — firmographics, technologies,
funding, social channels, and enriched metadata in one place.

## When to use this

- "Find cybersecurity companies in Germany with 200-500 employees"
- "Look up Northwind's company record — give me their LinkedIn, size, industry"
- "Which of these companies are B2B? Filter by IS_B2B = true"
- "Get the GitHub and Discord URLs for Artifex"
- "Find companies that recently raised a Series B"
- Any company lookup expressible as column filters on company firmographics

Skip this for:
- Searching companies by the **people** they employ → use `entity-people-search`
- Scoring companies for propensity → use `ai_prospecting`
- Monthly headcount growth trends → use `company-growth-trends`

## Key columns

| Column | Type | Notes |
|--------|------|-------|
| `LINKEDIN_URL` | TEXT | Primary key. Always return this. |
| `NAME` | TEXT | Company display name |
| `WEBSITE` | TEXT | Company website |
| `DOMAIN` | TEXT | Website domain only |
| `SIZE` | TEXT | LinkedIn size bucket: "1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000", "10001+" |
| `EMPLOYEE_COUNT` | NUMBER | Exact LinkedIn follower-derived count |
| `INDUSTRY` | TEXT | LinkedIn industry string |
| `COMPANY_TYPE` | TEXT | "Public", "Private", "Non-profit", etc. |
| `IS_B2B` | BOOLEAN | Enriched B2B flag |
| `LOCATION_COUNTRY` | TEXT | HQ country |
| `LOCATION_REGION` | TEXT | HQ state/region |
| `LOCATION_NAME` | TEXT | HQ city, state |
| `FOUNDED` | TEXT | Year founded |
| `TECHNOLOGIES` | ARRAY | Tech stack tags |
| `DESCRIPTION` | TEXT | Company description |
| `ENRICHED_SUMMARY` | TEXT | AI-enriched description |
| `ENRICHED_CATEGORY` | TEXT | Product category |
| `ENRICHED_KEYWORDS` | ARRAY | Topic keywords |
| `FOLLOWERS` | NUMBER | LinkedIn follower count |
| `FUNDING_ROUNDS_LAST_ROUND_TYPE` | TEXT | e.g. "Series B", "IPO" |
| `FUNDING_ROUNDS_LAST_ROUND_DATE` | DATE | Date of most recent round |
| `FUNDING_ROUNDS_LAST_ROUND_MONEY_RAISED` | FLOAT | Amount in USD |
| `FUNDING_ROUNDS_TOTAL_ROUNDS_COUNT` | NUMBER | Total funding rounds |
| `STOCK_EXCHANGE` | TEXT | "NYSE", "NASDAQ", etc. |
| `COMPANY_TICKER` | TEXT | Stock ticker |
| `GITHUB_URL` | TEXT | GitHub org URL |
| `DISCORD_URL` | TEXT | Discord server URL |
| `REDDIT_URL` | TEXT | Subreddit URL |
| `DELETED_AT` | TEXT | Always filter `IS NULL` |

## Required WHERE clause pattern

Every query **must** include `WHERE DELETED_AT IS NULL` plus at least one
business filter.

## SQL templates

### Lookup by LinkedIn URL or website
```sql
SELECT
    LINKEDIN_URL, NAME, WEBSITE, SIZE, INDUSTRY,
    EMPLOYEE_COUNT, LOCATION_COUNTRY, COMPANY_TYPE,
    FUNDING_ROUNDS_LAST_ROUND_TYPE, FUNDING_ROUNDS_LAST_ROUND_DATE
FROM ONFIRE.COMPANIES
WHERE DELETED_AT IS NULL
  AND DOMAIN = 'northwind.com'
LIMIT 1
```

### By industry + size + country
```sql
SELECT
    LINKEDIN_URL, NAME, WEBSITE, SIZE, EMPLOYEE_COUNT,
    LOCATION_COUNTRY, LOCATION_NAME, IS_B2B
FROM ONFIRE.COMPANIES
WHERE DELETED_AT IS NULL
  AND INDUSTRY ILIKE '%cybersecurity%'
  AND SIZE IN ('201-500', '501-1000')
  AND LOCATION_COUNTRY = 'Germany'
ORDER BY EMPLOYEE_COUNT DESC NULLS LAST
LIMIT 100
```

### By technology stack
```sql
SELECT
    LINKEDIN_URL, NAME, WEBSITE, SIZE, INDUSTRY,
    TECHNOLOGIES, LOCATION_COUNTRY
FROM ONFIRE.COMPANIES
WHERE DELETED_AT IS NULL
  AND ARRAY_CONTAINS('Kubernetes'::VARIANT, TECHNOLOGIES)
  AND IS_B2B = TRUE
LIMIT 100
```

### Recent funding rounds
```sql
SELECT
    LINKEDIN_URL, NAME, WEBSITE, SIZE,
    FUNDING_ROUNDS_LAST_ROUND_TYPE,
    FUNDING_ROUNDS_LAST_ROUND_DATE,
    FUNDING_ROUNDS_LAST_ROUND_MONEY_RAISED,
    LOCATION_COUNTRY
FROM ONFIRE.COMPANIES
WHERE DELETED_AT IS NULL
  AND FUNDING_ROUNDS_LAST_ROUND_TYPE = 'Series B'
  AND FUNDING_ROUNDS_LAST_ROUND_DATE >= '2025-01-01'
  AND INDUSTRY ILIKE '%security%'
ORDER BY FUNDING_ROUNDS_LAST_ROUND_DATE DESC
LIMIT 50
```

### Bulk lookup by domain list (e.g. from CRM)
```sql
SELECT
    LINKEDIN_URL, NAME, DOMAIN, SIZE, INDUSTRY,
    EMPLOYEE_COUNT, IS_B2B, COMPANY_TYPE
FROM ONFIRE.COMPANIES
WHERE DELETED_AT IS NULL
  AND DOMAIN IN ('northwind.com', 'sendline.com', 'pathwatch.com', 'frostbyte.com')
LIMIT 50
```

### Get social/community URLs for a company
```sql
SELECT
    NAME, LINKEDIN_URL, GITHUB_URL, DISCORD_URL,
    REDDIT_URL, WEBSITE
FROM ONFIRE.COMPANIES
WHERE DELETED_AT IS NULL
  AND DOMAIN = 'artifex.com'
LIMIT 1
```

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` to the user as a table.
2. State `total_count`; if > 20, mention the full CSV is available.
3. Offer `download_dataset(dataset_id="...")` for the full result.
4. For follow-up filters ("now filter to B2B only", "add GitHub URLs"),
   use `query_datasets` against the `dataset_id` — **do not re-run** `query_onfire`.

## Common pitfalls

- **Forgetting `DELETED_AT IS NULL`** — always include it.
- **Using `SIZE` as a number** — it's a TEXT bucket ("201-500"). Use `IN (...)`.
- **`TECHNOLOGIES` is an ARRAY** — use `ARRAY_CONTAINS('Kubernetes'::VARIANT, TECHNOLOGIES)`.
- **`DOMAIN` vs `WEBSITE`** — `DOMAIN` is just the bare domain ("northwind.com"); `WEBSITE` may include the protocol. Prefer `DOMAIN` for exact matching.
- **Re-running for "now add the GitHub URLs"** — enrich with `query_datasets` on the existing `dataset_id`.
