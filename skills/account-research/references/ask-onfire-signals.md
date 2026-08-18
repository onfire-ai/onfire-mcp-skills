# Steps 1a / 1d - concept resolution + `ask_onfire` warehouse signal recipes

The `account_research` orchestrator pre-pulls four blocks (filings,
footprint, intent signals, prospects). The Onfire warehouse holds more
signal surfaces that strengthen a report but are **not** in the
envelope. This file is the worked-recipe reference for pulling them with
`ask_onfire`.

`ask_onfire` takes a single `query` argument — a structured **QueryIR**,
never SQL:

```
ask_onfire(query={
  entity: "<entity>",
  select: ["<field>", ...],          // attributes / dimensions / measures on the entity
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  insight_filters: [{kind, value}],  // persona / technology concepts (resolved server-side)
  joins: [{entity, filters, insight_filters}],  // filter-only; cannot SELECT joined columns
  order_by: [{field, direction}],
  distinct_by: "<field>",
  limit: <int>                       // ROW BUDGET — see Billing
})
```

## The fixed pattern for every pull

1. **Scope to the account.** Filter the entity's company/contact URL
   dimension `eq` the account LinkedIn URL (`company.linkedin_url` from
   the envelope). Any URL format is normalized server-side. This is what
   keeps the pull small and on-topic.
2. **Resolve bound concepts first, and check the match tier.** A persona /
   technology / event name is a *concept*, not a literal. Pass it through
   `resolve_insights` (carrying `kind`) to get the canonical value.
   **Every candidate carries a `match` tier: `exact`, `synonym`, `partial`
   or `fuzzy`. Only `exact` and `synonym` are usable.** See "The
   resolution gate" below - this is the difference between a report that
   confirms the product the account actually runs and one that confirms a
   generic component term.
3. **Confirm field names if unsure.** Call
   `describe_onfire_schema(["<entity>"])` for the exact dimension /
   attribute / measure names before authoring. Never guess a field name.
4. **Set a small explicit `limit`** (see Billing) and submit.

## The resolution gate (Step 1a)

Tenant config stores vendors with a trailing `" Insight"` suffix
(`"datadog insight"`, `"zscaler insight"`). That suffix is not part of any
catalog name, so the suffixed form never matches exactly and **every concept
drops to the `partial` tier**. At `partial` the top-ranked candidate can be any
of three wrong things - and the tier is the only signal that anything is off:

| Passed as-is | Top candidate | Tier | What went wrong |
|---|---|---|---|
| `datadog insight` | `data` | partial | **wrong kind** - a persona, not a technology (`Datadog` ranks second) |
| `databricks insight` | `data` | partial | **wrong kind** - same persona wins again |
| `zscaler insight` | `SCA` | partial | wrong value - an analysis-technique acronym |
| `palo alto networks firewall insight` | `Network` | partial | wrong value - a broad infrastructure term |
| `microsoft 365 insight` | `Microsoft` | partial | too broad - the parent brand, not the product |
| `snowflake insight` | `Snowflake` | partial | right value, but still unverified confidence |
| `kubernetes insight` | `Kubernetes` | partial | right value, but still unverified confidence |

Strip the suffix and every one of them resolves cleanly:

| Passed stripped | Resolves to | Tier |
|---|---|---|
| `Datadog` | `Datadog` | **exact** |
| `Databricks` | `Databricks` | **exact** |
| `Snowflake` | `Snowflake` | **exact** |
| `Kubernetes` | `Kubernetes` | **exact** |
| `Salesforce` | `Salesforce` | **exact** |
| `Terraform` | `Terraform` | **exact** |
| `Zscaler` | `Zscaler` | **exact** |
| `Proofpoint` | `Proofpoint` | **exact** |
| `Microsoft 365` | `Microsoft 365` | **exact** |

Note the last two rows of the first table: a `partial` hit is **not** reliably
wrong, which is exactly why you cannot judge a candidate by whether its value
looks plausible. Judge it by the tier. Accepting only `exact` / `synonym`
handles all three failure modes at once - wrong kind, wrong value, and
right-value-low-confidence - without inspecting any of them.

So, once per report:

```
resolve_insights(
  concepts=[<every competitors + technologies value, " Insight" stripped>],
  kind="technology"
)
resolve_insights(
  concepts=[<every organization value + golden_persona>],
  kind="persona"
)
```

Two calls total. Keep candidates whose `match` is `exact` or `synonym`;
discard `partial` and `fuzzy` as unresolved. Never search on a discarded
term, and never name it in a confirmation label.

## Billing — read before calling

The orchestrator's footprint pull runs **unbilled** inside the MCP. A
direct `ask_onfire` call does **not**: it **bills the client 1 credit
per row returned**.

- Always set an explicit `limit`. For report evidence, **5-10 rows** is
  plenty. Never leave `limit` unset (an unset budget is bounced for
  confirmation).
- If the response is `needs_confirmation` with `stage: "row_budget"`,
  nothing was billed and no rows came back — the match is bigger than
  your budget. Lower `limit` to what the section actually needs and
  resubmit. Do **not** reflexively set `confirmed: true` to push a large
  pull through.
- The Step 1d **mandatory** pulls always run - they are what makes two runs
  of the same account produce the same report. Judgement applies only to the
  optional pulls: skip those when their section already has enough evidence.
- Budget guide: 5-10 rows for a signal pull, 25-30 for the competitor
  footprint, ~10 for golden-persona contacts. Roughly 60-90 rows per report.
- **Free alternative:** slicing a dataset the orchestrator already produced
  (`query_datasets`) is not billed per row. Prefer it over re-pulling
  anything already in `envelope.datasets`.

## Rendering hard-rule reminder

None of these entity names, `ask_onfire`, Snowflake, or any internal
pipeline term may appear in the customer HTML (see
`report-structure.md` "Forbidden internal tool names"). Map each to a
neutral abstraction: open roles → "open roles / hiring activity",
hiring managers → "key contacts", events → "[Event Name] [Year]",
growth → "adoption trend / market intelligence", github → "developer
community signal", career history → "career history / company-change
records". Quote any verbatim text (a `short_summary`, a `job_text`
excerpt) under the same verbatim rule as signals.

---

## Recipes

### 1. Hiring momentum — `job_post` → Why-Now / use-case signals

What roles the account is opening (a build-out / buying-intent signal).
Company-level only (no person link).

```
ask_onfire(query={
  entity: "job_post",
  select: ["job_post_title", "job_function", "seniority", "location", "date_posted", "external_url"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "application_active", op: "eq", value: 1}   // still-open postings
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: 10
})
```

- "How many roles is the company hiring for" → `select: ["post_count"]`
  (a measure) with the same filters, `limit: 1`.
- Narrow to a use case with `{dimension: "job_function", op: "contains", value: "security"}`
  (`job_function` is messy multi-value free text — use `contains`, not `eq`).
- Why-Now framing: "N open security roles, most recent posted
  [date_posted]".

### 2. Active hiring managers — `hiring_manager_signal` → Key contacts / Why-Now

A specific person actively hiring at the account — a live decision-maker
/ budget owner — with the role they are hiring for.

```
ask_onfire(query={
  entity: "hiring_manager_signal",
  select: ["full_name", "person_job_title", "job_post_title", "short_summary", "signal_date", "contact_url"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"}
    // optional seniority gate: {dimension: "person_seniority", op: "eq", value: "seniority_director"}
  ],
  distinct_by: "contact_url",   // one row per person (a person may carry several signals)
  order_by: [{field: "signal_date", direction: "desc"}],
  limit: 10
})
```

- `person_seniority` values: `seniority_executive` / `seniority_director` / `seniority_teamlead`.
- Map each to a use case via `job_post_title` (the role being hired for).
- Render in Key Contacts (Section 8) tagged "actively hiring -
  [job_post_title]"; when prospecting is disabled/empty these can be the
  section's sole contact source.

### 3. Event presence — `event_company` (counts) / `event_contact` (who)

Resolve the event name first (the stored form is `Event - <name>`).

Company's headcount at an event:

```
ask_onfire(query={
  entity: "event_company",
  select: ["event", "attendee_count"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "event", op: "eq", value: "RSAC 2026"}   // resolved to 'Event - RSAC 2026'
  ],
  limit: 5
})
```

Named attendees from the account (join from `contact`, since
`event_contact` has no profile fields to select):

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  joins: [{entity: "event_contact", filters: [{dimension: "event", op: "eq", value: "RSAC 2026"}]}],
  limit: 10
})
```

- `attendee_count` is pre-aggregated per (company, event) — read it
  directly, never re-aggregate.
- Why-Now framing: "[N] people from [Company] attended [Event] [Year]".

### 4. Adoption trend — `growth_insight_monthly` → Why-Now ("growing")

Monthly count of the account's contacts carrying a persona/technology,
with the month-over-month rate.

```
ask_onfire(query={
  entity: "growth_insight_monthly",
  select: ["month", "num_on_insight", "growth_rate"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "insight", op: "eq", value: "Kubernetes"}   // resolve via resolve_insights
  ],
  order_by: [{field: "month", direction: "desc"}],
  limit: 12
})
```

- The compiler casts the TEXT `num_on_insight` / `growth_rate` columns
  numerically for ordering. **It does not compute deltas in SQL** — read
  the latest row's `growth_rate` (positive = growing) or compare the
  first/last month yourself. Coverage is a trailing ~12 months.
- Why-Now framing: "[Persona/tech] adoption up [growth_rate] as of
  [month]".

### 5. Headcount trend — `headcount_monthly` → Why-Now / company card

```
ask_onfire(query={
  entity: "headcount_monthly",
  select: ["month", "headcount", "growth_rate"],
  filters: [{dimension: "company_url", op: "eq", value: "<account linkedin url>"}],
  order_by: [{field: "month", direction: "desc"}],
  limit: 12
})
```

- One headcount series per company (no `insight` filter needed).
- Same time-series caveat as growth: read `growth_rate`, no in-SQL MoM.

### 6. Dated deployment proof — `insight_evidence` → Confirmed deployment

"Since when" a signal has held at the account (real DATE windows).
**Always** constrain by url + insight (the table is ~1B rows).

```
ask_onfire(query={
  entity: "insight_evidence",
  select: ["start_date", "end_date"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "insight_value", op: "eq", value: "CrowdStrike"}   // resolve via resolve_insights
  ],
  order_by: [{field: "start_date", direction: "asc"}],
  limit: 5
})
```

- Earliest `start_date` = "in production since"; `end_date` NULL = still
  active.
- For a specific person, swap to `{dimension: "person_url", op: "eq", value: "<profile url>"}`.
- Use this to add a date to a Confirmed-deployment profile whose
  `evidence_sentence` is null.

### 7. Developer engagement — `github_member` → Why-Now (eng personas)

Employees at the account who starred/forked an OSS repo (bottom-up
technical interest). `github_member` has no company column, so scope via
a `contact` join.

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  joins: [{entity: "github_member", filters: [
    {dimension: "repo_name", op: "eq", value: "kubernetes"},   // bare name, not owner/repo
    {dimension: "activity", op: "eq", value: "star"}            // star | fork
  ]}],
  limit: 10
})
```

### 8. Alumni / career history — `people_experiences` → Key contacts context

Former employees of the account (warm-path / boomerang context):

```
ask_onfire(query={
  entity: "people_experiences",
  select: ["company_name", "title_name", "start_date", "end_date", "person_url"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "is_primary", op: "eq", value: false}   // past roles only (true = current)
  ],
  limit: 10
})
```

- `start_date` / `end_date` are TEXT (`'YYYY-MM'`) here — not real dates.
- To find current account employees who previously worked somewhere
  specific, query `entity: "contact"` and join `people_experiences`
  filtered to the prior `company_url` with `is_primary = false`.

### 9. Competitor / technology footprint — `contact` + technology insights (MANDATORY)

The Step 1d footprint pull, and the shape to use for any "who runs product
X here" question. **The whole resolved vendor set goes in one call.**

The vendor list below is **an example only** - always pass the tenant's own
resolved set, whatever category it competes in (endpoint, network, email,
observability, identity):

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "job_summary", "linkedin_url", "location_name"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  insight_filters: [{kind: "technology",
                     value: ["CrowdStrike", "SentinelOne", "Splunk"]}],  // e.g.
  limit: 30
})
```

**A list inside one `insight_filters` entry ORs; separate entries AND.**
So one entry with every `exact`/`synonym` vendor from the Step 1a gate
covers the full competitive set in a single round trip. Use separate
entries only when you genuinely need "carries X *and* Y".

Feed only gated terms in. A `partial`/`fuzzy` term here is how a report ends up
"confirming" a broad infrastructure term as if it were a product the account
runs.

This replaces the old raw `JOB_SUMMARY ILIKE` pattern.

### 10. Golden-persona contacts — `contact` + persona insight (MANDATORY)

The tenant's `golden_persona` is its literal buying persona, and the
orchestrator never queries it. These people carry Section 8 when
prospecting is empty.

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "linkedin_url", "location_name"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  insight_filters: [{kind: "persona", value: "<resolved golden_persona>"}],
  limit: 10
})
```

Widen with the other resolved `organization` personas (as a list, per
recipe 9) when the golden persona alone returns nothing. Label each contact
with its `display_names_mapping` label, not the raw config key.

### 11. Incumbent adoption + renewal timing — `product_adoption` (OPTIONAL, BETA)

Gives an incumbent's adoption quarter and the quarter of the year the
account tends to renew - the timing hook a displacement report otherwise
lacks.

```
ask_onfire(query={
  entity: "product_adoption",
  select: ["product", "adoption_quarter", "renewal_quarter"],
  filters: [{dimension: "company_linkedin_url", op: "eq", value: "<account linkedin url>"}],
  limit: 25
})
```

Rules that come with this entity:

- **BETA. Both dates are estimates, never facts.** Any figure surfaced from
  it must be labelled an estimate in the report. Never quote an accuracy rate.
- `renewal_quarter` carries **no year** - it is the quarter of the year the
  account tends to renew. Never render it as a date.
- Coverage is partial. **Absence is not evidence of non-use** - never write
  that an account does not run a product because it is missing here.

### 12. Company profile without a 10-K — `company` (Step 1e)

When `filings_10k.found` is false, the company card comes from here rather
than from unsourced prose.

```
ask_onfire(query={
  entity: "company",
  select: ["name", "industry", "location_country", "size_band", "company_type",
           "website", "linkedin_url"],
  filters: [{dimension: "linkedin_url", op: "eq", value: "<account linkedin url>"}],
  limit: 1
})
```

Pair with `get_company_headcount` for the current number and recipe 5
(`headcount_monthly`) for direction. Confirm the exact dimension names with
`describe_onfire_schema(["company"])` in the same batched call as the other
entities - the size/type field names vary.

### Slicing instead of pulling (free)

The orchestrator's own footprint dataset usually holds 20-30 evidence-backed
rows while `top_profiles` exposes 3. Slicing it costs nothing:

```
query_datasets(
  datasets={"footprint": "<envelope.datasets.linkedin_footprint>"},
  sql="SELECT full_name, linkedin_url, job_title, location_name,
              matched_keyword, evidence_sentence
       FROM footprint
       WHERE evidence_sentence IS NOT NULL"
)
```

Note the argument shape: `datasets` is an **alias -> dataset_id map**, and the
SQL references the alias as a table name.
