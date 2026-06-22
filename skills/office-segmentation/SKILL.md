---
name: office-segmentation
description: Build a geographic office segmentation for any company — where are the offices and how many employees work near each one. Orchestrates four tools in sequence: search_offices (discover office locations from Onfire's market intelligence), match_company (resolve LinkedIn URL), get_company_headcount (current employee count), and ask_onfire (per-office employee counts from the contact entity / ONFIRE.PEOPLE). Use when the user asks anything like "how are employees distributed across offices?", "how many people work in the London office?", "what's the geographic footprint of Northwind?", "which office is the biggest?", "map employees to office locations", or "where does the bulk of the workforce sit?".
---

# Office Segmentation

## What this skill does

Given a company name (and optionally a website), this skill:

1. Discovers all worldwide office locations from Onfire's market intelligence.
2. Resolves the company's LinkedIn URL via Matchbox.
3. Gets the current employee headcount snapshot.
4. Counts employees near each office from `ONFIRE.PEOPLE` (one `ask_onfire` count per office).
5. Assembles a ranked table: offices sorted by employee count, regional totals, and % of workforce per office.

---

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `company_name` | Yes | `"Voltaic"` |
| `company_website` | Optional | `"voltaic.com"` |

If the user provides a LinkedIn URL directly, skip Step 2.

---

## Step 1 — Discover offices

```
search_offices(
  company_name="<company_name>",
  company_website="<company_website>",   # pass if available
  telemetry={intent: "..."}
)
```

**Response fields used:**

| Field | Notes |
|-------|-------|
| `offices` | List of `{city, country, state, region, is_hq}` |
| `total_offices` | Total count for narration |

Store the offices list — you'll match location clusters against it in Step 5.

---

## Step 2 — Resolve LinkedIn URL

Skip this step if the user already provided a LinkedIn URL.

```
match_company(
  companies=[
    {"names": ["<company_name>"], "websites": ["<company_website>"]}
  ],
  telemetry={intent: "..."}
)
```

Extract `results[0].linkedin_url`. This is used as the filter key for Steps 3 and 4.

Parse the slug from the URL (e.g. `https://linkedin.com/company/voltaic` → slug = `voltaic`).

---

## Step 3 — Get current headcount

```
get_company_headcount(
  company_linkedin_urls=["<linkedin_url>"],
  months=1,
  telemetry={intent: "..."}
)
```

Use `months=1` — you only need the current snapshot, not historical trends.

**From the response:**

- `headcount.preview_rows[0].employee_count` → total current employees (use for % calculations).
- You do **not** need the employee roster here — location breakdown comes from Step 4.

---

## Step 4 — Get the per-office employee counts

`ONFIRE.PEOPLE` is the `contact` entity in `ask_onfire`. You query it with a
structured **QueryIR** (NOT SQL) — `ask_onfire(query={entity, select, filters, ...})`.

> **No GROUP BY.** `ask_onfire` cannot return a grouped location distribution
> (one query that buckets every employee into a location and counts each
> bucket). The `contact` entity has no per-location grouped measure. So instead
> of one distribution query, run **one count query per office** discovered in
> Step 1 — you already know the office list, so this covers the real need.

For **each** office from Step 1, run one count query. Filter `contact` to the
company's people (`current_company_url eq <linkedin_url>`) AND to that office's
location, and select the `contact_count` measure:

```
ask_onfire(query={
  entity: "contact",
  select: ["contact_count"],          # = COUNT(DISTINCT LINKEDIN_URL)
  filters: [
    {dimension: "current_company_url", op: "eq", value: "<linkedin_url>"},
    {dimension: "location_region", op: "eq", value: "<office region/state>"}
    # or, for a city-level office: {dimension: "location_locality", op: "eq", value: "<office city>"}
  ],
  limit: 1,
  telemetry={intent: "..."}
})
```

- Pass the full `<linkedin_url>` from Step 2 — any URL format is normalized
  server-side (no `ILIKE '%/company/<slug>%'` needed).
- `location_region` / `location_locality` are **free text stored lowercase** —
  pass lowercased literals (e.g. `value: "california"`, `value: "austin"`).
  `op: "contains"` is available if you need a looser substring match.
- One query per office. The returned `contact_count` is that office's employee
  count; use it directly in Step 6 (no Step 5 location-cluster matching needed
  when you count per office this way).

> **Billing / row budget.** `ask_onfire` bills **1 credit per row returned**.
> Each per-office count query returns a single row, so keep `limit: 1`. If a
> call comes back `needs_confirmation` (stage `row_budget`), nothing was billed
> and no rows returned — lower the budget and resubmit; do **not** reflexively
> set `confirmed: true`.

**Capability gap — full grouped distribution is not expressible.** If you need
the complete location distribution across *all* cities/regions (the old
GROUP BY that bucketed every employee into an arbitrary location, including ones
with no known office), `ask_onfire` cannot produce it: there is no grouped
location measure on `contact`. Flag this to the user and fall back to the
per-office counts above. A "Remote / Unknown" residual (total headcount from
Step 3 minus the summed per-office counts) approximates the employees not near
any known office.

---

## Step 5 — Assemble per-office counts (and the residual)

With one `contact_count` per office from Step 4, you already have employees per
office directly — no location-cluster matching is needed. Build the table from:

1. **Per-office count** — the `contact_count` returned for each office query.
2. **Choosing the office filter** — use `location_locality` (city) for a
   city-named office; use `location_region` (state/region) when the office is
   identified by its broader area. Pass lowercased literals.
3. **Remote / Unknown residual** — total headcount from Step 3 minus the summed
   per-office counts. This approximates employees not near any known office
   (fully remote, or in cities with no official office).

**Conflict rule (multiple offices in the same country/region):** if two offices
would both match the same `location_region`, prefer the narrower
`location_locality` (city) filter for each so their counts don't overlap. If you
cannot separate them by city, count them together and note the office cluster
rather than guessing a split.

---

## Step 6 — Build the output

### Office table (sort by employee_count desc)

| Office | Country | Region | HQ | Employees | % of Total |
|--------|---------|--------|-----|-----------|------------|
| Santa Clara | United States | Americas | ✓ | 4 200 | 31% |
| Tel Aviv | Israel | EMEA | | 1 800 | 13% |
| ... | | | | | |
| Remote / Unknown | — | — | | 950 | 7% |
| **Total** | | | | **13 500** | **100%** |

### Regional breakdown

| Region | Offices | Employees | % |
|--------|---------|-----------|---|
| Americas | N | N | N% |
| EMEA | N | N | N% |
| APAC | N | N | N% |
| Remote / Unknown | — | N | N% |

### Narrative

- Lead with the HQ and top 3 offices by headcount.
- Call out any region with >30% concentration.
- Note the Remote / Unknown % — if it's high (>20%), flag it: *"A significant portion of employees listed locations that didn't match a known office — they may be fully remote or based in cities where the company has no official office."*
- Offer `download_dataset` for the full location dataset.
- All office and employee data comes from Onfire. Never reference any external data provider in the output.

---

## Common pitfalls

- **Don't use `get_company_headcount` for the location breakdown** — use it only for the total snapshot. Per-office counts come from `ask_onfire` `contact_count` queries (Step 4).
- **`ask_onfire` cannot GROUP BY** — there is no single grouped location-distribution query. Run one count per known office; flag the full grouped distribution as a capability gap (see Step 4).
- **Location dimensions are free text, lowercase** — pass `location_region` / `location_locality` filter values lowercased (e.g. `"california"`, `"london"`). Use `op: "contains"` for a looser match when the office area doesn't map cleanly to a single locality/region string.
- **Multiple offices in the same region** — prefer the narrower `location_locality` (city) filter per office so counts don't overlap; if they can't be separated, count them together and note the cluster.
- **Billing** — `ask_onfire` bills 1 credit per row; per-office count queries return 1 row, so keep `limit: 1`. A `needs_confirmation` (stage `row_budget`) response means nothing was billed — lower the budget rather than setting `confirmed: true`.
- **Never mention the underlying data source** — always attribute office and employee data to Onfire only. Do not name any third-party provider in any response.
- **LinkedIn URL normalization** — pass the full URL from `match_company` straight into the `current_company_url` filter; `ask_onfire` normalizes any URL format server-side (no slug extraction or `ILIKE` needed).
