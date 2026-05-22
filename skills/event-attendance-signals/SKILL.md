---
name: event-attendance-signals
description: Find people who attended conferences, summits, webinars, or industry events using the `query_onfire` tool against ONFIRE.EVENTS_CONTACTS. Use when the user wants to know who went to a specific event, find attendees from a target company, discover which events a person attended, or filter prospects by event participation — phrases like "who attended Dreamforce 2025", "find people from Salesforce at RSA", "which events did people from our target accounts go to", "show me Gartner IT Symposium attendees", or any event attendance lookup.
---

# event-attendance-signals

SQL lookup against `ONFIRE.EVENTS_CONTACTS` via `query_onfire`. This
table records every tracked event attendance signal — who attended which
conference or industry gathering, their employer, and their location.

## When to use this

- "Who attended Dreamforce 2025?"
- "Find all Defcon 33 attendees from US-based companies"
- "Which events did people from Capital One go to?"
- "Show me every event a list of LinkedIn profiles attended"
- "Who from Germany was at the NabShow?"
- Any question about conference attendance or event participation

Skip this for:
- GitHub star/fork activity → use `github-repo-signals`
- Community membership (Slack/Discord/Reddit) → use `community-join-signals`
- People search by current job title / company → use `entity-people-search`

## Table structure

### Key columns

| Column | Type | Notes |
|--------|------|-------|
| `INSIGHT_ID` | TEXT | Unique row ID |
| `COMPANY_LINKEDIN_URL` | TEXT | Employer's LinkedIn URL at time of event |
| `COMPANY_LINKEDIN_ID` | NUMBER | Numeric company ID |
| `COMPANY_WEBSITE` | TEXT | Employer's website |
| `INSIGHT_NAME` | TEXT | Event name, always prefixed `Event - ` (e.g. `"Event - Dreamforce 2025"`) |
| `CONTACT_LINKEDIN_URL` | TEXT | Attendee's LinkedIn URL |
| `CONTACT_LINKEDIN_ID` | NUMBER | Numeric person ID |
| `CONTACT_COUNTRY` | TEXT | Lowercase country (e.g. `"united states"`) |
| `CONTACT_REGION` | TEXT | State/province (e.g. `"georgia"`) |
| `NUM_VALUE` | NUMBER | Always `1` — presence signal |
| `STR_VALUE` | TEXT | Usually NULL |
| `ACTIVE_EMPLOYMENT` | BOOLEAN | Whether the person was actively employed at this company at the time |
| `CREATED_AT` | TIMESTAMP | When the record was created |
| `UPDATED_AT` | TIMESTAMP | When the record was last updated |
| `DELETED_AT` | TIMESTAMP | Always filter `IS NULL` |

## Required WHERE clause

**Always include:**
```sql
WHERE deleted_at IS NULL
```

## SQL templates

### Who attended a specific event?
```sql
SELECT
    contact_linkedin_url,
    company_linkedin_url,
    company_website,
    contact_country,
    contact_region,
    insight_name
FROM ONFIRE.EVENTS_CONTACTS
WHERE deleted_at IS NULL
  AND insight_name ILIKE '%Dreamforce 2025%'
ORDER BY company_website NULLS LAST
LIMIT 500
```

### All events attended by people from a specific company
```sql
SELECT
    contact_linkedin_url,
    insight_name,
    contact_country,
    active_employment
FROM ONFIRE.EVENTS_CONTACTS
WHERE deleted_at IS NULL
  AND company_linkedin_url ILIKE '%/company/capital-one%'
ORDER BY insight_name
LIMIT 200
```

### Did specific people attend any events?
```sql
SELECT
    contact_linkedin_url,
    insight_name,
    company_website,
    contact_country
FROM ONFIRE.EVENTS_CONTACTS
WHERE deleted_at IS NULL
  AND contact_linkedin_url IN (
      'https://www.linkedin.com/in/alice-smith',
      'https://www.linkedin.com/in/bob-jones'
  )
ORDER BY insight_name
LIMIT 200
```

### Which events had the most attendees from a country?
```sql
SELECT
    insight_name,
    COUNT(DISTINCT contact_linkedin_url) AS unique_attendees
FROM ONFIRE.EVENTS_CONTACTS
WHERE deleted_at IS NULL
  AND LOWER(contact_country) = 'germany'
GROUP BY insight_name
ORDER BY unique_attendees DESC
LIMIT 30
```

### Which events attracted the most attendees from a set of target companies?
```sql
SELECT
    insight_name,
    COUNT(DISTINCT contact_linkedin_url) AS unique_attendees,
    COUNT(DISTINCT company_linkedin_url) AS unique_companies
FROM ONFIRE.EVENTS_CONTACTS
WHERE deleted_at IS NULL
  AND company_linkedin_url IN (
      'https://www.linkedin.com/company/stripe',
      'https://www.linkedin.com/company/twilio',
      'https://www.linkedin.com/company/datadog'
  )
GROUP BY insight_name
ORDER BY unique_attendees DESC
LIMIT 20
```

### Attendees from a region at a security-related event
```sql
SELECT
    contact_linkedin_url,
    company_linkedin_url,
    company_website,
    contact_region
FROM ONFIRE.EVENTS_CONTACTS
WHERE deleted_at IS NULL
  AND insight_name ILIKE '%RSA%'
  AND LOWER(contact_country) = 'united states'
  AND LOWER(contact_region) = 'california'
ORDER BY company_website NULLS LAST
LIMIT 200
```

## Output handling

`query_onfire` returns `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` as a table.
2. State `total_count`; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only active employees", "group by event", "who appears most") →
   use `query_datasets` against the `dataset_id` — **do not re-run** `query_onfire`.

## Common pitfalls

- **`INSIGHT_NAME` is always prefixed `Event - `** — e.g. `"Event - Dreamforce 2025"`. Use `ILIKE '%Dreamforce%'` for fuzzy matching; don't expect the bare event name.
- **`CONTACT_COUNTRY` is lowercase** — use `"united states"` not `"United States"`. Apply `LOWER()` when comparing.
- **`DELETED_AT IS NULL`** — always include this filter.
- **Re-running for follow-ups** — slice the existing dataset with `query_datasets`.
