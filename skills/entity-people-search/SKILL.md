---
name: entity-people-search
description: Search for people/prospects directly from Onfire's LinkedIn people entity (the `contact` entity) using the `ask_onfire` tool. Use when the user wants to find prospects by job title, company, location, seniority, persona/role, technology footprint, or keywords in their profile — phrases like "find engineers at Northwind", "who are the VPs of Security at banks in the US", "show me people with 'Loglytics' in their job summary", "look up this LinkedIn URL", or any people search that doesn't require Forschung's cross-database scoring.
---

# entity-people-search

Direct lookup of the canonical LinkedIn people entity via `ask_onfire`.
People live on the `contact` entity in the semantic model. `ask_onfire` does
**not** take SQL — it takes a structured
**QueryIR** (`query={...}`) that the server compiles for you. No external
API hop.

## When to use this

- "Find security engineers at Meridian Bank"
- "Who are the CISOs in financial services in Germany?"
- "Show me people whose job summary mentions Sentinex"
- "Look up this LinkedIn URL: linkedin.com/in/johndoe"
- "Get me VPs of Engineering at companies with 200-500 employees"
- Any people lookup that can be expressed as filters on LinkedIn profile data

Skip this for:
- Prospecting with Forschung's persona/event/technology scoring → use `ai_prospecting`
- Looking up a single person by name only (no company context) → use `match_person` first
- People who joined specific communities → use the `community-join-signals` skill

## `ask_onfire` shape

```
ask_onfire(query={
  entity: "contact",
  select: ["<field>", ...],          // attributes / dimensions on the entity
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  insight_filters: [{kind, value}],  // persona / technology concepts (resolved server-side)
  joins: [{entity, filters, insight_filters}],  // filter-only single hop; cannot SELECT joined columns
  distinct_by: "<field>",
  order_by: [{field, direction}],
  limit: <int>                       // ROW BUDGET — see Billing
})
```

## Fields

### Selectable attributes (returnable, NOT filterable)
| Field | Notes |
|-------|-------|
| `full_name` | First + last combined |
| `headline` | LinkedIn headline |
| `summary` | Career bio / About section |
| `job_summary` | Current role description (richest keyword field — but see caveat below) |
| `current_company_name` | Employer name |
| `location_name` | City, State |
| `job_start_date` | ISO date of current role start |
| `seniority_levels` | Seniority array (`JOB_TITLE_LEVELS`) — **returnable only**; filter seniority via persona insight_filters |

### Filterable dimensions (use in `filters`)
| Dimension | Notes |
|-----------|-------|
| `linkedin_url` | This person's profile. `eq` to look up ONE person. Any URL format is normalized server-side. |
| `job_title` | Free-text current title. Use `op: "contains"` for a keyword. |
| `job_title_role` | Normalised role category (e.g. "engineering") |
| `job_title_sub_role` | Finer role category |
| `location_country` | Stored lowercased — match lowercase literals (e.g. `"united states"`) |
| `location_region` | State / region (lowercased) |
| `location_locality` | City (lowercased) |
| `industry` | Person-level industry (lowercased) |
| `current_company_url` | Employer LinkedIn URL. `eq` to target ONE company's people. Any URL format is normalized. |
| `current_company_industry` | Employer industry (lowercased) |
| `current_company_size` | e.g. "201-500" |

`DELETED_AT` is handled for you — the `contact` entity is filtered to live
profiles server-side. You no longer write a delete filter.

### Persona / seniority / technology → `insight_filters` (NOT dimension filters)
Role, department, **seniority**, and technology/vendor are not columns —
they live in the insight catalog and go in `insight_filters` as *concepts*
(one concept per filter; multiple insight_filters are **AND**-ed):

- `{kind: "persona", value: "<role/department>"}` — e.g. `"appsec"`, `"devops"`, `"data engineering"`. A job-TITLE ("CISO", "VP Security") is the wrong thing to put here — see the population rule below.
- `{kind: "persona", value: "seniority_executive"}` — seniority is a **persona**, not a dimension.
  Use `seniority_executive` (covers VP / C-suite) / `seniority_director` / `seniority_teamlead` / `seniority_ic`.
- `{kind: "technology", value: "<tool/vendor>"}` — e.g. `"Sentinex"`. This is the
  correct replacement for the old "keyword in job summary" lookup when the
  keyword is a technology or vendor.

Values are resolved server-side to an exact `insight_name`, and an unresolvable
value bounces back with suggestions before anything runs or bills — so submit
the user's wording rather than pre-checking it. `resolve_insights` (carrying
`kind`) is for reading the vocabulary: an unresolved concept whose suggestions
weren't enough, an exact spelling to reuse, or an insight's `coverage` band.

### Which POPULATION you search — the choice that decides your results

Onfire holds a curated (ICP-filtered) people set and a much larger full
population. **The shape of your filter picks one**, and you never switch
entities or set a flag to do it:

| Filter | Population | Use for |
|---|---|---|
| `insight_filters` | curated only | cohorts, counts, qualified segments — deduped, active-employment-aware, high precision |
| `job_title contains [...]` | the FULL population | finding a specific person or title at a named company |

A query with no `insight_filters` that is scoped to a company/person, or filters
a title with `contains`, is served from the full population automatically. The
response then carries a `coverage` block naming which population ran and an
`exhaustive` note — **read it**: it means there is no broader set to escalate to,
so a small result is a finding, not a reason to re-query wider.

So **"who is the CISO of Acme"** is a title query, not a persona query:

```
ask_onfire(query={
  entity: "contact",
  select: ["linkedin_url", "full_name", "job_title", "location_name"],
  filters: [
    {dimension: "current_company_url", op: "eq", value: "linkedin.com/company/acme"},
    {dimension: "job_title", op: "contains",
     value: ["security", "cyber", "infosec", "ciso"]}   // family = ONE filter, OR
  ],
  limit: 25
})
```

Do **not** reach for `insight_filters` here. Personas are derived from profile
SIGNAL rather than the job title, so a scoped persona lookup can return someone
whose own title contradicts it *and* miss a real title-holder outside the curated
slice — you end up spending a second query to verify. A curated persona can
legitimately have **zero** holders at a company that plainly employs the role, so
0 rows from an `insight_filter` is not proof of absence, and never a reason to
fall back to web search. Report the closest titles you did find, or say plainly
that the title isn't in the data.


## Billing — read before calling

`ask_onfire` **bills the client 1 credit per row returned**.

- Always set a small explicit `limit` (the row budget). Set it to exactly
  the number the user asked for; for a quick look **5–10 rows** is plenty.
- If you do **not** know how many rows the user wants, leave `limit` unset:
  `ask_onfire` then returns how many rows match **without billing** so you
  can confirm the count and resubmit.
- If the response is `needs_confirmation` (the row-budget gate — triggered when
  the query's ACTUAL match count exceeds ~500 rows and `confirmed` is not set),
  **nothing was billed and no rows came back**. A generous `limit` over a small
  match set runs fine; the gate is about how many rows really match. Lower
  `limit` or tighten the filters and resubmit. Do **not** reflexively set
  `confirmed: true` just to push a large pull through — that flag records the
  USER's authorization.

## QueryIR templates

### By company LinkedIn URL
```
ask_onfire(query={
  entity: "contact",
  select: ["linkedin_url", "full_name", "job_title", "seniority_levels",
           "job_summary", "location_name", "job_start_date"],
  filters: [{dimension: "current_company_url", op: "eq",
             value: "linkedin.com/company/meridian-bank"}],
  order_by: [{field: "job_start_date", direction: "desc"}],
  limit: 50
})
```

### By job title keyword
```
ask_onfire(query={
  entity: "contact",
  select: ["linkedin_url", "full_name", "job_title", "seniority_levels",
           "current_company_name", "current_company_url"],
  filters: [
    {dimension: "job_title", op: "contains", value: "security engineer"},
    {dimension: "location_country", op: "eq", value: "united states"}
  ],
  limit: 50
})
```

### By technology footprint (replaces "keyword in job summary")
A tool/vendor keyword (e.g. Sentinex) is a **technology insight**, not a
profile substring — pass it as an `insight_filter`, not a `job_summary`
match (`job_summary` is selectable but not filterable):
```
ask_onfire(query={
  entity: "contact",
  select: ["linkedin_url", "full_name", "job_title",
           "current_company_url", "current_company_name", "job_summary"],
  filters: [{dimension: "current_company_url", op: "eq",
             value: "linkedin.com/company/northwind"}],
  insight_filters: [{kind: "technology", value: "Sentinex"}],
  limit: 30
})
```
`insight_filters` AND together — to cover several technologies, run one
query per technology and merge (there is no OR).

### By seniority (a persona, not a column)
Seniority is **not** a dimension — filter it with a `persona` insight_filter
(VP / C-suite map to `seniority_executive`):
```
ask_onfire(query={
  entity: "contact",
  select: ["linkedin_url", "full_name", "job_title", "seniority_levels",
           "current_company_name", "current_company_industry", "location_country"],
  filters: [{dimension: "current_company_industry", op: "contains", value: "financial"}],
  insight_filters: [{kind: "persona", value: "seniority_executive"}],
  limit: 50
})
```

### By LinkedIn URL (single person lookup)
```
ask_onfire(query={
  entity: "contact",
  select: ["linkedin_url", "full_name", "job_title", "seniority_levels",
           "current_company_name", "current_company_url", "location_name", "summary"],
  filters: [{dimension: "linkedin_url", op: "eq",
             value: "https://www.linkedin.com/in/johndoe"}],
  limit: 1
})
```

## Aggregate mode (distributions, counts, trends)

Set `group_by` and/or `aggregations` and leave `select` **empty** — the result
columns are the group keys plus the aggregation names. Never pull raw rows to
count them yourself.

```
ask_onfire(query={
  entity: "contact",
  filters: [{dimension: "current_company_url", op: "eq",
             value: "linkedin.com/company/acme"}],
  group_by: ["job_title_role"],
  aggregations: [{name: "people", fn: "count_distinct", field: "linkedin_url"}],
  order_by: [{field: "people", direction: "desc"}]
})
```

`fn`: count | count_distinct | sum | avg | min | max (`count` omits `field`).
`having: [{measure, op, value}]` filters on an aggregation after grouping.
Aggregates always run against the curated set, so two aggregates in one analysis
stay comparable.

## Reusing a list another tool returned

If a previous tool handed you a `dataset` (match_company, ai_prospecting, a
prior ask_onfire), filter by the HANDLE instead of re-typing the values:

```
filters: [{dimension: "current_company_url", op: "in",
           from_dataset: "ds_ab12cd34", column: "linkedin_url"}]
```

`describe_dataset` lists a dataset's columns.

## Output handling

`ask_onfire` returns a `dataset` handle + `preview_rows` (first 20).

1. Show `preview_rows` to the user as a formatted table.
2. State `total_count` — if it's more than 20, tell the user the full set is in the dataset.
3. Offer `download_dataset(dataset_id="...")` for the full CSV.
4. For follow-up filters ("show me only the VPs", "add their company size"),
   use `query_datasets` against the `dataset_id` — **do not re-run** `ask_onfire`
   (re-running rebills per row).

## What this entity CANNOT express

`ask_onfire` is a structured query, not SQL. The following are not
expressible against `contact` — do not try to fake them:

- **Filtering on `skills`** — `skills` is an array dimension, not
  scalar-filterable. If the user wants people by a skill tag, that filter
  cannot be applied here; the closest expressible proxy is a `technology`
  insight_filter when the skill is actually a tool/vendor.
- **Arbitrary free-text matches on `job_summary` / `summary` / `headline`** —
  these are selectable attributes, not filterable. If the keyword is a
  technology/vendor → use `insight_filters kind=technology` (above). If it
  is a role/department → use `insight_filters kind=persona`. If it is
  genuinely arbitrary free text with no insight equivalent, it cannot be
  filtered here — say so rather than fabricating a filter.
- **Window functions and arbitrary temporal math** — not supported. (GROUP BY
  distributions and aggregations ARE supported: set `group_by` + `aggregations`
  and leave `select` empty — see "Aggregate mode" below.)

## Common pitfalls

- **Putting persona / role / seniority / technology in `filters`** — they are
  not columns. They go in `insight_filters` (seniority as `kind: "persona"`,
  value `seniority_executive` etc.).
- **Trying to filter `job_summary`/`summary`/`headline`** — selectable only.
  For a tool/vendor keyword use a `technology` insight_filter instead.
- **Leaving `limit` unset on purpose** — that triggers the row-budget gate
  and returns no rows. Set the budget to what the user actually wants.
- **Re-running `ask_onfire` for "show me only the engineers"** — slice the
  existing dataset with `query_datasets` to avoid rebilling.
