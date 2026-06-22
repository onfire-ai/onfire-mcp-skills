---
name: competitor-report
description: Generate a full client-grade Competitor Intelligence Brief for a single competitor company. The window is configurable: either the last completed calendar quarter (default) or the trailing 12 months ending the last completed quarter. Produces an A4 HTML and an optional PDF using a McKinsey-style consulting layout (Pyramid Principle lead, SCR narrative arc, action titles). The brief covers org reshape (title movement by leadership vs department, paired swaps vs net-new functions, departed-no-backfill recoverability check), hires with geo + function + origin-company size, leavers with destinations, open job postings, customer acquisition motion (12-month measured motion from the insights pipeline, monthly stacked by industry), market sentiment split (owned brand surfaces vs external developer communities), GitHub footprint snapshot, vendor-trust events, an evidence wall of verbatim third-party-only quotes (target competitor and prepared-for tenant employees both excluded), an Assumptions and Definitions back matter, and a Company Reference Card exhibit. Use this skill whenever the user asks to "build a competitor brief", "competitive intelligence on X", "deep dive on competitor X", "Nexagon-style report on X", "scan competitor X for the last quarter", "12-month view of competitor Y", "what's happening at competitor Y", or any phrasing that mixes a vendor name with a request for an analytical multi-section report on their org and market posture.
---

# Competitor Intelligence Brief

## What this skill does

Given a **competitor company name** (e.g. `Nexagon`, `Codeshield`, `Artifex`),
this skill produces a **13-page A4 PDF analytical brief** by default.
The page count can flex to 14 when Complication 1B is split into a
geographic page (page 5) and a departmental-change page (new page 6) -
opt in to the split when the joiner book is rich enough to warrant a
function-bar visualisation and the internal-promotion list deserves its
own card. Briefs without vendor-trust events run 12 pages (Complication
3 is omitted).

The deliverable is internal-facing (prepared FOR the caller's tenant,
ABOUT a non-customer vendor) and written in a consulting-firm idiom -
Pyramid Principle, SCR (Situation / Complication / Resolution) narrative
arc, McKinsey-style action titles.

The brief is **analytical only**. No GTM plays, no recommendations, no
revenue estimates. The reader synthesises the implications themselves.

### Editorial policy: how the tenant appears

The brief is prepared for the **requesting tenant** (the company who
ran the report) and is about the **target competitor**. They are
treated asymmetrically in the deliverable:

| Subject | Appears named | Does not appear named |
|---|---|---|
| **Target competitor** | Cover, Exhibit A, action titles, findings, all analytical sections. The target is the subject. | The evidence wall — verbatim quotes from target employees are excluded (a competitor founder's rebuttal of a public critique is still a target voice). |
| **Prepared-for tenant** | Internal-only file metadata. The default cover line reads "Prepared for the requesting tenant" - explicitly opt in via `brand_cover: true` to name them. | Anywhere in the customer-facing copy. If a tenant CEO or employee publicly engaged with the target in-window, describe the event by category descriptor ("a category-incumbent CEO", "a public artifact-management vendor") - never by name. |

The rule formalises that the artefact stays distributable even if it
ends up outside the requesting tenant. The target is the subject; the
tenant is the reader.

---

## Inputs

| Input | Required | Example | Default |
|-------|----------|---------|---------|
| `competitor_name` | Yes | `Nexagon` | - |
| `company_linkedin_url` | Optional | `linkedin.com/company/nexagon` | resolved via `match_company` |
| `window_mode` | Optional | `quarter` or `12_month` | `quarter` |
| `quarter` | Optional | `Q1 2026` | the last fully completed calendar quarter |
| `prepared_for_tenant` | Optional | `artifex` | from `get_current_tenant` |
| `brand_cover` | Optional | `true` | `false` - cover line reads "Prepared for the requesting tenant" by default; opt in to name the tenant on the cover |

If `quarter` is not supplied, the skill computes it from today's date.
Today is in Q2 2026 → last completed quarter is Q1 2026 (Jan 1 - Mar 31).

### Window modes

| Mode | Window | Use when |
|---|---|---|
| `quarter` (default) | The single calendar quarter chosen (e.g. Q1 2026 = Jan 1 - Mar 31). Acquisition motion still uses a trailing 12-month series for context but every other section is bound to the quarter. | Quarterly tracking brief; what changed in the last 90 days. |
| `12_month` | The trailing 12 months ending at the last completed calendar quarter (e.g. Apr 1, 2025 - Mar 31, 2026). Every section - org reshape, hires, leavers, sentiment, vendor-trust - is bound to the full window. | Annual review brief; deeper analytical read; capturing a leadership-rebuild story that a single quarter would miss. |

The data slices are largely the same shape under either window - the
difference is the time predicate and the headline language. Switching
mode propagates to every page footer, the running headers, the
Assumptions block, and all action titles ("Q1 hiring tilt" vs
"12-month hiring tilt").

---

## The 6 phases

The skill works through **six phases in strict order**. Each phase has
mandatory inputs from the previous phase. Do not skip ahead; the
analysis phase depends on every data slice being persisted as a dataset.

```
Phase 0   Scope and identity            (~1 minute)
Phase 1   Data gathering                (~5-8 minutes)
Phase 2   Analysis                      (~3-5 minutes)
Phase 3   Report assembly               (~3-5 minutes)
Phase 3.5 Self-validation pass          (~3-5 minutes) — MANDATORY
Phase 4   Pre-delivery checklist        (~1 minute)
```

**Phase 3.5 is non-negotiable.** Every brief that has shipped without
this pass has contained at least one self-contradiction a careful
reader catches in five minutes. Triple-check every number, every
percentage, every cross-page reference. The brief is one argument
across all pages — if any two pages disagree on the same fact, the
brief is wrong.

---

## Phase 0 - Scope and identity

### 0.1 Compute the window

In bash:
```bash
TODAY=$(date +%Y-%m-%d)
# Compute last completed full quarter from today.
# Example: today 2026-05-24 → Q1 2026 = 2026-01-01 .. 2026-03-31
```

Persist these values for the rest of the run:

| Value | `quarter` mode | `12_month` mode |
|---|---|---|
| `window_start` | First day of the chosen quarter (e.g. `2026-01-01`) | `q_end - 12 months` (e.g. `2025-04-01`) |
| `window_end` | Last day of the chosen quarter (e.g. `2026-03-31`) | Last day of the most recent completed quarter (e.g. `2026-03-31`) |
| `window_label` | `Q1 2026` | `12 months ending Mar 2026` |
| `q_start` / `q_end` | Same as `window_start` / `window_end` | Used only for the recent-quarter bracket in the acquisition chart |

The customer-acquisition motion **always** uses a trailing 12-month
series ending at `q_end`. The other sections honour `window_mode`.

### 0.2 Resolve the competitor identity

```
Onfire MCP: match_company(
  name="<competitor_name>",
  telemetry={intent: "Competitor intelligence brief for <competitor_name>"}
)
```

Confirm the verified LinkedIn URL with the user before proceeding.
**Store** the firmographic block returned by `match_company`:

| Field | Used for |
|---|---|
| `linkedin_url` | every subsequent query (lowercased) |
| `name`, `display_name` | brief cover + exhibit + running headers |
| `hq`, `country`, `founded_year` | Exhibit A reference card |
| `revenue_band`, `ownership`, `last_funding_round` | Exhibit A timeline |
| `employee_count`, `size_band` | Exhibit A + headline framing |
| `industry`, `description` | Exhibit A positioning paragraph |
| `subsidiary_linkedin_urls[]` | fold into headcount aggregates (don't double-count) |

### 0.3 Resolve the "prepared for" tenant

```
Onfire MCP: get_current_tenant(telemetry={intent: "..."})
```

The cover line by default reads **"Prepared for the requesting
tenant"**. The tenant's brand name only lands on the cover when the
caller passes `brand_cover: true`.

Resolve the tenant's `company_linkedin_url` via `match_company` and
store it (lowercased) as `{tenant_linkedin_url}`. Two downstream
exclusions use it:

1. Phase 1.10 - exclude biased sentiment authors from `ds_authors_resolved`
2. Phase 3 - scrub any analytical mention of the tenant in customer-facing
   copy; replace with the category descriptor (see editorial policy above)

---

## Phase 1 - Data gathering

Each warehouse pull runs through **`ask_onfire`** — a structured
**QueryIR** (`query={entity, select, filters, insight_filters, joins,
order_by, distinct_by, limit, confirmed}`), **not** raw SQL. (The
removed `query_onfire` raw-SQL tool no longer exists.) Each pull persists
its result as a dataset; track the dataset IDs - the analysis phase joins
them with `query_datasets`. See `references/snowflake-queries.md` for the
per-slice QueryIR recipes and the table→entity map, and
`account-research/references/ask-onfire-signals.md` for the worked
patterns.

**Important — billing + capability:** `ask_onfire` **bills 1 credit per
row returned**, so set a small explicit `limit` on every call; an unset
or over-threshold budget returns `needs_confirmation` (`stage:
"row_budget"` — a free COUNT, nothing billed) so you can settle the count
with the user and resubmit with `confirmed: true`. Several brief slices
are full-cohort pulls feeding a downstream `query_datasets` analysis —
expect to hit and deliberately clear the confirmation gate. ask_onfire
**cannot** express GROUP-BY distributions beyond a single declared COUNT
measure, window functions, month-over-month / first-ever temporal cohort
logic, multi-field free-text OR-scans, `PAYLOAD:` JSON, or multi-hop
joins; for those slices (title movement, acquisition cohort, modal-
country, departed-no-backfill free-text scan) pull the constrained rows
with a QueryIR and do the analysis client-side (see snowflake-queries.md
for which is which).

### 1.1 Headcount trend + employee roster (single call — primary source for org-growth changes)

See `references/snowflake-queries.md` → query 01.

A single `get_company_headcount` call is the **primary source for all
org-growth changes** in the brief — monthly headcount trend, joiners,
leavers, joiner origins, and leaver destinations. It powers Phase 1.1
(headcount), Phase 1.3 (Q-hires), and Phase 1.12 (leavers + their
destinations). No separate `ask_onfire` pull is needed for any of those.

Headcount is derived from tenure intervals in
`ONFIRE.PEOPLE_GRAND_EXPERIENCES`; the employee roster joins each
tenure to `ONFIRE.PEOPLE_GRAND` for location and to **symmetric
self-joins** on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` for both the
immediately-prior company (joiner origin) and the immediately-next
company (leaver destination). **Neither `PEOPLE_GRAND` nor
`PEOPLE_GRAND_EXPERIENCES` has an `ask_onfire` semantic entity** — they
are tool-managed and reachable only through `get_company_headcount`; do
**not** attempt to author a QueryIR against them.

```
Onfire MCP: get_company_headcount(
  company_linkedin_urls=["{company_linkedin_url}"],
  months=12,
  telemetry={intent: "Competitor brief headcount + joiners + leavers"}
)
```

The roster is always returned alongside the monthly counts — no opt-in
flag needed. Each roster row covers joiners (`start_date IN window`),
still-active (`end_date IS NULL`), **and** leavers (`end_date IN
window` — incl. long-tenured departures whose start is outside the
window). `prior_*` columns are on every row; `next_*` columns are
populated for stints that ended.

Persist the two datasets returned:

| Dataset | From | Used by |
|---|---|---|
| `ds_headcount` | `response.headcount.dataset` | Complication 1B headcount % bars; exec-summary "Q net" callout |
| `ds_employees` | `response.employees.dataset` | Phase 1.3 (joiners filter via `start_date`), Phase 1.12 (leavers + destinations via `end_date` + `next_*`), and the talent-flow strategic-thread synthesis (joiner origins via `prior_*`, leaver destinations via `next_*`) |

Pull in-quarter rows from `ds_headcount` for the exec-summary "+X% Q1
net" callout. Each row carries `time_period` (first day of month),
`employee_count`, and `growth_pct` (MoM %; NULL for the oldest row).

Because joiners and leavers are derived from the same `ds_employees`
source as the headcount counts, the joiner / leaver math reconciles
with the MoM headcount delta within snapshot-lag tolerance — this is
the canonical pattern; do not re-derive these slices from
`people_experiences` via `ask_onfire`.

### 1.2 Title movement (window-bound)

See `references/snowflake-queries.md` → query 02.

Classify every in-window event into:
- **Net-new title** - title string had no prior holder
- **Now-gone title** - last remaining holder of an existing title departed

Persists as `ds_title_movement`. **Strictly bounded to the window** -
any event outside `window_start` / `window_end` is excluded.

For `12_month` mode the same query runs against the 12-month
predicate; expect ~5x more events than a single quarter.

### 1.3 Quarter hires with geo + function (derived from `ds_employees`)

No second tool call — Phase 1.1 already pulled the employee roster.
Derive `ds_q_hires` from `ds_employees` via `query_datasets`:

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
WHERE start_date >= '{rolling_12mo_start_yyyymm}'   -- '2025-04', match the YYYY-MM form
  AND start_date <= '{q_end_yyyymm}'                -- '2026-03'
  AND end_date IS NULL                              -- still in role
```

Persists as `ds_q_hires`.

The roster also carries `prior_company_name` / `prior_company_linkedin_url`
for every row — feed this into the Phase 2 strategic-thread synthesis
("which talent pools are they pulling from"). Persist it as
`ds_q_hires_priors` if you intend to surface it as its own exhibit.

### 1.4 Open job postings

See `references/snowflake-queries.md` → query 04.

`SILVER.JOB_POST.STG_JOB_POSTS` rows for the target quarter and currently-active
postings. Persists as `ds_open_jobs_quarter` (in-quarter) and `ds_open_jobs_active`
(currently open snapshot).

Pitfall: `SILVER.JOB_POST.STG_JOB_POSTS` does not have a `DELETED_AT`
column. Use `APPLICATION_ACTIVE = 1` to scope to currently open roles.

### 1.5 Persona / department trends

See `references/snowflake-queries.md` → query 05.

`GROWTH_INSIGHT_MONTHLY` for 12 months of persona-level adoption (e.g.
`growth-Data Engineering`, `growth-Product`). Persists as `ds_persona`.

### 1.6 GitHub footprint

See `references/snowflake-queries.md` → query 06.

`EVIDENCES` rows where `EVIDENCE_TYPE_ID = 6` and the
`PAYLOAD:REPO_OWNER` matches the competitor (or its open-source repo
naming convention). Persists as `ds_github`.

**Critical pitfall.** GitHub `EVIDENCES` rows carry the
**data-collection date** in the date field, **not** the actual star or
fork timestamp. Treat the GitHub section as a footprint snapshot only.
Never construct a time-trend. Always carry a methodology caveat into
the assembled report.

### 1.7 Customer acquisition motion (last 12 months)

See `references/snowflake-queries.md` → query 07.

**Methodology — first-ever, not any-mention.** The cohort is companies
whose **first-ever** Packmint mention in the insights pipeline (across
all time, not just the window) falls inside the 12-month window.
Companies with any prior mention before the window start are excluded.
This is the canonical "true new mentioner" cohort.

The naive "any mention in window" query over-counts dramatically:
on the canonical Packmint run the naive cut returned 87 companies,
of which only **63** were truly first-ever-in-window; 24 of the 87 had
earlier mentions and should not have been counted as "new".

**The first-ever-in-window cohort is NOT expressible in `ask_onfire`**
— it needs `MIN(start_date)` per company **across all time**, then a
keep-if-first-ever-date-in-window filter, then `COUNT(DISTINCT person)`
per company **inside** the window, plus a same-named-consultancy URL
guard. That is multi-stage GROUP-BY + `COUNT(DISTINCT)` keyed by
company + a `NOT ILIKE` exclusion, none of which a QueryIR can express.
So **pull the constrained `insight_evidence` rows with a bounded
`ask_onfire` QueryIR, persist them, then run all of the cohort logic
client-side in `query_datasets` (DuckDB).** `insight_value` is bound
and resolved server-side (`resolve_insights` shares the
persona/technology vocabulary), so the old `ILIKE` casing workaround
is gone — pass the competitor name and the resolver canonicalises it.
`insight_evidence` is ~1B rows, so the `insight_value` + `start_date`
window is what keeps the pull bounded; the row budget bills 1 credit
per row, so set `limit` to the cohort size and confirm against the
free COUNT when the `needs_confirmation` gate fires.

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

The QueryIR above fetches in-window rows only. The first-ever cohort
also needs each company's earliest mention **across all time** to
exclude companies that had pre-window mentions. Get that either with a
second per-candidate-company pull (`insight_value` + `company_url` eq,
selecting the `first_seen` measure = `MIN(start_date)`), or pull a
wider date range and compute `MIN` client-side. Persist the rows, then
in `query_datasets` (DuckDB) build the cohort:

```sql
-- runs in query_datasets over the persisted insight_evidence rows, NOT in Snowflake
WITH external_mentions AS (
  SELECT company_url, person_url, start_date
  FROM ds_evidence_rows
  WHERE company_url IS NOT NULL
    AND company_url NOT ILIKE '%/company/{competitor_slug}'
    AND company_url NOT ILIKE '%/company/{competitor_slug}s'  -- guard against same-named consultancies (Packmints)
    AND start_date IS NOT NULL
),
first_ever AS (   -- MIN across ALL time (from the all-time pull)
  SELECT company_url, MIN(start_date) AS first_ever_date
  FROM external_mentions
  GROUP BY company_url
),
first_in_window AS (
  SELECT * FROM first_ever
  WHERE first_ever_date BETWEEN '{window_start}' AND '{window_end}'
),
mentioner_counts AS (
  SELECT
    fiw.company_url,
    fiw.first_ever_date,
    COUNT(DISTINCT em.person_url) AS distinct_mentioners_in_window
  FROM first_in_window fiw
  JOIN external_mentions em
    ON em.company_url = fiw.company_url
   AND em.start_date BETWEEN '{window_start}' AND '{window_end}'
  GROUP BY 1, 2
)
SELECT * FROM mentioner_counts
```

Persists as `ds_acquisition`. **Production-depth = `distinct_mentioners_in_window >= 2`; evaluator = 1.**

**Validation check.** Compare the result against the naive "any mention
in window" count. Run this client-side over the same persisted rows
(the in-window pull alone is enough — no all-time `MIN` needed):

```sql
-- naive (over-counts; informational only) — query_datasets, not Snowflake
SELECT COUNT(DISTINCT company_url)
FROM ds_evidence_rows
WHERE start_date BETWEEN '{window_start}' AND '{window_end}'
  AND company_url NOT ILIKE '%/company/{competitor_slug}'
  AND company_url NOT ILIKE '%/company/{competitor_slug}s';
```

If `naive_count > first_ever_count`, the gap is companies with prior
mentions that the brief MUST NOT count. Surface the gap in the brief
as a footnote so the reader trusts the methodology.

Legacy template (any-mention in window, raw Snowflake — **DO NOT USE
for the brief**; the `query_onfire` raw-SQL tool that ran it no longer
exists; kept here only as a reference for what the brief is *not*
doing):

```sql
-- WRONG / over-counting / removed-tool syntax — kept for diff reference only
SELECT PERSON_LINKEDIN_URL, COMPANY_LINKEDIN_URL, MIN(START_DATE) AS first_seen
FROM ONFIRE.INSIGHTS_2_EVIDENCES
WHERE INSIGHT_VALUE = '{competitor_name}'
  AND START_DATE BETWEEN DATEADD(MONTH, -12, '{q_end}') AND '{q_end}'
GROUP BY PERSON_LINKEDIN_URL, COMPANY_LINKEDIN_URL
```

If `ask_onfire` rejects the `insight_evidence` entity (it is gated
per-tenant), fall back to a `contact` static snapshot — current
employees-of-other-companies who carry the competitor as a derived
**technology insight** (the curated catalog that superseded the raw
`PEOPLE` / `JOB_SUMMARY` free-text scan; ask_onfire has no
regex/word-boundary op):

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "current_company_name", "current_company_url"],
  insight_filters: [{kind: "technology", value: "{competitor_name}"}],   // resolved server-side
  limit: <snapshot budget>
})
```

This is a footprint snapshot, not a dated motion (no `first_seen`), so
label the section as "snapshot, not motion" in the brief — the Customer
Acquisition page becomes a Customer Footprint snapshot. The fallback
**must** be flagged in the Assumptions and Definitions block.

If the caller uploads a CSV with `(person_linkedin_url,
company_linkedin_url, first_seen)`, use that instead of the live
query - this is the explicit user-supplied data path.

Persists as `ds_acquisition`.

### 1.8 Customer firmographics

See `references/snowflake-queries.md` → query 08.

Join the distinct `company_linkedin_url` values from `ds_acquisition`
to `ONFIRE.COMPANIES` for `INDUSTRY`, `SIZE`, `LOCATION_COUNTRY`,
`EMPLOYEE_COUNT`. Persists as `ds_acq_firmo`.

### 1.9 Sentiment scoring (target quarter, full universe)

```
Onfire MCP: community_messages_sentiment(
  keyword="<competitor_name>",
  date_from="{q_start}",
  date_to="{q_end}",
  sample_size=null,    # full universe; do NOT subsample
  telemetry={intent: "Sentiment cut for the competitor brief"}
)
```

Persists as `ds_sentiment`. **Always score the full quarter universe**,
never a sample. The brief makes claims like "every Nexagon-mentioning
public message from Q1 2026" - that's only true if the call is
unsampled.

### 1.10 Resolve sentiment authors

See `references/snowflake-queries.md` → query 09.

For every opinionated (positive + negative) external author in
`ds_sentiment`, look up their LinkedIn URL in `ONFIRE.PEOPLE` to get
their current employer + country. Persists as `ds_authors_resolved`.

Authors that don't match a `PEOPLE` row, OR whose `PEOPLE` row has a
null `JOB_COMPANY_NAME`, are the "Unresolved" bucket - shown muted in
the cross-tab, not hidden.

**Bias exclusion.** After joining to `ONFIRE.PEOPLE`, discard any author
whose `JOB_COMPANY_LINKEDIN_URL` matches either `{company_linkedin_url}`
(the competitor being analysed) or `{tenant_linkedin_url}` (the origin
tenant). These authors have a direct stake in the outcome and must not
appear in `ds_authors_resolved`, the sentiment cross-tabs, or the
evidence wall.

### 1.11 Geo fallback for unresolved companies

See `references/snowflake-queries.md` → query 10.

For any company in `ds_acq_firmo` with NULL `LOCATION_COUNTRY`, query
`ONFIRE.PEOPLE` for that company's employees and use the **modal
country** as the inferred country. Persists as `ds_geo_fallback`.

### 1.12 Leavers and their destinations (derived from `ds_employees`)

No second tool call — Phase 1.1 already pulled the employee roster,
which now covers leavers (incl. long-tenured departures) and attaches
the immediately-next company on each row. Derive `ds_leavers` from
`ds_employees` via `query_datasets`:

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
    -- destination on the same row, no second join needed:
    next_company_name,
    next_company_linkedin_url,
    next_title,
    next_start_date,
    next_end_date
FROM e
WHERE end_date IS NOT NULL                           -- they left
  AND end_date >= '{window_start_yyyymm}'            -- in the window
  AND end_date <= '{window_end_yyyymm}'
ORDER BY end_date, location_country
```

`start_date` / `end_date` are stored as `YYYY-MM` strings, not full
dates — compare against `YYYY-MM` literals.

Tenure-at-target is derivable per row as `end_date - start_date` (in
months). Interns surface naturally as 4-6-month tenures with `intern`
in the title — call those out separately from real departures.

`ds_leavers` is a single dataset; destination columns live on the same
row. If a destination size / industry / country breakdown is needed,
pull the distinct `next_company_linkedin_url` values from the `company`
entity via a follow-up `ask_onfire` call (the Query 08 shape:
`linkedin_url op=in`, batch in groups of 30-50, `limit` = batch size).
Many leavers will not have a captured next role — call the gap out
explicitly ("6 of 18 destinations captured").

Used in: Complication 1B leavers card; Phase 2 strategic-thread
synthesis ("where are senior people going?").

### 1.13 Departed-no-backfill recoverability (only if Phase 2 detects any)

See `references/snowflake-queries.md` → query 13.

For each title classified as `departed-no-backfill` in Phase 2.1, run
two checks:

1. **Current-holder scan.** ask_onfire cannot OR-scan the free-text
   `SUMMARY` / `HEADLINE` / `JOB_SUMMARY` columns (they are returnable
   attributes, not filterable dimensions). Use the insight-native
   substitute instead: map the departed function to a curated persona
   (via `resolve_insights`) and scan current `contact` employees of the
   target with that `insight_filter` (see snowflake-queries.md → query
   13a). If the function does not resolve to any curated persona, the
   free-text "doing the work under a different title" scan has **no
   ask_onfire expression** — flag it and lean on check 2 alone.
2. **Open-job-posting check.** Filter `ds_open_jobs_active` for the
   same function keywords.

Three outcomes per departed-no-backfill title:

| Read | Definition |
|---|---|
| **Parallel hold by ...** | The function is still held by 1+ current employees whose role summary describes the work. Often pre-existed the departed person's tenure. |
| **Open posting in flight** | No current holder but an active posting targets the function. |
| **Function lapsed** | No current holder AND no open posting. The dedicated seat experiment ended and the work isn't visible elsewhere. |

This becomes the Departed-no-backfill detail table on page 4 - a
post-Phase-2 enrichment, not a Phase 1 data slice.

### 1.14 Office segmentation (geographic footprint for page 2)

Powers the **Geographic footprint** card on the executive summary
(page 2). Three calls in sequence:

```
Onfire MCP: search_offices(
  company_name="{competitor_name}",
  company_website="{competitor_website}",
  telemetry={intent: "Competitor brief office segmentation"}
)
```

Returns `offices` (list of `{city, country, state, region, is_hq}`)
and `total_offices`. Persist as `ds_offices`.

Then pull the company's employee locations. The per-location
`COUNT(*)` roll-up across `(country, region, name)` is a GROUP-BY
distribution **ask_onfire cannot return** (it exposes one declared
`contact_count` measure, not a multi-dimension group-by-with-count), so
pull the raw employee location rows with a QueryIR and aggregate in
`query_datasets`:

```
ask_onfire(query={
  entity: "contact",
  select: ["location_country", "location_region", "location_name"],
  filters: [{dimension: "current_company_url", op: "eq", value: "{company_linkedin_url}"}],
  limit: <headcount-sized budget; hits the row-budget gate — confirm against the COUNT>
})
```

Then in `query_datasets`: `GROUP BY location_country, location_region,
location_name`, `COUNT(*) AS employee_count`, `ORDER BY employee_count
DESC`. Persist the aggregated result as `ds_location_distribution`.

The old numeric `JOB_COMPANY_LINKEDIN_ID` disambiguation guard (needed
when the slug was ambiguous, e.g. `packmint` vs `packmints`) is no
longer available — ask_onfire has no numeric-ID dimension on `contact`.
Pass the **verified `company_linkedin_url`** from Phase 0
`match_company` as `current_company_url`; it is normalized server-side
and resolves to the one canonical company, so it does not pollute with a
same-named neighbour the way a bare slug `ILIKE` did.

**Use the headcount snapshot (from Phase 1.1) as the denominator** for
the % column, not the sum of the distribution rows. People with a null
`LOCATION_COUNTRY` are excluded from the group-by but are still part of
the headcount — surface this as a "Remote / location not disclosed"
row equal to `headcount_total − sum(employee_count)`.

#### Assignment rules (location cluster → office)

Per the `office-segmentation` skill:

1. **City match** — an office `city` (case-insensitive) appears inside
   `LOCATION_NAME` → assign cluster to that office.
2. **Country match** — only when no city match exists AND a single
   office exists in that country → assign to that office.
3. **Multiple offices in same country, no city hit** → assign to
   `Remote / Unknown` rather than guess.
4. **No match** → assign to `Remote / Unknown`.

For competitors with only 1 official office (common for sub-200-person
scale-ups), most clusters will only match by country. Surface the
distinction in the card narrative — Belfast HQ catchment vs distributed
hubs without an official site.

Persist the rolled-up table as `ds_office_segmentation`:

| Column | Notes |
|---|---|
| `bucket_label` | E.g. "Belfast HQ", "Jaipur cluster", "Remote / location not disclosed" |
| `bucket_type` | `hq` / `office` / `distributed_hub` / `other` / `remote_unknown` |
| `employee_count` | Sum of matching `LOCATION_NAME` clusters |
| `pct_of_total` | `employee_count / headcount_total` |
| `notes` | Cities included in this bucket |

### 1.15 Event attendance signals (conditional Complication 2D)

Powers the **Event attendance** page (Complication 2D). Source entity:
`event_contact` (`ONFIRE.EVENTS_CONTACTS`) — every captured signal of a
competitor person attending a conference, summit, webinar or industry
event.

The brief wants the attendees **with names + titles**, which the raw
query got by joining `EVENTS_CONTACTS` to `PEOPLE`. In ask_onfire that
is the documented inverse: query the `contact` entity (so you can SELECT
profile fields) and apply `event_contact` as a **filter-only join**
(`event_contact` exposes no profile fields to select):

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "location_name", "location_country"],
  filters: [{dimension: "current_company_url", op: "eq", value: "{company_linkedin_url}"}],
  joins: [{entity: "event_contact", filters: [
    // optionally pin one event: {dimension: "event", op: "eq", value: "RSAC 2026"}
    {dimension: "active_employment", op: "eq", value: true}   // attendee still at the company
  ]}],
  limit: <captured-attendances budget>
})
```

Two capability notes vs the raw query:

- **No numeric-ID disambiguation.** The raw query keyed on
  `company_linkedin_id` (numeric) to avoid same-named-company pollution.
  ask_onfire has no numeric-ID dimension — pass the **verified
  `company_linkedin_url`** from Phase 0 `match_company` (normalized
  server-side, resolves to the one canonical company).
- **Per-event grouping is client-side.** This single QueryIR cannot also
  return a per-event attendee `COUNT` and the named attendees at once. To
  list which events the company showed up at with counts, run a separate
  `event_company` pull (`select: ["event", "attendee_count"]`,
  `company_url eq`) — `attendee_count` is pre-aggregated, read it
  directly. If you instead want per-event grouping over the named-
  attendee rows, group `ds_events_contacts` by event in `query_datasets`.
  The stored event names are prefixed `Event - ` and resolved
  server-side from the human wording.

Persist as `ds_events_contacts`. **Include the Complication 2D page
only if at least one attendance signal is captured.** Below 5 captured
attendances, the sowhat MUST frame the absolute count as a floor and
focus on surface concentration (which events, which roles) rather than
counts.

---

## Phase 2 - Analysis

Read `references/analysis-patterns.md` for the canonical transforms.
The short version:

### 2.1 Title movement → 3 buckets

Classify every in-window event in `ds_title_movement`:

| Bucket | Definition |
|---|---|
| Paired swaps | Old title departed AND a new title arrived in the same function in-window |
| Departed-no-backfill | Title departed, no in-window replacement → trigger Phase 1.13 recoverability check |
| Net-new functions | Title arrived with no prior holder, no departure pair |

For each event, also tag **seniority**: leadership (VP / Director /
Manager+) vs department (IC, individual contributor, even Senior /
Principal / Staff).

Then synthesise the bets into **3-5 strategic threads** that explain
the cluster (e.g. "broaden public-sector GTM" or "build AI ops bench").

**Important:** the departed-no-backfill bucket is NOT a Q+1 watch list.
Most departed-no-backfill titles are short-tenure dedicated seats where
the function continues elsewhere - confirm via Phase 1.13 before
characterising a function as "lost."

### 2.2 Sentiment owned vs external

Split `ds_sentiment` opinionated rows by whether `community_name`
matches the competitor name (owned brand surface) or not (external
developer community). Compute the positive-share-of-opinionated for
each pool:

```
owned_pos_share    = owned_positive_count    / (owned_positive_count    + owned_negative_count)
external_pos_share = external_positive_count / (external_positive_count + external_negative_count)
```

Report as percentages. The brief uses percentages, not raw counts,
everywhere in opinion sections.

### 2.3 Resolved vs Unresolved authors

Join `ds_sentiment` to `ds_authors_resolved` by `linkedin_url`:

| Tag | Definition |
|---|---|
| `resolved` | LinkedIn URL has a `PEOPLE` row AND that row has a current `JOB_COMPANY_NAME` |
| `unresolved-no-employer` | `PEOPLE` row exists but `JOB_COMPANY_NAME IS NULL` |
| `unresolved-no-profile` | LinkedIn URL not in `PEOPLE` at all |

Compute % shares of positive / neutral / negative for each
continent and employer-size bucket from the resolved set. Show the
unresolved bucket muted at the bottom of each cross-tab.

### 2.4 Customer acquisition cohort

For every distinct `company_linkedin_url` in `ds_acquisition`, compute
the company-level `first_seen` (earliest first_seen across all that
company's employees). Then:

1. Filter to companies with `first_seen` in the last 12 months.
2. Join to `ds_acq_firmo` for industry, size, country.
3. For any company with NULL `LOCATION_COUNTRY`, take the modal employee
   country from `ds_geo_fallback`.
4. Bucket by industry into 5-8 categories (see
   `references/analysis-patterns.md` → §4).
5. Bucket by size (SMB 1-200, Mid-market 201-1000, Enterprise 1001+).
6. Bucket by region (North America / EMEA / Asia Pacific / South
   America).
7. Build a monthly stacked-bar histogram: rows = months, stacks = 4-5
   industry buckets.

### 2.5 People movement — joiner / leaver / promotion semantics

`ds_employees` returned by the headcount tool contains all the
person-stint events the brief needs. Three derived buckets feed pages
5, 6 and the exec-summary findings:

| Bucket | Rule | Use on |
|---|---|---|
| **External hires** | `start_date IN window AND end_date IS NULL` AND the person has no other stint at the target whose `end_date` is in window | Page 5 hero stat: "People joined"; page 5 Joiners card (region + seniority breakdown) |
| **Internal promotion** | One person has BOTH a stint ending in window AND a stint starting in window (`b.start_date >= a.end_date`, same `person_linkedin_url`) | Page 6 promotions card only — does NOT appear as a page 5 hero stat AND does NOT appear in either the Joiners or the Leavers card on page 5 |
| **Real departure** | `end_date IN window` AND the person has no active stint at the target (`end_date IS NULL` somewhere else for this person) | Page 5 hero stat: "People left"; page 5 Leavers card (region + seniority breakdown — real departures only) |

The net headcount growth is computed directly from movements — it is
NOT taken from `ds_headcount` snapshot delta:

```
net_headcount_growth = external_hires − real_departures
```

This is the only number shown as the Net stat on page 5. The three
page 5 hero stats are therefore:

| Card | Label | Value |
|---|---|---|
| 1 | People joined | `+{external_hires}` (green) |
| 2 | People left | `−{real_departures}` (red) |
| 3 | Net headcount growth | `+{external_hires − real_departures}` (green) |

The subtext on card 3 explains: "N joined − M left = +Z net new
people over the window." This makes the math explicit and
self-verifiable for the reader. Do NOT show the `ds_headcount`
snapshot endpoint numbers as the primary stat — they can diverge from
the movement-derived delta because LinkedIn profile updates lag behind
real role changes. The movement data is always authoritative.

Internal promotions are role changes within the company and do not
affect headcount. They appear on page 6 only, not in the page 5 hero
row.

#### 2.5.b Reconciling page 3 (titles) with pages 5+6 (people)

The two views count different things and do not arithmetically
reconcile - they are complementary:

| Page | Unit | Counts |
|---|---|---|
| Page 3 (Complication 1A) | Distinct title strings | Net-new = title with no prior holder, first arrived in window. Now-gone = title where the last remaining holder departed in-window. |
| Pages 5+6 (Complication 1B) | Person-stints | Joiners = stint started in window. Leavers = stint ended in window. Promotions = same person with both. |

A single internal promotion creates:
- **Page 3**: +1 net-new title (the new title string), possibly +1 now-gone (if the old title had no other holders)
- **Pages 5/6**: +1 joiner stint, +1 leaver stint, +0 headcount

A single external hire under a title that already exists at the company
creates:
- **Page 3**: 0 net-new, 0 now-gone (title pre-existed)
- **Pages 5/6**: +1 joiner stint, +1 headcount

This is why on a typical Packmint-scale 12-month window, page 3 will
show ~35 net-new titles while page 5 shows ~60 joiner stints. The page
3 number is always smaller because it dedupes within title; page 5 is
larger because every hire-into-existing-title still counts.

The brief should state the source explicitly on each page footer or
sowhat so readers do not try to reconcile manually.

### 2.6 Vendor-trust event detection

Scan opinionated negatives in `ds_sentiment` for distinct
**trust dimensions**:

| Dimension | Signal phrases (regex hints) |
|---|---|
| Vendor ethics | "took credit", "stole", "didn't credit", "CVE credit", "research credit" |
| Product quality | "false positive", "false negative", own admission of issues, bug reports |
| Commercial trust | "tripled", "bill", "pricing", "renewal", "contract", "billing" |

If 3+ distinct dimensions are hit by named verifiable authors with
quotable text, **include the Complication 3 - Vendor-trust events page
and amplify the thread** through the brief (exec summary callout,
finding #01, evidence wall). If fewer than 3 distinct dimensions are
detected, **omit the Complication 3 page entirely** - the brief skips
straight from sentiment to the evidence wall.

---

## Phase 3 - Report assembly

Load `references/design-system.md` for the full HTML template, CSS,
and the per-page layout spec.

### 3.1 Page order

The default brief is **13 pages**. Two pages are conditional and can
extend the brief by one position each:

- **Complication 3 - Vendor-trust events** (default: included only if
  3+ distinct trust dimensions are detected; see Phase 2.6).
- **Complication 1B continued - Departmental change** (default:
  omitted; include when the joiner book is rich enough that the
  function-bar visualisation and the internal-promotion grouping
  earn their own page). When included, the brief runs 14 pages.

| # | Section | Forced page break (`class="page act"`) | Default? |
|---|---|---|---|
| 1 | Cover | first page, no `.act` | always |
| 2 | Executive summary (+ Geographic footprint card) | yes | always |
| 3 | Complication 1A · Org reshape - hero + leadership / dept ledger | yes | always |
| 4 | Complication 1A · Functions added, replaced, lapsed + departed-no-backfill detail | yes | always |
| 5 | Complication 1B · Headcount chart + joiners (external only) + leavers (real departures only) | yes | always |
| 5.5 | **Complication 1B continued · Departmental change + internal promotions** | yes | **conditional** (see decision rule below) |
| 6 | Complication 1C · Captured job postings (window-only) | yes | always |
| 7 | Complication 2A · Customer acquisition motion | yes | always |
| 8 | Complication 2B · Sentiment split | yes | always |
| 9 | Complication 2C · GitHub footprint snapshot | yes | always |
| 10 | **Complication 2D · Event attendance signals** | yes | **conditional** (include if ≥ 1 captured attendance) |
| 11 | Complication 3 · Vendor-trust events | yes | **conditional** (3+ dimensions) |
| 12 | Evidence wall (verbatim quotes) | yes | always |
| 13 | Exhibit A · Company reference card | yes | always |
| 14 | Assumptions and definitions | yes | always |

**Renumbering rule.** When a conditional page is included or omitted,
EVERY subsequent page footer / running header / cross-reference must be
updated. After every insertion or removal:

1. Find every `NN / N` footer/header span and update both the numerator
   (the page's own number) and the denominator (the total).
2. Find every cross-reference of the form "see page N" / "on page N" /
   "(page N)" in action subs, sowhats, and findings — verify each one
   still points to the page it describes.
3. Re-run the Phase 3.5.b cross-page consistency check.

#### Decision rule for the Complication 1B split

Include the 1B-continued page when **all** of the following are true:

- ≥ 15 in-window joiner stints
- ≥ 4 distinct `title_role` functions represented in the joiner mix
- ≥ 3 internal promotions detected

Otherwise the function-bars and promotion-grouping content fold back
into page 5: re-add the joiner-by-function summary line on the
Joiners card, drop the promotions-by-department grid, and include a
short `.sowhat` block.

When the 1B split is enabled, page numbering bumps for every page
from "Open job postings" onward (the brief renders as 14 pages
total). When the vendor-trust page is also omitted, the brief stays
at 13 pages (the split absorbs the freed slot).

### 3.2 Hard layout rules

These come from the canonical Nexagon brief. Violate at peril:

- **A4 paged media.** `@page` block with 18mm margins.
- **Fonts.** Inter for body, Source Serif Pro for `.action-title`
  headings. Both loaded from Google Fonts CDN (only network call the
  template makes).
- **`.act` page break.** Every section above except the cover carries
  `class="page act"`. Without `.act`, sections orphan-flow mid-page.
- **Action titles are full sentences.** Never noun phrases. "Q1 was the
  leadership-replacement quarter" - not "Q1 leadership swaps".
- **Pyramid Principle leads.** Every page opens with its conclusion in
  the action title, then the supporting data.
- **Percentages, not raw counts** in opinion / sentiment sections.
- **No specific channel names.** Never name LinkedIn / Twitter / Slack
  community names in the customer-facing copy. Use "owned brand
  surfaces" vs "external developer communities".
- **No GTM recommendations.** This brief is analytical only.
- **No revenue estimates / dollar amounts.** None. Anywhere.
- **No em dashes.** Use a hyphen. Em dashes are forbidden except in
  verbatim evidence quotes.
- **Verbatim quotes only.** Author LinkedIn handles attached for
  verification. No paraphrasing.
- **Never name the prepared-for tenant in customer-facing copy.** Not
  in action titles, findings, callouts, Complication 3 descriptions,
  Exhibit A timeline, Assumptions list or anywhere else in the brief
  body. When the tenant naturally surfaces (e.g. their CEO publicly
  critiqued the target), describe by category descriptor - "a
  category-incumbent CEO" - never by name. The cover line is generic
  ("Prepared for the requesting tenant") unless `brand_cover: true`.
- **Evidence-wall voices are third-party only.** Never include
  verbatim messages on page 11 from either the target competitor or
  the prepared-for tenant. Both companies are excluded - this applies
  to the author of the post AND to any reposted customer testimonial
  whose attribution names a target or tenant employee. If the only
  available speaker for a trust event is a target or tenant voice,
  describe analytically on page 10 (Complication 3).
- **Unresolved rows shown muted.** Never hidden by default. Use
  `opacity: 0.65` and `color: var(--ink-3)` on those rows. (Caller
  may opt to drop them entirely - see Open knobs.)
- **Page numbers run sequentially** `02 / N` through `N / N`. The
  cover has no footer.

### 3.3 Filling sections from datasets

| Section | Reads from | Key template variables |
|---|---|---|
| Cover | Phase 0 firmo + tenant | `{competitor_name}`, `{window_label}`, `{brief_date}`; cover line "Prepared for the requesting tenant" unless `brand_cover: true` |
| Exec summary | All phases | hero callout if `vendor_trust_count >= 3`, three hero stats, **Geographic footprint card** from `ds_office_segmentation`, 5 numbered findings; the tenant is described by category descriptor where it surfaces |
| Org reshape A | `ds_title_movement` + Phase 2 buckets | IN / OUT / NET-DELTA cards + leadership-vs-dept ledger |
| Org reshape B | Phase-2 buckets + threads + Phase 1.13 recoverability | 3 movement-type cards + departed-no-backfill detail table + 3 strategic threads |
| Headcount + geographic movement (Page 5) | `ds_headcount` + `ds_employees` (filter joiners / leavers) + `ds_q_hires_priors` (origin firmographics) | Headcount chart with X+Y axis titles + Joiners card (by region, notable origins) + Leavers card (by region, captured destinations via `next_company_*`) |
| Departmental change + promotions (Page 6) | `ds_employees` aggregated by `title_role` | Function bar chart (joiner vs leaver stints per department with %) + internal-promotions card grouped by destination department |
| Open jobs (Page 7) | `ds_open_jobs_quarter` | Single table of captured-in-window postings (no active/closed column - we capture existence, not state) |
| Acquisition | `ds_acquisition` ⨝ `ds_acq_firmo` ⨝ `ds_geo_fallback` | monthly stacked bar SVG + size + region cards |
| Sentiment | `ds_sentiment` ⨝ `ds_authors_resolved` | three hero %, continent / size bars, owned-vs-external infographic |
| GitHub | `ds_github` | top countries bar + notable engagers table; country bars MUST sum to the headline engager-rows total (add `Unresolved` bucket if needed) |
| Event attendance (conditional) | `ds_events_contacts` from Phase 1.15 | 3 hero cards (captured attendances / distinct events / region) + detail table; if sample is single-digit, frame as a floor |
| Vendor-trust | Phase-2 detection | 3 trust-dimension cards |
| Evidence wall | `ds_sentiment` filtered to top quotes; authors from origin tenant (`{tenant_linkedin_url}`) or competitor (`{company_linkedin_url}`) excluded as biased | verbatim quote blocks with LinkedIn handles |
| Exhibit A (page 12) | Phase 0 firmo | firmographic cards + product table + timeline |
| Assumptions (page 13) | static | definitional list only — no "What this brief does not cover" subsection, no "Refresh cadence" subsection |

### 3.4 PDF rendering

After the HTML is assembled, render to PDF:

```bash
python3 -c "from weasyprint import HTML; HTML('competitor-brief.html').write_pdf('competitor-brief.pdf')"
```

If WeasyPrint is not installed:
```bash
pip install weasyprint --break-system-packages
```

Present both files to the user via `mcp__cowork__present_files`.

---

## Phase 3.5 - Self-validation pass (MANDATORY)

**Triple-check every fact, every number, every cross-reference before
moving to Phase 4. The brief loses all credibility the moment a careful
reader catches the report contradicting itself.** This phase is not
optional. Run it on every brief, every re-render, every time.

Adopt the mindset: *the reader will add up every bar group, divide every
percentage, cross-check every name and every page-number reference.
Anything that doesn't reconcile is a defect.*

### 3.5.a Arithmetic checks (every page, every bar group)

For each page that contains numeric breakdowns, compute the totals
yourself and compare against the headline number:

1. **Every bar group must sum to its stated total** (and that total must
   match the headline number elsewhere on the page).
   - Page 2 Geographic footprint bars → sum = live headcount.
   - Page 5 Joiners region / seniority / function bars → each sums to
     the External-hires hero (+49 in the canonical example).
   - Page 5 Leavers region / seniority bars → each sums to the Real-
     departures hero (−7 in the canonical example).
   - Page 6 department chart: external column sums to External-hires
     hero on page 5; promotions column sums to the Promotions card
     total below; departures column sums to Real-departures hero on
     page 5.
   - Page 7 Open jobs by-department / by-seniority / by-location each
     sums to the captured-postings count.
   - Page 8 acquisition motion: monthly cohort sums to N (87 in
     example); industry legend sums to N; size-band cuts sum to their
     stated n.
   - Page 9 sentiment: **every row must sum to exactly 100%.** If
     rounding produces 99% or 101%, bump one component by ±1 so the
     row reads 100. Do not ship a 99%/101% row.
   - Page 10 GitHub country bars sum to "Engager rows tracked"
     headline. If they don't, add an `Unresolved` bucket to make them
     reconcile.

2. **Every "X of Y" or "X%" claim must be derived from the actual data
   on the same page.** Recompute: if you claim "UK and US together
   account for 56%", the math is `(UK_engagers + US_engagers) /
   total_engagers`. Do the division yourself. Do not transcribe a
   number you saw earlier — recompute against what's now in the bars.

3. **Hero card numbers must match the chart they sit above/below.**
   On page 5, the "Net headcount change" hero card MUST equal the
   `last_month_headcount − first_month_headcount` shown in the chart.
   These two numbers come from the same source — they MUST agree.

4. **Joiner / Leaver hero cards are movement-derived events; the Net
   card is the snapshot delta.** If those two disagree by more than
   ±3 people, surface the gap in the action title as "the N-person
   gap reflects LinkedIn-profile lag" rather than silently averaging.

### 3.5.b Cross-page consistency checks

The brief is one argument across N pages. Numbers cited on multiple
pages MUST agree (or carry an explicit "different unit" note):

- Live headcount (140 in the canonical example) appears on **page 2
  Geographic footprint**, **page 5 chart endpoint**, **page 14 Exhibit
  A Employees card**, and possibly in **action titles**. All four
  numbers must agree. Round once, then never re-round.
- The 49 / 7 / +Net movement triple appears in **page 2 stat-card sub**
  ("page 5") and in **page 5 hero cards**. Verify both pages cite the
  same numbers.
- The 35 / 11 / +24 title triple appears in **page 2 stat-card sub**
  ("page 3"), **page 3 hero stats**, and possibly the **page 2 action
  sub**. Verify all three.
- The 87 / 6 / 81 acquisition triple appears in **page 2 third hero**,
  **page 2 finding #03**, and **page 8 hero**. All three must agree.
- The 4-dimension vendor-trust callout on **page 2** must match the
  **page 12 action title and cards** (3 cards + 1 callout = 4
  dimensions). Eyebrow must say "Four named vendor-trust dimensions",
  not "Three".
- **Page numbers in cross-references must match actual rendered page
  numbers.** When the brief inserts a new conditional page (e.g.
  Event-attendance), every "see page N" reference downstream shifts —
  audit every cross-reference after re-rendering.

### 3.5.b.1 Acquisition-motion methodology check

The Customer acquisition motion page (Complication 2A) MUST use the
"first-ever-in-window" cohort, NOT the "any-mention-in-window" cohort.
Re-verify by counting both and surfacing the gap:

- `first_ever_count` — from Phase 1.7's mentioner_counts CTE.
- `naive_any_mention_count` — companies with at least one mention in
  the window, regardless of prior history.

If `naive > first_ever`, the gap is companies with pre-window mentions.
The brief MUST cite `first_ever_count` everywhere — page 2 hero #3,
page 2 finding #03, page 2 action title/sub, page 8 hero #1+#2+#3, page
8 by-region and by-size cards, page 14 Exhibit A sowhat. Search the
assembled HTML for the naive count and replace; if you find any
instance, you have a defect.

### 3.5.c Text vs. data contradiction checks

The narrative copy must match the data, not the other way around. If
the narrative was written before the data was finalized, REWRITE the
narrative.

- Roles / titles mentioned in a sowhat must exist in the underlying
  data. ("All four attendees are by sales, marketing, enablement, or
  SRE" — but no attendee is in sales? Wrong. Drop "sales".)
- Geographic claims must match the location data. ("US east-coast
  tilt" — but one attendee is in Colorado? Wrong. Use "US-based" or
  "east-coast plus Mountain".)
- Claims of "cited explicitly in 4+ active job postings" must be
  verifiable in the page 7 table. If the postings table contains zero
  matches, drop the claim — do not let an overclaim sit unsupported.
- Headcount adjectives ("~150 employees", "140-person offsite",
  "around 150") all collapse to the single live snapshot number. Use
  one number throughout.

### 3.5.d Page-fit check (every section is one A4 page)

Render to PDF and count pages. If the rendered PDF has more physical
pages than logical sections, **at least one section is overflowing**
and creating whitespace on the next page. To diagnose:

```python
from weasyprint import HTML
doc = HTML(filename='{competitor_lc}-brief.html').render()
print(f'Physical pages: {len(doc.pages)}')

# Walk pages and find duplicated footers (= overflow)
seen = {}
overflow = []
for i, page in enumerate(doc.pages, 1):
    # extract footer text "NN / N"
    box = page._page_box
    texts = []
    def walk(b):
        if hasattr(b, 'text') and b.text and b.text.strip():
            texts.append(b.text.strip())
        if hasattr(b, 'children'):
            for c in b.children: walk(c)
    walk(box)
    footer = next((t for t in texts if ' / ' in t and t.split(' / ')[-1].isdigit()), None)
    if footer in seen:
        overflow.append(footer)
    seen[footer] = i
print(f'Overflowing sections: {overflow}')
```

If `overflow` is non-empty, trim the listed sections (see Phase 3.2
hard layout rules and the design-system per-page specs). Iterate until
physical pages == logical sections.

Common overflow causes:
- Action sub > 80 words
- Findings (.find) padding > 3pt
- Geographic footprint with no margin tightening
- Departed-no-backfill detail with verbose footnotes
- Footer pushed off by tall action title — reduce action-title font
  from 14pt → 12.5pt on dense pages

### 3.5.e Stale-comment / dev-marker sweep

HTML comments like `<!-- PAGE 10 / COMPLICATION 3 -->` don't render but
mislead anyone editing the file. When pages are reordered or inserted,
update the comments to match the actual footer page number.

### 3.5.f The "would a reader catch this?" final scan

Read the rendered PDF front-to-back **as a skeptical reader**. Stop at
every number and ask: *does this match what I read two pages ago?* Stop
at every "see page N" and verify the page exists and contains what's
referenced. Stop at every chart label and check it matches the bars.

If you would flinch reading it as an outsider, fix it before delivery.

---

## Phase 4 - Pre-delivery checklist

Before presenting, the agent must explicitly verify every item:

- [ ] Every `.page` after the cover has `class="page act"` to force its
      own page break
- [ ] Page numbers run sequentially from `02 / N` through `N / N`; cover
      has no footer
- [ ] No raw counts in opinion / sentiment cuts where percentages are
      more appropriate
- [ ] No specific channel names (LinkedIn, Twitter, specific Slack
      community names) anywhere in customer-facing copy
- [ ] No GTM recommendations or "you should do X" language - the brief
      is analytical only
- [ ] No revenue estimates / dollar amounts
- [ ] No em dashes outside verbatim quotes
- [ ] No GitHub time-trend claims; methodology caveat is present
- [ ] All sentiment quotes are verbatim; LinkedIn handles attached
- [ ] **Evidence wall contains no quotes from competitor employees or
      from prepared-for-tenant employees.** Both are discarded in Phase
      1.10 bias exclusion. Verify by scanning every `.ev.neg` and
      `.ev.pos` block on page 12 (page 11 if vendor-trust events page
      is omitted) against the two excluded `company_linkedin_url`
      values.
- [ ] **Pages 3 and 5/6 numbers come from the same source** -
      `ds_employees` returned by `get_company_headcount`. Page 3 counts
      title strings; pages 5/6 count person-stints. They do not
      arithmetically reconcile by design (a same-person internal
      promotion contributes +1 to page 3 net-new AND +1 joiner / +1
      leaver to page 5). The action-sub on each page must say which
      unit it counts to avoid reader confusion.
- [ ] **Page 5 hero stats: cards 1 + 2 are movement events; card 3 is
      the snapshot delta.** Card 1 = `+{external_hires}` (External hires
      hero), card 2 = `−{real_departures}` (Real departures hero), card
      3 = `+{snapshot_end − snapshot_start}` (Net headcount change). The
      Net card MUST equal the chart's last-month minus first-month
      headcount, NOT `external_hires − real_departures`. If those two
      diverge, surface the gap in the action title (e.g. "the 5-person
      gap to +37 reflects LinkedIn-profile lag"). The Net card subtext
      must state `{start_HC} → {end_HC} = +{net} (+{pct}%). Matches
      the bar chart below.` Do NOT compute the Net from movement math
      — snapshot is canonical.
- [ ] **Page 5 Joiners + Leavers card titles** are plain: `Joiners`
      and `Leavers` (with the IN / OUT pill). Do NOT append a
      parenthetical like `(n = 61 stints; 49 external + 12 internal
      promotions)` — the breakdown lives in the bars, not the title.
- [ ] **Page 5 Joiners card counts external hires only.** The region,
      seniority, and function bars on the Joiners card sum to
      `external_hires` (49 in the canonical example), NOT to `external
      + internal_promotions` (61). Internal promotions live on page 6
      only. Add a small grey subtitle on the card: "{N} external hires
      only. Internal promotions sit on page 6, not in these bars."
- [ ] **Page 5 Joiners card** includes a "By seniority" bar section
      (Leadership VP/Head/Director · Senior/Principal IC · Mid-level IC ·
      Junior/Associate) after the "By region" bars and before the "By
      function" text. Bars are green, proportional to the largest bucket.
- [ ] **Page 5 Leavers card classifies real departures only.**
      Internal promotions are role changes within the company and do
      NOT contribute to the Leavers card (region, seniority, or type
      summary). Including them breaks the logic: a promoted person did
      not leave. Bars are red. Seniority is derived from the actual
      `title_name` and `title_levels` fields on `ds_employees` for the
      real-departure subset.
- [ ] **Page 6 function bar chart** shows THREE bars per department row
      (not two): green (external hires), amber/warn (promotions within
      dept), red (real departures). Row label shows explicit triple:
      "External N · Promoted N · Departed N · Net +N". All bar widths
      are proportional to the same scale (max external hires = 100%).
      Flags any function with zero departures with a `CLEAN` pill (or
      `FLAT` if joiners = departures).
- [ ] **Page 6 promotions card** is grouped by destination function,
      not by month / cluster (e.g. Engineering · 5; Design · 2;
      Customer service · 2; Leadership · 2; Marketing · 1).
- [ ] **Page 6 action title and Biggest-gainer card report
      hires AS external + promotions explicitly.** Example: "Engineering
      added 13 external + 5 internal promotions (18 total)" — not "18
      external hires" (which contradicts the page 6 chart showing 13
      external). Departure counts in the Biggest-gainer subtext refer
      to that function's departures, NOT the company-wide total.
- [ ] **Sentiment rows on page 9 sum to 100%.** No 99% / 101% rows.
      If raw rounding gives 99 or 101, bump one component by ±1.
- [ ] **GitHub country bars on page 10 sum to the "Engager rows
      tracked" headline.** If a bar group sums to 67 but the headline
      says 68, add `+ 1 unresolved` to a bucket so the math closes.
      Every "UK and US together account for X%" claim must be derived
      by dividing the two named-country counts by the headline total.
- [ ] **No mention of the prepared-for tenant anywhere in customer-
      facing copy.** Grep the assembled HTML for the tenant's brand
      name - the only allowed occurrence is the cover line when
      `brand_cover: true` is set; otherwise nowhere.
- [ ] Unresolved rows shown muted (or dropped if `hide_unresolved:
      true` was set), not silently mixed into resolved counts
- [ ] No named accounts in summary stats or strategic-read callouts
      (named accounts allowed only in the cover, the exhibit, the
      evidence wall and the joiner / leaver detail cards on page 5)
- [ ] **Page order: Exhibit A precedes Assumptions.** Exhibit A is
      page 12 (one before last) and Assumptions is page 13 (last).
- [ ] **Page 2 Geographic footprint card** is present below the three
      hero stats and above the Five findings list. The card title reads
      `Geographic footprint · {N} official office(s), {M} employees`.
      The bucket bars come from `ds_office_segmentation`. The narrative
      flags any `Remote / location not disclosed` share above 20%.
- [ ] **Page 2 third hero stat is labelled "12-month indications from
      potential customers"** (not "12-month new external accounts").
      The number 87 (or equivalent) represents companies showing signals
      in the insights pipeline, not closed-won accounts — the language
      must reflect that.
- [ ] **Assumptions and Definitions** block present (not "Sources and
      methodology"). Definitions list ONLY — no "What this brief does
      not cover" subsection, no "Refresh cadence" subsection.
- [ ] Window is strictly enforced - every signal outside
      `window_start` / `window_end` is excluded or explicitly flagged.
      Page footers, running headers and section titles all reflect the
      chosen window mode (`Q1 2026` vs `12-month view`).
- [ ] Vendor-trust page included only if 3+ distinct trust dimensions
      detected
- [ ] **Departed-no-backfill detail table** on page 4 answers, for
      each departed title: (a) is the function still held under a
      different title (Phase 1.13 SUMMARY scan), (b) is there an open
      posting for it, (c) is the function lapsed?
- [ ] PDF rendered successfully; no overflow or whitespace bugs
- [ ] File presented to user with a one-line summary, not a recap of
      the brief contents

---

## Frequently used follow-up patterns

After delivery, the user often asks:

1. **"Can I see the source data for X?"** Re-query the relevant `ds_*`
   dataset with `query_datasets`; show 10-20 rows max.
2. **"Why is row Y unresolved?"** Explain the two unresolved types
   (no-profile vs no-employer) and offer to fold the employer via the
   `ds_geo_fallback` modal-country logic.
3. **"Pull these LinkedIns for me."** Slice the dataset; return as a
   list. Don't enrich (separate paid skill).
4. **"Re-run for Q2."** Recompute the quarter window and re-run Phase 1
   through Phase 4.
5. **"What's the trend over the last 6 months?"** Re-aggregate
   `ds_acquisition` by month with a shorter window.

---

## Open knobs (set explicitly per run)

| Knob | Default | When to change |
|---|---|---|
| `window_mode` | `quarter` | Set `12_month` for an annual review or when the quarter is too thin to read leadership intent from |
| `quarter` | Last completed full calendar quarter | User names a different quarter |
| `brand_cover` | `false` (cover reads "Prepared for the requesting tenant") | Set `true` only when the brief will not leave the tenant's organisation |
| `split_1b` | `auto` (apply the §3.1 thresholds: ≥ 15 joiners + ≥ 4 functions + ≥ 3 promotions). | Set `true` to force the page 5b split regardless; set `false` to keep page 5 monolithic. |
| `hide_unresolved` | `false` (Unresolved rows shown muted at the bottom of cross-tabs) | Set `true` to drop them entirely - cleaner-looking sentiment cards when the unresolved bucket is noisy |
| `hide_n_labels` | `false` (sentiment cross-tabs show `n=X` per row) | Set `true` to drop the `n=X` annotations - cleaner cards, but the reader loses the row weight |
| Vendor-trust threshold | 3 distinct dimensions | The user wants the page included regardless |
| Customer acquisition source | `INSIGHTS_2_EVIDENCES` if allowed; PEOPLE snapshot otherwise; uploaded CSV if provided | The caller forces a path |
| Sentiment scope | Full window universe (unsampled) | Never reduce |
| Industry buckets | 5 (Software / IT services / Public+Healthcare+Cyber+Financial / Media / Other) | Competitor has a heavy bias the bucketing doesn't expose |

## Casing notes on insight values

`ONFIRE.INSIGHTS_2_EVIDENCES.INSIGHT_VALUE` stores the competitor brand
in its **canonical capitalisation** which may not match the friendly
`competitor_name` (e.g. `PackMint` not `Packmint`, `Artifex` not
`artifex`). Use `ILIKE` or canonicalise both sides of the comparison.
A naive `INSIGHT_VALUE = '{competitor_name}'` filter will return zero
rows even when the data is there.

---

## Session changelog (most recent first)

### 2026-05-28 — Acquisition motion: methodology corrected to "first-ever-in-window"

The single biggest defect ever shipped from this skill was the
acquisition-motion methodology. Phase 1.7 was using "any mention in
the 12-month window" — which counts companies as "new" even if they
had Packmint mentions years earlier. On the canonical Packmint
run, that naive query returned **87** companies; the true first-ever-
in-window cohort is **63**. The 24-company gap was being framed in
the brief as "new external accounts" when they were not new.

**Fixes:**
- Phase 1.7 rewritten to use `MIN(start_date)` per company across all
  time, then filter `first_ever_date BETWEEN window_start AND window_end`.
- Production-depth threshold (≥ 2 distinct mentioners in window) is
  applied to the first-ever cohort only — on the canonical run this
  collapses production-depth from 6 to **1** (Bastion Labs). Cloudsift,
  Cloudvault, Cloudward, Voltaic, BotConsulting were all in the old "production-
  depth 6" list because they had prior mentions; under the corrected
  methodology they are excluded.
- A validation check query is included so the agent can quantify the
  gap between any-mention and first-ever counts on every run, and
  surface it in the brief.
- Same-named-consultancy guard: the SQL now excludes
  `linkedin.com/company/{slug}s` (e.g. `packmints`) in addition to
  the competitor's own company URL. The `s` suffix pattern catches
  the Packmint vs Packmints trap and analogous cases.
- Assumptions definition rewritten to be explicit about "first-ever",
  not "earliest first-seen in window" — the old phrasing was ambiguous
  enough to mis-implement.

This also means the Strategic-read sowhat on the acquisition page must
NOT claim "production accounts reveal a security-and-cloud-native
pattern" based on the old 6-company list — under the corrected
methodology there is typically only 1-2 production-depth companies and
the sowhat must reflect that floor honestly. The dominant story in the
corrected acquisition data is the breadth of the single-touch evaluator
pool, not the production-depth cluster.

### 2026-05-27 (v3) — Packmint re-edit round 2: snapshot delta, external-only joiners, event-attendance page, Phase 3.5 self-validation

Continuation of the in-session edit pass on the Packmint 12-month
brief. Every change below was triggered by a real inconsistency a
reader caught in the rendered PDF.

**Phase 3.5 — Self-validation pass (NEW phase, MANDATORY)**
- Inserted between Phase 3 (report assembly) and Phase 4 (pre-delivery
  checklist). The agent MUST triple-check every number, percentage,
  bar-sum and cross-page reference before delivery.
- Five sub-passes: arithmetic checks, cross-page consistency, text-vs-
  data contradiction, page-fit (one A4 per logical section), and stale
  dev-comment sweep.
- Failure mode the phase guards against: hero card #3 says +42 net but
  the chart says +29; UK + US = 56% when the math says 72%; "all four
  attendees are sales, marketing, enablement or SRE" when no attendee
  is in sales; "page 11 evidence wall" reference when the wall is now
  on page 13. Every one of these has shipped in a real brief.

**Page 5 hero card #3 (Net headcount) — switched from movement math to
snapshot delta**
- Was: `external_hires − real_departures` (e.g. 49 − 7 = +42).
- Now: `last_month_HC − first_month_HC` from the chart (e.g. 140 − 103
  = +37 = +35.9%). The hero number MUST equal the chart endpoints.
- The action title surfaces the gap explicitly: "the N-person gap to
  +{snapshot delta} reflects LinkedIn-profile lag".

**Page 5 chart — extended to full 12-month window**
- Was: 10 bars (Jun 25 → Mar 26). Now: 12 bars (Apr 25 → Mar 26).
- Apr 25 baseline bar renders as a minimal grey "base" bar with no
  MoM value. Pitch 52 with bar-width 38 for the 12-bar layout.

**Page 5 Joiners card — bars are EXTERNAL HIRES ONLY**
- Was: region / seniority / function bars summed to 61 (= 49 external +
  12 internal promotions).
- Now: bars sum to 49. A small grey subtitle on the card says: "49
  external hires only. Internal promotions sit on page 6, not in these
  bars." This keeps the Joiners card symmetric with the Leavers card
  (also real-departures only).

**Page 6 — Engineering numbers rewritten to avoid "18 external" overclaim**
- The action title and Biggest-gainer card previously said "Engineering
  added 18 external + 5 internal promotions" / "18 external hires + 5
  internal promotions". Both contradicted the page 6 chart that shows
  Engineering external = 13.
- Now reads "13 external + 5 internal promotions (18 total)" — explicit
  about the breakdown.
- Departure count fixed: "against 2 departures" (Engineering's
  departures) not "over 7 people out" (company-wide total).

**Page 7 — Open jobs Ireland (non-Dublin) bar fixed**
- Was: "Ireland (non-Dublin) 2 (20%)" — bars summed to 90%.
- Now: 3 (30%), bars sum to 100%. Three Ireland AppSec / Data
  postings (Oct, Dec, Jan) correctly counted.

**Page 9 sentiment rows — round so each sums to exactly 100%**
- Mid-market row was 36 / 27 / 36 = 99%. Now 36 / 28 / 36 = 100%.
- General rule for the skill: any cross-tab row that rounds to 99% or
  101% gets one component nudged ±1 to hit 100%.

**Page 10 GitHub — UK+US share corrected and 67-vs-68 reconciled**
- The "UK and US together account for 56% of engager rows" line was
  wrong: 25 + 24 = 49 of 68 = 72%. Fixed to 72%.
- Country bars previously summed to 67 vs the 68 headline. Fixed by
  adding "+ 1 unresolved" to the Other bucket (now 7 engagers), so
  bars sum to 68.

**Page 11 NEW — Event attendance signals (Complication 2D)**
- New full page between GitHub (Complication 2C) and Vendor-trust
  events (Complication 3). Source: `ONFIRE.EVENTS_CONTACTS` filtered
  by `company_linkedin_id`.
- Three-card hero: Captured attendances / Distinct events / Region of
  attendees. Detail table: one row per attendance, columns Event,
  Attendee, Role, Location.
- When the sample is thin (single-digit attendances), the sowhat
  frames it as a floor and does NOT claim coverage or trends — the
  brief should reach for surface concentration, not absolute counts.
- All page numbers downstream of the insertion must be renumbered.
  Audit cross-references ("see page N") after every insertion.

**Page 11 sowhat — text MUST match the data**
- Old text claimed "sales, marketing, enablement, or SRE roles"
  attended events. None of the four attendees was in sales — wrong.
- Fixed to "marketing, enablement, events, or SRE roles" and dropped
  the "US east-coast" geo claim (one attendee is in Colorado, not the
  east coast). Now reads "three east-coast — MA, PA, MD — plus one
  in Colorado".

**Page 12 vendor-trust — eyebrow + action sub corrected**
- Eyebrow was "Three named vendor-trust dimensions" but content shows
  four. Fixed to "Four named vendor-trust dimensions".
- Action sub now references the correct evidence-wall page number
  (13, not 11) after the event-attendance insertion.

**Page 14 Exhibit A — drop unsupported "Packmint 2.0" claim**
- Sowhat claimed "Packmint 2.0 platform build (cited explicitly in
  4+ active job postings)" — but the page 7 postings table contains
  no such citation. Removed the parenthetical; replaced with the
  general "this platform-and-GTM build".
- Headcount language standardized to single number (140 throughout —
  no more "~150 / 140-person offsite / size band 51-200" mixing).

**Page 2 — consolidated to fit one A4**
- Findings reduced from five to four (combined the durable-sentiment
  finding with the four-trust-frictions finding). Eyebrow updated to
  "Four findings".
- Action title font reduced to 12.5pt with line-height 1.2 on dense
  pages. `.find` padding reduced (5pt → 2pt), font-size 14pt → 10pt
  on the numeral.
- Geographic footprint card padding tightened.

**Page-fit rule (NEW)**
- Each logical section MUST fit on one A4 page. If physical PDF page
  count > logical section count, at least one section is overflowing.
- Use the WeasyPrint diagnostic in Phase 3.5.d to identify overflowing
  sections by footer-text duplication.
- Common trim levers: `.action-sub` 8pt → 7pt, `.find` padding 5pt →
  2pt, action-title font 14pt → 12.5pt, drop strategic-thread cards
  in favour of a consolidated sowhat.

**Indications terminology (across page 2 + page 8 + page 14)**
- The customer-acquisition headline (87 companies) is "potential
  customer indications" — NOT "new external accounts" (implies
  closed-won), NOT "first-seen in our insights pipeline" (jargon).
- Card label: "12-month indications from potential customers".
- Action title verb: "surfaced indications from" not "acquired" /
  "first-seen".

### 2026-05-27 — Packmint re-edit: page 2 geo card, leavers logic fix, page 12/13 swap

All changes shaken out by an in-session edit pass on the Packmint
12-month brief.

**Page 2 — Geographic footprint card (new)**
- New full-width card on the executive summary, between the three
  hero stats and the Five findings. Fed by `ds_office_segmentation`
  (Phase 1.14): one bucket per `search_offices` hit + distributed
  clusters from `ONFIRE.PEOPLE` + a `Remote / location not disclosed`
  bucket equal to `headcount_total − sum(matched_clusters)`.
- HQ bucket gets a green bar + `HQ` pill; distributed hubs get a
  grey-blue bar + `distributed` pill; remote/unknown is muted grey.
- Narrative flags any `Remote / location not disclosed` share above
  20% — common for cloud-native dev-tools scale-ups.

**Page 2 — third hero stat renamed**
- Was: `12-month new external accounts`. Now:
  `12-month indications from potential customers`. The number 87 (or
  equivalent) is companies showing signals in the insights pipeline,
  not closed-won accounts. Card subtext now reads "Distinct external
  companies showing {competitor} indications in our insights pipeline.
  N at production-depth; M still evaluators." The executive-summary
  action title uses "surfaced indications from {N} potential customer
  accounts" — not "acquired {N} net-new external accounts".

**Page 5 — Joiners / Leavers card titles**
- Card titles are plain `Joiners` and `Leavers` (with IN / OUT pill).
  Drop the `(n = 61 stints; 49 external + 12 internal promotions)`
  parenthetical — the breakdown lives in the bars, not the title.
- Customer-facing text now uses "people" instead of "stints" for count
  framing ("11 net-new people", "12 of 61 people are APAC", etc.).
  The methodology language in Phase 2.5 keeps "stints" as the technical
  term for the underlying person-stint events.

**Page 5 — Leavers card classifies real departures only**
- Previously the Leavers card mixed real departures with internal
  promotion old-titles ("both contribute to the leaver stint pool").
  That breaks the logic — a promoted person did not leave. The card
  now reflects real departures only, with a `By type:` line trimmed to
  just "{N} real departures: 1 Head of, 1 Director, 2 managers, …" and
  no reference to internal-promotion artifacts. Internal promotions
  remain on the Page 6 promotions card.

**Page 5 — Net headcount subtext**
- Card 3 subtext is just `{N} joined − {M} left = +{Z} net new people
  over the window.` Drop the trailing `consistent with the monthly
  chart below` — the chart is on the same page and the redundant
  cross-reference reads as filler.

**Page order — Exhibit A and Assumptions swapped**
- Was: page 12 Assumptions, page 13 Exhibit A. Now: page 12 Exhibit A,
  page 13 Assumptions. The brief closes on the definitional appendix
  rather than the firmographic card. When vendor-trust is omitted the
  numbering shifts but the relative order holds.

**Page 13 (Assumptions) — subsections removed**
- Removed the `What this brief does not cover` subsection and the
  `Refresh cadence` subsection. The page is the canonical definitions
  list and nothing else. Action title trimmed to "What each term in
  the brief means."

**Phase 1.14 — Office segmentation (new step)**
- New Phase 1 step combining `search_offices`, the location-distribution
  query on `ONFIRE.PEOPLE`, and the bucket-assignment rules from the
  `office-segmentation` skill. Output: `ds_office_segmentation`,
  feeding the page 2 Geographic footprint card.
- Use `JOB_COMPANY_LINKEDIN_ID = {company_linkedin_id}` in the location
  query alongside the slug `ILIKE` — slug-only matches pollute the
  result with same-named companies (e.g. `packmint` vs `packmints`).

### 2026-05-26 (v2) — Page 5/6 layout overhaul from Packmint post-review

**Page 5 hero stats — math must close**
- The three hero cards are now: **People joined** (`+N`, green) /
  **People left** (`−M`, red) / **Net headcount growth** (`+{N−M}`,
  green). The net is always `external_hires − real_departures` — pure
  movement math. The `ds_headcount` snapshot delta is no longer the
  source for the net card because snapshot counts lag behind movement
  records. The subtext on the net card states the arithmetic explicitly.
- Internal promotions do NOT appear as a hero stat on page 5 — they are
  role changes within the company and do not affect headcount.
- Removed all "snapshot lag ±5" language from the reconciliation rule
  and the pre-delivery checklist. The movement-derived delta is
  authoritative; snapshot divergences are a data-quality signal, not
  an expected tolerance.

**Page 5 Joiners + Leavers cards — seniority section added**
- Both the Joiners (green) card and the Leavers (red) card now include
  a **"By seniority"** bar section placed between the "By region" bars
  and the "By function" / "By type" summary text.
- Four tiers: Leadership (VP / Head of / Director) · Senior / Principal
  IC · Mid-level IC · Junior / Associate. Derived from `title_name` and
  `title_levels` on `ds_employees`.
- Joiner bars are green; Leaver bars are red. All bars proportional to
  the largest bucket in that card (= 100%).

**Page 6 department chart — 3 bars per row**
- The "Joiners vs leavers" chart is replaced by a three-bar chart:
  1. **Green** — External hires into this department
  2. **Amber** — Internal promotions within / into this department
  3. **Red** — Real departures from this department
- Row label changes from "Joiners N · Leavers N · Net +N" to
  "External N · Promoted N · Departed N · Net +N".
- All bar widths share the same scale (max external hires = 100%).
- Departments with zero departures get a `CLEAN` pill; departments where
  external hires = real departures get a `FLAT` pill.
- The chart title changes from "Joiners vs leavers by department
  (stints)" to "External hires · Internal promotions · Real departures
  by department".
- Legend shows three swatches (green / amber / red).

### 2026-05-26 — Packmint / Artifex brief learnings

Folded in from the Packmint × Artifex session. Every change below was
shaken out by a real brief that exposed a gap.

**Editorial / tenant policy**
- **Tenant is never named in customer-facing copy.** Action titles,
  findings, callouts, Complication 3 descriptions, Exhibit A timeline,
  Assumptions list - all must use category descriptors ("a category-
  incumbent CEO") instead of the tenant brand name. Cover line is
  generic by default; opt in via `brand_cover: true`. (Phase 3.2 hard
  rules + design-system Forbidden patterns + Phase 4 checklist.)
- **Evidence wall is third-party only.** Target competitor employees
  AND tenant employees are both excluded from verbatim quotes. Reposted
  customer testimonials get re-attributed to the underlying customer
  speaker. (design-system Page 11 spec + Phase 1.10 bias exclusion
  query.)

**Window modes**
- New `window_mode` knob: `quarter` (default) or `12_month`. The 12-
  month mode rewrites the page footers, headers, Assumptions block and
  every action title to read "12 months ending {Mon} {YYYY}" instead
  of "Q{N} {YYYY}". The customer-acquisition motion always uses a
  trailing 12-month series regardless of mode.

**Data sources**
- **Page 3 (titles) and Pages 5/5b (people) both source `ds_employees`
  returned by `get_company_headcount`** - which is backed by
  `ONFIRE.PEOPLE_GRAND_EXPERIENCES` + `ONFIRE.PEOPLE_GRAND` (tool-
  managed; no `ask_onfire` semantic entity). Same source, different
  units (title strings vs person-stints) - they're complementary not
  reconcilable. Each page must state its unit in the action-sub.
- **Open job postings: `SILVER.JOB_POST.STG_JOB_POSTS`** (Query 04).
  No `DELETED_AT` column - use `APPLICATION_ACTIVE = 1` for the active
  cut, but the brief currently disowns the active flag because the
  index only captures posting existence, not real-time open/closed
  state. Page 7 sums captured-in-window postings only, no active
  column.
- **`INSIGHT_VALUE` casing pitfall** on `ONFIRE.INSIGHTS_2_EVIDENCES`.
  The competitor brand may be stored in canonical capitalisation
  (`PackMint`, `Artifex`) that doesn't match `competitor_name`. Use
  `ILIKE`, never exact-match equality. (Casing notes section + Query
  07.)

**People-movement analysis (new)**
- Three derived buckets from `ds_employees`: **external hires**,
  **internal promotions**, **real departures** (Phase 2.5).
- Internal promotions = same person with both an in-window stint end
  and an in-window stint start. Detected via self-join on
  `person_linkedin_url`.
- Reconciliation rule: `external_hires - real_departures ≈
  headcount_delta` within ±5 (snapshot lag).

**Page 5 / 5b split**
- Page 5 stays focused on **geographic movement** (region bars, origins,
  destinations, headcount chart).
- New conditional Page 5b carries **departmental change** (function
  bars with %) and **internal promotions grouped by destination
  function**. Inclusion rule in §3.1.

**Departed-no-backfill recoverability (page 4)**
- Page 4 carries a detail table for every departed-no-backfill title:
  is the function still held by a current employee under a different
  title (Phase 1.13a SUMMARY scan, NOT title-keyword search), is there
  an open posting trying to backfill, or has the function lapsed.
- Distinguish same-person promotion vs different-person parallel
  coverage explicitly (§9.4 of analysis-patterns).

**Chart polish**
- Headcount chart on page 5: X-axis title ("Month · {start} - {end}")
  and Y-axis title ("MoM growth %") rotated -90° at the left edge.
  Use `viewBox="0 0 700 138"` with `max-height: 80pt` so font glyphs
  scale up visibly while the card stays compact.
- Page 6 function bars: explicit `Joiners X (Y%) · Leavers Z (W%) ·
  Net +N` triples on every row; FLAT pill for any function with
  joiners = leavers.
