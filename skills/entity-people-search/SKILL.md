---
name: entity-people-search
description: Search for people/prospects directly from Onfire's LinkedIn people entity table (GOLD.ENTITIES.PEOPLE) using the `query_onfire` tool. Use when the user wants to find prospects by job title, company, location, seniority, skills, or keywords in their profile — phrases like "find engineers at Stripe", "who are the VPs of Security at banks in the US", "show me people with 'Splunk' in their job summary", "look up this LinkedIn URL", or any people search that doesn't require Forschung's cross-database scoring.
---

# entity-people-search

Direct SQL lookup against `GOLD.ENTITIES.PEOPLE` via `query_onfire`.
No external API hop — query the canonical LinkedIn people entity table straight.

## When to use this

- "Find security engineers at Capital One"
- "Who are the CISOs in financial services in Germany?"
- "Show me people whose job summary mentions CrowdStrike"
- "Look up this LinkedIn URL: linkedin.com/in/johndoe"
- "Get me VPs of Engineering at companies with 200-500 employees"
- Any people lookup that can be expressed as column filters on LinkedIn profile data

Skip this for:
- Prospecting with Forschung's persona/event/technology scoring → use `ai_prospecting`
- Looking up a single person by name only (no company context) → use `match_person` first
- People who joined specific communities → use the `community-join-signals` skill

## Key columns

| Column | Type | Notes |
|--------|------|-------|
| `LINKEDIN_URL` | TEXT | Primary key. Always return this. |
| `FULL_NAME` | TEXT | First + last combined |
| `JOB_TITLE` | TEXT | Current role title |
| `JOB_TITLE_ROLE` | TEXT | Normalised role category (e.g. "engineering") |
| `JOB_TITLE_LEVELS` | ARRAY | Seniority array: `["director"]`, `["vp"]`, `["c_suite"]`, `["manager"]`, `["senior"]`, `["entry"]` |
| `JOB_SUMMARY` | TEXT | Current role description (richest keyword field) |
| `HEADLINE` | TEXT | LinkedIn headline |
| `SUMMARY` | TEXT | Career bio / About section |
| `SKILLS` | ARRAY | Skill tags |
| `JOB_COMPANY_LINKEDIN_URL` | TEXT | Employer LinkedIn URL |
| `JOB_COMPANY_NAME` | TEXT | Employer name |
| `JOB_COMPANY_DOMAIN` | TEXT | Employer website domain |
| `JOB_COMPANY_INDUSTRY` | TEXT | Employer industry |
| `JOB_COMPANY_SIZE` | TEXT | e.g. "201-500" |
| `JOB_START_DATE` | TEXT | ISO date of current role start |
| `LOCATION_COUNTRY` | TEXT | e.g. "United States" |
| `LOCATION_REGION` | TEXT | State / region |
| `LOCATION_NAME` | TEXT | City, State |
| `DELETED_AT` | TEXT | Always filter `IS NULL` |

## Required WHERE clause pattern

Every query **must** include `WHERE DELETED_AT IS NULL` plus at least one
business filter. Bare table scans are blocked.

## SQL templates

### By company LinkedIn URL
```sql
SELECT
    LINKEDIN_URL, FULL_NAME, JOB_TITLE, JOB_TITLE_LEVELS,
    JOB_SUMMARY, LOCATION_NAME, JOB_START_DATE
FROM GOLD.ENTITIES.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL ILIKE '%/company/capital-one%'
ORDER BY JOB_START_DATE DESC NULLS LAST
LIMIT 50
```

### By job title keyword
```sql
SELECT
    LINKEDIN_URL, FULL_NAME, JOB_TITLE, JOB_TITLE_LEVELS,
    JOB_COMPANY_NAME, JOB_COMPANY_LINKEDIN_URL, LOCATION_COUNTRY
FROM GOLD.ENTITIES.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_TITLE ILIKE '%security engineer%'
  AND LOCATION_COUNTRY = 'United States'
LIMIT 100
```

### By keyword in job summary (technology footprint)
```sql
SELECT
    LINKEDIN_URL, FULL_NAME, JOB_TITLE,
    JOB_COMPANY_LINKEDIN_URL, JOB_COMPANY_NAME,
    JOB_SUMMARY
FROM GOLD.ENTITIES.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL ILIKE '%/company/stripe%'
  AND (LOWER(JOB_SUMMARY) LIKE '%crowdstrike%'
       OR LOWER(HEADLINE) LIKE '%crowdstrike%')
LIMIT 30
```

### By seniority (array contains)
```sql
SELECT
    LINKEDIN_URL, FULL_NAME, JOB_TITLE, JOB_TITLE_LEVELS,
    JOB_COMPANY_NAME, JOB_COMPANY_INDUSTRY, LOCATION_COUNTRY
FROM GOLD.ENTITIES.PEOPLE
WHERE DELETED_AT IS NULL
  AND ARRAY_CONTAINS('vp'::VARIANT, JOB_TITLE_LEVELS)
  AND JOB_COMPANY_INDUSTRY ILIKE '%financial%'
LIMIT 100
```

### By LinkedIn URL (single person lookup)
```sql
SELECT *
FROM GOLD.ENTITIES.PEOPLE
WHERE DELETED_AT IS NULL
  AND LINKEDIN_URL = 'https://www.linkedin.com/in/johndoe'
LIMIT 1
```

## Output handling

`query_onfire` returns a `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` to the user as a formatted table.
2. State `total_count` — if it's more than 20, tell the user the full set is in the dataset.
3. Offer `download_dataset(dataset_id="...")` for the full CSV.
4. For follow-up filters ("show me only the VPs", "add their company size"),
   use `query_datasets` against the `dataset_id` — **do not re-run** `query_onfire`.

## Common pitfalls

- **Forgetting `DELETED_AT IS NULL`** — rows without this filter include stale/removed profiles.
- **Querying `JOB_TITLE_LEVELS` as TEXT** — it's an ARRAY. Use `ARRAY_CONTAINS('vp'::VARIANT, JOB_TITLE_LEVELS)`.
- **Using `=` on `JOB_COMPANY_LINKEDIN_URL`** — URLs vary in trailing slash and subdomain; prefer `ILIKE '%/company/slug%'`.
- **Re-running for "show me only the engineers"** — slice the existing dataset with `query_datasets`.
