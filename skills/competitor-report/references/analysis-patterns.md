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

### 1.2 Pair events into movement-type buckets

| Bucket | Rule |
|---|---|
| **Paired swap** | A `now_gone` title + a `net_new` title in the same broad function area in the same window. Function area = first 1-2 meaningful tokens (e.g. "Federal Sales" ↔ "Public Sector" → both GTM-public-sector) |
| **Departed-no-backfill** | A `now_gone` title with no `net_new` in-window pair → triggers the Phase 1.13 recoverability check |
| **Net-new function** | A `net_new` title with no `now_gone` in-window pair |

A swap is by definition a single old→new pair. Track them as
`(old_title, new_title, function_area)`.

**Important.** "Departed-no-backfill" is a *title* observation, not a
*function* observation. Most departed-no-backfill titles continue to
have the function performed under a different (often broader) title.
Always run the Phase 1.13 SUMMARY scan before characterising a
function as lost. See §9 for the function-still-held pattern.

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

Express both as percentages. The Nexagon brief headline was ~92%
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

This is what we did on the Nexagon brief to resolve "Ritual
Foundation" and "Annex Security" - both folded into North America.

---

## 6. Window math (quarter vs 12-month modes)

Today's date determines the **most recent completed quarter** unless
overridden. From there the window is bounded by `window_mode`.

| Today is in | Most recent completed quarter | Q-start | Q-end |
|---|---|---|---|
| Q1 (Jan-Mar) | Q4 previous year | `{prev_year}-10-01` | `{prev_year}-12-31` |
| Q2 (Apr-Jun) | Q1 current year | `{year}-01-01` | `{year}-03-31` |
| Q3 (Jul-Sep) | Q2 current year | `{year}-04-01` | `{year}-06-30` |
| Q4 (Oct-Dec) | Q3 current year | `{year}-07-01` | `{year}-09-30` |

### Window per mode

| `window_mode` | `window_start` | `window_end` | `window_label` |
|---|---|---|---|
| `quarter` (default) | Q-start | Q-end | `Q{N} {year}` (e.g. `Q1 2026`) |
| `12_month` | `DATEADD(MONTH, -12, q_end)` | Q-end | `12 months ending {Mon} {year}` (e.g. `12 months ending Mar 2026`) |

The customer-acquisition motion **always** spans the trailing 12
months ending `q_end` regardless of `window_mode`. The acquisition
chart still brackets the most-recent-quarter as the latest cohort -
just label the bracket "Last 3 months" instead of "Q1 2026" when
running in 12-month mode to keep the page voice consistent.

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
- "Nexagon's last-12-months acquisition motion has pivoted to
  software vendors and IT services - not to banks."

Bad:
- "Q1 title movement"  ← noun phrase, no verb, no conclusion
- "An analysis of Nexagon's customer base"  ← topic, not conclusion

---

## 9. Function-still-held check (Departed-no-backfill recoverability)

Triggered when Phase 2.1 classifies any title as `departed-no-backfill`.
For each such title, run the Phase 1.13 SUMMARY scan and decide between
three reads.

### 10.1 Pick function keywords

For each departed title, write 4-8 keywords that describe the function
in plain language. Examples:

| Departed title | Function keywords |
|---|---|
| Head of Technology Partnerships | partnership, alliance, ecosystem, integration partner, channel, business development |
| Technical Content Director | content, technical writing, documentation, editorial, blog |
| Web Developer (marketing site) | web, front-end, frontend, react, next.js, website, marketing site |
| VP Customer Success | customer success, account management, csm, customer experience |
| Head of Data | data engineering, analytics, data platform, data science |

Title-keyword search misses people doing the function under a
different title - the SUMMARY scan catches them.

### 10.2 Run the two-pass scan (see Query 13)

- **13a current-holder scan** against `pe.SUMMARY`, `p.HEADLINE`,
  `p.JOB_SUMMARY` on current employees
- **13b open-posting scan** against `ds_open_jobs_active.JOB_POST_TITLE`
  and `JOB_TEXT`

### 10.3 Read the result

| 13a result | 13b result | Read | Page-4 pill |
|---|---|---|---|
| 1+ rows | any | **Parallel hold by [title].** Often the parallel holder pre-existed the departed person's tenure - which means the dedicated seat experiment ended but the function never left. | `Parallel hold by ...` (warn) |
| 0 rows | 1+ active | **Open posting in flight.** The function is being actively backfilled. | `Open posting in flight` (warn) |
| 0 rows | 0 active | **Function lapsed.** The only true "lost capability" outcome - flag in the page 4 sowhat. | `Function lapsed` (neg) |

### 10.4 Be precise about same-person vs different-person

When writing the table row, distinguish:

- **Same person, internal promotion.** The departing title is the same
  person, internally promoted. (E.g. front-end developer → Principal
  UX Prototyping.) Note the promotion path.
- **Different person, parallel coverage.** A different employee was
  already doing the function when the departing person arrived. Note
  the parallel-holder's start date relative to the departing person's
  tenure.
- **Different person, hired after.** A different employee was hired
  for the function only after the departing person left. Note the gap.

The most common pattern on a real brief is the second - parallel
coverage that pre-existed. Be explicit about that.

---

## 10. People-movement classification (joiner / promotion / leaver)

`ds_employees` is the single source of truth for the people-side
analysis. Three derived buckets feed Pages 5, 5b and the exec-summary
findings.

### 10.1 Same-person stint pairing

For every person with **two stints at the target** where one stint
ends in window and the next stint starts in window:

```sql
-- datasets: {"e": "ds_employees"}
SELECT a.person_linkedin_url,
       a.title_name AS old_title,
       a.end_date   AS promotion_month_end,
       b.title_name AS new_title,
       b.start_date AS promotion_month_start,
       a.location_country
FROM e a
JOIN e b
  ON a.person_linkedin_url = b.person_linkedin_url
  AND a.end_date IS NOT NULL
  AND b.end_date IS NULL
  AND b.start_date >= a.end_date
WHERE a.end_date BETWEEN '{window_start}' AND '{window_end}'
ORDER BY a.end_date
```

That set is `internal_promotions`. The same join lets you reason
about whether the gap between `a.end_date` and `b.start_date` is
zero (clean within-month promotion) or one to two months (likely a
title change with a small delay).

### 10.2 The three buckets

| Bucket | Definition |
|---|---|
| **External hires** | Person whose first Packmint stint starts in window AND the person does NOT appear in `internal_promotions` (i.e. no parallel ending-stint). Equivalent: `start_date IN window AND end_date IS NULL` AND not in the promotion set. |
| **Internal promotions** | Per §10.1 - same person, ending stint AND starting stint both in window. |
| **Real departures** | Person whose final stint ends in window AND the person does NOT appear in `internal_promotions`. Equivalent: `end_date IN window` AND not in the promotion set. |

### 10.3 Reconciliation rule

```
net_headcount_growth = external_hires − real_departures
```

This is exact — not approximate. The movement data is authoritative.
Internal promotions are role changes within the company and contribute
zero to headcount either way.

A typical Packmint-scale run looks like:
- ~49 external hires
- ~12 internal promotions
- ~7 real departures
- net_headcount_growth = 49 − 7 = **+42**

The `ds_headcount` snapshot may show a slightly different endpoint
(e.g. 103 → 140 = +37 in the Packmint case) because LinkedIn profile
updates lag real role changes by days to weeks. The movement-derived
delta (+42) is always the number shown on page 5 — never the snapshot
delta. A divergence between the two signals that some profiles
updated late; it is a data-quality observation, not a tolerance band.
Do NOT label a snapshot-vs-movement gap as "expected snapshot lag" in
the brief. Show the movement-derived number and move on.

### 10.4 Function classification

The `title_role` field on `ds_employees` carries LinkedIn's
classification. Most rows map directly; rows with `title_role IS NULL`
are typically leadership / strategic seats (VP, Head of, Principal
something) that LinkedIn doesn't bucket.

Treat `null` title_role as a separate bucket labelled "Leadership /
unclassified" rather than dropping the rows.

### 10.4b Seniority classification (for page 5 Joiners + Leavers cards)

Classify every person-stint into one of four seniority tiers using
`title_name` (lowercased, word-boundary match) and `title_levels`:

| Tier | Signals |
|---|---|
| **Leadership** (VP / Head of / Director) | `title_name` contains: `vp`, `vice president`, `chief`, `cto`, `cfo`, `coo`, `ceo`, `director`, `head of`, `general manager`, `managing director`, `partner` — OR — `title_levels` includes `vp` or `director` |
| **Senior / Principal IC** | `title_name` contains `senior`, `principal`, `staff`, `lead`, `architect`, `specialist` — AND does NOT match the Leadership tier — OR — `title_levels` includes `senior` or `principal` |
| **Mid-level IC** | Engineer, designer, analyst, AE, BDR, SDR, CSM, TSE, manager (non-senior) — the majority of individual contributors not caught by the two tiers above |
| **Junior / Associate** | `title_name` contains `junior`, `associate`, `intern`, `graduate`, `trainee`, `entry` — OR — `title_levels` includes `entry` or `training` |

Apply this classification to **both** the Joiners pool and the Leavers
pool, with the **same symmetric "no promotions" rule** on both sides:

- **Joiners card** counts **external hires only** (49 in the canonical
  Packmint example). Internal promotions are excluded from the
  Joiners card region / seniority / function bars — they live on the
  page 6 promotions card.
- **Leavers card** counts **real departures only** (7 in the canonical
  example). Internal-promotion old-titles are role changes within the
  company and do NOT contribute to the Leavers card; including them
  breaks the logic because a promoted person did not leave.

The page 6 department chart is the only place that combines all three
(external + promotions + departures) in a single visual, with three
explicit bars per row.

Render as horizontal bar sections on the respective cards:
- **Joiners card** (green bars): labelled "By seniority." placed after
  the "By region." bars and before the "By function" summary text.
  Card carries a small grey subtitle: "{N} external hires only.
  Internal promotions sit on page 6, not in these bars."
- **Leavers card** (red bars): labelled "By seniority." placed after
  the "By region." bars and before the `{N} real departures:` summary
  text.

All four bars in each card are proportional to the same scale: the
largest bucket = 100% width. Include count + percentage in the right-
hand label of each bar row (e.g. `12 (20%)`).

If a tier is empty, omit its bar row entirely rather than showing a
zero bar.

### 10.5 Reconciliation between Page 3 and Pages 5/5b

The two views count different units and do not arithmetically
reconcile - they are complementary. Page 3 is title-string-level;
pages 5 / 5b are person-stint-level.

| Page | Unit | Counts |
|---|---|---|
| Page 3 (Complication 1A) | Distinct title strings | Net-new / now-gone title strings |
| Page 5 (Complication 1B) | Person-stints | Joiner / leaver / promotion / external-hire stints |
| Page 5b (1B continued) | Person-stints | Same, aggregated by function |

A single internal promotion creates:
- **Page 3:** +1 net-new title, possibly +1 now-gone title
- **Page 5:** +1 joiner stint, +1 leaver stint, 0 headcount

A single external hire under a pre-existing title creates:
- **Page 3:** 0 net-new, 0 now-gone (title already existed)
- **Page 5:** +1 joiner stint, +1 headcount

Always state the source explicitly on each page so readers do not
try to reconcile manually.

---

## 11. Sowhat synthesis blocks

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
