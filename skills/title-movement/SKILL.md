---
name: title-movement
description: >
  Detect month-by-month title movement (new hires and departures by job title) at any target company using `ONFIRE.PEOPLE_EXPERIENCES` via `ask_onfire`.

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

Detect which job titles are newly entering or permanently leaving a company, month by month. Data source: `ONFIRE.PEOPLE_EXPERIENCES` (entity `people_experiences`) via `ask_onfire`.

**How this skill works in two parts.** `ask_onfire` takes a structured QueryIR, not SQL — it can pull the employment-stint rows for a company, but it **cannot** compute month-over-month diffs, window functions, or temporal "first-ever" / "now-gone" flags. So the flow is:

1. **Pull the rows** (Step 2) — one bounded `ask_onfire` call returns the company's employment stints (`title_name`, `start_date`, `end_date`, `person_url`, …).
2. **Compute the movement client-side** (Step 3) — the agent buckets those rows by month and derives joiners, leavers, and the new-to-company / gone-from-company flags itself, over the returned rows. `ask_onfire` does none of this math.

---

## Step 1 — Parse inputs

| Parameter | Default | Notes |
|---|---|---|
| `company_linkedin_url` | **required** | e.g. `linkedin.com/company/taskboard`. Infer slug from company name if needed (e.g. "Cloudforce" → `linkedin.com/company/cloudforce`). State the inferred URL explicitly. Passed as a `company_url` filter value (any URL format is normalized server-side). |
| `start_date` | 12 months ago | Convert natural language: "2 years" → 24 months ago, "since Jan 2024" → `2024-01`, "6 months" → 6 months ago. Format: `YYYY-MM`. Used as the client-side cutoff in Step 3 — **not** a query filter (`start_date` on the entity is TEXT `'YYYY-MM'`, not a real date, so range filtering it in the query is unreliable). |
| `title_filter` | none | Translate "only engineering titles" or "titles with manager" to a dimension filter: `{dimension: "title_name", op: "contains", value: "engineer"}` (`title_name` is free text; `contains` is a case-insensitive substring match). **One keyword per query.** Multiple OR'd keywords are NOT expressible in a single QueryIR (dimension filters AND together, and there is no OR) — run one pull per keyword and merge the rows client-side, or filter the keywords in Step 3 over an unfiltered pull. |
| `show_all` | false | Default: in Step 3, only keep months/titles where `title_new_to_company = TRUE` OR `title_gone_from_company = TRUE`. If user says "show everything" or "all movement", keep every month/title bucket. |

---

## Step 2 — Pull the rows with `ask_onfire`

One bounded call pulls the company's employment stints. This returns **rows only** — the month-by-month movement is computed in Step 3, not here.

```
ask_onfire(query={
  entity: "people_experiences",
  select: ["person_url", "title_name", "title_role", "start_date", "end_date", "is_primary"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<company_linkedin_url>"}
    /* optional single-keyword title filter:
       {dimension: "title_name", op: "contains", value: "<keyword>"} */
  ],
  limit: 200
})
```

- **Scope to the company.** `company_url eq <slug>` is what keeps the pull small and on-topic. Any LinkedIn URL format is normalized server-side.
- **No date filter in the query.** `start_date` / `end_date` are TEXT `'YYYY-MM'` (not real dates) — the `start_date` window from Step 1 is applied client-side in Step 3 so it stays correct. Pulling without a date filter also lets Step 3 see the company's full history, which the "first ever month for this title" flag depends on.
- **`is_primary = true`** marks the person's current/primary stint; an empty/NULL `end_date` means the stint is ongoing.
- **Confirm field names if unsure:** `describe_onfire_schema(["people_experiences"])` before authoring. Never guess a field name.

### Billing & the row budget

`ask_onfire` **bills the client 1 credit per row returned**, so `limit` is a real budget — keep it tight.

- Always set an explicit `limit`. `200` is a reasonable ceiling for a single mid-size company's stint history; lower it for narrow title filters or short windows.
- If the response comes back `needs_confirmation` with `stage: "row_budget"`, **nothing was billed and no rows came back** — the match is bigger than your budget. Lower `limit` to what the analysis actually needs and resubmit, or (only once the count is settled with the user) set `confirmed: true`. Do **not** reflexively set `confirmed: true` just to push a large pull through.
- A larger company may need a higher `limit` to capture full history; trade that against the per-row cost and the window the user asked for.

### Simple lookups (expressible directly, no Step 3 needed)

These single-shot variants answer narrower questions without any client-side month math:

- **Current people by title** — add `{dimension: "is_primary", op: "eq", value: true}`; select `title_name`, `start_date`.
- **Past roles at the company** — add `{dimension: "is_primary", op: "eq", value: false}`; select `title_name`, `start_date`, `end_date`.

---

## Step 3 — Compute month-by-month movement (client-side, over the pulled rows)

`ask_onfire` returned raw stint rows; the agent now derives the movement itself. Treat each `start_date` / `end_date` as a `'YYYY-MM'` month string.

For each row, normalize the title: `title = lower(trim(title_name))`. Skip rows with no `title_name` or no `start_date`.

**First, over ALL pulled rows (full history — do not apply the date window yet), per title:**
- `first_ever_start` = the earliest `start_date` month seen for that title at the company.
- `currently_active` = count of stints for that title with an empty/NULL `end_date` (still ongoing).

**Then bucket by month, applying the `start_date` window from Step 1:**

- **Joiners** — group rows by (`start_date` month, `title`), counting distinct `person_url`. Keep only months `>= start_date`. A `(month, title)` bucket is `title_new_to_company = TRUE` when that month equals the title's `first_ever_start` (the first ever month anyone at the company held this title).
- **Leavers** — group rows with a non-empty `end_date` by (`end_date` month, `title`), counting distinct `person_url`. Keep only months `>= start_date`. A title is `title_gone_from_company = TRUE` when its `currently_active` count is 0 (nobody at the company currently holds it).

Merge joiners and leavers on (`month`, `title`): `joiners` defaults to 0, `leavers` defaults to 0, and the two flags default to FALSE.

**If `show_all = false`**, keep only rows where `title_new_to_company = TRUE` OR `title_gone_from_company = TRUE`. **If `show_all = true`**, keep every bucket.

Order by month descending, then by `joiners + leavers` descending.

**Two flag definitions worth knowing:**
- `title_new_to_company` — this is the *first ever month* anyone at the company held this title. Computed against full pulled history regardless of the date window.
- `title_gone_from_company` — current snapshot: nobody at the company currently holds this title (`end_date` is set for all stints of it). Not a point-in-time calculation for historical months.

> **Accuracy note.** Both flags are only as complete as the rows the pull returned. If `limit` truncated the company's stint history, `first_ever_start` and `currently_active` can be off — widen `limit` (mind the per-row billing) if the flags look suspect.

---

## Step 4 — Format the output

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
If the pull returns 0 rows, say:
> "No title movement found for `[url]` in this window. The LinkedIn URL slug may not match — try a variant (e.g. `linkedin.com/company/cloudforce` vs `linkedin.com/company/cloudforcecom`)."

---

## Edge cases

- **Inferred URL**: state it — *"Using `linkedin.com/company/cloudforce` — correct me if wrong."*
- **Title noise**: spelling variants (`mid-market solution engineer` vs `mid-market solutions engineer`) appear as separate rows. Mention if prominent.
- **Future-dated end_date**: occasional data artifact. Note if it affects results.
- **Large result sets** (>150 buckets with `show_all=true`): suggest narrowing by title filter or date range — this also lets you lower the `ask_onfire` `limit` and reduce per-row cost.
