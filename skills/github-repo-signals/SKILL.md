---
name: github-repo-signals
description: Find people who starred or forked GitHub repositories using the `query_onfire` tool against ONFIRE.GITHUB_MEMBERS. Use when the user wants to know who interacted with a GitHub repo, find developers who starred repos related to a technology or vendor, or check if people from a specific company engaged with a repo — phrases like "who starred any JFrog repo", "engineers who forked a Kubernetes repo", "did anyone from Stripe interact with our GitHub", "find developers in India interested in open-source security tools", or any GitHub repo engagement lookup.
---

# github-repo-signals

SQL lookup against `ONFIRE.GITHUB_MEMBERS` via `query_onfire`. This table
captures every recorded GitHub star/fork event — who interacted with a repo,
their name, GitHub profile, and matched LinkedIn URL.

## When to use this

- "Who starred any repo with 'sonatype' in the name?"
- "Find DevOps engineers who forked Kubernetes repos"
- "Did anyone from Capital One interact with any of our GitHub repos?"
- "Show me all GitHub activity from these LinkedIn URLs"
- Any question about who engaged with GitHub repos

Skip this for:
- Community membership (Slack/Discord/Reddit joins) → use `community-join-signals`
- People search by current job title / company → use `entity-people-search`

## Table structure

### Columns

| Column | Type | Notes |
|--------|------|-------|
| `NAME` | TEXT | Person's display name |
| `GITHUB_USERNAME` | TEXT | GitHub handle |
| `GITHUB_REPO_NAME` | TEXT | Repo that was starred/forked (e.g. "aquasecurity/trivy") |
| `GITHUB_ACTIVITY` | TEXT | Activity type: `"star"` or `"fork"` |
| `GITHUB_ACTIVITY_DATE` | TIMESTAMP | **When the star/fork happened** — use this for date filtering |
| `GITHUB_REPO_URL` | TEXT | Full URL of the repo |
| `GITHUB_PROFILE_URL` | TEXT | Full GitHub profile URL |
| `GITHUB_AVATAR_URL` | TEXT | GitHub avatar URL |
| `LINKEDIN_URL` | TEXT | Matched LinkedIn profile URL |
| `CREATED_AT` | TIMESTAMP | When Onfire collected this record |
| `LAST_RUN_AT` | TIMESTAMP | When Onfire last refreshed this record |

> **Never include `LINKEDIN_SOURCE` in SELECT** — always omit it from all queries.

## SQL templates

### Who interacted with repos by a vendor
```sql
SELECT
    name,
    github_username,
    github_repo_name,
    github_activity,
    github_activity_date,
    github_profile_url,
    linkedin_url
FROM ONFIRE.GITHUB_MEMBERS
WHERE github_repo_name ILIKE '%sonatype%'
ORDER BY github_activity_date DESC NULLS LAST
LIMIT 500
```

### Filter by repo name (find who starred a specific repo)
```sql
SELECT
    name,
    github_username,
    github_repo_name,
    github_activity,
    github_activity_date,
    github_profile_url,
    linkedin_url
FROM ONFIRE.GITHUB_MEMBERS
WHERE github_repo_name ILIKE '%trivy%'
  AND github_activity = 'star'
ORDER BY github_activity_date DESC NULLS LAST
LIMIT 200
```

### Filter by LinkedIn URLs (did specific people interact with repos?)
```sql
SELECT
    name,
    github_username,
    github_repo_name,
    github_activity,
    github_activity_date
FROM ONFIRE.GITHUB_MEMBERS
WHERE linkedin_url IN (
    'https://www.linkedin.com/in/alice-smith',
    'https://www.linkedin.com/in/bob-jones'
)
ORDER BY github_activity_date DESC NULLS LAST
LIMIT 200
```

### Date-bounded activity
```sql
SELECT
    name,
    github_username,
    github_repo_name,
    github_activity,
    github_activity_date,
    linkedin_url
FROM ONFIRE.GITHUB_MEMBERS
WHERE github_repo_name ILIKE '%jfrog%'
  AND github_activity_date >= '2025-01-01'
ORDER BY github_activity_date DESC
LIMIT 500
```

### Which repos got the most activity?
```sql
SELECT
    github_repo_name,
    COUNT(DISTINCT github_username) AS unique_people,
    COUNT(*) AS total_events
FROM ONFIRE.GITHUB_MEMBERS
WHERE github_repo_name ILIKE '%kubernetes%'
GROUP BY 1
ORDER BY unique_people DESC
LIMIT 20
```

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` as a table — **never display the `linkedin_source` column**.
2. State `total_count`; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only stars", "group by repo", "who appears most") →
   use `query_datasets` against the `dataset_id` — **do not re-run** `query_onfire`.

## Common pitfalls

- **`linkedin_source` must never appear in output** — always omit from SELECT and from displayed tables.
- **`CREATED_AT` / `LAST_RUN_AT` are NOT the interaction date** — use `GITHUB_ACTIVITY_DATE` for "when did this person star/fork".
- **Re-running for follow-ups** — slice the existing dataset with `query_datasets`.
