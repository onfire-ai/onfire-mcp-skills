---
name: hiring-signals
description: Find open job postings at target companies using the `ask_onfire` tool against the `job_post` entity. Use when the user wants to know what roles a company is actively hiring for, where they're hiring, what seniority they're posting, which companies are hiring for a technology or skill, what open positions signal budget or expansion - phrases like "what is Northwind hiring for?", "find VP-level roles at my target accounts", "which accounts are expanding their security team?", "find buyers at companies hiring AI engineers", "show open data engineer roles in EMEA", or any job posting / hiring signal lookup.
compatibility:
  tools:
    - ask_onfire
---

# hiring-signals

Structured lookup against the `job_post` entity via `ask_onfire`.
Each row = one job posting captured from LinkedIn Jobs. Use this to identify
budget signals, expansion areas, and the geographic / seniority shape of a
company's open requisitions.

`ask_onfire` takes a single `query` argument — a structured **QueryIR**,
never SQL:

```
ask_onfire(query={
  entity: "job_post",
  select: ["<field>", ...],          // attributes / dimensions / measures on the entity
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  joins: [{entity, filters}],        // filter-only; cannot SELECT joined columns
  order_by: [{field, direction}],
  distinct_by: "<field>",
  limit: <int>,                      // ROW BUDGET — see Billing
  confirmed: <bool>
})
```

## When to use this

- "What is Meridian Bank actively hiring for right now?"
- "Find companies hiring Kubernetes or Python engineers"
- "Which of our target accounts are expanding their security team?"
- "Show me all open DevSecOps roles posted in the last 30 days"
- "What's the geographic shape of Packmint's open postings?"
- "Which accounts have the most active postings in EMEA right now?"
- Any job posting lookup or hiring signal question

Skip this for:
- Current employee profiles (no hiring signal needed) → use `entity-people-search` or `employee-footprint`
- Company firmographics → use `entity-company-search`
- GitHub or community signals → use `github-repo-signals` / `community-join-signals`

## Entity structure

`job_post` (source `SILVER.JOB_POST.STG_JOB_POSTS`) - each row = one job
posting captured from LinkedIn Jobs. Company-level only — there is **no
person / hiring-manager link** on a posting. Author the QueryIR with these
**logical field names** (not the physical column names):

| Logical field | Kind | Notes |
|---|---|---|
| `company_url` | dimension | Company LinkedIn URL - use for account filtering. Any URL format is normalized server-side. |
| `company_name` | dimension | Company display name (free text; case-normalized server-side). |
| `country` | dimension | Country of the role (free text, e.g. `"United Kingdom"`, `"United States"`, `"Ireland"`, `"India"`). |
| `job_function` | dimension | LinkedIn job-function classification - **messy multi-value free text** (e.g. `"engineering and information technology"`). Match with `op: "contains"`, never `eq`. |
| `seniority` | dimension | Seniority level - closed list (see values below). |
| `employment_type` | dimension | Closed list: `"Full-time"`, `"Contract"`, `"Part-time"`, `"Internship"`, `"Temporary"`, `"Other"`, `"Volunteer"`. |
| `application_active` | dimension | `1` if the posting is currently open, `0` if closed / filled. |
| `job_post_title` | attribute | Title of the open role (e.g. `"Senior Application Security Engineer"`). **NOTE: the title field is `job_post_title`, not `job_title` — `job_title` only exists on the people/contact entity.** |
| `job_text` | attribute | Full job description. **Very long - avoid selecting unless explicitly needed.** |
| `location` | attribute | Lowercased city / region / country string (e.g. `"belfast, northern ireland, united kingdom"`). |
| `date_posted` | attribute | Original posting date on LinkedIn. **Use this for date filtering.** |
| `external_url` | attribute | The company's own careers-page URL when present (e.g. `careers.packmint.com/...`); often null. |
| `seniority_score` | attribute | Numeric seniority score (0 = lower, higher = more senior). |
| `post_count` | measure | `COUNT(*)` — number of postings matching the filters. |
| `company_count` | measure | `COUNT(DISTINCT company)` — number of distinct companies matching. |

`job_post` declares one join: `company` (firmographics) — **filter-only**, you
cannot SELECT company columns through it.

### `seniority` values
LinkedIn-standard strings: `"Entry level"`, `"Associate"`, `"Mid-Senior level"`,
`"Director"`, `"Executive"`, `"Internship"`, `"Not Applicable"` (when LinkedIn
did not classify the role).

### Scope to open roles
Use `{dimension: "application_active", op: "eq", value: 1}` to scope to
currently open roles. There is no soft-delete concept to worry about.

## Billing — read before calling

`ask_onfire` **bills the client 1 credit per row returned**. Always set a
small explicit `limit` — exactly the number of rows the section needs.

- For a "what are they hiring for" cut, **10-50 rows** is plenty.
- If you leave `limit` unset, or set it above the confirmation threshold
  (~50) without `confirmed: true`, `ask_onfire` returns
  `needs_confirmation` with `stage: "row_budget"` — nothing is billed and no
  rows come back. It tells you how many rows match; lower `limit` to what you
  actually need (or confirm the count with the user) and resubmit. Do **not**
  reflexively set `confirmed: true` to push a large pull through.
- A count question ("how many roles") uses a `post_count` measure with
  `limit: 1` — one row, one credit.

## QueryIR templates

### What is a company actively hiring for right now?
```
ask_onfire(query={
  entity: "job_post",
  select: ["job_post_title", "seniority", "job_function", "country", "location", "date_posted", "external_url"],
  filters: [
    {dimension: "company_url", op: "eq", value: "linkedin.com/company/meridian-bank"},
    {dimension: "application_active", op: "eq", value: 1}
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: 50
})
```

### How many roles is a company hiring for right now?
```
ask_onfire(query={
  entity: "job_post",
  select: ["post_count"],
  filters: [
    {dimension: "company_url", op: "eq", value: "linkedin.com/company/meridian-bank"},
    {dimension: "application_active", op: "eq", value: 1}
  ],
  limit: 1
})
```

### Postings dated in a specific window (e.g. last quarter)
```
ask_onfire(query={
  entity: "job_post",
  select: ["job_post_title", "seniority", "country", "location", "date_posted", "application_active", "external_url"],
  filters: [
    {dimension: "company_url", op: "eq", value: "linkedin.com/company/packmint"},
    {dimension: "date_posted", op: "gte", value: "2026-01-01"},
    {dimension: "date_posted", op: "lte", value: "2026-03-31"}
  ],
  order_by: [{field: "date_posted", direction: "asc"}],
  limit: 50
})
```

### Find roles by function keyword
```
ask_onfire(query={
  entity: "job_post",
  select: ["company_name", "company_url", "job_post_title", "seniority", "country", "location", "date_posted"],
  filters: [
    {dimension: "application_active", op: "eq", value: 1},
    {dimension: "job_function", op: "contains", value: "engineering"}
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: 50
})
```
`job_function` is messy multi-value free text — `contains` matches the
substring anywhere in the classification. **There is no OR across columns** in
QueryIR (filters AND together), so the old "title ILIKE OR job_text ILIKE"
keyword search is not directly expressible — see Not directly expressible
below.

### Target accounts hiring for a function
```
ask_onfire(query={
  entity: "job_post",
  select: ["company_name", "job_post_title", "seniority", "country", "location", "date_posted"],
  filters: [
    {dimension: "application_active", op: "eq", value: 1},
    {dimension: "company_url", op: "in", value: [
      "linkedin.com/company/northwind",
      "linkedin.com/company/sendline",
      "linkedin.com/company/pathwatch"
    ]},
    {dimension: "job_function", op: "contains", value: "security"}
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: 50
})
```

### Senior roles only (Director / Executive) at an account
```
ask_onfire(query={
  entity: "job_post",
  select: ["company_name", "job_post_title", "seniority", "country", "location", "date_posted"],
  filters: [
    {dimension: "application_active", op: "eq", value: 1},
    {dimension: "seniority", op: "in", value: ["Director", "Executive"]},
    {dimension: "company_url", op: "eq", value: "linkedin.com/company/nornet"}
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: 50
})
```

### Hiring volume across a set of accounts (totals)
```
ask_onfire(query={
  entity: "job_post",
  select: ["post_count", "company_count"],
  filters: [
    {dimension: "application_active", op: "eq", value: 1},
    {dimension: "company_url", op: "in", value: [
      "linkedin.com/company/northwind",
      "linkedin.com/company/sendline",
      "linkedin.com/company/pathwatch"
    ]}
  ],
  limit: 1
})
```
This returns the **total** open-role count and distinct-company count across
the set — not a per-company ranking. For "which account is hiring fastest",
run the count once per account (one query each with a single `company_url`
`eq` filter and `select: ["post_count"]`) and rank the results yourself; the
ranked GROUP BY is not expressible in one call — see below.

### Recent postings for a function (date window, across accounts)
```
ask_onfire(query={
  entity: "job_post",
  select: ["company_name", "job_post_title", "seniority", "country", "date_posted", "external_url"],
  filters: [
    {dimension: "application_active", op: "eq", value: 1},
    {dimension: "date_posted", op: "gte", value: "2026-06-08"},
    {dimension: "job_function", op: "contains", value: "engineering"}
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: 100
})
```
Compute the date boundary yourself (e.g. today minus 14 days) and pass it as a
literal — QueryIR has no `DATEADD` / relative-date math.

## Not directly expressible (QueryIR limits)

`ask_onfire` is a structured grammar, not SQL. These hiring cuts the old SQL
skill did **cannot** be expressed in one call — convert what you can and tell
the user the rest is out of scope for this tool:

- **Free-text keyword search across `job_post_title` OR `job_text`** — filters
  AND together and there is no cross-column OR. Use `job_function contains`
  for the functional cut, or fall back to scoping by `company_url` and reading
  `job_post_title` per row. A true title/description keyword OR is not
  available.
- **Grouped distributions** — "open roles GROUP BY country", "GROUP BY
  job_function, seniority", and "rank accounts by COUNT(*)" all need a GROUP BY
  the grammar doesn't have. The only measures are `post_count` and
  `company_count` over the filter set. Get a per-bucket count by running one
  filtered `post_count` query per bucket (per country, per account, etc.) and
  assembling the breakdown yourself.
- **Relative-date math** (`DATEADD`, "last 14 days") — compute the boundary
  date and pass it as a `gte` literal.
- **Hiring-manager / person fields** — posting-level only, no person link.
  Pair with `entity-people-search` on the company's recruiters / department
  heads if you need the person.

## Output handling

`ask_onfire` returns a `dataset` handle + preview rows.

1. Lead the table with: `job_post_title`, `company_name`, `date_posted`, `seniority`, `country`, `location`, `application_active`.
2. State the count; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only Director-level", "group by country", "last 7 days only") - use `query_datasets` on the `dataset_id`. **Do not re-run** `ask_onfire` (it re-bills).

## Reading the signals

- **`application_active = 1`** = the posting is currently open; the strongest budget signal.
- **`application_active = 0`** with a recent `date_posted` = role likely filled - a hire that may not yet show in our employment-history index.
- **`seniority = "Director" / "Executive"`** = leadership build; expensive seats.
- **Multiple active postings in one country/region** = geographic concentration; reads as a deliberate location strategy (Belfast HQ, EMEA build, US East-coast GTM, India delivery tier, etc.).
- **`job_function` patterns** - "engineering and information technology" dominating = platform / product build; "management and manufacturing" or sales-flavoured functions = GTM expansion.
- **High active-role count** = active expansion = budget signal. Use the `post_count` measure to size it.
- **`job_text`** captures stack mentions anywhere in the description, including the "Familiarity with our stack" or "Nice to have" sections — select it only when you need that depth (it is very long).

## Common pitfalls

- **No OR across columns** - filters AND together. The old "title ILIKE OR job_text ILIKE" keyword search is not expressible; use `job_function contains` or scope by account and read titles.
- **`job_function` is messy multi-value free text** - always match it with `op: "contains"`, never `eq` (e.g. `"engineering and information technology"` will never `eq` `"engineering"`).
- **Title field is `job_post_title`, not `job_title`** - `job_title` only exists on the people/contact entity; using it here will bounce as an unknown field.
- **`company_url`** accepts any URL format (normalized server-side); the slug form `linkedin.com/company/<slug>` is fine, no manual lower-casing needed.
- **`date_posted` is the posting date** - the pipeline-refresh timestamps are not exposed on this entity; use `date_posted` for all date filtering.
- **No hiring-manager fields** - this entity is posting-level only. If you need the person who posted the role, pair the posting with `entity-people-search` on the company's recruiters / department heads.
- **`job_text` is very long** - avoid selecting it by default; use `job_post_title` plus `job_function` for summaries.
- **`seniority = "Not Applicable"`** is a real value for roles LinkedIn did not classify - don't filter these out blindly.
- **Re-running for follow-ups re-bills** - slice the existing dataset with `query_datasets` on the `dataset_id` instead.
