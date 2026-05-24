---
name: hiring-signals
description: Find open job postings at target companies using the `query_onfire` tool against SILVER.JOB_POST.STG_JOB_POSTS. Use when the user wants to know what roles a company is actively hiring for, where they're hiring, what seniority they're posting, which companies are hiring for a technology or skill, what open positions signal budget or expansion - phrases like "what is Stripe hiring for?", "find VP-level roles at my target accounts", "which accounts are expanding their security team?", "find buyers at companies hiring AI engineers", "show open data engineer roles in EMEA", or any job posting / hiring signal lookup.
compatibility:
  tools:
    - query_onfire
---

# hiring-signals

SQL lookup against `SILVER.JOB_POST.STG_JOB_POSTS` via `query_onfire`.
Each row = one job posting captured from LinkedIn Jobs. Use this to identify
budget signals, expansion areas, and the geographic / seniority shape of a
company's open requisitions.

## When to use this

- "What is Capital One actively hiring for right now?"
- "Find companies hiring Kubernetes or Python engineers"
- "Which of our target accounts are expanding their security team?"
- "Show me all open DevSecOps roles posted in the last 30 days"
- "What's the geographic shape of Cloudsmith's open postings?"
- "Which accounts have the most active postings in EMEA right now?"
- Any job posting lookup or hiring signal question

Skip this for:
- Current employee profiles (no hiring signal needed) → use `entity-people-search` or `employee-footprint`
- Company firmographics → use `entity-company-search`
- GitHub or community signals → use `github-repo-signals` / `community-join-signals`

## Table structure

`SILVER.JOB_POST.STG_JOB_POSTS` - each row = one job posting captured from
LinkedIn Jobs.

| Column | Type | Notes |
|---|---|---|
| `ID` | TEXT | Unique job post ID (e.g. `"LinkedinJobs_4068734982"`) |
| `DATE_POSTED` | TIMESTAMP | Original posting date on LinkedIn. **Use this for date filtering.** |
| `COMPANY_LINKEDIN_URL` | TEXT | Company LinkedIn URL - use for account filtering. Format `linkedin.com/company/<slug>` (no `https://www.`). |
| `COMPANY_NAME` | TEXT | Company display name |
| `COMPANY_ID` | TEXT | Internal company ID |
| `COUNTRY` | TEXT | Country of the role (e.g. `"United Kingdom"`, `"United States"`, `"Ireland"`, `"India"`) |
| `LOCATION` | TEXT | Lowercased city / region / country string (e.g. `"belfast, northern ireland, united kingdom"`) |
| `JOB_TEXT` | TEXT | Full job description. **Very long - avoid selecting unless explicitly needed.** |
| `JOB_POST_TITLE` | TEXT | Title of the open role (e.g. `"Senior Application Security Engineer"`) |
| `JOB_FUNCTION` | TEXT | LinkedIn job-function classification (e.g. `"information technology"`, `"engineering and information technology"`, `"management and manufacturing"`) |
| `SENIORITY_JOB` | TEXT | Seniority level (see values below) |
| `JOB_POST_SENIORITY_SCORE` | NUMBER | Numeric seniority score (0 = lower, higher = more senior) |
| `EMPLOYMENT_TYPE` | TEXT | `"Full-time"`, `"Part-time"`, `"Contract"`, `"Internship"` |
| `EXTERNAL_URL` | TEXT | The company's own careers-page URL when present (e.g. `careers.cloudsmith.com/...`); often null |
| `REDIRECTED_URL` | TEXT | The LinkedIn Jobs URL for the posting |
| `APPLICATION_ACTIVE` | NUMBER | `1` if the posting is currently active, `0` if closed / filled |
| `PAYLOAD_LAST_UPDATED` | TIMESTAMP | When the source payload was last updated |
| `LAST_UPDATED_TIME` | TIMESTAMP | When Onfire last refreshed this record |
| `LAST_UPDATED_SRC` | TIMESTAMP | When the source last touched this record |

### `SENIORITY_JOB` values
LinkedIn-standard strings: `"Entry level"`, `"Associate"`, `"Mid-Senior level"`,
`"Director"`, `"Executive"`, `"Internship"`, `"Not Applicable"` (when LinkedIn
did not classify the role).

### No `DELETED_AT` column
This table does NOT have a soft-delete column. Do NOT include
`DELETED_AT IS NULL` - the query will fail.

Use `APPLICATION_ACTIVE = 1` to scope to currently open roles.

## SQL templates

### What is a company actively hiring for right now?
```sql
SELECT JOB_POST_TITLE,
       SENIORITY_JOB,
       JOB_FUNCTION,
       COUNTRY,
       LOCATION,
       DATE_POSTED,
       REDIRECTED_URL
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE LOWER(COMPANY_LINKEDIN_URL) = 'linkedin.com/company/capital-one'
  AND APPLICATION_ACTIVE = 1
ORDER BY DATE_POSTED DESC NULLS LAST
LIMIT 50
```

### Postings dated in a specific window (e.g. last quarter)
```sql
SELECT JOB_POST_TITLE,
       SENIORITY_JOB,
       COUNTRY,
       LOCATION,
       DATE_POSTED,
       APPLICATION_ACTIVE,
       REDIRECTED_URL
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE LOWER(COMPANY_LINKEDIN_URL) = 'linkedin.com/company/cloudsmith'
  AND DATE_POSTED BETWEEN '2026-01-01' AND '2026-03-31'
ORDER BY DATE_POSTED
```

### Find roles by keyword (title or full job text)
```sql
SELECT COMPANY_NAME,
       COMPANY_LINKEDIN_URL,
       JOB_POST_TITLE,
       SENIORITY_JOB,
       COUNTRY,
       LOCATION,
       DATE_POSTED,
       REDIRECTED_URL
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE APPLICATION_ACTIVE = 1
  AND (
        JOB_POST_TITLE ILIKE '%kubernetes%'
     OR JOB_TEXT       ILIKE '%kubernetes%'
  )
ORDER BY DATE_POSTED DESC NULLS LAST
LIMIT 100
```

### Target accounts hiring for a technology
```sql
SELECT COMPANY_NAME,
       JOB_POST_TITLE,
       SENIORITY_JOB,
       COUNTRY,
       LOCATION,
       DATE_POSTED
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE APPLICATION_ACTIVE = 1
  AND LOWER(COMPANY_LINKEDIN_URL) IN (
        'linkedin.com/company/stripe',
        'linkedin.com/company/twilio',
        'linkedin.com/company/datadog'
      )
  AND (
        JOB_POST_TITLE ILIKE '%security%'
     OR JOB_TEXT       ILIKE '%security%'
  )
ORDER BY DATE_POSTED DESC NULLS LAST
LIMIT 100
```

### Senior roles only (Director / Executive) at target accounts
```sql
SELECT COMPANY_NAME,
       JOB_POST_TITLE,
       SENIORITY_JOB,
       COUNTRY,
       LOCATION,
       DATE_POSTED
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE APPLICATION_ACTIVE = 1
  AND SENIORITY_JOB IN ('Director','Executive')
  AND LOWER(COMPANY_LINKEDIN_URL) = 'linkedin.com/company/cisco'
ORDER BY DATE_POSTED DESC NULLS LAST
LIMIT 50
```

### Hiring volume as a growth signal - which target accounts are expanding fastest?
```sql
SELECT COMPANY_NAME,
       COMPANY_LINKEDIN_URL,
       COUNT(*) AS open_roles
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE APPLICATION_ACTIVE = 1
  AND LOWER(COMPANY_LINKEDIN_URL) IN (
        'linkedin.com/company/stripe',
        'linkedin.com/company/twilio',
        'linkedin.com/company/datadog'
      )
GROUP BY COMPANY_NAME, COMPANY_LINKEDIN_URL
ORDER BY open_roles DESC
LIMIT 20
```

### Geographic shape of a company's open postings
```sql
SELECT COUNTRY,
       COUNT(*) AS open_roles
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE APPLICATION_ACTIVE = 1
  AND LOWER(COMPANY_LINKEDIN_URL) = 'linkedin.com/company/cloudsmith'
GROUP BY COUNTRY
ORDER BY open_roles DESC
```

### Functional / seniority breakdown of open roles
```sql
SELECT JOB_FUNCTION,
       SENIORITY_JOB,
       COUNT(*) AS n
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE APPLICATION_ACTIVE = 1
  AND LOWER(COMPANY_LINKEDIN_URL) = 'linkedin.com/company/cloudsmith'
GROUP BY JOB_FUNCTION, SENIORITY_JOB
ORDER BY n DESC
```

### Recent postings in a date window (across accounts)
```sql
SELECT COMPANY_NAME,
       JOB_POST_TITLE,
       SENIORITY_JOB,
       COUNTRY,
       DATE_POSTED,
       REDIRECTED_URL
FROM SILVER.JOB_POST.STG_JOB_POSTS
WHERE DATE_POSTED >= DATEADD(day, -14, CURRENT_DATE())
  AND APPLICATION_ACTIVE = 1
  AND (
        JOB_POST_TITLE ILIKE '%devops%'
     OR JOB_POST_TITLE ILIKE '%platform engineer%'
  )
ORDER BY DATE_POSTED DESC
LIMIT 200
```

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Lead the table with: `JOB_POST_TITLE`, `COMPANY_NAME`, `DATE_POSTED`, `SENIORITY_JOB`, `COUNTRY`, `LOCATION`, `APPLICATION_ACTIVE`.
2. State `total_count`; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only Director-level", "group by country", "last 7 days only") - use `query_datasets` on the `dataset_id`. **Do not re-run** `query_onfire`.

## Reading the signals

- **`APPLICATION_ACTIVE = 1`** = the posting is currently open; the strongest budget signal.
- **`APPLICATION_ACTIVE = 0`** with a recent `DATE_POSTED` = role likely filled - a hire that may not yet show in our employment-history index.
- **`SENIORITY_JOB = "Director" / "Executive"`** = leadership build; expensive seats.
- **Multiple active postings in one country/region** = geographic concentration; reads as a deliberate location strategy (Belfast HQ, EMEA build, US East-coast GTM, India delivery tier, etc.).
- **`JOB_FUNCTION` patterns** - "engineering and information technology" dominating = platform / product build; "management and manufacturing" or sales-flavoured functions = GTM expansion.
- **High active-role count** = active expansion = budget signal. Use the volume template to rank accounts.
- **`JOB_TEXT` keyword search** captures stack mentions anywhere in the description, including the "Familiarity with our stack" or "Nice to have" sections.

## Common pitfalls

- **No `DELETED_AT` column** - do NOT include `DELETED_AT IS NULL` (query will fail). Use `APPLICATION_ACTIVE = 1` for the active-only cut.
- **`COMPANY_LINKEDIN_URL` is the slug form** `linkedin.com/company/<slug>` (no `https://www.` prefix). Always lower-case both sides of the comparison.
- **`DATE_POSTED` vs `PAYLOAD_LAST_UPDATED` vs `LAST_UPDATED_TIME`** - `DATE_POSTED` is when LinkedIn shows the role as posted; the other two reflect refresh activity in our pipeline. Use `DATE_POSTED` for date filtering and the others for freshness checks.
- **No hiring-manager fields** - this table is posting-level only. If you need the person who posted the role, you'll need a separate signal (or pair the posting with `entity-people-search` on the company's recruiters / department heads).
- **`JOB_TEXT` is very long** - avoid selecting it by default; use `JOB_POST_TITLE` plus `JOB_FUNCTION` for summaries.
- **`SENIORITY_JOB = "Not Applicable"`** is a real value for roles LinkedIn did not classify - don't filter these out blindly.
- **Re-running for follow-ups** - slice the existing dataset with `query_datasets`.
