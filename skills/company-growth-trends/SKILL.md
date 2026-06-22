---
name: company-growth-trends
description: Analyse monthly headcount growth and technology/persona adoption trends for companies. For total company headcount use `get_company_headcount` (or the `headcount_monthly` entity via `ask_onfire`); for technology or persona growth use `ask_onfire` against the `growth_insight_monthly` entity. Use when the user wants to know if a company is hiring or contracting, whether a specific technology is spreading within a company, or how headcount growth compares to tech adoption — phrases like "is Acme growing?", "is EDR adoption growing at these accounts?", "compare Sentinex vs total headcount trend at Skywall Networks", "which accounts are shrinking?", "is the data engineering team at Frostbyte expanding?", or any month-over-month growth question.
---

# company-growth-trends

Two complementary data sources:

| What you need | Tool to use | Source / entity |
|---|---|---|
| **Total company headcount** over time + employee roster with prior/next-company | `get_company_headcount` | Tenure-based + profile enrichment, tool-managed (see flag below) |
| **Total company headcount** trend only (no roster, structured) | `ask_onfire` → entity `headcount_monthly` | Monthly total headcount + pre-computed MoM `growth_rate` |
| **Technology / persona growth** (e.g. Sentinex, data engineer) | `ask_onfire` → entity `growth_insight_monthly` | Pre-computed monthly count + `growth_rate` |

> **Rule:** For the **employee roster** (who joined/left, prior/next company), only `get_company_headcount` returns it — `ask_onfire`'s `headcount_monthly` is trend-only. For a pure headcount trend you can use either.

> **Note:** The raw-SQL `query_onfire` tool has been **removed**. Growth/headcount queries now go through `ask_onfire`, which takes a structured **QueryIR** (not SQL). `insight` values are resolved server-side — see `resolve_insights`.

---

## When to use this

- "Is Meridian Bank's Sentinex footprint growing?" → `ask_onfire` (`growth_insight_monthly`, insight)
- "Compare EDR adoption to total headcount at these 5 accounts" → both tools, then compare
- "Which of our target accounts are shrinking overall?" → `get_company_headcount`
- "Is the data engineering persona expanding at Frostbyte?" → `ask_onfire` (`growth_insight_monthly`, insight)
- "Who joined Northwind in the last 12 months and where did they come from?" → `get_company_headcount` (roster is always returned)
- "Who left Northwind in the last quarter and where did they go?" → `get_company_headcount` (roster includes leavers + next-company)
- Any month-over-month growth / trend question for companies

Skip this for:
- Single-month roster of *current* employees by keyword → use `employee-footprint`
- Open requisitions → use `hiring-signals`

---

## `get_company_headcount` — total headcount + employee roster

> **Flag — no semantic entity:** `get_company_headcount` is backed by
> `ONFIRE.PEOPLE_GRAND_EXPERIENCES` (tenure rows) + `ONFIRE.PEOPLE_GRAND`
> (profile enrichment). **Neither table is in the semantic model**, so there is
> **no `ask_onfire` entity** for them — the roster (joiners/leavers, prior/next
> company, profile fields) is only reachable through this dedicated tool. Do not
> try to author an `ask_onfire` QueryIR against PEOPLE_GRAND* — it does not exist.

Headcount is **derived from tenure rows** in `ONFIRE.PEOPLE_GRAND_EXPERIENCES`:
for each month M in the window, the tool counts distinct people whose tenure
covers M (`START_DATE <= last-day-of-M` AND `END_DATE IS NULL OR END_DATE >=
first-day-of-M`). MoM growth % is computed from those counts.

The roster is **always returned** alongside the monthly counts (no opt-in
flag). One row per (person × stint) where any of these hold:

- `start_date` falls in the lookback window → **joiner**
- `end_date IS NULL` → **still active**
- `end_date` falls in the lookback window → **leaver** (covers long-tenured
  departures whose start is outside the window)

Each row is joined to `ONFIRE.PEOPLE_GRAND` for profile fields (name,
country, region, current title) and self-joined to
`ONFIRE.PEOPLE_GRAND_EXPERIENCES` for the person's immediately-prior AND
immediately-next company. `next_*` is only populated for stints that
ended (`end_date IS NOT NULL`). Both tables are tool-managed and have no
semantic entity — `ask_onfire` cannot read them.

### Parameters

| Parameter | Type | Notes |
|---|---|---|
| `company_linkedin_urls` | `List[str]` | Required. Up to 50 URLs. Any variant accepted; normalized to `linkedin.com/company/<slug>`. |
| `months` | `int` | Optional. Months of history (default 13, max 36). Also the roster cutoff — joiners with `start_date` in the window, leavers with `end_date` in the window, plus all still-active employees. |

### Response shape

Both keys are always present.

```json
{
  "headcount": {
    "dataset":     {dataset handle},
    "total_count": N,
    "preview_rows": [first 20 rows]
  },
  "employees": {
    "dataset":     {dataset handle},
    "total_count": M,
    "preview_rows": [first 20 rows]
  }
}
```

#### Headcount rows (most-recent first)

| Column | Notes |
|---|---|
| `company_linkedin_url` | Normalized to `linkedin.com/company/...` |
| `time_period` | First day of the month (e.g. `2026-01-01`) |
| `employee_count` | Distinct people whose tenure covers that month |
| `growth_pct` | MoM % change (NULL for the oldest row in the window) |

The **first row per company** is the current month's count.

#### Employee rows (one per stint)

| Column | Source | Notes |
|---|---|---|
| `company_linkedin_url` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Target company |
| `person_linkedin_url`, `person_linkedin_id` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | The employee |
| `is_primary` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | LinkedIn's "current primary role" flag |
| `start_date`, `end_date` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | `YYYY-MM` strings (NULL end = still there) |
| `title_name`, `title_role`, `title_sub_role`, `title_levels` | `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Title classification at the company |
| `full_name`, `headline` | `ONFIRE.PEOPLE_GRAND` | Latest snapshot |
| `location_country`, `location_region`, `location_continent`, `location_name` | `ONFIRE.PEOPLE_GRAND` | Person's location |
| `current_job_title`, `current_company_name`, `current_company_linkedin_url` | `ONFIRE.PEOPLE_GRAND` | What they're doing *now* (may differ from the target stint if `end_date IS NOT NULL`) |
| `prior_company_name`, `prior_company_linkedin_url`, `prior_title` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Where they came from before the target stint |
| `prior_start_date`, `prior_end_date` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Prior stint's window |
| `next_company_name`, `next_company_linkedin_url`, `next_title` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Where they went after the target stint. **NULL when `end_date IS NULL`** (still active) |
| `next_start_date`, `next_end_date` | self-join on `ONFIRE.PEOPLE_GRAND_EXPERIENCES` | Next stint's window |

### Deriving joiners / leavers from the roster

The roster is one source of truth for both directions:

- **Joiners** — `WHERE start_date IN window AND end_date IS NULL` (or include short-stint leavers with `end_date IN window` if you want all arrivals)
- **Joiner origins** — `prior_company_name` is already attached
- **Leavers** — `WHERE end_date IN window`
- **Leaver destinations** — `next_company_name` is already attached

### Example calls

```python
# Default — monthly series + full roster (joiners, leavers, still-active)
get_company_headcount(
    company_linkedin_urls=["linkedin.com/company/packmint"],
    months=12,
)
```

### Example interpretation

- `employee_count: 533, growth_pct: 0.2` → 533 active employees this month, +0.2% MoM
- `growth_pct: null` → oldest month in the window (no prior month to diff against)
- `growth_pct: -1.5` → headcount contracted 1.5% MoM
- An employee row with `end_date IS NULL` is currently at the company
- `prior_company_name = "Globex"` → the person was at Globex right before this stint; useful for joiner-origin / talent-flow analysis
- `next_company_name = "Frostbyte"` → after leaving the target company they went to Frostbyte; useful for leaver-destination analysis (only set when `end_date IS NOT NULL`)

---

## `ask_onfire` → entity `growth_insight_monthly` — technology / persona growth

`ask_onfire` takes a structured **QueryIR** (not SQL). One row per
`(company_url, insight, month)` — `num_on_insight` is how many of the company's
contacts carried the insight that month, `growth_rate` is the **pre-computed**
month-over-month change (positive = growing). Coverage is a trailing ~12 months.

### Entity fields (`growth_insight_monthly`)

| Field | Kind | Notes |
|---|---|---|
| `company_url` | dimension | Company identifier. Pass a LinkedIn URL in any format — normalized server-side. |
| `insight` | dimension (bound) | Persona OR technology **concept**, resolved server-side. Pass the human/canonical value (e.g. `Sentinex`, `data engineer`) — **do not add a `growth-` prefix**; the server scopes it to the growth series. |
| `month` | dimension (date) | First day of the month. Filter a window with `gte` / `lte`. |
| `num_on_insight` | attribute (numeric) | Contacts carrying the insight that month. TEXT-stored; compiler casts numerically. |
| `growth_rate` | attribute (numeric) | Pre-computed MoM change. TEXT-stored; compiler casts numerically. Read it directly. |

> **Resolve the concept first.** `insight` is a bound concept, not a literal.
> Pass the human term and the server resolves it (bouncing suggestions if it
> can't), or confirm the canonical value with `resolve_insights`. The old
> `growth-<slug>` stored prefix and `LOWER(insight_name) = ...` matching are
> gone — never pass a prefix yourself.

> **Billing / row budget.** `ask_onfire` **bills 1 credit per row returned**.
> Always set a small explicit `limit` — `12` covers a year of monthly rows. If
> you leave `limit` unset or set it above the confirmation threshold, the call
> returns `needs_confirmation` (stage `row_budget`) with the matching row count
> and **bills nothing** — lower the limit and resubmit rather than reflexively
> setting `confirmed: true`.

### QueryIR templates

#### Tech/persona insight growth for one company
```python
ask_onfire(query={
  "entity": "growth_insight_monthly",
  "select": ["month", "num_on_insight", "growth_rate"],
  "filters": [
    {"dimension": "company_url", "op": "eq", "value": "linkedin.com/company/meridian-bank"},
    {"dimension": "insight", "op": "eq", "value": "Sentinex"}   # resolved server-side
  ],
  "order_by": [{"field": "month", "direction": "desc"}],
  "limit": 12
})
```

#### Recent window for one company (last few months)
```python
ask_onfire(query={
  "entity": "growth_insight_monthly",
  "select": ["month", "num_on_insight", "growth_rate"],
  "filters": [
    {"dimension": "company_url", "op": "eq", "value": "linkedin.com/company/frostbyte"},
    {"dimension": "insight", "op": "eq", "value": "Sentinex"},
    {"dimension": "month", "op": "gte", "value": "2026-04-01"}   # explicit window bound
  ],
  "order_by": [{"field": "month", "direction": "desc"}],
  "limit": 6
})
```

> **Limitation — no relative dates / no compiler date math.** QueryIR has no
> `DATEADD`/`CURRENT_DATE` equivalent: bound `month` with an explicit
> `YYYY-MM-01` value (`gte`/`lte`), or just pull the trailing window and slice
> client-side. **FLAG:** the old "all insights, last 3 months" template relied
> on `DATEADD(month, -3, CURRENT_DATE())` — not expressible as-is; compute the
> cutoff date yourself and pass it as a literal `month gte`.

#### Multiple companies — which insight is growing fastest?

> **FLAG — not expressible in one query.** The old SQL keyed off a correlated
> `time_period = (SELECT MAX(time_period) ...)` subquery and a multi-company
> `IN (...)`. QueryIR supports neither a "latest month" subquery nor a numeric
> rank over a multi-company pull, and `month`'s latest value isn't known
> client-side without a read. Do it in steps: run **one query per company**
> (`company_url eq`, `insight eq`, `order_by month desc`, `limit 1`) to grab
> each company's most-recent `month` + `growth_rate`, then **rank the
> `growth_rate` values yourself** across the returned rows. (`op: "in"` on
> `company_url` is grammar-valid, but you still cannot pin "latest month" or
> sort by `growth_rate` across companies in a single call without over-pulling.)

---

## Comparing total headcount vs tech growth

Call both tools and merge the results in your response.

**Step 1** — get total headcount (roster + trend):
```python
get_company_headcount(
    company_linkedin_urls=["linkedin.com/company/skywall-networks"],
    months=13,
)
```
(or, for the trend only via `ask_onfire`, use entity `headcount_monthly` — see below.)

**Step 2** — get tech insight growth via `ask_onfire`:
```python
ask_onfire(query={
  "entity": "growth_insight_monthly",
  "select": ["month", "num_on_insight", "growth_rate"],
  "filters": [
    {"dimension": "company_url", "op": "eq", "value": "linkedin.com/company/skywall-networks"},
    {"dimension": "insight", "op": "eq", "value": "Sentinex"}
  ],
  "order_by": [{"field": "month", "direction": "desc"}],
  "limit": 13
})
```

**Step 3** — narrate the comparison aligned by `month` / `time_period`.

### Headcount trend via `ask_onfire` (entity `headcount_monthly`)

For a structured total-headcount **trend** (no roster), `headcount_monthly` is
the `ask_onfire` alternative to `get_company_headcount`. One series per company —
**no `insight` filter needed**.

```python
ask_onfire(query={
  "entity": "headcount_monthly",
  "select": ["month", "headcount", "growth_rate"],
  "filters": [
    {"dimension": "company_url", "op": "eq", "value": "linkedin.com/company/skywall-networks"}
  ],
  "order_by": [{"field": "month", "direction": "desc"}],
  "limit": 13
})
```

---

## Interpreting results

- **Positive `growth_rate`** → company / tech is growing that month.
- **Negative `growth_rate`** → contracting.
- **`growth_rate` is the pre-computed MoM change** — read the latest row
  directly; do not recompute it. The oldest row in the window has no prior month
  to diff against, so its rate may be absent — drop it before averaging/charting.
- **No MoM math in the query.** `ask_onfire` cannot compute month-over-month
  deltas, windowed `LAG`, or any trend arithmetic in SQL. It only SELECTs
  `month` + `num_on_insight` + `growth_rate` and ORDERs by `month`. Any
  comparison the stored `growth_rate` doesn't already give you (e.g. first-vs-last
  month, multi-month averages) you compute **yourself over the pulled rows**.
- `insight` is resolved server-side — pass the human/canonical concept, never a
  `growth-` prefix or a stored slug.

---

## Output handling

`get_company_headcount` returns `dataset` handles + `preview_rows` (first 20).
`ask_onfire` returns the rows directly (subject to the row budget / `limit`).

1. Narrate the trend: *"Skywall Networks' total headcount grew +3.2% MoM in April 2025, while Sentinex persona adoption grew +8.5% — outpacing overall hiring."*
2. For time-series questions, show a table of `month → growth_rate`.
3. For `get_company_headcount`, offer `download_dataset` for the full CSV and use `query_datasets` against the existing `dataset_id` for follow-up slices.

---

## Common pitfalls

- **Trying to read total headcount or the roster via `ask_onfire`** — use `get_company_headcount` (full roster) or entity `headcount_monthly` (trend only). The PEOPLE_GRAND* tables have **no semantic entity**.
- **Expecting `ask_onfire` to compute MoM deltas / trend math in SQL** — it can't. Read the stored `growth_rate`; compute anything else yourself over the pulled rows.
- **Treating `next_company_name` as "current employer"** — it's the *next* stint after this one. For still-active people (`end_date IS NULL`) it's NULL. Use `current_company_name` for "where they work now".
- **Adding a `growth-` prefix or stored slug to `insight`** — pass the human/canonical concept; the server resolves and scopes it. Use `resolve_insights` if unsure.
- **Leaving `limit` unset / pushing a big pull through** — `ask_onfire` bills 1 credit/row. Set a small explicit `limit` (e.g. 12); on `needs_confirmation` (stage `row_budget`) lower it, don't reflexively set `confirmed: true`.
- **`start_date` / `end_date` in the employee roster are `YYYY-MM` strings**, not full dates. Treat them as month granularity.
