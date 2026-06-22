---
name: employee-footprint
description: Find employees at a target company whose profiles carry a specific technology or competitor signal using the `ask_onfire` tool (insight-based footprint). Use when the user wants proof a product is deployed at an account, wants a competitor footprint cut, or needs evidence from employee profiles — phrases like "who at Meridian Bank uses Sentinex", "find Ironwall users at Nornet", "do any Northwind engineers run Kubernetes", "show me the Sentinex footprint at Skywall Networks", or any technology/competitor footprint lookup at a specific company.
---

# employee-footprint

Insight-based footprint via `ask_onfire`. The strongest signal that a
product is in-production at an account is its employees carrying that
technology in their profile. `ask_onfire` resolves a product/competitor
to a curated **technology insight** server-side and returns the
employees who carry it — far more precise than a raw profile text match.

`ask_onfire` takes a structured **QueryIR** (never SQL). The footprint
shape is: scope to the company with a `current_company_url` filter, then
match the product with an `insight_filters` entry of `kind: "technology"`.

## When to use this

- "Who at Meridian Bank uses Sentinex?"
- "Find engineers at Nornet who run Kubernetes"
- "Does anyone at Northwind have Cloudgate?"
- "Show me the Sentinex footprint at Skywall Networks"
- "Find employees at these accounts who use our product"
- Any technology/competitor footprint lookup at a specific company

Skip this for:
- GitHub stars/forks → use `github-repo-signals`
- Community membership → use `community-join-signals`
- Event attendance → use `event-attendance-signals`
- Company firmographics → use `entity-company-search`

## How the footprint works

The `contact` entity is anchored on the people profile. `full_name`,
`job_title`, `job_summary`, `summary`, and `linkedin_url` are
**attributes** — selectable, returned on every row, but **not
filterable**. You can NOT `ILIKE` a profile field. A product or
competitor is matched as a **technology insight**, resolved server-side
from the curated catalog and applied as a semi-join.

| Field | Role | Notes |
|-------|------|-------|
| `full_name` | attribute (select) | Display name |
| `job_title` | attribute (select) | Current job title |
| `job_summary` | attribute (select) | Current role description — quote as evidence |
| `summary` | attribute (select) | Career bio / about section |
| `linkedin_url` | dimension | Person's profile URL |
| `current_company_url` | dimension (filter) | Employer LinkedIn URL — scopes the footprint |
| `location_country` | dimension (filter) | Free text, lowercased server-side |

**The product is NOT a column.** It is an `insight_filters` entry:
`{kind: "technology", value: "<product>"}`. Pass the human term; the
server canonicalises it. If unsure of the canonical name, call
`resolve_insights` (carrying `kind: "technology"`) first to confirm —
e.g. a query for `devops` will not match the catalog name `DevOps`.

## Billing — read before calling

`ask_onfire` **bills the client 1 credit per row returned**. Always set
a small explicit `limit` (5–10 rows is plenty for footprint evidence).
If you leave `limit` unset, or request more than the server threshold
without `confirmed: true`, the call returns `needs_confirmation` with
`stage: "row_budget"` — nothing is billed and no rows come back. Lower
`limit` to what you actually need and resubmit; do not reflexively set
`confirmed: true` to push a large pull through.

## QueryIR templates

### Single product at one company
```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "job_summary", "linkedin_url"],
  filters: [{dimension: "current_company_url", op: "eq", value: "https://www.linkedin.com/company/meridian-bank"}],
  insight_filters: [{kind: "technology", value: "Sentinex"}],
  limit: 10
})
```
Any LinkedIn URL format is normalized server-side, so a bare slug URL is fine.

### Several products from a list — one query each, then merge
`insight_filters` **AND** together (a person must carry every listed
insight). To find anyone using *any* product from a list, run **one
query per product** and union the results yourself — there is no OR.

```
// query 1
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "job_summary", "linkedin_url"],
  filters: [{dimension: "current_company_url", op: "eq", value: "https://www.linkedin.com/company/nornet"}],
  insight_filters: [{kind: "technology", value: "Ironwall"}],
  limit: 10
})
// query 2 — same shape, value: "Ironwall SASE"; merge the two result sets.
```

### Competitor footprint — which competitor has the strongest presence?
There is no single grouped query. Run one count per competitor and
compare the totals. Use the `contact_count` measure with a small
`limit` so you are billed for the count rows only:

```
// repeat per competitor: Sentinex, Vanguard, Cloudgate
ask_onfire(query={
  entity: "contact",
  select: ["contact_count"],
  filters: [{dimension: "current_company_url", op: "eq", value: "https://www.linkedin.com/company/meridian-bank"}],
  insight_filters: [{kind: "technology", value: "Sentinex"}],
  limit: 1
})
```
Rank the competitors by the `contact_count` each returns.

### Footprint across multiple target accounts
Scope to several companies with `op: "in"`, then match the product:

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "current_company_name", "linkedin_url"],
  filters: [{dimension: "current_company_url", op: "in", value: [
      "https://www.linkedin.com/company/northwind",
      "https://www.linkedin.com/company/sendline",
      "https://www.linkedin.com/company/pathwatch"
  ]}],
  insight_filters: [{kind: "technology", value: "Sentinex"}],
  distinct_by: "current_company_url",   // one row per account
  limit: 10
})
```
For a per-account headcount, run the single-account `contact_count`
template once per company.

### Senior contacts only (seniority filter)
Seniority is **not** a job-title text match — it is a persona insight.
Add a second `insight_filters` entry; the two AND together (technology
AND seniority):

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "job_summary", "linkedin_url"],
  filters: [{dimension: "current_company_url", op: "eq", value: "https://www.linkedin.com/company/meridian-bank"}],
  insight_filters: [
    {kind: "technology", value: "Sentinex"},
    {kind: "persona", value: "seniority_director"}   // or seniority_executive
  ],
  limit: 10
})
```
Persona seniority values: `seniority_executive` / `seniority_director` /
`seniority_teamlead` / `seniority_ic`.

## When the keyword is NOT a technology

`ask_onfire` matches a product/competitor via the **technology insight
catalog** — it cannot `ILIKE` an arbitrary free-text keyword in
`job_summary` / `summary` / `job_title`. If the user asks for employees
whose profile mentions a phrase that has no insight equivalent (a
project codename, a marketing slogan, a generic word), say so plainly:
the footprint is expressible only for terms that resolve to a technology
(or persona) insight. Run `resolve_insights` to check whether the term
maps to a catalog value before declaring it unsupported.

## Output handling

`ask_onfire` returns a `dataset` handle plus `preview_rows`.

1. Show `preview_rows` as a table. Quote the relevant snippet from
   `job_summary` as the evidence sentence — it is the proof the product
   is deployed.
2. State the total count; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only directors", "show only EMEA") → use
   `query_datasets` on the `dataset_id` — **do not re-run** `ask_onfire`
   (each re-run is billed again).

## Reading the evidence

The most valuable output field is `job_summary`. When presenting results:
- Quote the relevant substring verbatim as proof of deployment.
- `job_summary` mentions = current-role evidence (strongest).
- `summary` mentions = career bio (moderate — may be a past role).
- A technology-insight match without a quotable snippet is still a valid
  signal (the insight was resolved from the full profile + evidence).

## Common pitfalls

- **Product is not a filter** — never put a product in `filters`. It is
  an `insight_filters` entry with `kind: "technology"`.
- **Attributes are not filterable** — `job_summary` / `summary` /
  `job_title` are selectable only; you cannot match text against them.
- **`insight_filters` AND, never OR** — one product per query; run
  several queries and merge for a list.
- **Confirm the canonical name** — `resolve_insights` (kind=technology)
  before authoring if the product name might not match the catalog
  exactly.
- **Billing** — always set a small `limit`; mind the
  `needs_confirmation` row-budget gate.
- **Re-running for follow-ups** — slice the existing dataset with
  `query_datasets` instead of re-billing a new `ask_onfire` call.
