# Warehouse signal queries — Competitor Report

Warehouse pulls run through **`ask_onfire`**, which takes a structured
**QueryIR** (`query={entity, select, filters, insight_filters, joins,
order_by, distinct_by, limit, confirmed}`) — **not** raw SQL. The
removed `query_onfire` raw-SQL-over-`ONFIRE.*`-aliases tool no longer
exists; every recipe below has been ported to a QueryIR shape or, where
the analysis is beyond what ask_onfire can express, replaced with an
explicit "pull rows, compute client-side" note.

Read `account-research/references/ask-onfire-signals.md` for the worked
QueryIR recipe patterns this file mirrors.

**Billing gate.** `ask_onfire` **bills the client 1 credit per row
returned**. Always set a small explicit `limit`. If `limit` is unset (or
exceeds the server's threshold) the call returns `needs_confirmation`
with `stage: "row_budget"` — a free COUNT, nothing billed — so you can
settle the row count with the user and resubmit with `confirmed: true`.
For this brief most slices are full-cohort pulls feeding a downstream
`query_datasets` analysis, so the row budget is the real cohort size:
expect to hit the confirmation gate and confirm deliberately, never
reflexively.

**What ask_onfire cannot express (this brief leans on it heavily):**
GROUP BY distributions beyond a single declared COUNT measure, window
functions, month-over-month / first-ever-across-all-time temporal
cohort logic, multi-field free-text OR-scans, `PAYLOAD:` JSON
extraction, and multi-hop joins. Queries that need any of these (02,
05 in full, 06 owner-match, 07, 10, 13a) are flagged below: pull the
constrained rows with a QueryIR, then do the aggregation/temporal logic
client-side over the pulled dataset (`query_datasets`).

Entity mapping (table → ask_onfire entity): `ONFIRE.PEOPLE` = `contact`;
`ONFIRE.COMPANIES` = `company`; `ONFIRE.PEOPLE_EXPERIENCES` =
`people_experiences`; `ONFIRE.EVENTS_CONTACTS` = `event_contact`;
`ONFIRE.GROWTH_INSIGHT_MONTHLY` = `growth_insight_monthly`;
`ONFIRE.INSIGHTS_2_EVIDENCES` = `insight_evidence`; `ONFIRE.EVIDENCES`
= `evidence`; `ONFIRE.GITHUB_MEMBERS` = `github_member`;
`SILVER.JOB_POST.STG_JOB_POSTS` = `job_post`. **`ONFIRE.PEOPLE_GRAND`
and `ONFIRE.PEOPLE_GRAND_EXPERIENCES` have NO ask_onfire entity** — they
are reachable only through the `get_company_headcount` tool (Query 01);
never attempt to author a QueryIR against them.

Persona / technology / event / evidence-type values are *concepts*, not
literals — `ask_onfire` resolves them server-side (via `resolve_insights`
/ the bound vocabularies); pass the human term or pre-resolve it. Free-
text dimensions (country, industry) are stored lowercased and normalized
server-side; URL dimensions accept any format.

Template variables:

| Variable | Example | Source |
|---|---|---|
| `{company_linkedin_url}` | `linkedin.com/company/nexagon` | Phase 0 `match_company` |
| `{competitor_name}` | `Nexagon` | Phase 0 user input |
| `{q_start}` | `2026-01-01` | Phase 0 quarter math |
| `{q_end}` | `2026-03-31` | Phase 0 quarter math |
| `{rolling_12mo_start}` | `2025-04-01` | `DATEADD(MONTH, -12, '{q_end}')` |
| `{tenant_linkedin_url}` | `linkedin.com/company/artifex` | Phase 0 `get_current_tenant` |

---

## Query 01 — Headcount trend + employee roster (single MCP call)

**Not an `ask_onfire` query** — this slice lands via the dedicated
`get_company_headcount` tool, which reads from
`ONFIRE.PEOPLE_GRAND_EXPERIENCES` (tenure intervals) and
`ONFIRE.PEOPLE_GRAND` (profile enrichment) and self-joins on
`ONFIRE.PEOPLE_GRAND_EXPERIENCES` for **both** the person's prior AND
next company. **Neither table has an `ask_onfire` semantic entity** —
they are tool-managed and reachable only through `get_company_headcount`;
never try to author a QueryIR against `PEOPLE_GRAND*`.

```
get_company_headcount(
    company_linkedin_urls=["{company_linkedin_url}"],
    months=12,
)
```

The roster is always returned alongside the monthly counts — no opt-in
flag needed. The response carries two datasets, both always populated:

```json
{
  "headcount": {"dataset": {...}, "total_count": N, "preview_rows": [...]},
  "employees": {"dataset": {...}, "total_count": M, "preview_rows": [...]}
}
```

### `ds_headcount`

Per-month rows, most-recent first. Columns:

| Column | Notes |
|---|---|
| `company_linkedin_url` | `linkedin.com/company/<slug>` |
| `time_period` | First day of the month |
| `employee_count` | Distinct people whose tenure covers that month |
| `growth_pct` | MoM % change (NULL for the oldest row) |

Used in: exec-summary "+X% Q net" stat, Complication 1B headcount %
bar chart.

### `ds_employees`

One row per (person × stint) where any of these hold:

- `start_date` falls in the 12-month window → **joiner**
- `end_date IS NULL` → **still active**
- `end_date` falls in the 12-month window → **leaver** (covers long-tenured departures whose start is outside the window)

Columns:

| Column | Source | Notes |
|---|---|---|
| `person_linkedin_url`, `person_linkedin_id`, `is_primary` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Identity |
| `start_date`, `end_date` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | `YYYY-MM` strings; NULL end = still in role |
| `title_name`, `title_role`, `title_sub_role`, `title_levels` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Title classification at the company |
| `full_name`, `headline` | `ONFIRE.PEOPLE_GRAND` | Latest snapshot |
| `location_country`, `location_region`, `location_continent`, `location_name` | `ONFIRE.PEOPLE_GRAND` | Geo |
| `current_job_title`, `current_company_name`, `current_company_linkedin_url` | `ONFIRE.PEOPLE_GRAND` | What they're doing *now* |
| `prior_company_name`, `prior_company_linkedin_url`, `prior_title`, `prior_start_date`, `prior_end_date` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | The stint immediately before the target one (joiner origin) |
| `next_company_name`, `next_company_linkedin_url`, `next_title`, `next_start_date`, `next_end_date` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | The stint immediately after the target one (leaver destination). NULL when `end_date IS NULL` |

Used in: Phase 1.3 Q-hires filter (`start_date IN window`), Q-leavers
filter (`end_date IN window`), talent-flow strategic-thread synthesis
(joiner origins via `prior_*`, leaver destinations via `next_*`),
Complication 1B function/region breakdown.

---

## Query 02 — Title movement (target quarter only)

**Not expressible as a single `ask_onfire` query — pull rows, classify
client-side.** The net-new / now-gone classification is a per-title
temporal aggregation (`MIN(START_DATE)` and `MAX(END_DATE)` grouped by
title, with a `NOT EXISTS` "no remaining active holder" guard and a
window-bounded `HAVING`). ask_onfire exposes no GROUP-BY-per-title with
MIN/MAX measures, no `NOT EXISTS` correlation, and no UNION — so author
**one bounded row pull** with a QueryIR, then run the CTE logic in
`query_datasets` (DuckDB) over the pulled dataset.

Step 1 — pull every stint at the company (the `all_holders` universe)
via `ask_onfire`:

```
ask_onfire(query={
  entity: "people_experiences",
  select: ["title_name", "start_date", "end_date", "is_primary"],
  filters: [{dimension: "company_url", op: "eq", value: "{company_linkedin_url}"}],
  limit: <cohort size>          // hits the row-budget gate; confirm against the COUNT
})
```

- `company_url` normalizes any URL format server-side (no `LOWER()`
  needed). `people_experiences` rows are already live-scoped.
- `start_date` / `end_date` are TEXT (`'YYYY-MM'`) on this entity — the
  same string-comparison rule as the raw query.
- This is a **full-cohort pull** (every stint ever recorded at the
  target), so the row budget is large — confirm the count deliberately.

Step 2 — classify in `query_datasets` (this is where the old CTEs now
live): lowercase `title_name`, group by title, compute `MIN(start_date)`
and `MAX(end_date)`, apply the window `HAVING`, and apply the
"no row with `end_date IS NULL` for this title" guard for `now_gone`.

**Persists as `ds_title_movement`.**

Two event types:
- `net_new` - title string with no prior holder, first holder started in-quarter
- `now_gone` - existing title where the last remaining holder departed in-quarter

The "no remaining active holder" guard ensures `now_gone` excludes
titles that still have at least one active holder.

Used in: Complication 1A.

---

## Query 03 — Quarter hires with geo + function (derived from `ds_employees`)

**Not an `ask_onfire` query** — `ds_employees` from Query 01 already
contains the full 12-month roster with geo, title, and prior-company
fields. Filter it via `query_datasets`:

```sql
-- datasets: {"e": "ds_employees"}
SELECT
    person_linkedin_url,
    full_name,
    start_date,
    title_name,
    title_role,
    title_sub_role,
    title_levels,
    location_country,
    location_region,
    location_continent,
    prior_company_name,
    prior_company_linkedin_url,
    prior_title
FROM e
WHERE start_date >= '{rolling_12mo_start_yyyymm}'   -- e.g. '2025-04'
  AND start_date <= '{q_end_yyyymm}'                -- e.g. '2026-03'
  AND end_date IS NULL                              -- still in role
ORDER BY start_date, location_country
```

`start_date` / `end_date` are stored as `YYYY-MM` strings, not full
dates — compare against `YYYY-MM` literals, never against `YYYY-MM-DD`.

**Persists as `ds_q_hires`.**

Used in:

- Complication 1B continent breakdown (group by `location_continent`)
- Complication 1B function breakdown (classify `title_role` /
  `title_sub_role` / `title_name` into 5-6 coarse buckets — Engineering,
  Customer service, Design, Sales, Operations/Finance, Unclassified)
- Phase 2 strategic-thread synthesis on `prior_company_name` (talent
  pools the competitor is pulling from)

---

## Query 04 — Open job postings

Source entity: `job_post` (`SILVER.JOB_POST.STG_JOB_POSTS` — posting-
level, one row per LinkedIn job post). It has no `DELETED_AT`; the live
cut is `application_active = 1` (the `open` named filter). There is no
hiring-manager fan-out — if the brief needs an outreach target, pair
this slice with `hiring_manager_signal` (joined from `contact`) or
`entity-people-search` on the account's recruiters or team leads.

**Pitfall - allowlisting.** `job_post` is gated per-tenant. If
`ask_onfire` rejects the entity, the agent must either (a) accept a
user-uploaded CSV with the same schema, or (b) flag the open-jobs
section as "not captured in our pipeline for this tenant" in the
Assumptions block, and continue.

### 04a — Postings dated in the target quarter

**Date filtering is client-side.** `date_posted` is a returnable
*attribute* on `job_post`, not a filterable dimension — ask_onfire
cannot apply a `DATE_POSTED BETWEEN q_start AND q_end` server-side
filter. Pull the company's postings ordered by date (newest first) with
`ask_onfire`, then filter to the quarter window in `query_datasets`:

```
ask_onfire(query={
  entity: "job_post",
  select: ["job_post_title", "seniority", "job_function", "country",
           "location", "employment_type", "application_active",
           "date_posted", "external_url"],
  filters: [{dimension: "company_url", op: "eq", value: "{company_linkedin_url}"}],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: <enough to cover the window>
})
```

Then in `query_datasets`: `WHERE date_posted BETWEEN '{q_start}' AND
'{q_end}'`. **Persists as `ds_open_jobs_quarter`.**

### 04b — Currently-active postings (snapshot at brief time)

This one IS a clean server-side filter — `application_active` is a
dimension:

```
ask_onfire(query={
  entity: "job_post",
  select: ["job_post_title", "seniority", "job_function", "country",
           "location", "employment_type", "date_posted", "external_url"],
  filters: [
    {dimension: "company_url", op: "eq", value: "{company_linkedin_url}"},
    {dimension: "application_active", op: "eq", value: 1}    // still-open postings
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: <active-postings budget>
})
```

**Persists as `ds_open_jobs_active`.**

- "How many roles is the company hiring for" → `select: ["post_count"]`
  (the COUNT measure) with the same filters and `limit: 1`.

### Pitfalls

- `company_url` accepts any URL format and is normalized server-side —
  no `LOWER()` / slug-vs-https handling needed (the old raw query had to
  lower-case both sides).
- `job_function` is messy multi-value free text — match it with
  `op: "contains"`, never `eq` (e.g.
  `{dimension: "job_function", op: "contains", value: "security"}`).
- `date_posted` is when LinkedIn first showed the role; the pipeline-
  refresh timestamps (`PAYLOAD_LAST_UPDATED`, `LAST_UPDATED_TIME`) are
  governance-denied and not selectable anyway.
- `seniority = "Not Applicable"` is a real value for roles LinkedIn did
  not classify - keep these rows; many startup postings land here.
- The entity is posting-level only - no hiring-manager fields. If the
  brief page wants an outreach target, pair with `hiring_manager_signal`,
  `entity-people-search`, or `ai_prospecting`.

### Used in: Complication 1C - Open job postings

The page now shows **two cuts**:

1. **Postings dated in Q-window** (`ds_open_jobs_quarter`) - new requisitions
   the company published in the target quarter.
2. **Currently-active postings** (`ds_open_jobs_active`) - the live snapshot of
   open roles at brief date.

A useful synthesis for the page is the geographic and functional shape of
the active set (countries, `JOB_FUNCTION`, `SENIORITY_JOB`), plus a callout
on whether any active postings explicitly reference a major product /
release effort (search `JOB_TEXT` for the product name where relevant).

### DuckDB join patterns

```sql
-- datasets: {"q": "ds_open_jobs_quarter", "a": "ds_open_jobs_active"}

-- Geographic shape of the active set
SELECT country, COUNT(*) AS open_roles
FROM a
GROUP BY country
ORDER BY open_roles DESC;

-- Functional breakdown of the active set
SELECT job_function, seniority, COUNT(*) AS n
FROM a
GROUP BY job_function, seniority
ORDER BY n DESC;

-- Q1 postings that are still active
SELECT q.job_post_title, q.date_posted, q.country, q.application_active
FROM q
ORDER BY q.date_posted;
```

---

## Query 05 — Persona / department growth

**Per-insight pulls are expressible; the "every tracked persona at once"
wildcard is not.** The raw query swept *all* personas in one shot via
`INSIGHT_NAME LIKE 'growth-%'`. ask_onfire's `growth_insight_monthly`
entity takes ONE resolved `insight` value per query (the value is a
bound concept matched exactly server-side — no `LIKE` over the insight
space, no prefix handling; the server adds the `growth-` scope itself).
So you cannot enumerate every tracked persona in a single call.

Two ways to handle the department-by-department callouts:

1. **Targeted (preferred).** Decide the 4-6 personas/departments the
   brief actually discusses (resolve the wording with `resolve_insights`,
   `kind: "persona"`), then run **one QueryIR per insight** and merge:

   ```
   ask_onfire(query={
     entity: "growth_insight_monthly",
     select: ["month", "num_on_insight", "growth_rate"],
     filters: [
       {dimension: "company_url", op: "eq", value: "{company_linkedin_url}"},
       {dimension: "insight", op: "eq", value: "Data Engineering"}   // resolved value, no 'growth-' prefix
     ],
     order_by: [{field: "month", direction: "desc"}],
     limit: 12          // one company × one insight × ~12 trailing months
   })
   ```

   - `growth_rate` is the PRE-COMPUTED month-over-month change — read it
     directly; no client-side delta math. Coverage is a trailing ~12
     months, so a window filter on `month` is usually unnecessary.

2. **Exhaustive enumeration is not supported.** If the brief genuinely
   needs *every* persona tracked at the company (not a curated short
   list), ask_onfire cannot return that in one call — that is a
   capability the QueryIR grammar lacks (no wildcard over the bound
   insight space). Either restrict to the curated list above, or flag
   the all-personas sweep as unavailable.

**Persists as `ds_persona`** (the merged per-insight results). Used in:
Complication 1B department-by-department callouts.

---

## Query 06 — GitHub footprint

**Repo-name match is expressible via `github_member`; repo-OWNER match
and `PAYLOAD:` JSON extraction are not.** The raw query reached into
`ONFIRE.EVIDENCES.PAYLOAD` (a JSON blob, governance-denied and not
selectable through ask_onfire) and ILIKE-matched both `REPO_OWNER` and
`REPO_NAME` against the competitor. ask_onfire's `github_member` entity
exposes only the bare `repo_name` (not the `owner/repo` form, no
`repo_owner` column) and `activity` (`star` / `fork`), and carries no
company column — so scope it via a `contact` join. There is no way to
match on the repo *owner* org, and no JSON payload access.

The closest expressible cut — people who engaged with a repo whose
**bare name** contains the competitor token, with their profile —
joins `github_member` from `contact`:

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "current_company_name", "location_country"],
  filters: [],
  joins: [{entity: "github_member", filters: [
    {dimension: "repo_name", op: "contains", value: "{competitor_name_lc}"}
    // optional: {dimension: "activity", op: "eq", value: "star"}   // star | fork
  ]}],
  limit: <github engager budget>
})
```

If the brief specifically needs the competitor's **owned** repos (repos
under the competitor's GitHub org), that owner-level cut is **not
expressible** in ask_onfire — flag it. A bare-`repo_name contains`
match is a looser proxy (it catches repos *named* after the competitor,
not all repos *owned* by them) — note the difference in the Assumptions
block if you fall back to it.

**Persists as `ds_github`.** Aggregate downstream by country, by
employer, by federal-vs-enterprise (in `query_datasets`).

**Critical pitfall (unchanged).** The underlying engagement date
reflects a **data-collection date**, not the actual star or fork event
timestamp. The brief must treat this as a footprint snapshot only -
never a time series.

---

## Query 07 — Customer acquisition motion (last 12 months)

### Preferred path — `insight_evidence` (pull rows, compute the cohort client-side)

**The first-ever-in-window cohort logic is NOT expressible in
ask_onfire — it must be computed client-side.** The canonical
methodology (SKILL.md Phase 1.7) is: `MIN(START_DATE)` per company
**across all time**, then keep companies whose first-ever date falls in
the window, then `COUNT(DISTINCT person)` per company **inside** the
window — plus same-named-consultancy URL guards and a naive-vs-first-
ever validation count. That is multi-stage GROUP-BY + `COUNT(DISTINCT)`
+ a self-referential "first-ever then first-in-window" cohort: ask_onfire
has no GROUP-BY-per-company-with-MIN, no `COUNT(DISTINCT person)` keyed
by company, and no `NOT ILIKE` URL-exclusion filter. So **pull the
constrained evidence rows with a QueryIR and run all of the cohort logic
in `query_datasets`.**

`insight_value` is a bound concept resolved server-side (it shares the
persona/technology vocabulary), so the old `ILIKE` casing workaround is
gone — pass the competitor name and the resolver canonicalises it. The
table is ~1B rows, so the `insight_value` constraint is what keeps the
pull bounded (always present here):

```
ask_onfire(query={
  entity: "insight_evidence",
  select: ["person_url", "company_url", "evidence_type", "start_date"],
  filters: [
    {dimension: "insight_value", op: "eq", value: "{competitor_name}"},   // resolved server-side
    {dimension: "start_date", op: "gte", value: "{rolling_12mo_start}"},
    {dimension: "start_date", op: "lte", value: "{q_end}"}
  ],
  limit: <window cohort size>     // large — hits the row-budget gate; confirm against the COUNT
})
```

- `start_date` / `end_date` ARE real DATEs on `insight_evidence` (unlike
  `evidence` / `people_experiences`), so `gte` / `lte` window filters
  work server-side.
- **But note** the QueryIR window above only fetches in-window rows. The
  first-ever cohort also needs each company's earliest mention *across
  all time* to exclude companies that had pre-window mentions. Get that
  either with a second unbounded-by-date pull per candidate company
  (`insight_value` + `company_url` eq, `select: ["first_seen"]` — the
  `MIN(START_DATE)` measure), or pull a wider date range and compute
  `MIN` in `query_datasets`. The `evidence_type` column lets you split
  the cohort by signal source downstream.
- Same-named-consultancy guard (`company_url NOT ILIKE
  '%/company/{slug}s'`) and the company-level `MIN`/`COUNT(DISTINCT)`
  roll-ups all happen in `query_datasets`, not in the QueryIR.

**Persists as `ds_acquisition`** (after the client-side cohort build).

If `ask_onfire` rejects the `insight_evidence` entity (it is gated
per-tenant), fall back:

### Fallback path — `contact` static snapshot

The raw fallback used a `PEOPLE` word-boundary `REGEXP_LIKE` across
`JOB_SUMMARY` / `JOB_TITLE` / `HEADLINE`. **That multi-field free-text
regex is not expressible** — those are returnable attributes, not
filterable dimensions, and ask_onfire has no regex / word-boundary op.
The ask_onfire-native replacement for "people whose profile signals the
competitor" is a **technology insight_filter** (the curated catalog that
superseded raw `JOB_SUMMARY ILIKE`):

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "current_company_name", "current_company_url"],
  insight_filters: [{kind: "technology", value: "{competitor_name}"}],   // resolved server-side
  limit: <snapshot budget>
})
```

This returns current employees-of-other-companies who carry the
competitor as a derived technology insight — a footprint snapshot, not a
dated motion (there is no `first_seen` here). When this fallback is used,
**flag the brief section explicitly** - the Customer Acquisition page
becomes a Customer Footprint snapshot, and the Assumptions and
Definitions block must say so. If the curated insight does not resolve
to the competitor, the free-text-regex cohort is simply unavailable.

### Alternative path — user-uploaded CSV

If the user uploads a CSV with columns
`person_linkedin_url, company_linkedin_url, first_seen`, use it
directly and skip both warehouse paths.

---

## Query 08 — Customer firmographics

After `ds_acquisition` is built, pull firmographics for the distinct
companies. This is a clean `company` lookup — `linkedin_url` with
`op: "in"` over the distinct URL list (any URL format is normalized
server-side, so no `LOWER()`):

```
ask_onfire(query={
  entity: "company",
  select: ["name", "industry", "size_band", "employee_count",
           "location_country", "location_locality"],
  filters: [{dimension: "linkedin_url", op: "in", value: [
    // distinct company_linkedin_url values from ds_acquisition
  ]}],
  limit: <number of distinct companies in this batch>
})
```

**Persists as `ds_acq_firmo`.**

- Field mapping vs the old raw columns: `SIZE` → `size_band`,
  `LOCATION_NAME` → `location_locality` (the closest company attribute;
  `company` has no `location_name`). `linkedin_url` is selectable, so the
  result still carries the join key back to `ds_acquisition`.
- Each row returned is billed — `limit` should equal the batch size.
  Batch the `in` list in groups of 30-50 URLs to keep each pull (and its
  row budget) reasonable; merge the batches in `query_datasets`.

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

Then look them up in the `contact` entity via `ask_onfire` —
`linkedin_url` with `op: "in"` over the author URL list (normalized
server-side; select `current_company_url` too so the bias exclusion
below can run):

```
ask_onfire(query={
  entity: "contact",
  select: ["linkedin_url", "current_company_name", "current_company_url",
           "job_title", "location_country", "location_name"],
  filters: [{dimension: "linkedin_url", op: "in", value: [
    // opinionated-external author URLs
  ]}],
  limit: <number of distinct author URLs>
})
```

**Persists as `ds_authors_resolved`.** Field mapping vs the old raw
columns: `JOB_COMPANY_NAME` → `current_company_name`,
`JOB_COMPANY_LINKEDIN_URL` → `current_company_url`, `JOB_TITLE` →
`job_title`, `LOCATION_NAME` → `location_name`. Each returned row is
billed — set `limit` to the author-URL count.

Tagging in the join (done in `query_datasets`):
- `resolved` — a `contact` row exists AND `current_company_name IS NOT NULL`
- `unresolved-no-employer` — `contact` row exists, `current_company_name IS NULL`
- `unresolved-no-profile` — no `contact` row for the URL

**Bias exclusion (mandatory).** After the join, discard any author row
where `current_company_url` matches either of the two biased parties.
ask_onfire has no `NOT IN` exclusion filter, so this runs in
`query_datasets` over the resolved-authors dataset:

```sql
-- via query_datasets (run against ds_authors_resolved)
-- datasets: {"r": "ds_authors_resolved"}
SELECT *
FROM r
WHERE LOWER(current_company_url) NOT IN (
    '{company_linkedin_url}',   -- competitor employees: direct stake in the outcome
    '{tenant_linkedin_url}'     -- origin-tenant employees: our own people
)
```

Authors removed by this step are **silently dropped** - they are not
surfaced in unresolved buckets, not quoted in the evidence wall, and not
counted in the sentiment cross-tabs. They are biased, not merely
unresolvable.

---

## Query 10 — Modal-country geo fallback

**The modal-country roll-up is a GROUP-BY distribution — not expressible
in ask_onfire — so pull the constrained employee rows and compute the
mode client-side.** ask_onfire declares only a single `contact_count`
measure on `contact` and cannot GROUP BY `(company, country)` to return
a per-(company,country) count; the `OR` across two free-text key lists
(`JOB_COMPANY_NAME` / `JOB_COMPANY_LINKEDIN_URL`) is also not a single
QueryIR filter.

For companies in `ds_acq_firmo` with NULL `location_country`, pull their
employees by **company URL** (the clean key — `current_company_url` with
`op: "in"`; drop the name-based `OR` branch), then take the modal
country in `query_datasets`:

```
ask_onfire(query={
  entity: "contact",
  select: ["current_company_name", "current_company_url", "location_country"],
  filters: [{dimension: "current_company_url", op: "in", value: [
    // company URLs from ds_acq_firmo with NULL location_country
  ]}],
  limit: <employee-row budget across these companies>
})
```

**Persists as `ds_geo_fallback`** (raw employee rows). Then in
`query_datasets`: `GROUP BY current_company_url, location_country`,
`COUNT(*)`, and take the modal `location_country` per company. The pull
is billed per employee row, so the budget can be sizeable — confirm
against the COUNT, and consider capping per-company (e.g. only the first
N employees per company are needed to establish a mode). If no employees
match, leave the company in the Unresolved bucket (shown muted).

---

## Query 11 — Leavers + destinations (derived from `ds_employees`)

**Not an `ask_onfire` query.** Phase 1.1's `ds_employees` already
covers leavers (rows where `end_date IN window`) and attaches the
immediately-next company per row via the symmetric self-join. The
old separate raw query against `PEOPLE_EXPERIENCES` plus the
window-function CTE for destinations are **superseded** (and the
next-company self-join was a window function ask_onfire could never
express anyway) — derive a single `ds_leavers` from `ds_employees` via
`query_datasets`:

```sql
-- datasets: {"e": "ds_employees"}
SELECT
    person_linkedin_url,
    person_linkedin_id,
    full_name,
    title_name,
    title_role,
    title_sub_role,
    title_levels,
    start_date,
    end_date,
    location_country,
    location_region,
    location_continent,
    location_name,
    current_job_title,
    current_company_name,
    current_company_linkedin_url,
    -- destination is on the same row, no second join needed:
    next_company_name,
    next_company_linkedin_url,
    next_title,
    next_start_date,
    next_end_date
FROM e
WHERE end_date IS NOT NULL                            -- they left
  AND end_date >= '{window_start_yyyymm}'             -- in the window
  AND end_date <= '{window_end_yyyymm}'
ORDER BY end_date, location_country
```

**Persists as `ds_leavers`.**

`start_date` / `end_date` are stored as `YYYY-MM` strings — compare
against `YYYY-MM` literals, never `YYYY-MM-DD`. Tenure-at-target =
`end_date - start_date` (in months).

Interns surface naturally as 4-6-month tenures with `intern` in
`title_name` — call those out separately from real departures.

`next_company_*` is NULL for some leavers — their next role hasn't
landed in the data lake yet. Call the gap out explicitly ("6 of 18
destinations captured"). For destination size / industry / country,
batch-pair the distinct `next_company_linkedin_url` values to the
`company` entity via a follow-up `ask_onfire` call (the Query 08 shape:
`linkedin_url op=in`, groups of 30-50, `limit` = batch size).

Symmetric pattern for **joiner origins**: `ds_employees` already
carries the `prior_company_*` block on every row — slice the same
dataset with `start_date IN window AND end_date IS NULL` to get the
joiner cohort with origins attached (this is `ds_q_hires` from
Query 03; the slim-projected-with-origins flavour is `ds_q_hires_priors`).

There is no separate `ds_leaver_destinations` dataset — destinations
ride on the leaver row.

Used in: Complication 1B leavers card; Phase 2 strategic-thread
synthesis ("where are senior people going?").

---

## ~~Query 12~~ — deprecated (folded into Query 11)

The previous raw CTE that detected leavers in `PEOPLE_EXPERIENCES` and
window-functioned the next employer has been **replaced** by Query 11's
`query_datasets` derivation (and a next-employer window function was
never expressible in ask_onfire regardless). The
`get_company_headcount` tool emits both halves on the same row via the
`next_*` columns, so no separate destinations dataset is needed.

---

## Query 13 — Departed-no-backfill recoverability (SUMMARY scan)

For each title in the `departed-no-backfill` bucket from Phase 2.1,
two passes against current employees:

### 13a — Current-holder scan

**The free-text SUMMARY/HEADLINE/JOB_SUMMARY OR-scan is NOT expressible
in ask_onfire.** The raw query OR-chained `LIKE '%keyword%'` across three
free-text columns spanning two joined tables (`SUMMARY` on
people_experiences + `HEADLINE` / `JOB_SUMMARY` on people). In ask_onfire
those are all **returnable attributes, not filterable dimensions** —
there is no `contains` filter on `summary` / `headline` / `job_summary`,
and no OR across columns of two entities. The curated replacement for raw
profile-keyword ILIKE is an `insight_filter` (persona/technology). So:

- **Preferred (insight-native).** Map the departed function to a curated
  persona (resolve the wording with `resolve_insights`, `kind: "persona"`
  — e.g. a "Head of Technology Partnerships" → a partnerships/alliances
  persona if one resolves), then scan current employees:

  ```
  ask_onfire(query={
    entity: "contact",
    select: ["full_name", "job_title", "current_company_name"],
    filters: [{dimension: "current_company_url", op: "eq", value: "{company_linkedin_url}"}],
    insight_filters: [{kind: "persona", value: "<resolved function persona>"}],
    limit: 20
  })
  ```

  The contact insight search defaults to current holders
  (`active_employment = TRUE`), which mirrors the old `END_DATE IS NULL`
  "still in role" guard.

- **Capability gap to flag.** If the function does not resolve to any
  curated persona/technology, the original intent (catch people doing
  the work *by free-text profile keyword under a different title*) has
  **no ask_onfire expression** — there is no way to substring-match
  `summary` / `headline` / `job_summary`. Note this in the Assumptions
  block; the recoverability read for that title then rests on 13b
  (open-posting check) alone.

### 13b — Open-posting check

```sql
-- against ds_open_jobs_active
SELECT job_post_title, job_function, country, date_posted
FROM a
WHERE LOWER(job_post_title) LIKE '%{function_keyword_1}%'
   OR LOWER(job_text)       LIKE '%{function_keyword_1}%'
```

### 13c — Read

| 13a result | 13b result | Read |
|---|---|---|
| 1+ rows | any | **Parallel hold by [title].** The function is still held by a current employee whose role summary describes the work. Often the parallel holder pre-existed the departed person's tenure. |
| 0 rows | 1+ active posting | **Open posting in flight.** No current holder but an active req targets the function. |
| 0 rows | 0 active postings | **Function lapsed.** Dedicated seat experiment ended and the work isn't visible elsewhere - the only true "lost capability" outcome. |

**Always check 13a before concluding "function lost"** - title-keyword
search routinely overstates departed-no-backfill as lost capability.
On real briefs most outcomes are 13a-hits (parallel hold).

Used in: Page 4 Departed-no-backfill detail table.

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

Every pull in this file is read-only. The brief never writes back to the
warehouse. `ask_onfire` is read-only by construction (it compiles a
QueryIR to a bounded SELECT; no free-form SQL ever originates from the
client), so the read-only stance is enforced by the tool surface itself.

The skill never calls `contact_data_enrichment` either - the brief is
a competitive-intelligence read, not a contact-enrichment exercise.
