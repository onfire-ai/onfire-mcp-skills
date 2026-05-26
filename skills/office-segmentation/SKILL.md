---
name: office-segmentation
description: Build a geographic office segmentation for any company — where are the offices and how many employees work near each one. Orchestrates four tools in sequence: search_offices (discover office locations from Onfire's market intelligence), match_company (resolve LinkedIn URL), get_company_headcount (current employee count), and query_onfire (location distribution from ONFIRE.PEOPLE). Use when the user asks anything like "how are employees distributed across offices?", "how many people work in the London office?", "what's the geographic footprint of Stripe?", "which office is the biggest?", "map employees to office locations", or "where does the bulk of the workforce sit?".
---

# Office Segmentation

## What this skill does

Given a company name (and optionally a website), this skill:

1. Discovers all worldwide office locations from Onfire's market intelligence.
2. Resolves the company's LinkedIn URL via Matchbox.
3. Gets the current employee headcount snapshot.
4. Pulls a location-distribution summary from `ONFIRE.PEOPLE`.
5. Matches location clusters to the nearest office and produces a ranked table: offices sorted by employee count, regional totals, and % of workforce per office.

---

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `company_name` | Yes | `"NVIDIA"` |
| `company_website` | Optional | `"nvidia.com"` |

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

Parse the slug from the URL (e.g. `https://linkedin.com/company/nvidia` → slug = `nvidia`).

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

## Step 4 — Get location distribution

Query `ONFIRE.PEOPLE` grouped by location to get a compact distribution
(counts per city/country) without loading thousands of individual rows.

```
query_onfire(
  sql="""
    SELECT
        LOCATION_COUNTRY,
        LOCATION_REGION,
        LOCATION_NAME,
        COUNT(*) AS employee_count
    FROM ONFIRE.PEOPLE
    WHERE JOB_COMPANY_LINKEDIN_URL ILIKE '%/company/<slug>%'
      AND DELETED_AT IS NULL
    GROUP BY LOCATION_COUNTRY, LOCATION_REGION, LOCATION_NAME
    ORDER BY employee_count DESC
    LIMIT 500
  """,
  telemetry={intent: "..."}
)
```

Replace `<slug>` with the slug extracted in Step 2.

This returns up to 500 distinct location clusters with their employee counts.

---

## Step 5 — Match locations to offices

For each location cluster from Step 4, find the best-matching office from Step 1 using this priority order:

1. **City match** — office `city` (case-insensitive) appears anywhere in `LOCATION_NAME`.  
   Example: office city = `"Austin"`, location_name = `"Austin, Texas, United States"` → match.
2. **Country match** — office `country` matches `LOCATION_COUNTRY` (case-insensitive).  
   Use this only when no city match exists, and only if a single office exists in that country.
3. **No match** → assign to `"Remote / Unknown"`.

Sum `employee_count` per assigned office to get employees per office.

**Conflict rule (multiple offices in the same country):** When two or more offices share a country and only a country match is available (no city hit), assign the cluster to `"Remote / Unknown"` rather than guessing.

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

- **Don't use `get_company_headcount` for the location breakdown** — its roster can be large and isn't pre-grouped. Use `query_onfire` with GROUP BY for the distribution.
- **`LOCATION_NAME` format varies** — it's typically `"City, Region, Country"` but not always. Use substring match, not an exact equality check.
- **Multiple offices in the same country** — don't assign a location cluster to a country's only big city if the cluster says e.g. `"Germany"` with no city. Assign to Remote / Unknown.
- **`LOCATION_COUNTRY` can be null** — exclude nulls from location matching; they count toward Remote / Unknown.
- **Never mention the underlying data source** — always attribute office and employee data to Onfire only. Do not name any third-party provider in any response.
- **LinkedIn URL normalization** — `match_company` returns a full URL; extract just the slug for the `ILIKE '%/company/<slug>%'` filter in `query_onfire`.
