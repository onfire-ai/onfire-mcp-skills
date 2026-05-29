---
name: community-join-signals
description: Find people who joined specific online communities (Slack workspaces, Discord servers, Reddit communities, LinkedIn groups, GitHub orgs) using the `query_onfire` tool against ONFIRE.EVIDENCES. Use when the user asks who joined a community, who is a member of a specific Slack/Discord/Reddit/LinkedIn group, or wants to find community presence signals for accounts or individuals — phrases like "who joined the Artifex Slack", "members of the DevSecOps Discord", "find everyone from Northwind who's in any Kubernetes community", "who joined any security Slack since January", or any community-membership lookup.
---

# community-join-signals

SQL lookup against `ONFIRE.EVIDENCES` (evidence_type_id = 7) via
`query_onfire`. This table captures every recorded community-join event —
person joins Slack workspace, Discord server, Reddit community, LinkedIn
group, or GitHub org. It's the primary source for community intent signals.

## When to use this

- "Who joined the Artifex Slack?"
- "Members of the Keep Security Discord"
- "Find everyone from Meridian Bank who's in any DevSecOps community"
- "Who from Northwind joined any GitHub org related to Kubernetes?"
- "Show me LinkedIn group members for BigQuery"
- Any question asking about community membership or join events

Skip this for:
- Sentiment *within* community messages → use `community-messages-sentiment`
- People search by job title / company → use `entity-people-search`

## Table structure

The `EVIDENCES` table has structured columns plus a `PAYLOAD` variant
(JSON object). Community join records use `evidence_type_id = 7`.

### Structured columns

| Column | Type | Notes |
|--------|------|-------|
| `EVIDENCE_ID` | TEXT | Unique event ID |
| `PERSON_LINKEDIN_URL` | TEXT | Person who joined |
| `COMPANY_LINKEDIN_URL` | TEXT | Their employer at time of join |
| `START_DATE` | DATE | Date they joined |
| `EVIDENCE_TYPE_ID` | NUMBER | Always 7 for community joins |
| `DELETED_AT` | TEXT | Always filter `IS NULL` |

### PAYLOAD fields (Snowflake variant — use `::VARCHAR` cast)

| Field | How to access | Example values |
|-------|---------------|----------------|
| Community name | `PAYLOAD:COMMUNITY_NAME::VARCHAR` | "Artifex Slack", "DevSecOps Community" |
| Platform type | `PAYLOAD:COMMUNITY_TYPE::VARCHAR` | "Slack", "Discord", "Github", "Linkedin", "Reddit" |
| Community URL | `PAYLOAD:COMMUNITY_URL::VARCHAR` | "https://artifex.slack.com" |
| Member ID | `PAYLOAD:MEMBER_ID::VARCHAR` | Platform-native member identifier |
| Join timestamp | `PAYLOAD:TIMESTAMP::VARCHAR` | ISO timestamp of join |

## Required WHERE clause

**Always include both:**
```sql
WHERE evidence_type_id = 7
  AND deleted_at IS NULL
```

## SQL templates

### Who joined a community by name
```sql
SELECT
    person_linkedin_url,
    company_linkedin_url,
    start_date,
    PAYLOAD:COMMUNITY_NAME::VARCHAR   AS community_name,
    PAYLOAD:COMMUNITY_TYPE::VARCHAR   AS community_type,
    PAYLOAD:COMMUNITY_URL::VARCHAR    AS community_url
FROM ONFIRE.EVIDENCES
WHERE evidence_type_id = 7
  AND deleted_at IS NULL
  AND PAYLOAD:COMMUNITY_NAME::VARCHAR ILIKE '%artifex%'
ORDER BY start_date DESC NULLS LAST
LIMIT 500
```

### Filter by platform (e.g. Slack only)
```sql
SELECT
    person_linkedin_url,
    company_linkedin_url,
    start_date,
    PAYLOAD:COMMUNITY_NAME::VARCHAR   AS community_name,
    PAYLOAD:COMMUNITY_URL::VARCHAR    AS community_url
FROM ONFIRE.EVIDENCES
WHERE evidence_type_id = 7
  AND deleted_at IS NULL
  AND PAYLOAD:COMMUNITY_TYPE::VARCHAR = 'Slack'
  AND PAYLOAD:COMMUNITY_NAME::VARCHAR ILIKE '%security%'
ORDER BY start_date DESC NULLS LAST
LIMIT 500
```

### Filter by company (who from employer X joined any community)
```sql
SELECT
    person_linkedin_url,
    start_date,
    PAYLOAD:COMMUNITY_NAME::VARCHAR   AS community_name,
    PAYLOAD:COMMUNITY_TYPE::VARCHAR   AS community_type
FROM ONFIRE.EVIDENCES
WHERE evidence_type_id = 7
  AND deleted_at IS NULL
  AND company_linkedin_url ILIKE '%/company/meridian-bank%'
ORDER BY start_date DESC NULLS LAST
LIMIT 200
```

### Filter by person list (did specific people join?)
```sql
SELECT
    person_linkedin_url,
    start_date,
    PAYLOAD:COMMUNITY_NAME::VARCHAR   AS community_name,
    PAYLOAD:COMMUNITY_TYPE::VARCHAR   AS community_type
FROM ONFIRE.EVIDENCES
WHERE evidence_type_id = 7
  AND deleted_at IS NULL
  AND person_linkedin_url IN (
      'https://www.linkedin.com/in/alice-smith',
      'https://www.linkedin.com/in/bob-jones'
  )
LIMIT 100
```

### Date-bounded (joins since a specific date)
```sql
SELECT
    person_linkedin_url,
    company_linkedin_url,
    start_date,
    PAYLOAD:COMMUNITY_NAME::VARCHAR   AS community_name,
    PAYLOAD:COMMUNITY_TYPE::VARCHAR   AS community_type
FROM ONFIRE.EVIDENCES
WHERE evidence_type_id = 7
  AND deleted_at IS NULL
  AND PAYLOAD:COMMUNITY_NAME::VARCHAR ILIKE '%kubernetes%'
  AND start_date >= '2025-01-01'
ORDER BY start_date DESC
LIMIT 500
```

### Community breakdown — which communities has a company's employees joined?
```sql
SELECT
    PAYLOAD:COMMUNITY_NAME::VARCHAR   AS community_name,
    PAYLOAD:COMMUNITY_TYPE::VARCHAR   AS community_type,
    PAYLOAD:COMMUNITY_URL::VARCHAR    AS community_url,
    COUNT(DISTINCT person_linkedin_url) AS member_count
FROM ONFIRE.EVIDENCES
WHERE evidence_type_id = 7
  AND deleted_at IS NULL
  AND company_linkedin_url ILIKE '%/company/northwind%'
GROUP BY 1, 2, 3
ORDER BY member_count DESC
LIMIT 30
```

Note: the GROUP BY version is allowed because it has a meaningful business
dimension (community breakdown per company), unlike a bare `COUNT(*)`.

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` as a table.
2. State `total_count`. Offer `download_dataset` for the full CSV.
3. Common follow-ups are answerable from the dataset via `query_datasets`:
   - "Show me only the Discord joins" → `WHERE community_type = 'Discord'`
   - "Who joined most recently?" → `ORDER BY start_date DESC LIMIT 10`
   - "Which people appear in multiple communities?" → `GROUP BY person_linkedin_url HAVING COUNT(*) > 1`

## Common pitfalls

- **Forgetting `evidence_type_id = 7`** — without this you'd mix in all evidence types (job changes, etc.).
- **PAYLOAD fields without cast** — `PAYLOAD:COMMUNITY_NAME` alone returns a VARIANT. Always cast: `::VARCHAR`.
- **Case-sensitive platform type values** — use exact case: "Slack", "Discord", "Github", "Linkedin", "Reddit".
- **Re-running for follow-up slices** — use `query_datasets` on the existing `dataset_id`.
