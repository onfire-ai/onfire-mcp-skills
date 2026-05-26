---
name: competitor-report
description: Generate a full client-grade Competitor Intelligence Brief for a single competitor company. The window is configurable: either the last completed calendar quarter (default) or the trailing 12 months ending the last completed quarter. Produces an A4 HTML and an optional PDF using a McKinsey-style consulting layout (Pyramid Principle lead, SCR narrative arc, action titles). The brief covers org reshape (title movement by leadership vs department, paired swaps vs net-new functions, departed-no-backfill recoverability check), hires with geo + function + origin-company size, leavers with destinations, open job postings, customer acquisition motion (12-month measured motion from the insights pipeline, monthly stacked by industry), market sentiment split (owned brand surfaces vs external developer communities), GitHub footprint snapshot, vendor-trust events, an evidence wall of verbatim third-party-only quotes (target competitor and prepared-for tenant employees both excluded), an Assumptions and Definitions back matter, and a Company Reference Card exhibit. Use this skill whenever the user asks to "build a competitor brief", "competitive intelligence on X", "deep dive on competitor X", "Sonatype-style report on X", "scan competitor X for the last quarter", "12-month view of competitor Y", "what's happening at competitor Y", or any phrasing that mixes a vendor name with a request for an analytical multi-section report on their org and market posture.
---

# Competitor Intelligence Brief

## What this skill does

Given a **competitor company name** (e.g. `Sonatype`, `Snyk`, `JFrog`),
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
| `competitor_name` | Yes | `Sonatype` | - |
| `company_linkedin_url` | Optional | `linkedin.com/company/sonatype` | resolved via `match_company` |
| `window_mode` | Optional | `quarter` or `12_month` | `quarter` |
| `quarter` | Optional | `Q1 2026` | the last fully completed calendar quarter |
| `prepared_for_tenant` | Optional | `jfrog` | from `get_current_tenant` |
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

## The 5 phases

The skill works through **five phases in strict order**. Each phase has
mandatory inputs from the previous phase. Do not skip ahead; the
analysis phase depends on every data slice being persisted as a dataset.

```
Phase 0  Scope and identity            (~1 minute)
Phase 1  Data gathering                (~5-8 minutes)
Phase 2  Analysis                       (~3-5 minutes)
Phase 3  Report assembly                (~3-5 minutes)
Phase 4  Pre-delivery checklist         (~1 minute)
```

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

Each query runs through `query_onfire` and persists its result as a
dataset. Track the dataset IDs - the analysis phase joins them.

**Important:** all `query_onfire` calls must use 3-part `ONFIRE.*` table
names and include a `DELETED_AT IS NULL` filter where applicable.

### 1.1 Headcount trend + employee roster (single call — primary source for org-growth changes)

See `references/snowflake-queries.md` → query 01.

A single `get_company_headcount` call is the **primary source for all
org-growth changes** in the brief — monthly headcount trend, joiners,
leavers, joiner origins, and leaver destinations. It powers Phase 1.1
(headcount), Phase 1.3 (Q-hires), and Phase 1.12 (leavers + their
destinations). No separate `query_onfire` is needed for any of those.

Headcount is derived from tenure intervals in
`ONFIRE.PEOPLE_GRAND_EXPERIENCES`; the employee roster joins each
tenure to `ONFIRE.PEOPLE_GRAND` for location and to **symmetric
self-joins** on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` for both the
immediately-prior company (joiner origin) and the immediately-next
company (leaver destination). Both tables are tool-managed —
do **not** attempt to query them via `query_onfire`.

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
`PEOPLE_EXPERIENCES` via `query_onfire`.

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

If `INSIGHTS_2_EVIDENCES` is in the allowed-tables list for
`query_onfire`, prefer this query:

```sql
SELECT PERSON_LINKEDIN_URL, COMPANY_LINKEDIN_URL, MIN(START_DATE) AS first_seen
FROM ONFIRE.INSIGHTS_2_EVIDENCES
WHERE INSIGHT_VALUE = '{competitor_name}'
  AND START_DATE BETWEEN DATEADD(MONTH, -12, '{q_end}') AND '{q_end}'
GROUP BY PERSON_LINKEDIN_URL, COMPANY_LINKEDIN_URL
```

If the table is NOT allowlisted, fall back to a `PEOPLE`-based static
snapshot (any company with employees whose `JOB_SUMMARY` mentions the
competitor as a whole word) and label the section as "snapshot, not
motion" in the brief. The fallback **must** be flagged in the
Assumptions and Definitions block.

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
never a sample. The brief makes claims like "every Sonatype-mentioning
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
join the distinct `next_company_linkedin_url` values to
`ONFIRE.COMPANIES` via a follow-up `query_onfire` call (batch in groups
of 30-50). Many leavers will not have a captured next role — call the
gap out explicitly ("6 of 18 destinations captured").

Used in: Complication 1B leavers card; Phase 2 strategic-thread
synthesis ("where are senior people going?").

### 1.13 Departed-no-backfill recoverability (only if Phase 2 detects any)

See `references/snowflake-queries.md` → query 13.

For each title classified as `departed-no-backfill` in Phase 2.1, run
two checks:

1. **Current-holder scan.** Query `ONFIRE.PEOPLE_EXPERIENCES.SUMMARY`
   and `ONFIRE.PEOPLE.HEADLINE` / `JOB_SUMMARY` for current target
   employees whose free-text mentions the function's work (not just
   keyword on title). A title-keyword search misses people doing the
   work under a different title.
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
| **External hires** | `start_date IN window AND end_date IS NULL` AND the person has no other stint at the target whose `end_date` is in window | Page 5 hero stat: "People joined"; pages 5+6 joiner cards |
| **Internal promotion** | One person has BOTH a stint ending in window AND a stint starting in window (`b.start_date >= a.end_date`, same `person_linkedin_url`) | Page 6 promotions card only - does NOT appear as a page 5 hero stat |
| **Real departure** | `end_date IN window` AND the person has no active stint at the target (`end_date IS NULL` somewhere else for this person) | Page 5 hero stat: "People left"; page 5 leavers card |

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

This is why on a typical Cloudsmith-scale 12-month window, page 3 will
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
| 2 | Executive summary | yes | always |
| 3 | Complication 1A · Org reshape - hero + leadership / dept ledger | yes | always |
| 4 | Complication 1A · Movement types + departed-no-backfill detail + strategic threads | yes | always |
| 5 | Complication 1B · Headcount chart + joiners + leavers | yes | always |
| 5.5 | **Complication 1B continued · Departmental change + internal promotions** | yes | **conditional** (see decision rule below) |
| 6 | Complication 1C · Captured job postings (window-only) | yes | always |
| 7 | Complication 2A · Customer acquisition motion | yes | always |
| 8 | Complication 2B · Sentiment split | yes | always |
| 9 | Complication 2C · GitHub footprint snapshot | yes | always |
| 10 | Complication 3 · Vendor-trust events | yes | **conditional** (3+ dimensions) |
| 11 | Evidence wall (verbatim quotes) | yes | always |
| 12 | Assumptions and definitions | yes | always |
| 13 | Exhibit A · Company reference card | yes | always |

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

These come from the canonical Sonatype brief. Violate at peril:

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
| Exec summary | All phases | hero callout if `vendor_trust_count >= 3`, three hero stats, 5 numbered findings; the tenant is described by category descriptor where it surfaces |
| Org reshape A | `ds_title_movement` + Phase 2 buckets | IN / OUT / NET-DELTA cards + leadership-vs-dept ledger |
| Org reshape B | Phase-2 buckets + threads + Phase 1.13 recoverability | 3 movement-type cards + departed-no-backfill detail table + 3 strategic threads |
| Headcount + geographic movement (Page 5) | `ds_headcount` + `ds_employees` (filter joiners / leavers) + `ds_q_hires_priors` (origin firmographics) | Headcount chart with X+Y axis titles + Joiners card (by region, notable origins) + Leavers card (by region, captured destinations via `next_company_*`) |
| Departmental change + promotions (Page 6) | `ds_employees` aggregated by `title_role` | Function bar chart (joiner vs leaver stints per department with %) + internal-promotions card grouped by destination department |
| Open jobs (Page 7) | `ds_open_jobs_quarter` | Single table of captured-in-window postings (no active/closed column - we capture existence, not state) |
| Acquisition | `ds_acquisition` ⨝ `ds_acq_firmo` ⨝ `ds_geo_fallback` | monthly stacked bar SVG + size + region cards |
| Sentiment | `ds_sentiment` ⨝ `ds_authors_resolved` | three hero %, continent / size bars, owned-vs-external infographic |
| GitHub | `ds_github` | top countries bar + notable engagers table |
| Vendor-trust | Phase-2 detection | 3 trust-dimension cards |
| Evidence wall | `ds_sentiment` filtered to top quotes; authors from origin tenant (`{tenant_linkedin_url}`) or competitor (`{company_linkedin_url}`) excluded as biased | verbatim quote blocks with LinkedIn handles |
| Assumptions | static | definitional list (no source counts) |
| Exhibit A | Phase 0 firmo | firmographic cards + product table + timeline |

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
- [ ] **Page 5 hero stats show movement-derived math:** card 1 =
      `+{external_hires}` (People joined), card 2 = `−{real_departures}`
      (People left), card 3 = `+{external_hires − real_departures}` (Net
      headcount growth). Card 3 subtext must state the arithmetic
      explicitly. `ds_headcount` snapshot numbers must NOT appear as the
      primary net stat.
- [ ] **Page 5 Joiners card** includes a "By seniority" bar section
      (Leadership VP/Head/Director · Senior/Principal IC · Mid-level IC ·
      Junior/Associate) after the "By region" bars and before the "By
      function" text. Bars are green, proportional to the largest bucket.
- [ ] **Page 5 Leavers card** includes a "By seniority" bar section
      (same four tiers) after the "By region" bars and before the "By
      type" text. Bars are red. Seniority is derived from the actual
      `title_name` and `title_levels` fields on `ds_employees`; internal
      promotion old-titles and real departures are classified together
      since both contribute to the leaver stint pool.
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
- [ ] **No mention of the prepared-for tenant anywhere in customer-
      facing copy.** Grep the assembled HTML for the tenant's brand
      name - the only allowed occurrence is the cover line when
      `brand_cover: true` is set; otherwise nowhere.
- [ ] Unresolved rows shown muted (or dropped if `hide_unresolved:
      true` was set), not silently mixed into resolved counts
- [ ] No named accounts in summary stats or strategic-read callouts
      (named accounts allowed only in the cover, the exhibit, the
      evidence wall and the joiner / leaver detail cards on page 5)
- [ ] **Assumptions and Definitions** block present (not "Sources and
      methodology")
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
`competitor_name` (e.g. `CloudSmith` not `Cloudsmith`, `JFrog` not
`Jfrog`). Use `ILIKE` or canonicalise both sides of the comparison.
A naive `INSIGHT_VALUE = '{competitor_name}'` filter will return zero
rows even when the data is there.

---

## Session changelog (most recent first)

### 2026-05-26 (v2) — Page 5/6 layout overhaul from Cloudsmith post-review

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

### 2026-05-26 — Cloudsmith / JFrog brief learnings

Folded in from the Cloudsmith × JFrog session. Every change below was
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
  managed, not exposed via `query_onfire`). Same source, different
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
  (`CloudSmith`, `JFrog`) that doesn't match `competitor_name`. Use
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
