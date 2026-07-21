---
name: title-movement
description: >
  Detect month-by-month title movement (new hires and departures by job title) at any target company using `ONFIRE.EXPERIENCES_FULL` via `ask_onfire`.

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
    - ask_onfire
---

# Title Movement Skill

Detect which job titles are newly entering or permanently leaving a company, month by month. Data source: the **extended employment-history pool** — entity `experiences_pool` (alias `ONFIRE.EXPERIENCES_FULL`) via `ask_onfire`. This is the broad superset (~5x) of the curated `people_experiences`, one row per person-stint, and is the right source for *whole-pool* org movement because it covers people regardless of whether they carry curated insights.

> **`experiences_pool` is GATED.** It is withheld from the routing catalog and has **no insight search**. You must name the entity explicitly *and* set `allow_extended_pool: true` in every QueryIR below, or the query will not run. The narrower curated alternative is `people_experiences` — it covers only insight-connected people (a fraction of the pool), so prefer `experiences_pool` here for complete movement coverage; fall back to `people_experiences` only if a caller explicitly wants the curated subset.

**How this skill works in two parts.** `ask_onfire` takes a structured QueryIR, not SQL. Two of its capabilities do most of the work for us:

1. **Per-month counts run *inside* `ask_onfire` (aggregate mode).** The month-by-month new-hire and departure counts by title are now AGGREGATE-MODE QueryIR queries — `ask_onfire` buckets `start_date` / `end_date` by month, groups by title, and counts distinct people server-side. No raw rows are pulled for this, and no client-side bucketing is needed.
2. **The "first-ever / now-gone" flags stay client-side (Step 4).** Whether a title is *genuinely new* to the company (first-ever appearance) or *fully gone* (nobody currently holds it) needs a window/self-join over the title's full history. That is **not** expressible in a QueryIR (confirmed by the entity's own caveats), so it is computed by the agent over one small bounded `query_datasets` pull.

So the flow is: two aggregate `ask_onfire` calls for the monthly hire/departure counts (Step 2 + Step 3), one tiny bounded pull for the flags (Step 4), then merge and format.

---

## Step 1 — Parse inputs

| Parameter | Default | Notes |
|---|---|---|
| `company_linkedin_url` | **required** | e.g. `linkedin.com/company/taskboard`. Infer slug from company name if needed (e.g. "Cloudforce" → `linkedin.com/company/cloudforce`). State the inferred URL explicitly. Passed as a `company_url` filter value (any URL format is normalized server-side). |
| `start_date` | 12 months ago | Convert natural language: "2 years" → 24 months ago, "since Jan 2024" → `2024-01`, "6 months" → 6 months ago. Format: `YYYY-MM`. Applied as a client-side cutoff on the returned month buckets — **not** as a query filter (`start_date` / `end_date` on the entity are TEXT `'YYYY-MM'`, not real dates, so range filtering them in the query is unreliable). |
| `title_filter` | none | Translate "only engineering titles" or "titles with manager" to a dimension filter: `{dimension: "title_name", op: "contains", value: "engineer"}` (`title_name` is free text; `contains` is a case-insensitive substring match). **One keyword per query.** Multiple OR'd keywords are NOT expressible in a single QueryIR (dimension filters AND together, and there is no OR) — run one set of calls per keyword and merge the groups client-side. |
| `group_grain` | `title_role` | The title axis to group hires/departures by. `title_role` is the closed, normalized role taxonomy (cleaner buckets, fewer spelling variants); `title_name` is the free-text raw title. Group by `title_role` by default; switch to (or add) `title_name` when the user wants the raw titles. |
| `show_all` | false | Default: in the final table (Step 5), only keep months/titles where `title_new_to_company = TRUE` OR `title_gone_from_company = TRUE`. If user says "show everything" or "all movement", keep every month/title bucket. |

---

## Step 2 — New hires per month by title (aggregate mode, `ask_onfire`)

Hires = a month-bucket over `start_date`, grouped by month + title, counting distinct people. This runs entirely inside `ask_onfire` — it returns one row per `(month, title)` group, **not** raw stints.

```
ask_onfire(query={
  entity: "experiences_pool",
  allow_extended_pool: true,
  filters: [
    {dimension: "company_url", op: "eq", value: "<company_linkedin_url>"}
    /* optional single-keyword title filter:
       {dimension: "title_name", op: "contains", value: "<keyword>"} */
  ],
  buckets: [{name: "hire_month", field: "start_date", part: "month"}],
  group_by: ["hire_month", "title_role"],
  aggregations: [{name: "hires", fn: "count_distinct", field: "person_url"}],
  order_by: [{field: "hire_month", direction: "desc"}],
  limit: 200
})
```

Result columns: `hire_month`, `title_role`, `hires`. (Swap `title_role` → `title_name` — in both `group_by` and `order_by` if you order on it — to group by the raw title; add both to group by each.)

## Step 3 — Departures per month by title (aggregate mode, `ask_onfire`)

Departures = the **same query bucketed on `end_date`** instead of `start_date`. A non-empty `end_date` is a stint that ended (a departure from that role); ongoing stints have NULL/empty `end_date` and simply don't bucket.

```
ask_onfire(query={
  entity: "experiences_pool",
  allow_extended_pool: true,
  filters: [
    {dimension: "company_url", op: "eq", value: "<company_linkedin_url>"}
    /* same optional single-keyword title filter as Step 2 */
  ],
  buckets: [{name: "depart_month", field: "end_date", part: "month"}],
  group_by: ["depart_month", "title_role"],
  aggregations: [{name: "departures", fn: "count_distinct", field: "person_url"}],
  order_by: [{field: "depart_month", direction: "desc"}],
  limit: 200
})
```

Result columns: `depart_month`, `title_role`, `departures`.

### Notes on Steps 2–3

- **Scope to the company.** `company_url eq <slug>` keeps each query small and on-topic. Any LinkedIn URL format is normalized server-side.
- **`allow_extended_pool: true` is mandatory** on both calls — `experiences_pool` is gated and the query will not run without it.
- **No date filter in the query.** `start_date` / `end_date` are TEXT `'YYYY-MM'`, so the month bucket is fine but range-filtering them is not — apply the Step 1 `start_date` window as a client-side cutoff on the returned `*_month` values when you build the final table.
- **`count_distinct` requires the `field`** (`person_url`) — that is what counts *people*, not stints. (`count` may omit a field; the distinct/sum/avg/min/max functions all require one.)
- **`select` MUST be empty in aggregate mode** — the result columns are exactly the `group_by` keys followed by the aggregation names. Do not add a `select` list.
- **Confirm field names if unsure:** `describe_onfire_schema(["experiences_pool"])` before authoring. Never guess a field name.

### Billing & the row budget (aggregate mode)

`ask_onfire` **bills 1 credit per RETURNED row — and in aggregate mode a returned row is a group**, i.e. one `(month, title)` bucket. So `limit` is a real budget on the number of groups.

- Always set an explicit `limit`. `200` groups comfortably covers a year-plus of monthly buckets across the common roles at a mid-size company; lower it for a narrow title filter or a short window.
- If the response comes back `needs_confirmation` with `stage: "row_budget"`, **nothing was billed and no rows came back** — there are more groups than your budget. Lower `limit` to what the analysis actually needs and resubmit, or (only once the count is settled with the user) set `confirmed: true`. Do **not** reflexively set `confirmed: true` just to push a large pull through.
- A larger or older company spans more months × more roles; trade a higher `limit` against the per-group cost and the window the user asked for.

### Simple lookups (expressible directly)

These single-shot variants answer narrower questions without the flag step:

- **Current people by title** — drop the buckets/aggregations and pull rows: `filters` add `{dimension: "is_primary", op: "eq", value: true}` (the entity's `current` named filter, `IS_PRIMARY = TRUE`); `select: ["person_url", "title_name", "title_role", "start_date"]`. (Remember to keep `allow_extended_pool: true`.)
- **Headcount by role right now** — aggregate: `filters` add `is_primary = true`; `group_by: ["title_role"]`; `aggregations: [{name: "people", fn: "count_distinct", field: "person_url"}]`.

---

## Step 4 — The "first-ever / now-gone" flags (client-side, bounded pull)

This is the **only** part `ask_onfire` cannot express. Whether a `(month, title)` bucket is *genuinely new* (the first-ever month anyone at the company held that title) or a title is *fully gone* (nobody currently holds it) requires a window / self-join over each title's full history — there is no QueryIR for that, and the `experiences_pool` caveats say so explicitly. So compute these two flags client-side over **one small bounded pull**, then join them onto the aggregate counts from Steps 2–3.

Pull just the columns the flags need, over the company's full history (no date cutoff — the "first-ever" flag depends on seeing all of it):

```
query_datasets:  pull stints for the company from experiences_pool
  entity: "experiences_pool", allow_extended_pool: true,
  filters: [{dimension: "company_url", op: "eq", value: "<company_linkedin_url>"}],
  select: ["title_role", "title_name", "start_date", "end_date"],
  limit: <bounded>   /* this is a row pull again — billed per stint, so keep it tight */
```

Treat `start_date` / `end_date` as `'YYYY-MM'` month strings. For the chosen `group_grain` (default `title_role`), over ALL pulled rows:

- `first_ever_start[title]` = the earliest `start_date` month seen for that title at the company.
- `currently_active[title]` = count of stints for that title with an empty/NULL `end_date` (still ongoing).

Then derive the flags:

- `title_new_to_company` is **TRUE** for a `(hire_month, title)` bucket when `hire_month == first_ever_start[title]` — the first-ever month anyone at the company held this title.
- `title_gone_from_company` is **TRUE** for a title when `currently_active[title] == 0` — nobody at the company currently holds it.

> **This pull is billed per stint** (it is a row pull, not aggregate mode), so keep `limit` tight — only the columns above, only this company. If `limit` truncates the company's stint history, `first_ever_start` / `currently_active` can be off; widen it (mind the per-row cost) if the flags look suspect.

---

## Step 5 — Merge and apply the window

Join the aggregate counts (Steps 2–3) and the flags (Step 4) on `(month, title)`:

- Start from the union of `(hire_month, title)` and `(depart_month, title)` keys.
- `joiners` = `hires` from Step 2 (default 0); `leavers` = `departures` from Step 3 (default 0).
- `title_new_to_company` / `title_gone_from_company` from Step 4 (default FALSE).
- **Apply the `start_date` window from Step 1**: keep only months `>= start_date`. (The window is applied here, not in the query, because the month columns are TEXT.)

**If `show_all = false`**, keep only rows where `title_new_to_company = TRUE` OR `title_gone_from_company = TRUE`. **If `show_all = true`**, keep every bucket.

Order by month descending, then by `joiners + leavers` descending.

**Two flag definitions worth knowing:**
- `title_new_to_company` — the *first ever month* anyone at the company held this title. Computed against the full Step 4 pull regardless of the date window.
- `title_gone_from_company` — current snapshot: nobody at the company currently holds this title (`end_date` is set for all its stints). Not a point-in-time calculation for historical months.

---

## Step 6 — Format the output

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
If the aggregate calls return 0 groups, say:
> "No title movement found for `[url]` in this window. The LinkedIn URL slug may not match — try a variant (e.g. `linkedin.com/company/cloudforce` vs `linkedin.com/company/cloudforcecom`)."

---

## Edge cases

- **Inferred URL**: state it — *"Using `linkedin.com/company/cloudforce` — correct me if wrong."*
- **Title noise**: grouping by `title_role` (default) collapses most spelling variants; if you group by `title_name`, variants (`mid-market solution engineer` vs `mid-market solutions engineer`) appear as separate groups. Mention if prominent.
- **Future-dated end_date**: occasional data artifact that can produce a departure bucket in the future. Note if it affects results.
- **Large result sets** (many `(month, title)` groups with `show_all=true`): suggest narrowing by title filter or date range — this also lets you lower the `ask_onfire` `limit` and reduce per-group cost.
