---
name: poc-intelligence
description: >
  Generate a full POC Intelligence Report for a customer tenant. Use this skill whenever someone mentions:
  "POC report", "CRM report", "prepare for POC", "funnel analysis for [customer]", "pipeline status for [customer]",
  "where should we focus for [customer]", "what's the CRM status for [tenant]", "analyze accounts for [customer]",
  "help me win the POC", "conversion rate analysis", "what titles are they targeting", "contact depth",
  "inbound outbound split", "plays for [customer]", "how do we move the numbers for [customer]".
  The skill discovers the tenant's CRM structure dynamically (never assumes field names), pulls live data from
  Salesforce, Metabase, Onfire datasets, and Snowflake, and produces a consolidated HTML report covering:
  three hero numbers (open pipeline ARR, win rate, closed lost ARR), four data-grounded Onfire plays,
  funnel health, competitive intelligence, deal velocity, persona distribution, contact quality,
  stalled deals, win/loss analysis, and a POC playbook.
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
- **Plays layer (top)**: Three hero numbers + four Onfire plays that move those numbers. This is the main value for the customer.
- **Detail layer (below)**: Full CRM analysis — funnel, competitive, velocity, personas, contact quality, stalled deals, wins, losses, POC playbook, data appendix.

The user provides a tenant name. The skill resolves all integration details dynamically. Never assume CRM field names.

---

## Core Principles

**Schema-first, always.** Every query is built from the field map produced in Step 2. If discovery fails for a concept, note it gracefully — do not error.

**Customer-facing framing.** Play descriptions reference data from the customer's own CRM. Do not frame problems as comparisons between CRM state and what Onfire knows — the report describes their situation using their own data, and Onfire is the solution.

**Plays use AI Prospecting.** When describing how Onfire finds contacts, always say "Onfire AI Prospecting" — it finds the best prospects to reach out to, ranked by signal strength, with warm intro paths surfaced (shared connections, former colleagues, mutual touchpoints).

**No internal API references in the report.** Endpoint names and raw field names stay out of customer-facing HTML. Technical details belong in this skill file only.

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

**Key patterns to check:**
- `Amount` vs ARR custom field — some customers use Amount for bookings. Always use the ARR-labeled field.
- Competitor boolean flags: collect all of them. Cross against `IsWon` to compute head-to-head win rates.
- Prospect object: check whether Contact or Lead is primary. For some customers it is Lead (e.g. Torq: 227k active Leads).

---

### Path C — Snowflake Discovery

Run `SHOW TABLES IN SCHEMA GOLD.ENTITIES` — works without a warehouse, returns row counts.
Then `DESCRIBE TABLE` each table for columns — also works without a warehouse.

**Important:** All SELECT queries require a warehouse. If queries fail with error code `391920`, the warehouse is suspended. Document available signals in the report, skip queries, note in Appendix.

**Verified GOLD.ENTITIES schema:**

| Table | Rows | Key fields for POC reports |
|---|---|---|
| COMPANIES | 12.9M | DOMAIN, TECHNOLOGIES (array), FUNDING_ROUNDS_LAST_ROUND_DATE, FUNDING_ROUNDS_LAST_ROUND_MONEY_RAISED, EMPLOYEE_COUNT, COMPANY_UPDATES (array), ENRICHED_KEYWORDS |
| PEOPLE | 93.7M | LINKEDIN_URL, EMAILS (array), JOB_TITLE, JOB_TITLE_LEVELS (array), JOB_COMPANY_DOMAIN, JOB_LAST_CHANGED (date), SKILLS (array) |
| PEOPLE_EXPERIENCES | 415M | Full work history — role change detection, previous employers |

**Top signals to pull when warehouse is available:**

| Sector | Signal | Snowflake source |
|---|---|---|
| Open pipeline | Current SIEM/SOAR stack | COMPANIES.TECHNOLOGIES |
| Open pipeline | Recent funding = budget unlocked | COMPANIES.FUNDING_ROUNDS_LAST_ROUND_DATE |
| Missing contacts | Fill phone/LinkedIn/title gaps | PEOPLE.EMAILS, PEOPLE.JOB_TITLE, PEOPLE.LINKEDIN_URL |
| Stalled deals | Contact changed roles (explains ghosting) | PEOPLE.JOB_LAST_CHANGED |
| Closed lost | Champion left the company | PEOPLE_EXPERIENCES |

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

**Competitive win rates:** Pull all competitor booleans in one GROUP BY query. The result is combinatorial (each row = unique combination of flags). Post-process in Python to sum wins/losses/ARR per individual competitor flag.

**Velocity note:** SOQL does not support DATEDIFF. Use `Days_to_Close__c` if present. Otherwise compute from CloseDate - CreatedDate after pulling raw dates.

---

## Step 4 — Contact Data Quality

```sql
-- Coverage on accounts created in current year
SELECT COUNT(Id) total, COUNT(Email) has_email, COUNT(Phone) has_phone,
       COUNT(MobilePhone) has_mobile, COUNT(Title) has_title,
       COUNT(linkedin_url__c) has_linkedin, COUNT(latest_signal_date__c) has_signal
FROM Contact WHERE IsDeleted=false
AND AccountId IN (SELECT Id FROM Account WHERE CreatedDate>=<year>-01-01T00:00:00Z)
```

Report gap as % and absolute count per field. If `latest_signal_date__c` coverage is near 0% on new accounts, this means `aifire` is disabled — note as a configuration action item.

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

**Anomaly detection:** If the Decision stage shows anomalously low average ARR versus adjacent stages, flag it — it likely contains stale or duplicate records.

---

## Step 6 — Unique CRM Signal Discovery

Scan for and surface custom fields that encode the customer's sales methodology:

- **Pain tracking fields** (e.g. `Alert_Triage_Pain__c`) — if populated, reveal documented ICP pain across the pipeline
- **Scoring fields** (e.g. `MEDDPICC_Score__c`) — distribution across won/lost reveals qualification quality
- **Competitor boolean flags** — always cross against IsWon to produce head-to-head win rates
- **POC tracking fields** — population rate shows POC hygiene
- **Replacing technology** — distribution shows which incumbents are being displaced

Include populated custom signals in a "CRM Unique Signals" subsection of the report.

---

## Step 7 — Plays Data Queries

These queries power the four plays at the top of the report:

```sql
-- Open deals with no buyer (Play 1 + Play 3)
SELECT COUNT(Id) total, SUM(Net_New_ARR__c) arr FROM Opportunity
WHERE IsDeleted=false AND IsClosed=false AND Champion__c=null AND Economic_Buyer__c=null

-- Top open deals with no buyer (named accounts for plays)
SELECT Id, Name, StageName, Net_New_ARR__c, OwnerId,
       PA_XSOAR__c, Splunk_SOAR__c, Replacing_Technology__c, POC_Status__c
FROM Opportunity WHERE IsDeleted=false AND IsClosed=false
AND Net_New_ARR__c>=200000 AND Champion__c=null AND Economic_Buyer__c=null
ORDER BY Net_New_ARR__c DESC LIMIT 20

-- Recoverable closed lost (Play 2)
SELECT Id, Name, Net_New_ARR__c, Loss_Reason__c, LeadSource, CloseDate, LastActivityDate
FROM Opportunity WHERE IsDeleted=false AND IsClosed=true AND IsWon=false
AND Loss_Reason__c IN ('No Customer Response','Loss to No Decision','Loss to No Funding')
AND CloseDate>=2025-01-01
ORDER BY Net_New_ARR__c DESC LIMIT 25

-- Recoverable ARR total
SELECT COUNT(Id) total, SUM(Net_New_ARR__c) arr FROM Opportunity
WHERE IsDeleted=false AND IsClosed=true AND IsWon=false AND CloseDate>=2025-01-01
AND Loss_Reason__c IN ('No Customer Response','Loss to No Decision','Loss to No Funding')
```

---

## Step 8 — Four Plays Generation

The plays section opens the report. Generate exactly four plays grounded in the data above.
Frame every play using the customer's own CRM data as the problem — Onfire is the solution, not the comparison point.

### Play 1 — Signal the Open Pipeline
- **Trigger:** Large volume of open deals with no buying committee
- **Problem:** X deals ($Y ARR) have no Champion or Economic Buyer in Salesforce. No basis to prioritise who to call — the full list gets equal attention.
- **Onfire action:** Use Onfire AI Prospecting on each of the X accounts to find the best 2–3 contacts to reach out to right now, ranked by buying signal strength and seniority fit. Onfire surfaces warm intro paths for each — shared connections, former colleagues, or mutual event touchpoints. Output is a prioritised call list per rep, not a flat spreadsheet.
- **Outcome:** Every blank deal gets a named contact and a warm entry point. Prioritisation moves from rep instinct to signal rank.

### Play 2 — Recover Closed Lost (Ghost + No Decision)
- **Trigger:** Significant ARR in ghost/no-decision closed lost
- **Problem:** X deals ($Y ARR) closed since [date] because a single Champion-level contact went quiet. These accounts still have the same problem — they are the warmest cold leads in the database.
- **Onfire action:** For each account, use Onfire AI Prospecting to find the VP Security or CISO who was never in the original deal. Onfire identifies the warmest entry point: a shared connection for a direct intro, a recent role change ("I know your predecessor was evaluating us"), or a fresh signal giving a personalised re-open reason.
- **Outcome:** 15% re-engagement on the recoverable ARR pool = $X back in active pipeline. Zero re-education cost — these accounts already know the product.

### Play 3 — Fill the Buying Committee Gap
- **Trigger:** Low Economic Buyer and Technical Champion coverage
- **Problem:** Only X% of open deals have an Economic Buyer. No Decision ($Y annually) and Disqualified ($Z) are the 2nd and 3rd largest loss reasons — both caused by deals advancing without executive buy-in.
- **Onfire action:** For each open deal missing an Economic Buyer, use Onfire AI Prospecting to find the CISO or VP Security. For each missing a Technical Champion, find the Detection Engineering Manager or SOC Architect. Onfire prioritises the warmest path to each — a warm intro from a shared connection is worth 10 cold sequences. Gate deal advancement: no deal moves from Qualification to Solution Definition without an Economic Buyer identified.
- **Outcome:** Win rate lift of 6–8 points. The pipeline already exists — the only change is the right person is in each deal before it stalls.

### Play 4 — Competitive Pipeline Expansion
- **Trigger:** Strong win rate on specific competitors + open displacement deals + net-new market available
- **Problem:** X XSOAR and Y Splunk SOAR deals are in open pipeline. But these are only accounts that found their way into the CRM through existing motions. Every enterprise running these tools today is a prospective deal — most have never been contacted.
- **Onfire action (two parts):**
  - *Net-new pipeline:* Use Onfire AI Prospecting to build a target list of companies currently running [competitor tools], filtered by ICP (size, industry, geography). For each, Onfire finds the Detection Engineer (direct product pain) and the CISO (budget decision), plus the warmest intro path to each.
  - *Existing deals:* For each open displacement deal, use Onfire to find the Detection Engineer who works in the tool daily. Structure the POC as a direct side-by-side build — same automation, both tools, letting the engineer see the difference firsthand.
  - *Tines/simplicity-tool motion:* Find accounts where the tool has hit a ceiling — complex workflows, compliance, scale. Look for security teams posting engineering roles suggesting the tool is no longer enough.
- **Outcome:** Win rate improvement on existing competitive deals + $15–20M net-new qualified pipeline from competitive prospecting over two quarters.

---

## Step 9 — Report Generation

Produce the full report as a self-contained HTML file. No external dependencies except Google Fonts.
Must be A4-ready for PDF export via browser print.

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
  ├── #play1        (.play card)
  ├── #play2        (.play card)
  ├── #play3        (.play card)
  ├── #play4        (.play card)
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

**Play cards (.play):** White card, 4px left border (teal-to-purple gradient), `play-n` (10px uppercase label), `play-tags` (pill badges), `play-title` (15px 800), `play-body` (13px prose), `outcome` (green tinted box, `→` prefix).

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
.g5 { grid-template-columns: repeat(3, 1fr) !important; }
.g4 { grid-template-columns: repeat(2, 1fr) !important; }
body { font-size: 11.5px !important; }
.stat-val { font-size: 20px !important; }
```

Include a "Save as PDF" button (hidden in print) calling `window.print()`.

---

## Step 10 — POC Playbook Section

Generate a customer-specific POC playbook using the product the customer sells and the win/loss data found. Not generic — every phase must reference a specific data point from the CRM.

For SOAR customers (e.g. Torq), the standard phases:
1. Before POC (Week -1): Map the customer's SIEM stack; find the Detection Engineer before kickoff
2. Before POC (competitive): Prepare side-by-side build for XSOAR/Splunk accounts
3. During POC (Day 1-2): Live alert triage automation in 48 hours using the customer's actual SIEM data
4. During POC (Week 1-3): Give SOC Analysts direct access to build, not just watch
5. Closing (Final week): POC results document with MTTR numbers for the CISO to use for budget approval

Adapt framework to the customer's product and the specific deals found.

---

## Step 11 — Competitive Intelligence

From the competitor boolean fields:
- Win rate per competitor = wins / (wins + losses)
- Present as paired bars (wins green, losses red) — volume matters as much as percentage
- Highlight: which competitors have the highest loss volume (priority problem), which have the best win rate (priority displacement motion)
- Multi-competitor deals vs single-competitor deals — if multi-competitor has higher win rate, note it (deal complexity often favours breadth)
- Greenfield win rate — the baseline when there is no incumbent tool

Always surface the velocity insight: if won deals have a significantly longer average cycle than lost deals, the implication is persistence beats speed.

---

## Step 12 — Snowflake Signal Layer

Attempt enrichment after CRM data is pulled. Use `SHOW TABLES` and `DESCRIBE TABLE` first (no warehouse). For SELECT queries, check warehouse status first.

Match accounts via COMPANIES.DOMAIN to Salesforce Account.Website.
Match contacts via PEOPLE.LINKEDIN_URL to `linkedin_url__c`.

If warehouse is suspended: list available signals in the report Appendix with "available when warehouse is resumed" note.

---

## Error Handling

| Error | Action |
|---|---|
| Tenant not found | Stop, ask for correct name |
| SOQL field not found | Note in CRM Structure section, proceed without it |
| SOQL DATEDIFF not supported | Use Days_to_Close__c; if absent, compute from raw dates via Python |
| Metabase namespaced table error | Try quoting the table name: `salesforce_torq."Opportunity"` |
| Snowflake warehouse suspended (391920) | Document schema, skip SELECT queries, note in Appendix |
| Competitor boolean data sparse | Run analysis anyway, note low sample sizes where relevant |
| ARR field appears to be Bookings | Use ARR-labeled field, note discrepancy in Appendix |
| aifire disabled | Note as configuration action item in report intro, not a data quality gap |
| No Onfire data for tenant | Skip AI Prospecting in play descriptions, replace with manual research guidance |

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

---

## Reference Files

See `references/sf-soql-patterns.md` — SOQL pagination, aggregate limits, syntax differences (no DATEDIFF, no window functions).
See `references/persona-taxonomy.md` — title-to-persona mapping rules.
See `references/play-templates.md` — full play copy library with example text for each play type.

---

## Step 13 — Account Research Integration

When `account_research.enabled = true` in the tenant settings (confirmed via `get_tenant_settings`), the skill should use the pre-configured research setup for every key account in the report.

The configuration in tenant settings defines:
- `golden_persona` — the primary ICP role to score accounts against
- `queries_sections.competitors` — which competitor tools to detect at each account
- `queries_sections.organization` — which org personas to map (CISO, SecOps, Detection Engineer, etc.)
- `queries_sections.technologies` — which technology stack signals to surface
- `buying_committee_queries` — the exact persona + seniority combinations to find for each account

**When to run account research:**
- Every open pipeline account above $100k ARR
- Every stalled deal (14+ days no activity)
- Every recoverable closed lost account (ghost + no-decision)

**Output in report:** Rank all results by ICP score and include a ranked account summary in the Data Appendix. This replaces rep-level "who do I call first" decisions with a data-driven ranked list every time the report is generated.

**Customer-facing language:** Describe this capability as "Onfire AI Prospecting" in all report sections. Never expose the endpoint name or technical configuration in customer-facing content.
