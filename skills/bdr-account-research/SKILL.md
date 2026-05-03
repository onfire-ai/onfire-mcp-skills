---
name: bdr-account-research
description: >
  Generate a full BDR (Business Development Representative) account research report for any
  company, combining live data from three sources: Onfire MCP (tenant config + Phoenix AI
  prospecting), Snowflake (SEC 10-K/EDGAR filings), and Metabase (intent signals).
  Use this skill whenever a user asks to "generate a report", "research an account",
  "build a BDR brief", "run account research", or mentions a company domain alongside
  words like "signals", "prospects", "10-K", "use cases", or "tenant". The skill
  automatically reads the tenant's configuration to determine relevant use cases,
  excludes what the tenant has flagged as not interesting, and produces both an inline
  HTML widget and a downloadable PDF. Always use this skill rather than manually
  querying sources one by one.
compatibility: "claude.ai with Onfire MCP, Snowflake, and Metabase MCP connectors"
---

# BDR Account Research Report

## What this skill does

Given a **company website** (e.g. `capitalone.com`) and a **tenant ID** (e.g. `fortinet`),
this skill:

1. Reads the tenant's configuration to derive relevant use cases and excluded topics
2. Queries Snowflake for SEC EDGAR 10-K filings to extract financial, risk, and technology disclosures
3. Discovers and queries the Metabase signals table for live intent signals at this account
4. Runs Phoenix AI prospecting (if the tenant has it enabled) to surface scored prospects
5. Synthesises everything into a structured BDR brief rendered as an HTML widget + PDF

---

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `company_website` | Yes | `capitalone.com` |
| `tenant_id` | Yes | `fortinet` |
| `company_linkedin_url` | Optional | `https://www.linkedin.com/company/capital-one/` — used for Phoenix prospecting; skill will attempt to derive it if missing |

---

## Step 0 — Determine execution plan

Assess what is available by checking which MCP connectors are active:
- **Onfire MCP**: tenant config + Phoenix prospecting
- **Snowflake**: EDGAR 10-K filings
- **Metabase**: intent signals

Run all available sources. Skip sources whose connector is not active and note the gap in
the report. The order is up to you — run in parallel when possible.

---

## Step 1 — Read tenant configuration (Onfire MCP)

Call `get_tenant_settings(tenant_id=<tenant_id>)`.

From the response, extract:

```
config.account_research.enabled          → bool: run Phoenix prospecting?
config.account_research.golden_persona   → primary persona label
config.account_research.queries_sections → {competitors, technologies, organization, cloud_providers}
config.account_research.buying_committee_queries → list of persona groups
config.account_research.display_names_mapping → friendly labels for internal persona keys
```

### Derive use cases

The tenant config does **not** have an explicit use case list. Derive it by mapping
`queries_sections.technologies` signal keywords to use case buckets. Use the mapping
in `references/use-case-mapping.md`. Each use case in the final report must:

- Be supported by ≥1 technology or competitor signal from the tenant config
- Not be in the tenant's exclusion list (see `references/use-case-mapping.md` for how
  to detect excluded use cases from config)

Only report on use cases that pass both tests. Never include AppSec if not present in
the derived set — or any other use case the tenant config doesn't support.

---

## Step 2 — Query EDGAR 10-K filings (Snowflake)

```sql
SELECT
  COMPANY_NAME,
  TICKER,
  FILING_TYPE,
  FILING_DATE,
  FULL_MARKDOWN
FROM bronze.edgar_reports.edgar_latest_view
WHERE website = '<company_website>'
ORDER BY FILING_DATE DESC
```

**If zero rows are returned**: continue without 10-K data. Note the absence in the report
header. Do not fail or stop.

**If rows exist**: the `FULL_MARKDOWN` column contains the full filing as markdown text.
It can be very large (500K–900K chars). Extract only the sections relevant to the report
using targeted substring searches. See `references/10k-extraction.md` for the exact
keywords and extraction patterns for each use case category.

Priority sections to extract (in order):
1. `Item 1C. Cybersecurity` — governance, CISO/CTRO credentials, response plans, third-party risk
2. Risk Factors mentioning: `cyber-attack`, `generative AI`, `third-party AI`, `cloud infrastructure`
3. `integration of [acquired company]` — post-M&A security surface expansion
4. Technology strategy / cloud provider mentions (AWS, Azure, GCP, on-prem)
5. Key executives mentioned alongside cyber/tech/AI

Cap extraction per filing at ~4,000 characters per section to stay within context limits.

---

## Step 3 — Query Metabase signals

### 3a — Discover the signals table dynamically

Every time — do not use hardcoded table IDs.

```
metabase:search(term_queries=["signals"])
```

From the results, find the table where:
- `name` is `"signals"` or `"platform_prod_signals"`
- `database_engine` is `"postgres"`
- `updated_at` is the most recent among candidates (prefer freshest data)

Read the table schema:
```
metabase:get_table(id=<table_id>, with-fields=true)
```

Confirm it has columns: `tenant_id`, `account_website`, `signal_type`, `message_text`,
`intent_holder_linkedin_url`, `date`, `source_type`, `source_name`, `name`.

### 3b — Construct and execute the query

```
metabase:construct_query(
  table_id=<discovered_table_id>,
  fields=[signal_type, message_text, intent_holder_linkedin_url,
          date, source_type, source_name, name, product_lines, topics],
  filters=[
    {field_id: account_website, operation: "equals", value: "<company_website>"},
    {field_id: tenant_id, operation: "equals", value: "<tenant_id>"}
  ],
  order_by=[{field: date, direction: "desc"}],
  limit=50
)
```

Then `metabase:execute_query(query=<constructed_query>)`.

**If zero rows**: continue. Note "No live signals found" in the report.

**If rows exist**: group signals by source type (e.g. `RSA Conference`, `LinkedIn`,
`Slack`, `Discord`) and by signal intent holder. For each unique person, resolve their
identity (name + title + LinkedIn URL) from the `intent_holder_linkedin_url` field.
Cross-reference with Phoenix prospects where possible.

**Quote, never rewrite.** For every signal row rendered in the report, attach a
verbatim excerpt from `message_text` as the proof of intent. You MAY trim with
leading/trailing ellipses (`…`) to focus on the relevant span, but you MUST NOT
paraphrase, summarize, translate, fix typos, reflow whitespace, or otherwise alter
the characters inside the quoted span. The text inside the quote must be a
contiguous substring of `message_text` byte-for-byte. If `message_text` is empty
or null, render `(no message text on record)` — do not substitute another column.

---

## Step 4 — Phoenix AI prospecting (conditional)

**Only run if** `config.account_research.enabled` is `true` from Step 1.

If `company_linkedin_url` was not provided by the user, derive it:
- Try `https://www.linkedin.com/company/<company_name_slug>/`
- If uncertain, skip prospecting and note the gap

```
Onfire MCP:ai_prospecting(
  action="run",
  company_linkedin_url=<url>,
  use_cache=true,
  telemetry={intent: "BDR account research report for tenant"}
)
```

Poll until `status == "completed"` by calling again with identical arguments.

Once complete, call `describe_dataset(dataset_id=<id>, sample_rows=10)` to get all
prospect rows.

For each prospect, map their `TITLE_NAME` and `ai_reasoning` signals to the derived
use cases from Step 1. Use `references/persona-to-usecase.md` for the mapping logic.

---

## Step 5 — Synthesise and render the report

Now combine all collected data into the report. Read `references/report-structure.md`
for the full HTML widget template and section-by-section synthesis rules.

### Report sections (in order)

1. **Report header** — company name, ticker, HQ, revenue, employee count, data sources
   used (badges showing which of Snowflake/Metabase/Phoenix contributed data)

2. **Why now** — 3–5 bullet narrative synthesised from: M&A activity (10-K),
   recent signals (Metabase), prospect activity (Phoenix). Each point must cite its source.

3. **Live signals** — full table of Metabase signals, grouped by person. For any signal
   holder who is also a Phoenix prospect, merge the rows and show AI reasoning inline.
   Highlight the most recent signal and the highest-seniority person.

4. **Use case cards** (one per derived use case, ordered by fit score descending):
   - Fit score (1–10): computed from signal count + prospect title match + 10-K keyword density
   - Account signals (from Metabase + 10-K)
   - Tenant config match (technologies + personas from config)
   - Talking points (grounded in 10-K quotes where available — paraphrased, not verbatim)
   - Top prospects for this use case (from Phoenix, filtered by persona mapping)

5. **Buying committee** — full ranked table from Phoenix + signal holders.
   Priority: `high` = economic buyers (VP+, C-suite, named in 10-K);
   `medium` = technical champions; `support` = influencers / end users.

6. **Approach + cold opens** — one recommended outreach sequence narrative +
   two cold open scripts (one for the most senior buyer, one for the top technical champion).
   Cold opens must cite a specific piece of evidence (10-K disclosure, signal source,
   conference attendance, etc.) — never generic.

---

## Step 6 — Output

### HTML widget

Render the report as an inline HTML widget using `visualize:show_widget`. Follow the
design system in `references/report-structure.md`. Key rules:
- Dark source badges in the header (Metabase = red, Snowflake = blue, Phoenix = green)
- Use case cards with color-coded badges matching the use case (see mapping file)
- Fit score shown as a filled progress bar
- Signals section: most recent signal highlighted with a border-left accent
- 10-K quotes: indented blockquote style with source label
- All LinkedIn URLs rendered as clickable `<a>` links

### PDF

After rendering the HTML widget, also generate a downloadable PDF. Use the approach in
`references/pdf-generation.md`. The PDF mirrors the widget structure with print-friendly
typography. Save to `/mnt/user-data/outputs/account-research-<company>-<tenant>.pdf` and
call `present_files` to make it downloadable.

---

## Error handling and fallbacks

| Situation | Action |
|-----------|--------|
| Tenant config not found | Proceed without use case filtering; show all use cases |
| Snowflake 0 rows | Skip 10-K section; note in header badge |
| Metabase table not found | Skip signals section; note in header badge |
| Metabase 0 signals | Show "No live signals" in signals section |
| Phoenix disabled on tenant | Skip prospecting; note in header badge |
| Phoenix returns 0 prospects | Show "No prospects scored" in buying committee |
| LinkedIn URL unknown | Skip Phoenix; note the gap |
| Any MCP connector inactive | Skip that source entirely; never fail the whole report |

---

## Reference files

- `references/use-case-mapping.md` — Map tenant config technology signals → use case buckets;
  detect excluded use cases
- `references/10k-extraction.md` — Keywords and extraction patterns for each section of EDGAR filings
- `references/persona-to-usecase.md` — Map prospect titles and Phoenix AI reasoning → use cases
- `references/report-structure.md` — Full HTML widget template, section layout, CSS variables,
  color assignments per use case, fit score calculation formula
- `references/pdf-generation.md` — PDF generation approach using weasyprint or pdfkit from HTML

Read the relevant reference file before executing the corresponding step.
