---
name: title-movement
description: >
  Detect month-by-month title movement (new hires and departures by job title) at any target company using `ONFIRE.PEOPLE_EXPERIENCES` via `query_onfire`.

  Use this skill whenever the user asks about:
  - "title movement" or "role movement" at a company
  - "new titles at [company]" or "what titles are they adding"
  - "titles that left [company]" or "what roles are disappearing"
  - "hiring signals for [company]" based on title patterns
  - "title changes at [company]" or "what roles are growing / shrinking"
  - detecting org changes, headcount shifts, or leadership gaps at a company
  - any question combining a company name with tracking who joined or left by title

  Trigger even if the user just pastes a LinkedIn company URL and asks "what's happening there?" or "show me movement." Works for any company — just needs a `company_linkedin_url` slug.
compatibility:
  tools:
    - query_onfire
---

# Title Movement Skill

Detect which job titles are newly entering or permanently leaving a company, month by month. Data source: `ONFIRE.PEOPLE_EXPERIENCES` via `query_onfire`.

---

## Step 1 — Parse inputs

| Parameter | Default | Notes |
|---|---|---|
| `company_linkedin_url` | **required** | e.g. `linkedin.com/company/mondaydotcom`. Infer slug from company name if needed (e.g. "Salesforce" → `linkedin.com/company/salesforce`). State the inferred URL explicitly. |
| `start_date` | 12 months ago | Convert natural language: "2 years" → 24 months ago, "since Jan 2024" → `2024-01-01`, "6 months" → 6 months ago. Format: `YYYY-MM-DD`. |
| `title_filter` | none | Translate "only engineering titles" or "titles with manager" to SQL: `AND LOWER(TITLE_NAME) ILIKE '%engineer%'`. Multiple keywords → `AND (LOWER(TITLE_NAME) ILIKE '%kw1%' OR LOWER(TITLE_NAME) ILIKE '%kw2%')`. |
| `show_all` | false | Default: only rows where `title_new_to_company = TRUE` OR `title_gone_from_company = TRUE`. If user says "show everything" or "all movement", remove the signal filter. |

---

## Step 2 — Run the SQL

```sql
WITH exp AS (
  SELECT
    PERSON_LINKEDIN_ID,
    LOWER(TRIM(TITLE_NAME)) AS title,
    TRY_TO_DATE(START_DATE || '-01') AS start_dt,
    TRY_TO_DATE(END_DATE   || '-01') AS end_dt
  FROM ONFIRE.PEOPLE_EXPERIENCES
  WHERE company_linkedin_url = '<company_linkedin_url>'
    AND TITLE_NAME IS NOT NULL
    AND START_DATE IS NOT NULL
    /* optional title filter: AND LOWER(TITLE_NAME) ILIKE '%<keyword>%' */
),
title_stats AS (
  /* No date filter here — so first_ever_start reflects true company history */
  SELECT
    title,
    MIN(start_dt)            AS first_ever_start,
    COUNT_IF(end_dt IS NULL) AS currently_active
  FROM exp
  GROUP BY 1
),
joins AS (
  SELECT
    DATE_TRUNC('month', e.start_dt) AS month,
    e.title,
    COUNT(DISTINCT e.PERSON_LINKEDIN_ID)                               AS n_joiners,
    BOOLOR_AGG(ts.first_ever_start = DATE_TRUNC('month', e.start_dt)) AS title_new_to_company
  FROM exp e JOIN title_stats ts USING (title)
  WHERE e.start_dt >= '<start_date>'::date
  GROUP BY 1, 2
),
leaves AS (
  SELECT
    DATE_TRUNC('month', e.end_dt) AS month,
    e.title,
    COUNT(DISTINCT e.PERSON_LINKEDIN_ID)       AS n_leavers,
    BOOLOR_AGG(ts.currently_active = 0)        AS title_gone_from_company
  FROM exp e JOIN title_stats ts USING (title)
  WHERE e.end_dt IS NOT NULL
    AND e.end_dt >= '<start_date>'::date
  GROUP BY 1, 2
)
SELECT
  COALESCE(j.month, l.month)                 AS month,
  COALESCE(j.title, l.title)                 AS title,
  COALESCE(j.n_joiners, 0)                   AS joiners,
  COALESCE(l.n_leavers, 0)                   AS leavers,
  COALESCE(j.title_new_to_company,    FALSE) AS title_new_to_company,
  COALESCE(l.title_gone_from_company, FALSE) AS title_gone_from_company
FROM joins j
FULL OUTER JOIN leaves l ON l.month = j.month AND l.title = j.title
/* show_all=false → */ WHERE COALESCE(j.title_new_to_company, FALSE) OR COALESCE(l.title_gone_from_company, FALSE)
/* show_all=true  → remove the WHERE clause above */
ORDER BY month DESC, joiners + leavers DESC
```

**Two flag definitions worth knowing:**
- `title_new_to_company` — this is the *first ever month* anyone at the company held this title. Computed against full company history regardless of the date window.
- `title_gone_from_company` — current snapshot: nobody at the company currently holds this title (end_dt is not null for all). Not a point-in-time calculation for historical months.

---

## Step 3 — Format the output

### Summary line (always first)
```
📊 **[Company name]** · [N] months · 🟢 [X] new titles · 🔴 [Y] titles gone
```
If `show_all=true`, append: ` · [Z] total move events`

### Table (grouped by month, most recent first)

| Month | Title | Joiners | Leavers | Signal |
|---|---|---|---|---|
| 2026-02 | 🟢 distribution manager, latam | 1 | 0 | **new to company** |
| 2026-02 | 🔴 head of marketing | 0 | 1 | **title now gone** |
| 2026-02 | software engineer | 2 | 1 | *(only if show_all=true)* |

**Signal rules:**
- `title_new_to_company = TRUE` → 🟢 prefix + Signal = **new to company**
- `title_gone_from_company = TRUE` → 🔴 prefix + Signal = **title now gone**
- Both false → no emoji, blank Signal (only shown when `show_all=true`)

### No results
If the query returns 0 rows, say:
> "No title movement found for `[url]` in this window. The LinkedIn URL slug may not match — try a variant (e.g. `linkedin.com/company/salesforce` vs `linkedin.com/company/salesforcecom`)."

---

## Edge cases

- **Inferred URL**: state it — *"Using `linkedin.com/company/salesforce` — correct me if wrong."*
- **Title noise**: spelling variants (`mid-market solution engineer` vs `mid-market solutions engineer`) appear as separate rows. Mention if prominent.
- **Future-dated END_DATE**: occasional data artifact. Note if it affects results.
- **Large result sets** (>150 rows with `show_all=true`): suggest narrowing by title filter or date range.
