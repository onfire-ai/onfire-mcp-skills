---
name: github-repo-signals
description: Find people who starred or forked GitHub repositories using the `query_onfire` tool against GOLD.EVIDENCES.EVIDENCES (evidence_type_id = 6). Use when the user wants to know who interacted with a GitHub repo, find developers who starred repos related to a technology or vendor, or check if people from a specific company engaged with a repo — phrases like "who starred any JFrog repo", "engineers who forked a Kubernetes repo", "did anyone from Stripe interact with our GitHub", "find developers in India interested in open-source security tools", or any GitHub repo engagement lookup.
---

# github-repo-signals

SQL lookup against `GOLD.EVIDENCES.EVIDENCES` (evidence_type_id = 6) via
`query_onfire`. This table captures every recorded GitHub star/fork event —
who interacted with a repo, their job title, company, and location at the
time of the interaction.

## When to use this

- "Who starred any repo with 'sonatype' in the name?"
- "Find DevOps engineers who forked Kubernetes repos"
- "Did anyone from Capital One interact with any of our GitHub repos?"
- "Who in Germany starred a security-related repo this year?"
- "Show me all GitHub activity from these LinkedIn URLs"
- Any question about who engaged with GitHub repos

Skip this for:
- Community membership (Slack/Discord/Reddit joins) → use `community-join-signals`
- People search by current job title / company → use `entity-people-search`

## Table structure

Same `EVIDENCES` table as community-join-signals, different `evidence_type_id`.

### Structured columns

| Column | Type | Notes |
|--------|------|-------|
| `EVIDENCE_ID` | TEXT | Unique event ID |
| `PERSON_LINKEDIN_URL` | TEXT | Person who starred/forked |
| `COMPANY_LINKEDIN_URL` | TEXT | Their employer at time of activity |
| `START_DATE` | DATE | Date of the GitHub interaction |
| `EVIDENCE_TYPE_ID` | NUMBER | Always **6** for GitHub activity |
| `DELETED_AT` | TEXT | Always filter `IS NULL` |

### PAYLOAD fields (use `::VARCHAR` cast)

| Field | How to access | Notes |
|-------|---------------|-------|
| Repo name | `PAYLOAD:REPO_NAME::VARCHAR` | e.g. "sonatype/nexus-public" |
| Job title | `PAYLOAD:JOB_TITLE::VARCHAR` | Title at time of activity |
| Company name | `PAYLOAD:JOB_COMPANY_NAME::VARCHAR` | Employer at time of activity |
| Country | `PAYLOAD:LOCATION_COUNTRY::VARCHAR` | Lowercase, e.g. "india" |
| Region | `PAYLOAD:LOCATION_REGION::VARCHAR` | State/province |
| Locality | `PAYLOAD:LOCATION_LOCALITY::VARCHAR` | City |
| Continent | `PAYLOAD:LOCATION_CONTINENT::VARCHAR` | e.g. "asia" |

## Required WHERE clause

**Always include both:**
```sql
WHERE evidence_type_id = 6
  AND deleted_at IS NULL
```

## SQL templates

### Who interacted with repos by a vendor
```sql
SELECT
    person_linkedin_url,
    company_linkedin_url,
    start_date,
    PAYLOAD:REPO_NAME::VARCHAR         AS repo_name,
    PAYLOAD:JOB_TITLE::VARCHAR         AS job_title,
    PAYLOAD:JOB_COMPANY_NAME::VARCHAR  AS job_company_name,
    PAYLOAD:LOCATION_COUNTRY::VARCHAR  AS location_country
FROM GOLD.EVIDENCES.EVIDENCES
WHERE evidence_type_id = 6
  AND deleted_at IS NULL
  AND PAYLOAD:REPO_NAME::VARCHAR ILIKE '%sonatype%'
ORDER BY start_date DESC NULLS LAST
LIMIT 500
```

### Filter by job title (find engineers who starred a repo)
```sql
SELECT
    person_linkedin_url,
    company_linkedin_url,
    start_date,
    PAYLOAD:REPO_NAME::VARCHAR         AS repo_name,
    PAYLOAD:JOB_TITLE::VARCHAR         AS job_title,
    PAYLOAD:LOCATION_COUNTRY::VARCHAR  AS location_country
FROM GOLD.EVIDENCES.EVIDENCES
WHERE evidence_type_id = 6
  AND deleted_at IS NULL
  AND PAYLOAD:REPO_NAME::VARCHAR ILIKE '%kubernetes%'
  AND PAYLOAD:JOB_TITLE::VARCHAR ILIKE '%devops%'
ORDER BY start_date DESC NULLS LAST
LIMIT 200
```

### Did anyone from a specific company interact with our repos?
```sql
SELECT
    person_linkedin_url,
    start_date,
    PAYLOAD:REPO_NAME::VARCHAR         AS repo_name,
    PAYLOAD:JOB_TITLE::VARCHAR         AS job_title
FROM GOLD.EVIDENCES.EVIDENCES
WHERE evidence_type_id = 6
  AND deleted_at IS NULL
  AND company_linkedin_url ILIKE '%/company/capital-one%'
ORDER BY start_date DESC NULLS LAST
LIMIT 200
```

### Filter by country
```sql
SELECT
    person_linkedin_url,
    company_linkedin_url,
    start_date,
    PAYLOAD:REPO_NAME::VARCHAR         AS repo_name,
    PAYLOAD:JOB_TITLE::VARCHAR         AS job_title,
    PAYLOAD:JOB_COMPANY_NAME::VARCHAR  AS job_company_name
FROM GOLD.EVIDENCES.EVIDENCES
WHERE evidence_type_id = 6
  AND deleted_at IS NULL
  AND PAYLOAD:REPO_NAME::VARCHAR ILIKE '%security%'
  AND PAYLOAD:LOCATION_COUNTRY::VARCHAR = 'india'
ORDER BY start_date DESC NULLS LAST
LIMIT 200
```

### Which repos got the most activity from a set of people?
```sql
SELECT
    PAYLOAD:REPO_NAME::VARCHAR         AS repo_name,
    COUNT(DISTINCT person_linkedin_url) AS unique_people
FROM GOLD.EVIDENCES.EVIDENCES
WHERE evidence_type_id = 6
  AND deleted_at IS NULL
  AND person_linkedin_url IN (
      'https://www.linkedin.com/in/alice-smith',
      'https://www.linkedin.com/in/bob-jones'
  )
GROUP BY 1
ORDER BY unique_people DESC
LIMIT 20
```

### Date-bounded activity
```sql
SELECT
    person_linkedin_url,
    company_linkedin_url,
    start_date,
    PAYLOAD:REPO_NAME::VARCHAR         AS repo_name,
    PAYLOAD:JOB_COMPANY_NAME::VARCHAR  AS job_company_name
FROM GOLD.EVIDENCES.EVIDENCES
WHERE evidence_type_id = 6
  AND deleted_at IS NULL
  AND PAYLOAD:REPO_NAME::VARCHAR ILIKE '%jfrog%'
  AND start_date >= '2025-01-01'
ORDER BY start_date DESC
LIMIT 500
```

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` as a table.
2. State `total_count`; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only engineers", "group by repo", "who appears most") →
   use `query_datasets` against the `dataset_id` — **do not re-run** `query_onfire`.

## Common pitfalls

- **Wrong `evidence_type_id`** — GitHub activity is **6**; community joins are 7. Don't mix them.
- **PAYLOAD fields without cast** — always `::VARCHAR`, otherwise you get a VARIANT.
- **`LOCATION_COUNTRY` is lowercase** in PAYLOAD — use lowercase values: `'india'` not `'India'`.
- **Re-running for follow-ups** — slice the existing dataset with `query_datasets`.
