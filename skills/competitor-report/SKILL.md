---
name: competitor-report
description: Generate a full client-grade Competitor Intelligence Brief for a single competitor company, scoped strictly to the last completed quarter. Produces an A4 HTML and an optional PDF using a McKinsey-style consulting layout (Pyramid Principle lead, SCR narrative arc, action titles). The brief covers org reshape (title movement by leadership vs department, paired swaps vs net-new functions), Q-hires with geo, open job postings, customer acquisition motion (last 12 months, monthly stacked by industry), market sentiment split (owned brand surfaces vs external developer communities), GitHub footprint snapshot, vendor-trust events, an evidence wall of verbatim quotes, an Assumptions and Definitions back matter, and a Company Reference Card exhibit. Use this skill whenever the user asks to "build a competitor brief", "competitive intelligence on X", "deep dive on competitor X", "Sonatype-style report on X", "scan competitor X for the last quarter", "what's happening at competitor Y", or any phrasing that mixes a vendor name with a request for an analytical multi-section report on their org and market posture.
---

# Competitor Intelligence Brief

## What this skill does

Given a **competitor company name** (e.g. `Sonatype`, `Snyk`, `JFrog`),
this skill produces a 12-13 page A4 PDF analytical brief covering the
competitor's last completed quarter. The deliverable is internal-facing
(prepared FOR the caller's tenant, ABOUT a non-customer vendor) and
written in a consulting-firm idiom - Pyramid Principle, SCR (Situation /
Complication / Resolution) narrative arc, McKinsey-style action titles.

The brief is **analytical only**. No GTM plays, no recommendations, no
revenue estimates. The reader synthesises the implications themselves.

---

## Inputs

| Input | Required | Example | Default |
|-------|----------|---------|---------|
| `competitor_name` | Yes | `Sonatype` | - |
| `company_linkedin_url` | Optional | `linkedin.com/company/sonatype` | resolved via `match_company` |
| `quarter` | Optional | `Q1 2026` | the last fully completed calendar quarter |
| `prepared_for_tenant` | Optional | `jfrog` | from `get_current_tenant` |

If `quarter` is not supplied, the skill computes it from today's date.
Today is in Q2 2026 → last completed quarter is Q1 2026 (Jan 1 - Mar 31).

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

### 0.1 Compute the quarter window

In bash:
```bash
TODAY=$(date +%Y-%m-%d)
# Default = last completed full quarter
# Example: today 2026-05-24 → window 2026-01-01 .. 2026-03-31 (Q1 2026)
```

Persist three values for the rest of the run:
- `q_start` (e.g. `2026-01-01`)
- `q_end` (e.g. `2026-03-31`)
- `q_label` (e.g. `Q1 2026`)

The rolling 12-month window for the customer-acquisition motion is
`q_end - 12 months .. q_end` (e.g. `2025-04-01 .. 2026-03-31`).

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

Use the tenant's `display_name` for the cover's "Prepared for X" line.
Store the tenant's `company_linkedin_url` (lowercased) as `{tenant_linkedin_url}` -
used in Phase 1.10 to exclude biased sentiment authors from the evidence wall.

---

## Phase 1 - Data gathering

Each query runs through `query_onfire` and persists its result as a
dataset. Track the dataset IDs - the analysis phase joins them.

**Important:** all `query_onfire` calls must use 3-part `ONFIRE.*` table
names and include a `DELETED_AT IS NULL` filter where applicable.

### 1.1 Headcount trend (12 months)

See `references/snowflake-queries.md` → query 01.

```sql
SELECT TIME_PERIOD, STR_VALUE AS pct_change
FROM ONFIRE.GROWTH_TOTAL_HEADCOUNT_MONTHLY
WHERE LOWER(COMPANY_LINKEDIN_URL) = '{company_linkedin_url}'
  AND DELETED_AT IS NULL
  AND STR_VALUE IS NOT NULL
  AND TIME_PERIOD BETWEEN DATEADD(MONTH, -12, '{q_end}') AND '{q_end}'
ORDER BY TIME_PERIOD
```

Persists as `ds_headcount`. Pull in-quarter month rows for the
exec-summary "+1.4% Q1 net" callout.

### 1.2 Title movement (target quarter only)

See `references/snowflake-queries.md` → query 02.

Classify every Q-event into:
- **Net-new title** - title string had no prior holder
- **Now-gone title** - last remaining holder of an existing title departed

Persists as `ds_title_movement`. **Strictly bounded to the target
quarter** - any event outside is excluded.

### 1.3 Quarter hires with geo

See `references/snowflake-queries.md` → query 03.

`PEOPLE_EXPERIENCES` rows with `START_DATE` in the quarter and
`END_DATE IS NULL`, joined to `PEOPLE` for `LOCATION_COUNTRY`. Persists
as `ds_q_hires`.

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

---

## Phase 2 - Analysis

Read `references/analysis-patterns.md` for the canonical transforms.
The short version:

### 2.1 Title movement → 3 buckets

Classify every Q-event in `ds_title_movement`:

| Bucket | Definition |
|---|---|
| Paired swaps | Old title departed AND a new title arrived in the same function in-quarter |
| Departed-no-backfill | Title departed, no Q-replacement seen → Q+1 hiring watch |
| Net-new functions | Title arrived with no prior holder, no departure pair |

For each Q-event, also tag **seniority**: leadership (VP / Director /
Manager+) vs department (IC, individual contributor, even Senior /
Principal / Staff).

Then synthesise the bets into **3-5 strategic threads** that explain
the cluster (e.g. "broaden public-sector GTM" or "build AI ops bench").

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

### 2.5 Vendor-trust event detection

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

| # | Section | Forced page break (`class="page act"`) |
|---|---|---|
| 1 | Cover | first page, no `.act` |
| 2 | Executive summary | yes |
| 3 | Complication 1A · Org reshape - hero + leadership / dept ledger | yes |
| 4 | Complication 1A · Movement types + strategic threads | yes |
| 5 | Complication 1B · Geo + Q-hires + headcount trend | yes |
| 6 | Complication 1C · Open job postings | yes |
| 7 | Complication 2A · Customer acquisition motion | yes |
| 8 | Complication 2B · Sentiment split | yes |
| 9 | Complication 2C · GitHub footprint snapshot | yes |
| 10 | Complication 3 · Vendor-trust events (conditional) | yes |
| 11 | Evidence wall (verbatim quotes) | yes |
| 12 | Assumptions and definitions | yes |
| 13 | Exhibit A · Company reference card | yes |

The conditional page 10 shifts everything below by one position when
omitted.

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
- **Unresolved rows shown muted.** Never hidden. Use `opacity: 0.65`
  and `color: var(--ink-3)` on those rows.
- **Page numbers run sequentially** `02 / N` through `N / N`. The
  cover has no footer.

### 3.3 Filling sections from datasets

| Section | Reads from | Key template variables |
|---|---|---|
| Cover | Phase 0 firmo + tenant | `{competitor_name}`, `{prepared_for}`, `{q_label}`, `{brief_date}` |
| Exec summary | All phases | hero callout if `vendor_trust_count >= 3`, three hero stats, 5 numbered findings |
| Org reshape A | `ds_title_movement` + Phase 2 buckets | IN / OUT / NET-DELTA cards + leadership-vs-dept ledger |
| Org reshape B | Phase-2 buckets + threads | 3 movement-type cards + 3 strategic threads |
| Geo + GTM | `ds_q_hires` + `ds_headcount` | continent bars + headcount % bars |
| Open jobs | `ds_open_jobs_quarter` + `ds_open_jobs_active` | Q-window postings table + active-set grouped by function |
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
- [ ] Evidence wall contains no quotes from origin-tenant employees or
      competitor employees (both discarded in Phase 1.10 bias exclusion)
- [ ] Unresolved rows shown muted, not hidden
- [ ] No named accounts in summary stats or strategic-read callouts
      (named accounts allowed only in the cover, the exhibit, and the
      evidence wall)
- [ ] **Assumptions and Definitions** block present (not "Sources and
      methodology")
- [ ] Quarter window is strictly enforced - every signal outside the
      window is excluded or explicitly flagged
- [ ] Vendor-trust page included only if 3+ distinct trust dimensions
      detected
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
| Quarter window | last completed full calendar quarter | user names a different quarter |
| Vendor-trust threshold | 3 distinct dimensions | the user wants the page included regardless |
| Customer acquisition source | `INSIGHTS_2_EVIDENCES` if allowed; PEOPLE snapshot otherwise; uploaded CSV if provided | the caller forces a path |
| Sentiment scope | full quarter universe (unsampled) | never reduce |
| Industry buckets | 5 (Software / IT services / Public+Healthcare+Cyber+Financial / Media / Other) | competitor has a heavy bias the bucketing doesn't expose |
