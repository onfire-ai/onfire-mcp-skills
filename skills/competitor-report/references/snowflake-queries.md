# Snowflake Queries — Competitor Report

Every query runs through `query_onfire`. All table references use the
3-part `ONFIRE.*` form. Every query filters on `DELETED_AT IS NULL`
where the column exists (see exceptions below).

Template variables:

| Variable | Example | Source |
|---|---|---|
| `{company_linkedin_url}` | `linkedin.com/company/sonatype` | Phase 0 `match_company` |
| `{competitor_name}` | `Sonatype` | Phase 0 user input |
| `{q_start}` | `2026-01-01` | Phase 0 quarter math |
| `{q_end}` | `2026-03-31` | Phase 0 quarter math |
| `{rolling_12mo_start}` | `2025-04-01` | `DATEADD(MONTH, -12, '{q_end}')` |

---

## Query 01 — Headcount trend (12 months)

```sql
SELECT TIME_PERIOD,
       STR_VALUE AS pct_change
FROM ONFIRE.GROWTH_TOTAL_HEADCOUNT_MONTHLY
WHERE LOWER(COMPANY_LINKEDIN_URL) = '{company_linkedin_url}'
  AND DELETED_AT IS NULL
  AND STR_VALUE IS NOT NULL
  AND TIME_PERIOD BETWEEN DATEADD(MONTH, -12, '{q_end}') AND '{q_end}'
ORDER BY TIME_PERIOD
```

**Persists as `ds_headcount`.**

Used in: exec summary "+1.4% Q net" stat, Complication 1B headcount %
bar chart.

---

## Query 02 — Title movement (target quarter only)

```sql
WITH all_holders AS (
  SELECT LOWER(JOB_TITLE) AS title,
         START_DATE,
         END_DATE
  FROM ONFIRE.PEOPLE_EXPERIENCES
  WHERE LOWER(COMPANY_LINKEDIN_URL) = '{company_linkedin_url}'
    AND DELETED_AT IS NULL
    AND START_DATE IS NOT NULL
),
net_new AS (
  SELECT title,
         MIN(START_DATE) AS event_date
  FROM all_holders
  GROUP BY title
  HAVING MIN(START_DATE) BETWEEN '{q_start}' AND '{q_end}'
),
now_gone AS (
  SELECT a.title,
         MAX(a.END_DATE) AS event_date
  FROM all_holders a
  WHERE a.END_DATE IS NOT NULL
  GROUP BY a.title
  HAVING MAX(a.END_DATE) BETWEEN '{q_start}' AND '{q_end}'
     AND NOT EXISTS (
       SELECT 1 FROM all_holders b
       WHERE LOWER(b.title) = a.title
         AND b.END_DATE IS NULL
     )
)
SELECT 'net_new' AS event_type, title, event_date FROM net_new
UNION ALL
SELECT 'now_gone' AS event_type, title, event_date FROM now_gone
ORDER BY event_date
```

**Persists as `ds_title_movement`.**

Two event types:
- `net_new` - title string with no prior holder, first holder started in-quarter
- `now_gone` - existing title where the last remaining holder departed in-quarter

The `NOT EXISTS` clause ensures `now_gone` excludes titles that still
have at least one active holder.

Used in: Complication 1A.

---

## Query 03 — Quarter hires with geo

```sql
SELECT pe.PERSON_LINKEDIN_URL,
       pe.JOB_TITLE,
       pe.START_DATE,
       p.LOCATION_COUNTRY,
       p.LOCATION_NAME
FROM ONFIRE.PEOPLE_EXPERIENCES pe
LEFT JOIN ONFIRE.PEOPLE p
  ON LOWER(p.LINKEDIN_URL) = LOWER(pe.PERSON_LINKEDIN_URL)
  AND p.DELETED_AT IS NULL
WHERE LOWER(pe.COMPANY_LINKEDIN_URL) = '{company_linkedin_url}'
  AND pe.DELETED_AT IS NULL
  AND pe.START_DATE BETWEEN '{q_start}' AND '{q_end}'
  AND pe.END_DATE IS NULL
ORDER BY pe.START_DATE, p.LOCATION_COUNTRY
```

**Persists as `ds_q_hires`.**

Used in: Complication 1B continent breakdown of in-quarter hires.

---

## Query 04 — Open job postings (target quarter)

```sql
SELECT JOB_TITLE,
       HIRING_MANAGER_NAME,
       HIRING_MANAGER_LINKEDIN_URL,
       FIRST_SEEN_DATE,
       JOB_LOCATION,
       JOB_DESCRIPTION
FROM ONFIRE.HIRING_MANAGER_SIGNAL
WHERE LOWER(COMPANY_LINKEDIN_URL) = '{company_linkedin_url}'
  AND FIRST_SEEN_DATE BETWEEN '{q_start}' AND '{q_end}'
ORDER BY FIRST_SEEN_DATE
```

**Persists as `ds_open_jobs`.**

**Pitfall.** `HIRING_MANAGER_SIGNAL` does NOT have a `DELETED_AT`
column. Do not include `DELETED_AT IS NULL` here.

Used in: Complication 1C, grouped by hiring manager.

---

## Query 05 — Persona / department growth

```sql
SELECT TIME_PERIOD,
       INSIGHT_NAME,
       STR_VALUE AS pct_change
FROM ONFIRE.GROWTH_INSIGHT_MONTHLY
WHERE LOWER(COMPANY_LINKEDIN_URL) = '{company_linkedin_url}'
  AND DELETED_AT IS NULL
  AND STR_VALUE IS NOT NULL
  AND INSIGHT_NAME LIKE 'growth-%'
  AND TIME_PERIOD BETWEEN DATEADD(MONTH, -12, '{q_end}') AND '{q_end}'
ORDER BY INSIGHT_NAME, TIME_PERIOD
```

**Persists as `ds_persona`.**

The `INSIGHT_NAME` column is prefixed `growth-` for each tracked
persona, e.g. `growth-Data Engineering`. Used in: Complication 1B
department-by-department callouts.

---

## Query 06 — GitHub footprint

```sql
SELECT e.PERSON_LINKEDIN_URL,
       p.FULL_NAME,
       p.JOB_COMPANY_NAME,
       p.JOB_TITLE,
       p.LOCATION_COUNTRY,
       e.PAYLOAD:REPO_NAME::VARCHAR AS repo_name,
       e.PAYLOAD:REPO_OWNER::VARCHAR AS repo_owner,
       e.PAYLOAD:EVENT_TYPE::VARCHAR AS event_type
FROM ONFIRE.EVIDENCES e
LEFT JOIN ONFIRE.PEOPLE p
  ON LOWER(p.LINKEDIN_URL) = LOWER(e.PERSON_LINKEDIN_URL)
  AND p.DELETED_AT IS NULL
WHERE e.DELETED_AT IS NULL
  AND e.EVIDENCE_TYPE_ID = 6
  AND (
        LOWER(e.PAYLOAD:REPO_OWNER::VARCHAR) ILIKE '%{competitor_name_lc}%'
     OR LOWER(e.PAYLOAD:REPO_NAME::VARCHAR)  ILIKE '%{competitor_name_lc}%'
  )
```

**Persists as `ds_github`.**

Aggregate downstream by country, by employer, by federal-vs-enterprise.

**Critical pitfall.** This table's date columns reflect
**data-collection dates**, not the actual star or fork event timestamps.
The brief must treat this as a footprint snapshot only - never a time
series.

---

## Query 07 — Customer acquisition motion (last 12 months)

### Preferred path — `INSIGHTS_2_EVIDENCES`

```sql
SELECT PERSON_LINKEDIN_URL,
       COMPANY_LINKEDIN_URL,
       MIN(START_DATE) AS first_seen
FROM ONFIRE.INSIGHTS_2_EVIDENCES
WHERE INSIGHT_VALUE = '{competitor_name}'
  AND START_DATE IS NOT NULL
  AND START_DATE BETWEEN DATEADD(MONTH, -12, '{q_end}') AND '{q_end}'
GROUP BY PERSON_LINKEDIN_URL, COMPANY_LINKEDIN_URL
```

**Persists as `ds_acquisition`.**

If `query_onfire` rejects the table (it is gated per-tenant), fall back:

### Fallback path — `PEOPLE` static snapshot

```sql
SELECT LINKEDIN_URL AS person_linkedin_url,
       JOB_COMPANY_LINKEDIN_URL AS company_linkedin_url,
       NULL AS first_seen
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND JOB_COMPANY_LINKEDIN_URL IS NOT NULL
  AND (
        REGEXP_LIKE(LOWER(JOB_SUMMARY),   '\\\\b{competitor_name_lc}\\\\b')
     OR REGEXP_LIKE(LOWER(JOB_TITLE),     '\\\\b{competitor_name_lc}\\\\b')
     OR REGEXP_LIKE(LOWER(HEADLINE),      '\\\\b{competitor_name_lc}\\\\b')
  )
```

When the fallback is used, **flag the brief section explicitly** -
the Customer Acquisition page becomes a Customer Footprint snapshot,
and the Assumptions and Definitions block must say so.

### Alternative path — user-uploaded CSV

If the user uploads a CSV with columns
`person_linkedin_url, company_linkedin_url, first_seen`, use it
directly and skip both Snowflake paths.

---

## Query 08 — Customer firmographics

After `ds_acquisition` is built, pull firmographics for the distinct
companies:

```sql
SELECT LOWER(LINKEDIN_URL) AS linkedin_url,
       NAME,
       INDUSTRY,
       SIZE,
       EMPLOYEE_COUNT,
       LOCATION_COUNTRY,
       LOCATION_NAME
FROM ONFIRE.COMPANIES
WHERE DELETED_AT IS NULL
  AND LOWER(LINKEDIN_URL) IN (
    -- comma-separated list of distinct company_linkedin_url values
    -- from ds_acquisition; batch in groups of 30-50 if the list is large
  )
```

**Persists as `ds_acq_firmo`.**

Batch the `IN` list in groups of 30-50 URLs to keep payloads reasonable.

---

## Query 09 — Sentiment-author resolution

After `community_messages_sentiment` returns `ds_sentiment`, pull the
distinct opinionated external authors:

```sql
-- via query_datasets
SELECT DISTINCT linkedin_url, sender_name, community_name, sentiment_value
FROM s
WHERE sentiment_value IN ('positive', 'negative')
  AND community_name != '{competitor_name}'
  AND message_timestamp >= '{q_start}'
  AND message_timestamp <  DATEADD(DAY, 1, '{q_end}')
  AND linkedin_url IS NOT NULL
```

Then look them up in PEOPLE via query_onfire:

```sql
SELECT LOWER(LINKEDIN_URL) AS linkedin_url,
       JOB_COMPANY_NAME,
       JOB_TITLE,
       LOCATION_COUNTRY,
       LOCATION_NAME
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND LOWER(LINKEDIN_URL) IN (
    -- comma-separated list of opinionated-external author URLs
  )
```

**Persists as `ds_authors_resolved`.**

Tagging in the join:
- `resolved` — `PEOPLE` row exists AND `JOB_COMPANY_NAME IS NOT NULL`
- `unresolved-no-employer` — `PEOPLE` row exists, `JOB_COMPANY_NAME IS NULL`
- `unresolved-no-profile` — `PEOPLE` row does not exist

---

## Query 10 — Modal-country geo fallback

For companies in `ds_acq_firmo` with NULL `LOCATION_COUNTRY`:

```sql
SELECT JOB_COMPANY_NAME,
       JOB_COMPANY_LINKEDIN_URL,
       LOCATION_COUNTRY,
       COUNT(*) AS n_employees
FROM ONFIRE.PEOPLE
WHERE DELETED_AT IS NULL
  AND (
       LOWER(JOB_COMPANY_NAME) IN ( /* list of company names */ )
    OR LOWER(JOB_COMPANY_LINKEDIN_URL) IN ( /* list of company URLs */ )
  )
GROUP BY JOB_COMPANY_NAME, JOB_COMPANY_LINKEDIN_URL, LOCATION_COUNTRY
ORDER BY JOB_COMPANY_NAME, n_employees DESC
```

**Persists as `ds_geo_fallback`.**

Then take the modal `LOCATION_COUNTRY` per company. If no employees
match either, leave the company in the Unresolved bucket (shown muted).

---

## DuckDB join patterns (post-Snowflake)

Once everything is persisted, use `query_datasets` to join. DuckDB
rejects `UNION` and `CTE-named-as-dataset-alias`; keep joins as flat
LEFT JOINs against named dataset aliases.

Example — month-by-month industry rollup:

```sql
-- datasets: {"a": "ds_acquisition", "f": "ds_acq_firmo", "g": "ds_geo_fallback"}
SELECT SUBSTR(MIN(a.first_seen), 1, 7) AS first_seen_month,
       CASE
         WHEN f.industry IN ('computer software','internet') THEN 'Software / internet'
         WHEN f.industry IN ('information technology and services','information services','management consulting') THEN 'IT services / consulting'
         WHEN f.industry IN ('hospital & health care','health, wellness and fitness','research','insurance','banking','financial services','computer & network security','government administration','non-profit organization management','museums and institutions') THEN 'Public / Healthcare / Cyber / Financial'
         WHEN f.industry IN ('media production','broadcast media') THEN 'Media'
         ELSE 'Other'
       END AS industry_bucket,
       COUNT(DISTINCT a.company_linkedin_url) AS n_companies
FROM a
LEFT JOIN f ON a.company_linkedin_url = f.linkedin_url
GROUP BY first_seen_month, industry_bucket
ORDER BY first_seen_month, industry_bucket
```

---

## Read-only stance

Every query in this file is `SELECT`-only. The brief never writes back
to Snowflake. The `query_onfire` tool enforces this.

The skill never calls `contact_data_enrichment` either - the brief is
a competitive-intelligence read, not a contact-enrichment exercise.
