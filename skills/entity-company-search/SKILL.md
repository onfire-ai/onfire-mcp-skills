---
name: entity-company-search
description: Search for companies directly from Onfire's LinkedIn company entity (the `company` entity, table ONFIRE.COMPANIES) using the `ask_onfire` tool. Use when the user wants company firmographics, technology adoption, funding data, or social URLs — phrases like "find fintech companies in Israel with 50-200 employees", "look up Northwind's company data", "which companies in our list are publicly traded", "get the GitHub URL for Artifex", or any company lookup that can be answered with structured filters on LinkedIn company data.
---

# entity-company-search

Direct lookup of the `company` entity (table `ONFIRE.COMPANIES`) via `ask_onfire`.
The canonical LinkedIn company entity — firmographics, technologies,
funding, social channels, and enriched metadata in one place.

`ask_onfire` does **not** take SQL. It takes a structured **QueryIR** object —
`{entity, select, filters, insight_filters, joins, order_by, distinct_by, limit}` —
that the server compiles to SQL against the semantic model. You author logical
field names (lowercase, from the schema below), never raw columns or `FROM`/`WHERE`.

> **Billing & limit (read first).** `ask_onfire` bills **1 credit per row
> returned**. Always set a small explicit `limit` for exactly what the user
> asked for. If you leave `limit` unset (or set it large), the call is bounced
> with `needs_confirmation` (`stage: "row_budget"`) — **nothing is billed and no
> rows come back** — it just reports how many rows match so you can pick a budget
> and resubmit. Do not reflexively set `confirmed: true` to push a large pull
> through; lower the `limit` instead.

## When to use this

- "Find cybersecurity companies in Germany with 200-500 employees"
- "Look up Northwind's company record — give me their LinkedIn, size, industry"
- "Which of these companies are B2B? Filter by is_b2b = true"
- "Get the GitHub URL for Artifex"
- "Find publicly traded companies in a sector"
- Any company lookup expressible as structured filters on company firmographics

Skip this for:
- Searching companies by the **people** they employ → use `entity-people-search`
- Scoring companies for propensity → use `ai_prospecting`
- Monthly headcount growth trends → use `company-growth-trends`

## Logical fields (from the `company` entity schema)

Author the QueryIR with these logical names. Call
`describe_onfire_schema(["company"])` to confirm if unsure — never guess a field.

**Filterable dimensions** (use in `filters` with op `eq` | `in` | `gte` | `lte` | `contains`):

| Field | Notes |
|-------|-------|
| `linkedin_url` | Primary identity. `eq` to target ONE company. Any URL format is normalized server-side. |
| `domain` | Bare website domain ("northwind.com"). Prefer for exact matching. |
| `industry` | LinkedIn industry, free text, stored lowercase — use `contains` or a lowercase `eq`. |
| `size_band` | LinkedIn bucket: "1-10","11-50","51-200","201-500","501-1000","1001-5000","5001-10000","10001+". Use `in` for a set. |
| `employee_count` | Numeric — use `gte` / `lte`. |
| `location_country` | HQ country, stored lowercase. |
| `location_region` | HQ state/region, stored lowercase. |
| `location_locality` | HQ city, stored lowercase. |
| `company_type` | "Public", "Private", "Non-profit", etc. |
| `is_b2b` | Boolean enriched flag. |
| `founded` | Year founded. |
| `annual_revenue_range` | Closed bucket. |
| `enriched_category` | Product category, stored lowercase. |
| `technologies` | Self-declared tech **array** — cannot be scalar-filtered (see "Technology adoption" below). |

**Returnable attributes** (use in `select`, not filterable as dimensions):
`name`, `website`, `domain`, `description`, `enriched_summary`, `followers`,
`github_url`, `company_ticker`, `stock_exchange`, `funding_last_round_type`,
`funding_last_round_date`.

**Measure:** `company_count` (= `COUNT(DISTINCT linkedin_url)`) — select alone for a count.

`linkedin_url` is the primary key — keep it in `select`. The soft-delete /
"live" filter (`DELETED_AT IS NULL`) is applied **server-side**; you no longer
author it.

## QueryIR templates

### Lookup by domain (or LinkedIn URL)
```
ask_onfire(query={
  entity: "company",
  select: ["linkedin_url", "name", "website", "size_band", "industry",
           "employee_count", "location_country", "company_type",
           "funding_last_round_type", "funding_last_round_date"],
  filters: [{dimension: "domain", op: "eq", value: "northwind.com"}],
  limit: 1
})
```
Swap the filter for `{dimension: "linkedin_url", op: "eq", value: "<url>"}` to look up by LinkedIn URL.

### By industry + size + country
```
ask_onfire(query={
  entity: "company",
  select: ["linkedin_url", "name", "website", "size_band", "employee_count",
           "location_country", "is_b2b"],
  filters: [
    {dimension: "industry", op: "contains", value: "cybersecurity"},
    {dimension: "size_band", op: "in", value: ["201-500", "501-1000"]},
    {dimension: "location_country", op: "eq", value: "germany"}
  ],
  order_by: [{field: "employee_count", direction: "desc"}],
  limit: 100
})
```
`industry` and `location_country` are stored lowercase — match a lowercase
literal (`"germany"`, not `"Germany"`), and use `contains` for fuzzy industry
matches.

### By technology adoption
The native `technologies` dimension is a self-declared **array** and cannot be
filtered with a scalar op. For adoption depth, use `insight_filters` with
`kind: "technology"` — these are Onfire-derived insight concepts resolved
server-side, with `min_count` = minimum active contacts carrying the technology:
```
ask_onfire(query={
  entity: "company",
  select: ["linkedin_url", "name", "website", "size_band", "industry",
           "location_country"],
  insight_filters: [{kind: "technology", value: "Kubernetes", min_count: 1}],
  filters: [{dimension: "is_b2b", op: "eq", value: true}],
  limit: 100
})
```
Technology/persona values are concepts, not literals — pass the human term and
the server canonicalises it, or confirm the exact value with `resolve_insights`
(carry `kind`) first. Multiple `insight_filters` AND together — run one query per
concept and merge if you need an OR.

### Publicly traded companies in a sector
```
ask_onfire(query={
  entity: "company",
  select: ["linkedin_url", "name", "website", "size_band",
           "company_ticker", "stock_exchange", "location_country"],
  filters: [
    {dimension: "company_type", op: "eq", value: "Public"},
    {dimension: "industry", op: "contains", value: "security"}
  ],
  limit: 50
})
```
NOTE — funding **filtering** is not expressible: `funding_last_round_type` /
`funding_last_round_date` are returnable attributes only, not filterable
dimensions, so you cannot filter "raised a Series B since 2025-01-01" in the
QueryIR. You can `select` them to read each match's last round, but the
round-type / date-range filter itself must be applied after the fact (e.g. on
the downloaded dataset) — flag this to the user rather than dropping it silently.

### Bulk lookup by domain list (e.g. from CRM)
```
ask_onfire(query={
  entity: "company",
  select: ["linkedin_url", "name", "domain", "size_band", "industry",
           "employee_count", "is_b2b", "company_type"],
  filters: [{dimension: "domain", op: "in",
             value: ["northwind.com", "sendline.com", "pathwatch.com", "frostbyte.com"]}],
  limit: 50
})
```

### Get social / community URLs for a company
```
ask_onfire(query={
  entity: "company",
  select: ["name", "linkedin_url", "github_url", "website"],
  filters: [{dimension: "domain", op: "eq", value: "artifex.com"}],
  limit: 1
})
```
NOTE — only `github_url` is exposed on the `company` entity. Discord / Reddit /
other community URLs are not selectable fields here; if the user needs those,
say so rather than implying they were returned.

## Output handling

`ask_onfire` returns a `dataset` handle plus `preview_rows` (first 20).

1. Show `preview_rows` to the user as a table.
2. State `total_count`; if > 20, mention the full CSV is available.
3. Offer `download_dataset(dataset_id="...")` for the full result.
4. For follow-up filters ("now filter to B2B only", "add GitHub URLs"),
   use `query_datasets` against the `dataset_id` — **do not re-run** `ask_onfire`
   (a re-run re-bills per row).

## Common pitfalls

- **Authoring SQL or a `DELETED_AT` filter** — `ask_onfire` takes a QueryIR, not
  SQL, and the live/soft-delete filter is applied server-side.
- **Leaving `limit` unset / too large** — bounced for confirmation (nothing
  billed); set the exact row budget you need.
- **Using `size_band` as a number** — it's a TEXT bucket ("201-500"). Use `in`.
- **Filtering on `technologies` directly** — it's a self-declared array; use a
  `technology` insight_filter (with `min_count`) for adoption.
- **Filtering funding** — `funding_*` are returnable attributes only, not
  filterable dimensions (see the publicly-traded template note).
- **Case on free text** — `industry` / `location_country` / `enriched_category`
  are stored lowercase; match lowercase literals.
- **`domain` vs `website`** — `domain` is the bare domain ("northwind.com");
  prefer it for exact `eq` / `in` matching.
- **Re-running for "now add the GitHub URLs"** — enrich with `query_datasets` on
  the existing `dataset_id` instead of re-billing a fresh `ask_onfire`.
