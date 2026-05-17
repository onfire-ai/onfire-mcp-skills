---
name: poc-intelligence
description: >
  Generate a full POC Intelligence Report for a customer tenant. Use this skill whenever someone mentions:
  "POC report", "CRM report", "prepare for POC", "funnel analysis for [customer]", "pipeline status for [customer]",
  "where should we focus for [customer]", "what's the CRM status for [tenant]", "analyze accounts for [customer]",
  "help me win the POC", "conversion rate analysis", "what titles are they targeting", "contact depth",
  "inbound outbound split", "plays for [customer]", "how do we move the numbers for [customer]",
  "find detection engineers for [customer]", "map the SIEM for [customer]".
  The skill discovers the tenant's CRM structure dynamically (never assumes field names), pulls live data from
  Salesforce, Metabase, Onfire datasets, and Snowflake, and produces a consolidated HTML report covering:
  three hero numbers (open pipeline ARR, win rate, closed lost ARR), four data-grounded Onfire plays each with
  3 real account examples from Snowflake, funnel health, competitive intelligence, deal velocity, persona
  distribution, contact quality, stalled deals, win/loss analysis, and a POC playbook.
  Always trigger this skill when the user provides a tenant name and asks for any CRM, pipeline, or POC analysis.
compatibility:
  tools:
    - Onfire MCP (get_tenant_settings, integration_proxy, list_datasets, query_datasets, describe_dataset, search_people, ai_prospecting)
    - Metabase (search, query, get_table, execute_query)
    - Snowflake (sql_exec_tool — DESCRIBE only without warehouse; SELECT requires warehouse)
---

# POC Intelligence Skill

## Overview

This skill produces a full POC Intelligence Report for a given customer tenant as a self-contained HTML file.
It is customer-facing: clean language, no internal field names in the body, all raw data in the Appendix.

The report has two layers:
- **Plays layer (top):** Three hero numbers + four Onfire plays that move those numbers. Each play contains 3 real account examples sourced from Snowflake — named contacts with persona signals confirmed, SIEM stacks verified from GOLD.ENTITIES.COMPANIES.TECHNOLOGIES.
- **Detail layer (below):** Full CRM analysis — funnel, competitive, velocity, personas, contact quality, stalled deals, wins, losses, POC playbook, data appendix.

The user provides a tenant name. The skill resolves all integration details dynamically. Never assume CRM field names.

---

## Core Principles

**Schema-first, always.** Every query is built from the field map produced in Step 2. If discovery fails for a concept, note it gracefully — do not error.

**Customer-facing framing.** Play descriptions reference data from the customer's own CRM. Do not frame problems as comparisons between CRM state and what Onfire knows — the report describes their situation using their own data, and Onfire is the solution.

**Snowflake before AI Prospecting.** Always query GOLD.ENTITIES.PEOPLE and GOLD.ENTITIES.COMPANIES first. The Snowflake entity data is usually sufficient to find real named contacts with persona signals for every example in the report. Fall back to AI Prospecting only when Snowflake returns no usable result for a specific account.

**Plays use AI Prospecting in copy, Snowflake in examples.** The play body text says "Onfire AI Prospecting" — but the inline examples section inside each play card must show real contacts sourced from Snowflake with confirmed persona signals and SIEM stack data.

**No internal API references in the report.** Endpoint names and raw field names stay out of customer-facing HTML. Technical details belong in this skill file only.

**Examples go inside play cards, not in a separate section.** The 3 account examples for each play are injected between the play body and the outcome box — they are part of the play card, not a standalone section.

---

## Step 1 — Resolve Tenant

Run a Metabase SQL query against the platform production database:

```sql
SELECT * FROM tenants WHERE id = '<tenant_name>'
```

Extract:
- `id` — used in all subsequent Onfire MCP calls
- CRM integration ID and type (confirm Salesforce)
- SEP integration ID if present (Outreach, Salesloft)
- Any Snowflake or Metabase database IDs

Also call `get_tenant_settings` to retrieve the full tenant configuration, including:
- `aifire.enabled` — whether automatic CRM enrichment is running
- `account_research.enabled` and `golden_persona` — ICP configuration
- `account_research.queries_sections` — competitor, org, technology, and cloud signals tracked
- `signals_settings.excluded_companies` — competitor domains excluded from signals
- `crm_settings.crm_fields_mapping` — which Salesforce fields Onfire writes to (signal date, text, source platform)

If the tenant is not found, stop and ask for the correct name.

---

## Step 2 — Three-Path Schema Discovery (run all three in parallel)

### Path A — Metabase Discovery

Search Metabase for existing questions, dashboards, and synced CRM tables.

Run `Metabase:search` in parallel for: `pipeline`, `funnel`, `opportunities`, `deals`, `accounts`, `contacts`, `leads`, `BDR`, `SDR`, `stage`, `owner`, `lead source`, `CRM`.

For each matching table, call `Metabase:get_table` with `with-fields: true` to get the column list.

Extract:
- Which CRM objects are synced (Opportunity, Contact, Lead, Account, custom)
- Pre-built pipeline/funnel dashboards — reference their IDs directly in the report
- Whether a full CRM mirror exists in Metabase SQL — if yes, prefer it for complex queries

**Note:** CRM tables in Metabase may be namespaced (e.g. `salesforce_torq."Opportunity"`) — always quote table names.

---

### Path B — Salesforce Schema Inspection

Via `integration_proxy` (GET), pull the field list for each core object:

```
GET services/data/v56.0/sobjects/Opportunity/describe
GET services/data/v56.0/sobjects/Account/describe
GET services/data/v56.0/sobjects/Contact/describe
GET services/data/v56.0/sobjects/Lead/describe
```

Detect field candidates for these concepts:

| Concept | Field candidates |
|---|---|
| ARR / deal value | `Amount`, `ARR__c`, `Net_New_ARR__c`, `MRR__c`, `ACV__c`, `TCV__c` |
| Pipeline stage | `StageName`, `Stage__c`, `Deal_Stage__c` |
| Lead source / motion | `LeadSource`, `Lead_Source__c`, `Lead_Source_Detail__c` |
| Opp owner | `OwnerId`, `BDR_Owner__c`, `SDR_Owner__c`, `AE_Owner__c` |
| Last activity | `LastActivityDate`, `Last_Touch__c`, `Last_Contact_Date__c` |
| Velocity | `Days_to_Close__c`, `CreatedDate` + `CloseDate` |
| Loss reason | `Loss_Reason__c`, `Closed_Lost_Reason__c` |
| Buying committee | `Champion__c`, `Economic_Buyer__c`, `Tech_Champion__c`, `Champion_Score__c` |
| POC tracking | `POC_Status__c`, `POC_Won__c`, `POC_Scope__c`, `POC_Summary__c` |
| Competitor flags | any boolean containing `XSOAR`, `Splunk`, `Tines`, `Swimlane`, `Microsoft`, `IBM`, `Rapid7`, `ServiceNow`, `D3`, `FortiSOAR`, `Homegrown`, `Greenfield`, `Competing_Against` |
| Pain tracking | fields containing `Pain`, `MEDDPICC`, `Score`, `Alert_Triage`, `SecOps_Pain` |
| Replacing technology | `Replacing_Technology__c`, `Incumbent__c`, `Current_Tool__c` |
| Onfire signal | `latest_signal_date__c`, `latest_signal_text__c`, `latest_signal_source_platform__c` |
| LinkedIn | `linkedin_url__c` |

**Key patterns:**
- `Amount` vs ARR field — some customers use Amount for bookings. Always use the ARR-labeled field.
- Competitor boolean flags — collect all of them. Cross against `IsWon` to compute head-to-head win rates.
- Prospect object — check whether Contact or Lead is primary. Check population of both before assuming.

---

### Path C — Snowflake Discovery

Run `SHOW TABLES IN SCHEMA GOLD.ENTITIES` — works without a warehouse.
Run `SHOW TABLES IN SCHEMA GOLD.INSIGHTS` — reveals available persona/tech insight catalogs.

Then `DESCRIBE TABLE` each table for columns — also works without a warehouse.

**Important:** All SELECT queries require a warehouse. If queries fail with error 391920, the warehouse is suspended — note in report and document what enrichment is available once resumed.

**Verified GOLD schema:**

| Table | Rows | Key fields |
|---|---|---|
| GOLD.ENTITIES.COMPANIES | 12.9M | NAME, WEBSITE, LINKEDIN_URL, TECHNOLOGIES (array — JSON objects with `technology` and `last_verified_at`), FUNDING_ROUNDS_LAST_ROUND_DATE, EMPLOYEE_COUNT, COMPANY_UPDATES (array) |
| GOLD.ENTITIES.PEOPLE | 93.7M | FULL_NAME, LINKEDIN_URL, JOB_TITLE, JOB_COMPANY_NAME, JOB_COMPANY_LINKEDIN_URL, JOB_TITLE_LEVELS (array), JOB_TITLE_ROLE, JOB_LAST_CHANGED, EMAILS (array), SKILLS (array), LOCATION_COUNTRY |
| GOLD.ENTITIES.PEOPLE_EXPERIENCES | 415M | Full work history — role change detection |
| GOLD.INSIGHTS.PERSONA_INSIGHTS | 115 rows | INSIGHT_ID, INSIGHT_NAME, INSIGHT_DEFINITION (full regex — not a join key) |
| GOLD.INSIGHTS.QUERIES_MVIEW | ~3,500 rows | INSIGHT_NAME only — used to check which insights are active, not to join to contacts |

**Critical Snowflake query patterns — verified working:**

```sql
-- Step 1: Get company LinkedIn URLs from website domains
-- (NEVER query PEOPLE directly by website domain — they don't have it)
-- (ALWAYS go through COMPANIES first to get JOB_COMPANY_LINKEDIN_URL)
SELECT NAME, LINKEDIN_URL, WEBSITE, TECHNOLOGIES
FROM GOLD.ENTITIES.COMPANIES
WHERE WEBSITE IN ('company1.com', 'company2.com', ...)
AND LINKEDIN_URL IS NOT NULL

-- Step 2: Query PEOPLE using JOB_COMPANY_LINKEDIN_URL (the correct join key)
SELECT FULL_NAME, LINKEDIN_URL, JOB_TITLE, JOB_COMPANY_NAME,
       JOB_COMPANY_LINKEDIN_URL, JOB_TITLE_LEVELS, JOB_TITLE_ROLE, LOCATION_COUNTRY
FROM GOLD.ENTITIES.PEOPLE
WHERE JOB_COMPANY_LINKEDIN_URL IN (
  'linkedin.com/company/company-a', 'linkedin.com/company/company-b', ...
)
AND REGEXP_COUNT(COALESCE(JOB_TITLE,''),
  '\\b(detection engineer|soc|secops|threat|incident response|security analyst|
  security operations|infosec|information security|cybersecurity|security architect)\\b',
  1, 'i') > 0
AND JOB_TITLE IS NOT NULL
AND ARRAY_SIZE(JOB_TITLE_LEVELS) > 0
ORDER BY JOB_COMPANY_LINKEDIN_URL, JOB_TITLE_LEVELS
LIMIT 100

-- Step 3: Get SIEM/SOAR security tech stack per account
-- TECHNOLOGIES is an ARRAY type — filter with ARRAY_TO_STRING + FILTER
SELECT NAME, WEBSITE,
  ARRAY_TO_STRING(
    FILTER(TECHNOLOGIES, t ->
      REGEXP_COUNT(t:technology::STRING,
        '\\b(splunk|qradar|sentinel|chronicle|xsoar|crowdstrike|sentinelone|
        defender|elastic siem|sumo logic|logrhythm|exabeam|securonix|cortex|demisto)\\b',
        1, 'i') > 0
    ), ', '
  ) AS siem_stack
FROM GOLD.ENTITIES.COMPANIES
WHERE WEBSITE IN (...)
```

**What does NOT work (verified failures):**
- `PARSE_JSON(TECHNOLOGIES)` — TECHNOLOGIES is already an ARRAY, not a string. Use FILTER() directly.
- Querying PEOPLE by company domain directly — PEOPLE has `JOB_COMPANY_LINKEDIN_URL`, not website. Always resolve via COMPANIES first.
- `GOLD.INSIGHTS.QUERIES_CONTACTS_VIEW` — this table does not exist. The correct table is `GOLD.INSIGHTS.QUERIES_MVIEW` and it contains only `INSIGHT_NAME`, not entity-level contact data.
- Multiple SQL statements in one call — Snowflake MCP requires exactly one statement per call.

**Persona insights — how to use them:**
The `GOLD.INSIGHTS.PERSONA_INSIGHTS` table contains behavioural definitions (regex on title, summary, skills). It does NOT map to individual contacts via a join. Use it to:
1. Understand which personas are available for the tenant (e.g. `soc_specialist` ID=5, `detection_engineer` ID=116)
2. Understand what qualifies a contact as that persona (regex patterns) — use those patterns in your own PEOPLE queries
3. Reference the persona name in the report copy: "confirmed soc_specialist signal"

The persona filters to use in PEOPLE queries for security personas:

```
soc_specialist / detection_engineer / secops signal:
REGEXP_COUNT(COALESCE(JOB_TITLE,''),
  '\\b(detection engineer|soc|secops|threat detection|threat hunter|
  incident response|security analyst|security operations|infosec|
  information security|cybersecurity|security architect|blue team|siem|soar)\\b',
  1, 'i') > 0
```

---

### Field Map Output

Consolidate all paths into a single JSON field map. Publish in the Appendix. Example:

```json
{
  "tenant_id": "torq",
  "crm_integration_id": 1131,
  "opp_arr_field": "Net_New_ARR__c",
  "opp_stage_field": "StageName",
  "opp_lead_source_field": "LeadSource",
  "opp_loss_reason_field": "Loss_Reason__c",
  "opp_velocity_field": "Days_to_Close__c",
  "opp_poc_status_field": "POC_Status__c",
  "opp_poc_won_field": "POC_Won__c",
  "opp_buying_committee_fields": ["Champion__c", "Economic_Buyer__c", "Tech_Champion__c"],
  "opp_competitor_boolean_fields": ["PA_XSOAR__c", "Splunk_SOAR__c", "Competing_Against_Checkbox__c", "..."],
  "prospect_object_primary": "Lead",
  "prospect_linkedin_field": "linkedin_url__c",
  "prospect_signal_date_field": "latest_signal_date__c",
  "aifire_enabled": false,
  "golden_persona": "soc_specialist",
  "snowflake_warehouse": "MCP",
  "snowflake_warehouse_status": "SUSPENDED"
}
```

---

## Step 3 — CRM Data Pull (run all queries in parallel)

**Core pipeline queries:**

```sql
-- Open pipeline by stage
SELECT StageName, COUNT(Id) cnt, SUM(Net_New_ARR__c) arr
FROM Opportunity WHERE IsDeleted=false AND IsClosed=false
GROUP BY StageName ORDER BY arr DESC

-- Closed won/lost velocity
SELECT IsWon, COUNT(Id) cnt, SUM(Net_New_ARR__c) arr, AVG(Days_to_Close__c) avg_days
FROM Opportunity WHERE IsDeleted=false AND IsClosed=true AND CloseDate>=2024-01-01
GROUP BY IsWon

-- Loss reasons
SELECT Loss_Reason__c, COUNT(Id) cnt, SUM(Net_New_ARR__c) arr
FROM Opportunity WHERE IsDeleted=false AND IsClosed=true AND IsWon=false AND CloseDate>=2024-01-01
GROUP BY Loss_Reason__c ORDER BY arr DESC

-- Buying committee coverage
SELECT COUNT(Id) total, COUNT(Champion__c) has_champion,
       COUNT(Economic_Buyer__c) has_eb, COUNT(Tech_Champion__c) has_tc
FROM Opportunity WHERE IsDeleted=false AND IsClosed=false

-- Stalled deals (14+ days no activity)
SELECT Id, Name, StageName, Net_New_ARR__c, LastActivityDate, OwnerId
FROM Opportunity WHERE IsDeleted=false AND IsClosed=false
AND LastActivityDate < LAST_N_DAYS:14
ORDER BY Net_New_ARR__c DESC

-- POC status distribution
SELECT POC_Status__c, COUNT(Id) cnt, SUM(Net_New_ARR__c) arr
FROM Opportunity WHERE IsDeleted=false AND IsClosed=false
GROUP BY POC_Status__c

-- POC win multiplier by source
SELECT POC_Won__c, LeadSource, COUNT(Id) cnt, SUM(Net_New_ARR__c) arr
FROM Opportunity WHERE IsDeleted=false AND IsClosed=true AND IsWon=true AND CloseDate>=2024-01-01
GROUP BY POC_Won__c, LeadSource
```

**Competitive win rates:** Pull all competitor booleans in one GROUP BY. The result is combinatorial. Post-process in Python to sum wins/losses/ARR per individual competitor flag.

**Velocity:** SOQL does not support DATEDIFF. Use `Days_to_Close__c` if present.

---

## Step 4 — Contact Data Quality

```sql
SELECT COUNT(Id) total, COUNT(Email) has_email, COUNT(Phone) has_phone,
       COUNT(MobilePhone) has_mobile, COUNT(Title) has_title,
       COUNT(linkedin_url__c) has_linkedin, COUNT(latest_signal_date__c) has_signal
FROM Contact WHERE IsDeleted=false
AND AccountId IN (SELECT Id FROM Account WHERE CreatedDate>=<year>-01-01T00:00:00Z)
```

Report gap as % and absolute count per field. If `latest_signal_date__c` coverage is near 0%, note `aifire` is disabled — configuration action item.

---

## Step 5 — Funnel Stage Mapping

Map the customer's Salesforce stage names to 5 standard business stages:

| Business Stage | Maps from |
|---|---|
| Meeting | Pre-Qualification, Meeting Set, MQL |
| Opportunity | Qualification, Qualified, Discovery |
| POC | Solution Definition, Technical Validation, Proof of Concept |
| Decision | Business Validation, Contracting, Negotiation, Pending Decision |
| Closed Won / Closed Lost | Closed Won, Closed Lost |

Flag anomalously low average ARR in Decision stage — likely stale or duplicate records.

---

## Step 6 — Unique CRM Signal Discovery

Scan for custom fields encoding the customer's sales methodology:
- Pain tracking fields (e.g. `Alert_Triage_Pain__c`) — reveal documented ICP pain
- Scoring fields (e.g. `MEDDPICC_Score__c`) — distribution across won/lost reveals qualification quality
- Competitor boolean flags — always cross against IsWon for head-to-head win rates
- POC tracking fields — population rate shows POC hygiene
- Replacing technology — distribution shows which incumbents are being displaced

---

## Step 7 — Plays Data Queries (run in parallel with Step 3)

These queries power both the play copy and the per-play Snowflake examples:

```sql
-- Total open pipeline missing buyer (Play 1 + Play 3 sizing)
SELECT COUNT(Id) total, SUM(Net_New_ARR__c) arr FROM Opportunity
WHERE IsDeleted=false AND IsClosed=false AND Champion__c=null AND Economic_Buyer__c=null

-- Top POC-stage accounts missing Tech Champion (Detection Engineer examples)
-- Use StageName IN ('Solution Definition','Technical Validation') for precision
SELECT Id, Name, AccountId, Account.Name, Account.Website,
       StageName, Net_New_ARR__c, OwnerId,
       Tech_Champion__c, Economic_Buyer__c, Champion__c,
       PA_XSOAR__c, Splunk_SOAR__c, Replacing_Technology__c, POC_Status__c
FROM Opportunity WHERE IsDeleted=false AND IsClosed=false
AND StageName IN ('Solution Definition','Technical Validation')
ORDER BY Net_New_ARR__c DESC LIMIT 50
-- Then filter Tech_Champion__c=null in post-processing

-- Recoverable closed lost (Play 2 sizing)
SELECT COUNT(Id) total, SUM(Net_New_ARR__c) arr FROM Opportunity
WHERE IsDeleted=false AND IsClosed=true AND IsWon=false AND CloseDate>=2025-01-01
AND Loss_Reason__c IN ('No Customer Response','Loss to No Decision','Loss to No Funding')

-- Top recoverable accounts (Play 2 examples)
SELECT Id, Name, Net_New_ARR__c, Loss_Reason__c, LeadSource, CloseDate, LastActivityDate
FROM Opportunity WHERE IsDeleted=false AND IsClosed=true AND IsWon=false
AND Loss_Reason__c IN ('No Customer Response','Loss to No Decision','Loss to No Funding')
AND CloseDate>=2025-01-01
ORDER BY Net_New_ARR__c DESC LIMIT 25
```

**Important:** Pull `Account.Website` via relationship query so you have the domain needed for the Snowflake COMPANIES lookup in Step 8.

---

## Step 8 — Snowflake Account + People Enrichment (for play examples)

This step finds the real named contacts and SIEM stacks shown inside each play card.

**Execution order — 3 sequential queries per batch:**

### Query 1 — Resolve company LinkedIn URLs from website domains

```sql
SELECT NAME, LINKEDIN_URL, WEBSITE
FROM GOLD.ENTITIES.COMPANIES
WHERE WEBSITE IN ('domain1.com', 'domain2.com', ...)
AND LINKEDIN_URL IS NOT NULL
```

Use the `Account.Website` values from Step 7. Batch all domains in one query. Some websites won't match (e.g. the account uses a different domain in COMPANIES) — include alternate domains where known.

### Query 2 — Find security personas at those accounts

```sql
SELECT FULL_NAME, LINKEDIN_URL, JOB_TITLE, JOB_COMPANY_NAME,
       JOB_COMPANY_LINKEDIN_URL, JOB_TITLE_LEVELS, JOB_TITLE_ROLE, LOCATION_COUNTRY
FROM GOLD.ENTITIES.PEOPLE
WHERE JOB_COMPANY_LINKEDIN_URL IN (
  -- Use the LINKEDIN_URL values returned from Query 1
  'linkedin.com/company/company-a', ...
)
AND REGEXP_COUNT(COALESCE(JOB_TITLE,''),
  '\\b(detection engineer|soc|secops|threat|incident response|security analyst|
  security operations|infosec|information security|cybersecurity|cyber security|
  security architect|devsecops|blue team|siem|soar)\\b', 1, 'i') > 0
AND JOB_TITLE IS NOT NULL
AND ARRAY_SIZE(JOB_TITLE_LEVELS) > 0
ORDER BY JOB_COMPANY_LINKEDIN_URL, JOB_TITLE_LEVELS
LIMIT 100
```

Prefer contacts with `JOB_TITLE_LEVELS` containing `director`, `senior`, `manager`, or `cxo` for examples — these are the right seniority for the buying committee.

### Query 3 — Get SIEM/SOAR stack per account

```sql
SELECT NAME, WEBSITE,
  ARRAY_TO_STRING(
    FILTER(TECHNOLOGIES, t ->
      REGEXP_COUNT(t:technology::STRING,
        '\\b(splunk|qradar|sentinel|chronicle|xsoar|crowdstrike|sentinelone|
        defender|elastic siem|sumo logic|logrhythm|exabeam|securonix|cortex|demisto)\\b',
        1, 'i') > 0
    ), ', '
  ) AS siem_stack
FROM GOLD.ENTITIES.COMPANIES
WHERE WEBSITE IN (...)
ORDER BY NAME
```

Note: `TECHNOLOGIES` elements contain `technology` and `last_verified_at` fields. Filter by `last_verified_at > '2025-01-01'` if you want only recently confirmed tools.

### Persona confirmation

After getting contacts from Query 2, confirm their persona match by checking `GOLD.INSIGHTS.PERSONA_INSIGHTS` for the relevant insight name (e.g. `soc_specialist`, `detection_engineer`) and cross-referencing that the contact's title/summary patterns match the definition. Use the INSIGHT_NAME in the report copy as the signal label.

### Fallback to AI Prospecting

Only if Snowflake returns no usable named contact for a specific account after both queries: fall back to `ai_prospecting` or `search_people` for that account specifically. Note in the example that the contact was sourced via AI Prospecting rather than PEOPLE data.

---

## Step 9 — Four Plays Generation

Each play card has four parts in this exact order:
1. **Play header** — number, target metric, timing label, tag pills
2. **Play body** — problem (from CRM data) + Onfire action (AI Prospecting language) + named accounts
3. **Play examples** — 3 real accounts from Snowflake, between the body and the outcome box
4. **Outcome box** — projected ARR impact

### Play examples HTML component

Each play card uses a `.play-examples` block injected between the play body and the `.outcome` div:

```css
.play-examples { margin-top:16px; border-top:1px solid var(--border); padding-top:14px }
.play-ex-label { font-size:10px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--t3); margin-bottom:10px }
.play-ex-grid  { display:grid; grid-template-columns:repeat(3,1fr); gap:10px }
.pex           { background:rgba(0,48,73,.03); border:1px solid var(--border); border-radius:var(--rs); padding:10px 12px }
.pex-account   { font-size:12px; font-weight:700; color:var(--navy); margin-bottom:1px }
.pex-arr       { font-size:10px; font-weight:700; color:var(--teal) }
.pex-contact   { font-size:11px; color:var(--navy2); margin:5px 0 2px; font-weight:600 }
.pex-title     { font-size:11px; color:var(--t3); margin-bottom:5px }
.pex-tags      { display:flex; gap:4px; flex-wrap:wrap; margin-bottom:6px }
.pex-siem      { display:flex; flex-direction:column; gap:3px; margin:5px 0 }
.pex-siem-row  { font-size:10px; font-weight:600; color:var(--navy2) }
.pex-siem-row span { color:var(--t3); font-weight:400 }
.pex-action    { font-size:11px; color:var(--t2); line-height:1.55; border-top:1px solid var(--border); padding-top:5px; margin-top:2px }
```

Each `.pex` card contains:
- Account name + ARR + stage + incumbent tool
- Named contact from Snowflake (FULL_NAME, JOB_TITLE, LINKEDIN_URL)
- Persona signal tag (e.g. `soc_specialist`, `secops`) — from PERSONA_INSIGHTS catalog
- Source tag (e.g. "PEOPLE confirmed" or "AI Prospecting")
- SIEM stack from COMPANIES.TECHNOLOGIES (label + value pairs)
- Personalised action: a specific opening message referencing the account's stack + deal situation

### What to show per play

| Play | Example focus | Contact persona | SIEM/stack use |
|---|---|---|---|
| Play 1 (Signal pipeline) | High-ARR open deals with no buyer — POC-stage priority | soc_specialist / detection_engineer | Show confirmed SIEM as POC Day 1 integration target |
| Play 2 (Recover closed lost) | Ghost or No Decision accounts — new contact never in original deal | CISO / VP Security | Show SIEM migration signals as re-open hook (e.g. new tool adoption) |
| Play 3 (Buying committee gap) | Active POC deals with no EB or TC — most urgent = Technical Validation | CISO for EB gap; Detection Engineer for TC gap | Show stack complexity as reason the right person is critical |
| Play 4 (Competitive expansion) | Open XSOAR/Splunk displacement deals + net-new targets | Detection Engineer — the person with direct product pain | Show full SIEM/SOAR stack — side-by-side POC is already set up by the environment |

### Play copy framework

**Problem statement:** Always sourced from CRM data — specific numbers (X deals, $Y ARR), named stage, named loss reason.

**Onfire action:** Use "Onfire AI Prospecting" language. Describe warm intro paths (shared connections, former colleagues, recent role changes). Never reference internal endpoints.

**Named accounts in body:** Pick the highest-ARR accounts matching the play trigger. Reference their stage, ARR, and incumbent tool.

**Outcome box:** Specific ARR projection — based on historical win rates applied to the addressable pool.

---

## Step 10 — Report Generation

Produce the full report as a self-contained HTML file. No external dependencies except Google Fonts (Plus Jakarta Sans). Must be A4-ready for PDF export via browser print.

### Design system (never deviate)

| Token | Value | Usage |
|---|---|---|
| `--navy` | `#003049` | Primary text, headers, nav |
| `--teal` | `#0BA3A3` | Primary accent, highlights |
| `--purple` | `#7C5CFC` | Secondary accent |
| `--green` | `#16A34A` | Won, positive, success |
| `--red` | `#DC2626` | Lost, risk, negative |
| `--amber` | `#B45309` | Warning, stalled, attention |
| `--bg` | `#EEF6FF` | Page background |
| `--card` | `#FFFFFF` | Card background |

Background: layered radial gradients (teal top-left, purple bottom-right) + 48px grid tile pattern. Use `position: fixed` on screen, `position: absolute` in print.

Typography: Plus Jakarta Sans. Section headers: `sec-eye` (10px uppercase teal) + `sec-title` (20px 800 navy) + `sec-sub` (13px body).

### HTML report structure

```
header          — Navy bar, Onfire logo (base64 JPEG embedded), tenant name, date
nav             — Sticky. Order: The Numbers → Play 1 → Play 2 → Play 3 → Play 4 → CRM Status → Funnel → Competitive → Velocity → Contacts → Stalled → Wins → Losses → POC → Data
div.main
  ├── #plays-intro  (3 stat cards + impact alert)
  ├── #play1        (.play card — body → .play-examples [3 pex cards] → .outcome)
  ├── #play2        (.play card — body → .play-examples [3 pex cards] → .outcome)
  ├── #play3        (.play card — body → .play-examples [3 pex cards] → .outcome)
  ├── #play4        (.play card — body → .play-examples [3 pex cards] → .outcome)
  ├── <hr> divider
  ├── #status       (5 stat cards + 3 alerts)
  ├── #funnel       (funnel bars + POC status)
  ├── #competitive  (head-to-head bars)
  ├── #velocity     (won vs lost days)
  ├── #personas     (title distribution)
  ├── #contacts     (field coverage)
  ├── #stalled      (rep table + account list)
  ├── #wins         (POC multiplier + top reps)
  ├── #losses       (loss reason breakdown + insight)
  ├── #poc          (6-phase POC playbook cards)
  └── #data         (appendix: field map, raw tables, Snowflake schema)
footer          — Navy bar, Onfire logo, date
```

### Component rules

**Stat cards (.stat):** White card, 3px colored bottom border. `stat-val` at 26px 800-weight. Never use full dark backgrounds for hero numbers — maintain proportions.

**Play cards (.play):** White card, 4px left border (teal-to-purple gradient). Structure: `.play-n` → `.play-tags` → `.play-title` → `.play-body` → `.play-examples` → `.outcome`.

**Play examples (.play-examples):** 3-column grid of `.pex` cards. Sits between play body and outcome. Uses subtle grey background (`rgba(0,48,73,.03)`) — same card style as the rest of the report.

**Competitive bars:** Two paired bars per competitor (green = wins, red = losses), win rate % on the right. Sort by total volume descending.

**Onfire logo:** Always embed as base64 JPEG. Header: 40px, border-radius 9px. Footer: 28px, border-radius 7px. `object-fit: cover`.

### A4 / PDF print CSS (required in every report)

```css
@page { size: A4; margin: 12mm 14mm; }
* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
body::before { position: absolute !important; }
body::after  { display: none !important; }
.nav         { display: none !important; }
.main        { max-width: 100% !important; padding: 18px 0 !important; }
#competitive, #wins, #poc, #plays, #data { break-before: page; page-break-before: always; }
.card, .play, .stat, .alert, .tbl tr { break-inside: avoid; page-break-inside: avoid; }
.play-ex-grid { grid-template-columns: repeat(2,1fr) !important; }
.g5 { grid-template-columns: repeat(3, 1fr) !important; }
.g4 { grid-template-columns: repeat(2, 1fr) !important; }
body { font-size: 11.5px !important; }
.stat-val { font-size: 20px !important; }
```

Include a "Save as PDF" button (screen only) calling `window.print()`.

---

## Step 11 — POC Playbook Section

Generate a customer-specific POC playbook using the product the customer sells and the win/loss data found. Not generic — every phase must reference a specific data point from the CRM.

For SOAR customers (e.g. Torq), the standard phases:
1. Before POC (Week -1): Map the customer's SIEM stack (from Snowflake); find the Detection Engineer before kickoff
2. Before POC (competitive): Prepare side-by-side build for XSOAR/Splunk accounts
3. During POC (Day 1-2): Live alert triage automation in 48 hours using the customer's actual SIEM data
4. During POC (Week 1-3): Give SOC Analysts direct access to build, not just watch
5. Closing (Final week): POC results document with MTTR numbers for the CISO to use for budget approval

Adapt framework to the customer's product and the specific deals found.

---

## Step 12 — Competitive Intelligence

From the competitor boolean fields:
- Win rate per competitor = wins / (wins + losses)
- Present as paired win/loss bars — volume matters as much as percentage
- Highlight: highest loss volume (priority problem) and best win rate (priority displacement motion)
- Multi-competitor deals vs single-competitor — if multi-competitor has higher win rate, note it
- Greenfield win rate — the baseline

Always surface the velocity insight: if won deals have a significantly longer average cycle than lost deals, persistence beats speed.

---

## Step 13 — Snowflake Signal Layer (summary stats)

In addition to the per-play examples in Step 8, surface aggregate Snowflake signals in the report:

**Summary numbers to include:**
- How many POC-stage accounts have a confirmed SIEM stack in COMPANIES.TECHNOLOGIES
- How many have no SIEM identified (ask in kickoff)
- SIEM distribution: Splunk (any variant), Azure Sentinel, Cortex/XSOAR, IBM QRadar, CrowdStrike
- How many POC-stage accounts are missing Tech Champion (Detection Engineer) in Salesforce

These go in the Contact Data Quality or POC Playbook section as a callout, not a separate standalone section.

---

## Step 14 — Account Research Integration

When `account_research.enabled = true` in tenant settings, the skill should use the pre-configured research setup for every key account.

**When to run:** Every open pipeline account above $100k ARR, every stalled deal (14+ days dark), every recoverable closed lost account.

**Customer-facing language:** Describe as "Onfire AI Prospecting" everywhere in the report. Never expose endpoint names or config keys.

---

## Error Handling

| Error | Action |
|---|---|
| Tenant not found | Stop, ask for correct name |
| SOQL field not found | Note in CRM Structure section, proceed without it |
| SOQL DATEDIFF not supported | Use `Days_to_Close__c`; if absent, compute from raw dates via Python |
| Metabase namespaced table error | Try quoting: `salesforce_torq."Opportunity"` |
| Snowflake warehouse suspended (391920) | Document schema, skip SELECT queries, note in Appendix |
| `PARSE_JSON(TECHNOLOGIES)` error | TECHNOLOGIES is already ARRAY — use `FILTER(TECHNOLOGIES, t -> ...)` directly |
| PEOPLE query returns 0 rows for a company | Company LinkedIn URL format mismatch — get it from COMPANIES first, then re-query PEOPLE |
| `GOLD.INSIGHTS.QUERIES_CONTACTS_VIEW` not found | Table does not exist. Use `GOLD.INSIGHTS.QUERIES_MVIEW` (INSIGHT_NAME only — no entity join) and `GOLD.INSIGHTS.PERSONA_INSIGHTS` (full regex definitions). |
| Competitor boolean data sparse | Run analysis anyway, note low sample sizes where relevant |
| ARR field appears to be Bookings | Use ARR-labeled field, note discrepancy in Appendix |
| aifire disabled | Note as configuration action item, not a data quality gap |
| No Snowflake contact found for an account | Fall back to AI Prospecting for that account; label the example accordingly |

---

## Torq Field Map (verified reference)

| Concept | Field |
|---|---|
| Net new ARR | `Net_New_ARR__c` (not `Amount` = bookings) |
| Stage | `StageName` |
| Lead source | `LeadSource` |
| Onfire source tag | `Lead_Source_Detail__c = "OnFire"` |
| AE owner | `OwnerId` |
| BDR owner | `BDR_Owner__c` (4% populated) |
| Velocity | `Days_to_Close__c` |
| Loss reason | `Loss_Reason__c` |
| Replacing technology | `Replacing_Technology__c` |
| POC status | `POC_Status__c` |
| POC won | `POC_Won__c` |
| Champion | `Champion__c` |
| Economic Buyer | `Economic_Buyer__c` |
| Technical Champion | `Tech_Champion__c` |
| Alert triage pain | `Alert_Triage_Pain__c` |
| SecOps pain | `SecOps_Pain__c` |
| MEDDPICC score | `MEDDPICC_Score__c` |
| Competitor: XSOAR | `PA_XSOAR__c` |
| Competitor: Splunk SOAR | `Splunk_SOAR__c` |
| Competitor: Tines | `Competing_Against_Checkbox__c` |
| Competitor: D3 | `D3_Security__c` |
| Competitor: Swimlane | `Swimlane__c` |
| Competitor: Microsoft | `Microsoft__c` |
| Competitor: ServiceNow | `Service_Now__c` |
| Competitor: IBM | `IBM_Resilient__c` |
| Competitor: Rapid7 | `Rapid7__c` |
| Competitor: FortiSOAR | `FortiSOAR__c` |
| LinkedIn (Lead/Contact) | `linkedin_url__c` |
| Onfire signal date | `latest_signal_date__c` |
| Onfire signal text | `latest_signal_text__c` |
| Primary prospect object | `Lead` (227k active) |
| Secondary prospect object | `Contact` (post-conversion) |

**Torq Competitive Win Rates (2,575 closed deals since 2024):**

| Competitor | Wins | Losses | Win Rate | Note |
|---|---|---|---|---|
| Greenfield | 81 | 85 | 49% | Best baseline |
| Splunk SOAR | 51 | 55 | 48% | Best displacement motion |
| D3 Security | 12 | 15 | 44% | |
| Swimlane | 28 | 48 | 37% | |
| Tines | 104 | 208 | 33% | Highest loss volume |
| Microsoft | 9 | 19 | 32% | |
| XSOAR (Cortex) | 39 | 87 | 31% | Largest displacement opportunity |
| Homegrown | 9 | 30 | 23% | |
| ServiceNow | 2 | 16 | 11% | Hard to win |
| IBM Resilient | 0 | 9 | 0% | Qualify out early |

Won deals avg: 245 days. Lost deals avg: 155 days. **Persistence beats speed.**

**Torq Snowflake SIEM coverage across 50 POC accounts (verified April 2026):**
- Splunk (any variant): 35/50 accounts (70%)
- CrowdStrike: 29/50 (58%)
- Azure Sentinel / Microsoft: 17/50 (34%)
- Cortex XSOAR: 14/50 (28%)
- IBM QRadar: 7/50 (14%)
- No SIEM identified: 14/50 — confirm in kickoff call

---

## Reference Files

See `references/sf-soql-patterns.md` — SOQL pagination, aggregate limits, syntax differences (no DATEDIFF, no window functions).
See `references/persona-taxonomy.md` — title-to-persona mapping rules.
See `references/play-templates.md` — full play copy library with example text for each play type.
