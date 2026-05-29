---
name: employee-footprint
description: Find employees at a target company whose LinkedIn profiles mention specific technology or competitor keywords using the `query_onfire` tool against ONFIRE.PEOPLE. Use when the user wants proof a product is deployed at an account, wants a competitor footprint cut, or needs evidence sentences from employee profiles — phrases like "who at Meridian Bank mentions Sentinex", "find Ironwall users at Nornet", "do any Northwind engineers mention Kubernetes in their profile", "show me the Sentinex footprint at Skywall Networks", or any keyword-based employee profile lookup at a specific company.
---

# employee-footprint

SQL lookup against `ONFIRE.PEOPLE` via `query_onfire`. Match
employees whose `JOB_SUMMARY` (current role description), `SUMMARY`
(career bio), or `JOB_TITLE` contains a product or competitor keyword —
the strongest signal of in-production deployment at an account.

## When to use this

- "Who at Meridian Bank mentions Sentinex in their profile?"
- "Find engineers at Nornet whose job summary mentions Kubernetes"
- "Does anyone at Northwind have Cloudgate in their LinkedIn?"
- "Show me the Sentinex footprint at Skywall Networks"
- "Find employees at these accounts who mention our product"
- Any keyword-based employee profile lookup at a specific company

Skip this for:
- GitHub stars/forks → use `github-repo-signals`
- Community membership → use `community-join-signals`
- Event attendance → use `event-attendance-signals`
- Company firmographics → use `entity-company-search`

## Key columns

| Column | Type | Notes |
|--------|------|-------|
| `LINKEDIN_URL` | TEXT | Person's LinkedIn URL |
| `FULL_NAME` | TEXT | Display name |
| `JOB_TITLE` | TEXT | Current job title |
| `JOB_SUMMARY` | TEXT | Current role description — **strongest signal** |
| `SUMMARY` | TEXT | Career bio / about section |
| `HEADLINE` | TEXT | LinkedIn headline |
| `JOB_COMPANY_LINKEDIN_URL` | TEXT | Employer's LinkedIn URL |
| `JOB_START_DATE` | DATE | When they started this role |
| `LOCATION_NAME` | TEXT | City, country |
| `DELETED_AT` | TEXT | Always filter `IS NULL` |

**Evidence priority:** `JOB_SUMMARY` (current role) > `SUMMARY` (career bio) > `JOB_TITLE`

## Required WHERE clause

```sql
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL ILIKE '%/<company-slug>%'
```

## SQL templates

### Single keyword at one company
```sql
SELECT
    LINKEDIN_URL,
    FULL_NAME,
    JOB_TITLE,
    JOB_SUMMARY,
    LOCATION_NAME,
    JOB_START_DATE
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL ILIKE '%/meridian-bank%'
  AND (
      LOWER(JOB_SUMMARY) LIKE '%sentinex%'
   OR LOWER(SUMMARY)     LIKE '%sentinex%'
   OR LOWER(JOB_TITLE)   LIKE '%sentinex%'
  )
ORDER BY JOB_START_DATE DESC NULLS LAST
LIMIT 50
```

### Multiple keywords (OR) — any product from a list
```sql
SELECT
    LINKEDIN_URL,
    FULL_NAME,
    JOB_TITLE,
    JOB_SUMMARY,
    LOCATION_NAME
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL ILIKE '%/nornet%'
  AND (
      LOWER(JOB_SUMMARY) LIKE '%ironwall%'   OR LOWER(SUMMARY) LIKE '%ironwall%'   OR LOWER(JOB_TITLE) LIKE '%ironwall%'
   OR LOWER(JOB_SUMMARY) LIKE '%ironwall%'  OR LOWER(SUMMARY) LIKE '%ironwall%'  OR LOWER(JOB_TITLE) LIKE '%ironwall%'
   OR LOWER(JOB_SUMMARY) LIKE '%ironwall sase%'  OR LOWER(SUMMARY) LIKE '%ironwall sase%'  OR LOWER(JOB_TITLE) LIKE '%ironwall sase%'
  )
ORDER BY JOB_START_DATE DESC NULLS LAST
LIMIT 100
```

### Competitor footprint — which competitor has the strongest presence?
```sql
SELECT
    CASE
        WHEN LOWER(JOB_SUMMARY) LIKE '%sentinex%' OR LOWER(SUMMARY) LIKE '%sentinex%' THEN 'sentinex'
        WHEN LOWER(JOB_SUMMARY) LIKE '%vanguard%' OR LOWER(SUMMARY) LIKE '%vanguard%' THEN 'vanguard'
        WHEN LOWER(JOB_SUMMARY) LIKE '%cloudgate%'     OR LOWER(SUMMARY) LIKE '%cloudgate%'     THEN 'cloudgate'
        ELSE 'other'
    END                                    AS matched_keyword,
    COUNT(DISTINCT LINKEDIN_URL)           AS employee_count
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL ILIKE '%/meridian-bank%'
  AND (
      LOWER(JOB_SUMMARY) LIKE '%sentinex%' OR LOWER(SUMMARY) LIKE '%sentinex%'
   OR LOWER(JOB_SUMMARY) LIKE '%vanguard%' OR LOWER(SUMMARY) LIKE '%vanguard%'
   OR LOWER(JOB_SUMMARY) LIKE '%cloudgate%'     OR LOWER(SUMMARY) LIKE '%cloudgate%'
  )
GROUP BY 1
ORDER BY employee_count DESC
```

### Footprint across multiple target accounts
```sql
SELECT
    JOB_COMPANY_LINKEDIN_URL,
    COUNT(DISTINCT LINKEDIN_URL) AS employees_mentioning_keyword
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL IN (
      'https://www.linkedin.com/company/northwind',
      'https://www.linkedin.com/company/sendline',
      'https://www.linkedin.com/company/pathwatch'
  )
  AND (
      LOWER(JOB_SUMMARY) LIKE '%sentinex%'
   OR LOWER(SUMMARY)     LIKE '%sentinex%'
  )
GROUP BY 1
ORDER BY employees_mentioning_keyword DESC
```

### Senior contacts only (title-based seniority filter)
```sql
SELECT
    LINKEDIN_URL,
    FULL_NAME,
    JOB_TITLE,
    JOB_SUMMARY,
    LOCATION_NAME
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL ILIKE '%/meridian-bank%'
  AND (
      LOWER(JOB_SUMMARY) LIKE '%sentinex%'
   OR LOWER(SUMMARY)     LIKE '%sentinex%'
  )
  AND (
      LOWER(JOB_TITLE) LIKE '%director%'
   OR LOWER(JOB_TITLE) LIKE '%head of%'
   OR LOWER(JOB_TITLE) LIKE '%vp %'
   OR LOWER(JOB_TITLE) LIKE '%chief%'
   OR LOWER(JOB_TITLE) LIKE '%manager%'
  )
ORDER BY JOB_START_DATE DESC NULLS LAST
LIMIT 30
```

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` as a table. Quote the relevant snippet from `JOB_SUMMARY` as the evidence sentence — it's the proof the product is deployed.
2. State `total_count`; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only directors", "group by keyword", "show only EMEA") → use `query_datasets` on the `dataset_id` — **do not re-run** `query_onfire`.

## Reading the evidence

The most valuable output field is `JOB_SUMMARY`. When presenting results:
- Quote the relevant substring verbatim as proof of deployment
- `JOB_SUMMARY` mentions = current-role evidence (strongest)
- `SUMMARY` mentions = career bio (moderate — may be a past role)
- `JOB_TITLE` matches = title-only (weakest — job title includes the keyword)

## Common pitfalls

- **Company slug format** — `JOB_COMPANY_LINKEDIN_URL` is stored as the full URL. Always filter with `ILIKE '%/<slug>%'` (leading slash + slug), not an exact match.
- **Case sensitivity** — always `LOWER(JOB_SUMMARY) LIKE '%keyword%'` — never raw `ILIKE` on a computed column.
- **`DELETED_AT IS NULL`** — always include.
- **Re-running for follow-ups** — slice the existing dataset with `query_datasets`.
