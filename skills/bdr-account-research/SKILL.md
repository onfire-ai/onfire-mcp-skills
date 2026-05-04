---
name: bdr-account-research
description: >
  Generate a full BDR (Business Development Representative) account research report for any
  company, combining live data from four sources: Onfire MCP (tenant config + Phoenix AI
  prospecting), Snowflake (SEC 10-K/EDGAR filings + LinkedIn profile data), and Metabase
  (intent signals).
  Use this skill whenever a user asks to "generate a report", "research an account",
  "build a BDR brief", "run account research", or mentions a company domain alongside
  words like "signals", "prospects", "10-K", "use cases", or "tenant". The skill
  automatically reads the tenant's configuration to determine relevant use cases,
  excludes what the tenant has flagged as not interesting, and produces a
  customer-facing A4 HTML file. Always use this skill rather than manually querying
  sources one by one.
compatibility: "claude.ai with Onfire MCP, Snowflake, and Metabase MCP connectors"
---

# BDR Account Research Report

## What this skill does

Given a **company website** (e.g. `capitalone.com`) and a **tenant ID** (e.g. `fortinet`),
this skill:

1. Reads the tenant's configuration to derive relevant use cases and excluded topics
2. Queries Snowflake for SEC EDGAR 10-K filings to extract financial, risk, and technology disclosures
3. Queries Snowflake `gold.entities.people` for current employees whose LinkedIn profiles
   mention the tenant's products or competitor products in their job descriptions
4. Discovers and queries the Metabase signals table for live intent signals at this account
5. Runs Phoenix AI prospecting (if the tenant has it enabled) to surface scored prospects
6. Synthesises everything into a structured Account Research report rendered as a self-contained A4 HTML file

---

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `company_website` | Yes | `capitalone.com` |
| `tenant_id` | Yes | `fortinet` |
| `company_linkedin_url` | Optional | `https://www.linkedin.com/company/capital-one/` |

---

## Step 0 — Determine execution plan

Assess what is available by checking which MCP connectors are active:
- **Onfire MCP**: tenant config + Phoenix prospecting
- **Snowflake**: EDGAR 10-K filings + LinkedIn profile data (`gold.entities.people`)
- **Metabase**: intent signals

Run all available sources in parallel when possible. Skip sources whose connector is not
active and note the gap in the report.

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
- Not be in the tenant's exclusion list (see `references/use-case-mapping.md`)

Only report on use cases that pass both tests.

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

**If zero rows**: continue without 10-K data. Many non-US companies (e.g. Siemens AG,
listed on Frankfurt Stock Exchange) do not file with the SEC. Note the absence in the
report header. Do not fail or stop.

**If rows exist**: extract only relevant sections using targeted substring searches.
See `references/10k-extraction.md` for exact keywords and extraction patterns.

Priority sections to extract (cap at ~4,000 chars each):
1. `Item 1C. Cybersecurity` — governance, CISO/CTRO credentials, response plans
2. Risk Factors mentioning: `cyber`, `AI`, `third-party`, `cloud`, `acquisition integration`
3. Technology strategy / cloud provider mentions
4. Key executives mentioned alongside cyber/tech/AI

---

## Step 3 — Query LinkedIn profile data (Snowflake `gold.entities.people`)

This is the strongest possible evidence of product deployment — direct employee
LinkedIn profiles confirming technology in use.

```sql
SELECT
  FULL_NAME,
  LINKEDIN_URL,
  JOB_TITLE,
  JOB_SUMMARY,
  HEADLINE,
  SUMMARY,
  LOCATION_NAME,
  JOB_START_DATE
FROM gold.entities.people
WHERE (
    JOB_COMPANY_LINKEDIN_URL ILIKE '%<company_linkedin_slug>%'
  )
  AND (
    LOWER(JOB_SUMMARY) LIKE '%<tenant_product_1>%'
    OR LOWER(JOB_SUMMARY) LIKE '%<tenant_product_2>%'
    OR LOWER(SUMMARY)    LIKE '%<tenant_product_1>%'
    -- Also search for key competitors from tenant config
    OR LOWER(JOB_SUMMARY) LIKE '%<competitor_1>%'
    OR LOWER(JOB_SUMMARY) LIKE '%<competitor_2>%'
  )
ORDER BY JOB_START_DATE DESC
LIMIT 30
```

For a Fortinet tenant, search for: `fortinet`, `fortigate`, `fortisase`, `forticlient`,
`forti`, and key competitors: `palo alto`, `crowdstrike`, `zscaler`, `prisma`, `splunk`.

**Derive `company_linkedin_slug`** from the company's LinkedIn URL:
- `https://www.linkedin.com/company/capital-one/` → `capital-one`
- `https://www.linkedin.com/company/siemens/` → `siemens`

**What to do with results:**

From the query results, pick the **3 strongest profiles** per company:
- Prefer profiles with **direct product mentions** (e.g. "Managed Fortinet firewalls,
  including FortiGate models") over general skill mentions
- Prefer **currently employed** people (most recent `JOB_START_DATE`)
- Prefer **senior roles** (engineer, architect, manager, director)

These become the "Confirmed technology deployment" section in the report — inserted
immediately after "Why Now" and before the signals section. Each entry shows:
- Person's name + LinkedIn link + title + location
- The exact sentence from their profile that confirms the product
- A clear label of what the evidence proves (e.g. "FortiGate confirmed in-production")

**Important**: quote the profile text verbatim in the evidence block. This is first-party
data from the person's own LinkedIn description — the strongest possible evidence of
product deployment.

---

## Step 4 — Query Metabase signals

### 4a — Discover the signals table dynamically

Every time — do not use hardcoded table IDs.

```
metabase:search(term_queries=["signals"])
```

Find the table where `name` is `"signals"` or `"platform_prod_signals"`, then:
```
metabase:get_table(id=<table_id>, with-fields=true)
```

### 4b — Construct and execute the query

Fetch `message_text` for evidence — **do not fetch or use `short_summary`**.
Always quote `message_text` verbatim; never substitute `short_summary` or any
other column for evidence rendering:

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
  limit=100
)
```

### 4c — Signal filtering rules (CRITICAL)

**Never use AI-generated summaries to describe what a signal says.** Always use the
raw `message_text` field as the evidence. Read each signal's `message_text` and make
your own judgment about relevance.

**Signal types and how to handle each:**

| Signal type | Action |
|-------------|--------|
| `High Intent` with real `message_text` | Include if message is relevant to the tenant's use cases |
| `High Intent` with empty `message_text` | Include if source confirms a known buying event (e.g. RSA Conference speaker) |
| `Company Change` | Always include if the person moved to/from a relevant role |
| `Promotion` | Include if the person was promoted into a security/IT leadership role |
| `Event Attendee` | Include as-is — confirmed attendance at a relevant industry event is a valid signal |

**What counts as "relevant":**
- Message text mentions a product the tenant sells or a direct competitor
- Message asks about firewall, security tools, or cloud security topics
- Message discusses challenges that map to the tenant's use cases
- Source is a community/event directly related to the tenant (e.g. Fortinet Discord = relevant even if message is about a competitor)

**What to REMOVE:**
- Signals where `message_text` discusses an unrelated topic with no connection to the
  tenant's products (e.g. a general software engineering post with no security relevance)
- Signals where the only "evidence" is an AI summary that doesn't match the actual message
- Duplicate signals from the same person within the same week about the same topic

**Signal source tags** — always use the real source, never invent labels:

| Raw `source_name` / `source_type` | Tag to display in report |
|-----------------------------------|--------------------------|
| RSA Conference, KubeCon, GTC, etc. | "[Event Name] [Year]" |
| Slack | "Professional community" |
| Discord | "Community engagement" |
| LinkedIn | "Digital intent signal" |
| Reddit | "Professional community" |
| GitHub | "Developer community signal" |
| Company Change | "Company change - [From] → [To]" |
| Promotion | "Promotion - [New Title]" |

**Evidence block — Quote, never rewrite (CRITICAL).** For every signal with a
non-empty `message_text`, show that message in a grey evidence block as a
**verbatim** excerpt. You MAY trim with leading/trailing ellipses (`…`) to focus
on the relevant span, but you MUST NOT paraphrase, summarize, translate, fix
typos, reflow whitespace, or otherwise alter the characters inside the quoted
span. The text inside the quote must be a contiguous substring of `message_text`
byte-for-byte. **Never substitute `short_summary` or any other column** — for
Company Change and Promotion signals as well, the evidence block is `message_text`
or nothing. If `message_text` is empty or null, render `(no message text on record)`
or skip the evidence block; do not fabricate or substitute another field.

---

## Step 5 — Phoenix AI prospecting (conditional)

**Only run if** `config.account_research.enabled` is `true` from Step 1.

```
Onfire MCP:ai_prospecting(
  action="run",
  company_linkedin_url=<url>,
  use_cache=true,
  telemetry={intent: "BDR account research report for tenant"}
)
```

Poll until `status == "completed"`. Then call `describe_dataset(dataset_id=<id>, sample_rows=10)`.

For each prospect, map their `TITLE_NAME` and `ai_reasoning` to the derived use cases
from Step 1. Use `references/persona-to-usecase.md` for mapping logic.

---

## Step 6 — Synthesise and render the report

Read `references/report-structure.md` for the full A4 HTML template.

### Writing rules (non-negotiable)

- **No em dashes (—)** anywhere. Use a regular hyphen (-) instead.
- **No internal tool names** anywhere in the HTML. Never mention Metabase, Snowflake,
  Phoenix, Onfire, or any MCP tool. Use: "market intelligence", "intent signals",
  "public filings", "annual filing", "industry research".
- **Company name is a LinkedIn link** — `<a href="[linkedin]">` with `border-bottom: 1.5pt dotted #AEABA5`.
- **Employee stat clarity** — always break down headcount: "~100K Total employees
  (Company A 55K + Company B 45K, post-acquisition)".
- **"Account Research"** label — never "Account Brief". Used in header bar, masthead, and footer.
- **No buying committee or cold opens section** — remove from all reports.
- **No footer sources line** — the footer shows only: company name · Account Research · [Month Year].
- **Signal messages are quoted verbatim** — never paraphrase or reframe what someone said.

### Report section order

1. **Red header bar** — Fortinet logo (base64) + "Account Research - [Company]" + date
2. **Company header card** — name (LinkedIn link), ticker, HQ, stat grid, overview paragraph
3. **Why this account - why now** — 3-5 numbered points from 10-K, signals, M&A, LinkedIn profiles
4. **Confirmed technology deployment** — LinkedIn profile evidence section (Step 3 results)
   - Label: "Current employees listing [tenant] or competitor products directly in their LinkedIn job descriptions"
   - 3 strongest profiles, each with real quoted evidence from their profile text
5. **Intent signals** — verified signals only, each with real `message_text` evidence block
6. **Solution fit section title** — red divider
7. **Use case cards** (one per use case, ordered by fit score) — signals + talking points + 10-K quotes
8. **Key contacts per use case** — `break-before: page`, color-coded by use case

---

## Step 7 — Output

### A4 HTML file

Generate a **fully self-contained** HTML file:

- **No Google Fonts CDN** — use system font stack only:
  `-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif`
  and `monospace` for code/numbers. Google Fonts CDN is blocked when opening local
  `file://` HTML files in Chrome — always use system fonts.
- Fortinet logo embedded as **base64 data URI** — no external image references
- `@page { size: A4; margin: 16mm 18mm 18mm 18mm }` and `body { width: 174mm }`
- All font sizes in `pt`: body 9pt, labels 7pt, headings 11-15pt
- **`print-color-adjust: exact` CSS rule** — required to preserve background colors
  (score bar fills, tags, red header) when printing to PDF. Include in `@media print`:
  ```css
  @media print {
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  }
  ```
- Every `.card` has `break-inside: avoid`
- Key contacts sections have `break-before: page`
- Save to `/mnt/user-data/outputs/account-research-<company>-<tenant>.html`
- Call `present_files`

### PDF instructions for user

Tell the user:
> "To convert to PDF: open in Chrome → Cmd/Ctrl+P → Save as PDF → enable **Background graphics** → Save."

---

## Error handling

| Situation | Action |
|-----------|--------|
| Tenant config not found | Proceed without use case filtering |
| Snowflake 0 rows (10-K) | Skip 10-K section; note non-SEC-registered company |
| Snowflake 0 rows (people) | Skip footprint section silently |
| Metabase table not found | Skip signals section |
| Metabase 0 signals | Show "No live signals found" |
| Phoenix disabled | Skip prospecting |
| Phoenix 0 prospects | Show "No prospects scored" |
| Any connector inactive | Skip that source; never fail the whole report |

---

## Reference files

- `references/use-case-mapping.md` — Map tenant config signals → use case buckets
- `references/10k-extraction.md` — Extraction patterns for each EDGAR filing section
- `references/persona-to-usecase.md` — Map prospect titles → use cases
- `references/report-structure.md` — Full HTML template, CSS, layout rules
- `references/pdf-generation.md` — PDF conversion instructions
