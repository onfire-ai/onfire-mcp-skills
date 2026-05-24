# Analysis Patterns — Competitor Report

This file is the playbook for turning raw data into the brief's
conclusions. Every transform here is canonical - re-running the same
slice on a different competitor should reach the same kind of
synthesis if the data has the same shape.

---

## 1. Title movement → 3 buckets + 3-5 strategic threads

Input: `ds_title_movement` (one row per Q-event:
`event_type ∈ {net_new, now_gone}`, `title`, `event_date`).

### 1.1 Tag every event with seniority

| Title contains | Seniority |
|---|---|
| `vp`, `vice president`, `chief`, `cto`, `cfo`, `coo`, `ceo`, `director`, `head of`, `manager` (lowercased, word-boundary match) | **Leadership** |
| Everything else (Senior, Principal, Staff, Engineer, Designer, etc.) | **Department (IC)** |

Note: "Senior", "Principal", and "Staff" alone are senior-IC levels,
NOT management. Only `manager` and higher count as leadership.

### 1.2 Pair Q-events into movement-type buckets

| Bucket | Rule |
|---|---|
| **Paired swap** | A `now_gone` title + a `net_new` title in the same broad function area in the same quarter. Function area = first 1-2 meaningful tokens (e.g. "Federal Sales" ↔ "Public Sector" → both GTM-public-sector) |
| **Departed-no-backfill** | A `now_gone` title with no `net_new` Q-pair |
| **Net-new function** | A `net_new` title with no `now_gone` Q-pair |

A swap is by definition a single old→new pair. Track them as
`(old_title, new_title, function_area)`.

### 1.3 Generate 3-5 strategic threads

Read the swaps + net-new functions together. Group them into 3-5
themes. Common patterns:

- **GTM expansion** - "Regional VP X" → "VP X+adjacent" reads as
  broadening a sales motion.
- **Top-layer build** - multiple Director / Chief-of-Staff
  net-news in a single month read as a deliberate executive build.
- **AI / data science seeding** - a senior DS / ML / AI Operations
  net-new is a bench-building bet.
- **IC → manager conversion** - a Principal / Staff IC departs and a
  Manager arrives in the same function. Reads as a shift from depth
  to managed-team scale.
- **Unbackfilled marketing seat** - VP Marketing departures without a
  Q-replacement read as "next quarter's hiring focus".

Write each thread as a one-sentence label + a one-paragraph rationale.
This becomes the 3-card "Strategic threads" row on Page 4.

---

## 2. Sentiment two-cut

Input: `ds_sentiment` (every Q-message scored as
positive / neutral / negative / off-topic).

### 2.1 Owned vs External

Owned = `community_name = {competitor_name}` (case-insensitive).
External = everything else.

Drop off-topic and neutral rows for the headline ratio. Compute:

```
owned_positive_share    = owned_positive    / (owned_positive    + owned_negative)
external_positive_share = external_positive / (external_positive + external_negative)
```

Express both as percentages. The Sonatype brief headline was ~92%
owned vs ~16% external - the contrast is the story.

### 2.2 By continent + employer size

Drop off-topic. From the resolved opinionated external authors,
compute three-way splits (positive / neutral / negative) per cohort:

- By continent: NA, Europe, Asia, Africa / Oceania / SA, Unresolved
- By employer size: SMB 1-200, Mid-market 201-1000, Enterprise 1001+,
  Unresolved

Report each row as `pos% / neu% / neg%`. Unresolved rows are shown
muted (opacity 0.65, color `var(--ink-3)`).

### 2.3 Negative concentration

Compute which 2-3 community names hold the majority of the external
negative volume. In the customer-facing copy, refer to them by their
ecosystem category, not by name (e.g. "Java / Maven build-tool
ecosystem" instead of community names).

---

## 3. Vendor-trust event detection

Input: opinionated negatives from `ds_sentiment`, with linkedin handles.

### 3.1 Trust dimensions

Scan the negative `message_text` corpus for distinct dimensions:

| Dimension | Detection hints |
|---|---|
| **Vendor ethics** | "took credit", "stole credit", "didn't credit", "CVE credit", "research credit", "claiming our work", "republishing our findings" |
| **Product quality** | "false positive", "false negative", "their own data shows", "broken", "doesn't catch", "missed CVE", own admissions in the company's own report |
| **Commercial trust** | "tripled", "bill", "pricing", "renewal", "contract", "billing", "seat to usage", "switched pricing model" |
| **Operational reliability** | "outage", "down for", "broken for", "401 / 402", "rate limit", "deprecating without notice" |
| **Vendor trustworthiness (general)** | "deprecating", "abandoning", "shutting down", "going commercial", "rug pull" |

### 3.2 Inclusion criteria

For the Complication 3 page to be included, **3+ distinct dimensions
must be hit by named verifiable authors with quotable text**:

- Each event needs a named author with a LinkedIn handle
- Each event needs a verbatim quote (no paraphrasing)
- Each event needs a different trust dimension (don't list 3 pricing
  events - that's one dimension, not three)

If fewer than 3 distinct dimensions detected: **omit the Complication 3
page entirely**. The brief jumps from sentiment (page 8) to the
evidence wall (page 11). Renumber pages accordingly.

### 3.3 Amplification when included

When 3+ dimensions hit, the trust-events thread amplifies through:

- Exec summary action title (one sentence calling out the events)
- 3-card red callout at the top of the exec summary
- Finding #01 in the 5-item findings list
- Complication 3 page with the 3 trust-dimension cards
- Evidence wall opens with the 3 verbatim trust-event quotes

---

## 4. Customer acquisition cohort

Input: `ds_acquisition` (person-company-first_seen) joined to
`ds_acq_firmo` (industry, size, country) and `ds_geo_fallback`
(modal-country backfill).

### 4.1 Company-level first_seen

Per company, take the **earliest** first_seen across all that company's
employees in `ds_acquisition`. A company "arrived" when its first
known employee mention dates inside the rolling 12-month window.

### 4.2 Industry buckets

Collapse the firmographic `INDUSTRY` field into 5 buckets:

| Bucket | Source industries |
|---|---|
| Software / internet | `computer software`, `internet` |
| IT services / consulting | `information technology and services`, `information services`, `management consulting` |
| Public / Healthcare / Cyber / Financial | `hospital & health care`, `health, wellness and fitness`, `research`, `insurance`, `banking`, `financial services`, `computer & network security`, `government administration`, `non-profit organization management`, `museums and institutions` |
| Media / publishing | `media production`, `broadcast media` |
| Other | everything else (e-learning, semiconductors, consumer services, wholesale, airlines, etc.) |

### 4.3 Size buckets

```
SMB         = SIZE IN ('1-10', '11-50', '51-200')
Mid-market  = SIZE IN ('201-500', '501-1000')
Enterprise  = SIZE IN ('1001-5000', '5001-10000', '10001+')
```

If `SIZE` is null, use `EMPLOYEE_COUNT` to bucket (use the same
boundaries: ≤200 / 201-1000 / 1001+).

### 4.4 Region buckets

```
North America  = {united states, canada}
EMEA           = {united kingdom, france, germany, netherlands, ireland,
                  sweden, finland, belgium, denmark, israel, turkey,
                  united arab emirates, pakistan, georgia, italy, spain,
                  poland, switzerland, austria, ...}
Asia Pacific   = {australia, india, vietnam, japan, china, korea, ...}
South America  = {brazil, argentina, mexico, ...}
```

If `LOCATION_COUNTRY` is null, look up `ds_geo_fallback` for the modal
employee country. If no employees either, the company stays in an
Unresolved bucket - but you should rarely see this in a healthy run.

### 4.5 Monthly stacked bar

Build the dataset for the SVG: 12 month rows, each row carrying the
5 industry-bucket counts. Total = sum of all 5 stacks. Q-window =
the 3 in-quarter columns; bracket them in the SVG with a "Q{N} {YYYY}
- {N} NEW" caption.

---

## 5. Resolved vs Unresolved fallbacks

### 5.1 Sentiment authors

For each opinionated external author, the resolution tag:

| Tag | Definition |
|---|---|
| `resolved` | `PEOPLE` row exists AND `JOB_COMPANY_NAME IS NOT NULL` |
| `unresolved-no-employer` | `PEOPLE` row exists, `JOB_COMPANY_NAME IS NULL` |
| `unresolved-no-profile` | `PEOPLE` row does not exist |

Resolved authors get bucketed into the continent + employer-size
cross-tabs. Unresolved authors are aggregated into a single muted
row at the bottom of each cross-tab.

### 5.2 Acquisition-cohort companies

For each company in `ds_acq_firmo` with `LOCATION_COUNTRY IS NULL`:

1. Query `ONFIRE.PEOPLE` for all employees of that company.
2. Group by `LOCATION_COUNTRY`, count employees, take the modal value.
3. If a modal country exists, **fold the company into that region's
   bucket**.
4. If no employees match (rare), keep the company in an Unresolved row.

This is what we did on the Sonatype brief to resolve "Ritual
Foundation" and "Annex Security" - both folded into North America.

---

## 6. Q-window math

Today's date determines the brief's quarter unless overridden.

| Today is in | Last completed quarter | Q-start | Q-end |
|---|---|---|---|
| Q1 (Jan-Mar) | Q4 previous year | `{prev_year}-10-01` | `{prev_year}-12-31` |
| Q2 (Apr-Jun) | Q1 current year | `{year}-01-01` | `{year}-03-31` |
| Q3 (Jul-Sep) | Q2 current year | `{year}-04-01` | `{year}-06-30` |
| Q4 (Oct-Dec) | Q3 current year | `{year}-07-01` | `{year}-09-30` |

Brief label: `Q{N} {year}`. E.g. `Q1 2026`.

Rolling 12-month window for the customer-acquisition motion:
`DATEADD(MONTH, -12, q_end)` to `q_end`.

---

## 7. Pre-flight data quality checks

Before declaring Phase 1 complete, the agent should verify:

| Check | How |
|---|---|
| Title movement has both event types | `ds_title_movement` has ≥ 1 `net_new` and ≥ 1 `now_gone` ideally; if zero events, flag in the brief |
| Sentiment scored the full universe | `ds_sentiment` row count matches `community_messages_sentiment` returned `row_count` |
| GitHub footprint has at least one row | `ds_github` row count > 0; if 0, the GitHub page is omitted |
| Customer acquisition has data in-window | `ds_acquisition` row count > 0; if 0, fall back to snapshot mode |
| Resolved sentiment authors > 50% | If less than half of opinionated external authors resolve to a current employer, flag the cross-tab as "indicative, not load-bearing" |
| Headcount trend has 12 rows | If shorter, label the chart with the actual window length |

---

## 8. Action-title rules (the McKinsey idiom)

Every page action title must:

1. Be a **complete sentence** with a subject + verb (not a noun phrase)
2. State the **conclusion**, not the topic
3. Be **specific and falsifiable** (numbers or named facts welcome)
4. Be **scannable in 5 seconds** - 12-18 words ideal

Good:
- "Q1 was the leadership-replacement quarter: 5 net-new titles
  arrived, 4 old ones departed."
- "Sonatype's last-12-months acquisition motion has pivoted to
  software vendors and IT services - not to banks."

Bad:
- "Q1 title movement"  ← noun phrase, no verb, no conclusion
- "An analysis of Sonatype's customer base"  ← topic, not conclusion

---

## 9. Sowhat synthesis blocks

Every page closes with a `.sowhat` callout that synthesises the page
into one paragraph. The convention:

- Opens with bold `What this means.` or `Bottom line.` or
  `Strategic read.`
- Restates the page's conclusion in plain English
- Connects to at least one other section's finding (so the brief reads
  as one argument, not 13 isolated pages)
- 1-3 sentences max

Example:
> **What this means.** The historical book of business and the current
> acquisition motion tell two different stories. The installed-base
> footprint is concentrated in global banks - the legacy ICP. But the
> last 12 months of new account acquisition pivoted decisively to
> software vendors and IT services / SI firms.
