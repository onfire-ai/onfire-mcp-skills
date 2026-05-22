---
name: hiring-signals
description: Find open job posts and their hiring managers at target companies using the `query_onfire` tool against ONFIRE.HIRING_MANAGER_SIGNAL. Use when the user wants to know what roles a company is actively hiring for, who the hiring manager is, which companies are hiring for a technology or skill, what open positions signal budget or expansion, or who to reach out to at an account — phrases like "what is Stripe hiring for?", "who is the hiring manager for the DevOps role at Cisco?", "find VP-level hiring managers at my target accounts", "which accounts are expanding their security team?", "who should I reach out to about our Kubernetes tool?", "find buyers at companies hiring AI engineers", or any job posting or hiring signal lookup.
compatibility:
  tools:
    - query_onfire
    - contact_data_enrichment
---

# hiring-signals

SQL lookup against `ONFIRE.HIRING_MANAGER_SIGNAL` via `query_onfire`.
Each row = one job posting paired with the LinkedIn profile of the hiring manager —
the person responsible for filling the role. Useful for identifying budget signals,
expansion areas, and warm contacts at target accounts.

## When to use this

- "What is Capital One actively hiring for right now?"
- "Who is the hiring manager for the Data Engineer role at Scry AI?"
- "Find companies hiring Kubernetes or Python engineers"
- "Which of our target accounts are expanding their security team?"
- "Find VP/Director-level hiring managers at my target accounts"
- "Who's the right person to reach out to about our DevOps tool at Stripe?"
- "Which companies have a senior buyer actively hiring for AI/ML?"
- "Show me all open DevSecOps roles posted in the last 30 days"
- Any job posting lookup or hiring signal question

Skip this for:
- Current employee profiles (no hiring signal needed) → use `entity-people-search` or `employee-footprint`
- Company firmographics → use `entity-company-search`
- GitHub or community signals → use `github-repo-signals` / `community-join-signals`

## Table structure

Each row = one job posting paired with the person who posted it.

| Column | Type | Notes |
|--------|------|-------|
| `ID` | TEXT | Unique job post ID (e.g. `"LinkedinJobs_3681433407"`) |
| `NAME` | TEXT | Hiring manager's full name (lowercase) |
| `CONTACT_LINKEDIN_URL` | TEXT | Hiring manager's LinkedIn profile — primary outreach target |
| `COMPANY_LINKEDIN_URL` | TEXT | Company LinkedIn URL — use for account filtering |
| `COMPANY_NAME` | TEXT | Company display name |
| `SHORT_SUMMARY` | TEXT | AI-generated one-liner: "[Name] is the hiring manager for [role] at [company]" |
| `JOB_POST_JOB_TITLE` | TEXT | Title of the open role |
| `JOB_POST_SENIORITY` | TEXT | Seniority of the open role (see values below) |
| `PERSON_JOB_TITLE` | TEXT | **Hiring manager's own current job title** |
| `PERSON_SENIORITY` | TEXT | **Hiring manager's seniority slug** (see values below) |
| `SIGNAL_TYPE` | TEXT | Always `"hiring_manager"` |
| `PERSONA_INSIGHTS` | TEXT | Comma-separated tech keywords and persona tags extracted from the job post text |
| `JOB_POST_TEXT` | TEXT | Full job description — very long, avoid selecting unless explicitly needed |
| `DATE` | TIMESTAMP | Date the job was posted |
| `SOURCE_LINK` | TEXT | Direct URL to the job posting |
| `SOURCE_NAME` | TEXT | Source platform (always `"LinkedIn Jobs"`) |
| `CREATED_AT` | TIMESTAMP | When Onfire ingested this record — not the post date |
| `LAST_RUN_AT` | TIMESTAMP | When Onfire last refreshed this record — not the post date |
| `DELETED_AT` | TIMESTAMP | Soft-delete marker — **always filter `IS NULL`** |
| `PAYLOAD` | VARIANT | Reserved — typically null |

### `PERSON_SENIORITY` values (hiring manager's level)
`seniority_executive`, `seniority_director`, `seniority_manager`,
`seniority_teamlead`, `seniority_senior`, `seniority_mid`, `seniority_junior`

### `JOB_POST_SENIORITY` values (level of the open role)
`"Entry level"`, `"Associate"`, `"Mid-Senior level"`, `"Director"`, `"Executive"`, `"Internship"`

### Key distinction: `PERSON_*` vs `JOB_POST_*`

| Field group | What it describes |
|---|---|
| `PERSON_JOB_TITLE`, `PERSON_SENIORITY` | The **hiring manager** — who you want to talk to |
| `JOB_POST_JOB_TITLE`, `JOB_POST_SENIORITY` | The **open role** — what they're expanding |

A `seniority_director` posting a `"Mid-Senior level"` role = a director-level buyer expanding their team.
Filter on `PERSON_SENIORITY` to target buyers; filter on `JOB_POST_SENIORITY` to understand what they're building.

## Required WHERE clause

```sql
WHERE deleted_at IS NULL
```

## SQL templates

### What is a company actively hiring for?
```sql
SELECT
    JOB_POST_JOB_TITLE,
    JOB_POST_SENIORITY,
    NAME                AS hiring_manager,
    PERSON_JOB_TITLE,
    PERSON_SENIORITY,
    CONTACT_LINKEDIN_URL,
    SHORT_SUMMARY,
    DATE,
    SOURCE_LINK
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND COMPANY_LINKEDIN_URL ILIKE '%/company/capital-one%'
ORDER BY DATE DESC NULLS LAST
LIMIT 50
```

### Find roles by keyword (title or job post text)
```sql
SELECT
    COMPANY_NAME,
    COMPANY_LINKEDIN_URL,
    JOB_POST_JOB_TITLE,
    JOB_POST_SENIORITY,
    NAME                AS hiring_manager,
    PERSON_JOB_TITLE,
    PERSON_SENIORITY,
    CONTACT_LINKEDIN_URL,
    DATE,
    SOURCE_LINK
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND (
      JOB_POST_JOB_TITLE ILIKE '%kubernetes%'
   OR PERSONA_INSIGHTS   ILIKE '%kubernetes%'
  )
ORDER BY DATE DESC NULLS LAST
LIMIT 100
```

### Target accounts hiring for a technology — who is doing the hiring?
```sql
SELECT
    COMPANY_NAME,
    NAME                AS hiring_manager,
    PERSON_JOB_TITLE,
    PERSON_SENIORITY,
    CONTACT_LINKEDIN_URL,
    JOB_POST_JOB_TITLE,
    DATE
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND COMPANY_LINKEDIN_URL IN (
      'https://www.linkedin.com/company/stripe',
      'https://www.linkedin.com/company/twilio',
      'https://www.linkedin.com/company/datadog'
  )
  AND (
      JOB_POST_JOB_TITLE ILIKE '%security%'
   OR PERSONA_INSIGHTS   ILIKE '%security%'
  )
ORDER BY DATE DESC NULLS LAST
LIMIT 100
```

### Senior buyers (director+) at target accounts — budget owners expanding their team
```sql
SELECT
    COMPANY_NAME,
    NAME                AS hiring_manager,
    PERSON_JOB_TITLE,
    PERSON_SENIORITY,
    CONTACT_LINKEDIN_URL,
    JOB_POST_JOB_TITLE,
    PERSONA_INSIGHTS,
    DATE
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND PERSON_SENIORITY IN ('seniority_executive', 'seniority_director')
  AND COMPANY_LINKEDIN_URL ILIKE '%/company/cisco%'
ORDER BY DATE DESC NULLS LAST
LIMIT 50
```

### Unique hiring managers at an account (one row per person, not per job post)
```sql
SELECT
    NAME                AS hiring_manager,
    PERSON_JOB_TITLE,
    PERSON_SENIORITY,
    CONTACT_LINKEDIN_URL,
    COUNT(*)            AS roles_posted,
    MAX(DATE)           AS most_recent_post
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND COMPANY_LINKEDIN_URL ILIKE '%/company/cisco%'
GROUP BY NAME, PERSON_JOB_TITLE, PERSON_SENIORITY, CONTACT_LINKEDIN_URL
ORDER BY roles_posted DESC, most_recent_post DESC
LIMIT 30
```

### Hiring volume as a growth signal — which accounts are expanding fastest?
```sql
SELECT
    COMPANY_NAME,
    COMPANY_LINKEDIN_URL,
    COUNT(*) AS open_roles
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND COMPANY_LINKEDIN_URL IN (
      'https://www.linkedin.com/company/stripe',
      'https://www.linkedin.com/company/twilio',
      'https://www.linkedin.com/company/datadog'
  )
  AND DATE >= DATEADD(day, -30, CURRENT_DATE())
GROUP BY COMPANY_NAME, COMPANY_LINKEDIN_URL
ORDER BY open_roles DESC
LIMIT 20
```

### Rank accounts by number of senior hiring managers active recently
```sql
SELECT
    COMPANY_NAME,
    COMPANY_LINKEDIN_URL,
    COUNT(DISTINCT CONTACT_LINKEDIN_URL) AS senior_hiring_managers
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND PERSON_SENIORITY IN ('seniority_executive', 'seniority_director', 'seniority_manager')
  AND DATE >= DATEADD(day, -90, CURRENT_DATE())
GROUP BY COMPANY_NAME, COMPANY_LINKEDIN_URL
ORDER BY senior_hiring_managers DESC
LIMIT 25
```

### Recent postings in a date window
```sql
SELECT
    COMPANY_NAME,
    JOB_POST_JOB_TITLE,
    JOB_POST_SENIORITY,
    NAME                AS hiring_manager,
    CONTACT_LINKEDIN_URL,
    DATE,
    SOURCE_LINK
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND DATE >= DATEADD(day, -14, CURRENT_DATE())
  AND (
      JOB_POST_JOB_TITLE ILIKE '%devops%'
   OR JOB_POST_JOB_TITLE ILIKE '%platform engineer%'
  )
ORDER BY DATE DESC
LIMIT 200
```

### Technology-specific hiring — use PERSONA_INSIGHTS for fuzzy tech matching
```sql
SELECT
    COMPANY_NAME,
    COMPANY_LINKEDIN_URL,
    JOB_POST_JOB_TITLE,
    PERSONA_INSIGHTS,
    NAME                AS hiring_manager,
    PERSON_JOB_TITLE,
    PERSON_SENIORITY,
    CONTACT_LINKEDIN_URL,
    DATE
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE deleted_at IS NULL
  AND PERSONA_INSIGHTS ILIKE '%crowdstrike%'
ORDER BY DATE DESC NULLS LAST
LIMIT 100
```

## Follow-up: enrich hiring managers with email / phone

Once you have `CONTACT_LINKEDIN_URL` values, pass them to `contact_data_enrichment`
to get verified emails and phone numbers. Use the two-phase consent flow for > 10 contacts.

```
contact_data_enrichment(
    contacts=[...rows from query_onfire...],
    linkedin_url_column="contact_linkedin_url",
    account_website_column="company_linkedin_url",
    person_name_column="hiring_manager",
    include_email=True,
    include_phone=True
)
```

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Lead the table with: `JOB_POST_JOB_TITLE`, `COMPANY_NAME`, `DATE`, `hiring_manager`, `PERSON_SENIORITY`, `CONTACT_LINKEDIN_URL`.
2. State `total_count`; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only director-level", "group by company", "last 7 days only") → use `query_datasets` on the `dataset_id` — **do not re-run** `query_onfire`.

## Reading the signals

- **`CONTACT_LINKEDIN_URL`** is the hiring manager's personal LinkedIn — the warm outreach target.
- **`PERSON_SENIORITY = seniority_executive / seniority_director`** = economic buyer who almost certainly owns budget.
- **`PERSON_SENIORITY = seniority_teamlead / seniority_senior`** = technical champion — influential but may not own budget; good for bottom-up motion.
- **Multiple roles posted by the same person** (use the deduplication template) = actively building a team — high-urgency contact.
- **`PERSONA_INSIGHTS`** is your tech filter proxy — parsed from the full job text, so it captures technologies mentioned anywhere in the description, not just the title.
- **`SHORT_SUMMARY`** gives a concise human-readable description; show this instead of `JOB_POST_TEXT` unless the user explicitly asks for the full description.
- **High hiring volume** at an account = active expansion = budget signal. Use the volume template to rank accounts.

## Common pitfalls

- **`DELETED_AT IS NULL`** — always include.
- **`CREATED_AT` / `LAST_RUN_AT` are NOT the post date** — they reflect when Onfire ingested/refreshed the record. Use `DATE` for when the job was posted.
- **`PERSONA_INSIGHTS` is plain text**, not an array — use `ILIKE '%keyword%'`, not `ARRAY_CONTAINS`.
- **`CONTACT_LINKEDIN_URL` is not unique per company** — the same person can post multiple roles. Use the deduplication template (`GROUP BY CONTACT_LINKEDIN_URL`) when you want a headcount of people, not posts.
- **`DATE` is a TIMESTAMP** — use `DATEADD(day, -N, CURRENT_DATE())` for relative date windows.
- **`NAME` is lowercase** — use it for display only. Match people by `CONTACT_LINKEDIN_URL`, not `NAME`.
- **`JOB_POST_TEXT` is very long** — avoid selecting it by default; use `SHORT_SUMMARY` and `PERSONA_INSIGHTS` for summaries.
- **Re-running for follow-ups** — slice the existing dataset with `query_datasets`.
