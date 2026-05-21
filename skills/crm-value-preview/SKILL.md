---
name: crm-value-preview
description: >
  Generate a customer-facing CRM Value Preview — a pre-sync, read-only interactive HTML report
  that proves Onfire's value on the customer's own Salesforce data before they commit to a sync.
  Use this skill whenever someone mentions: "value preview", "CRM preview", "pre-sync demo",
  "show what Onfire would do on my CRM", "self-serve demo", "value report", "preview for [tenant]",
  "what would Onfire find in our Salesforce", "live proof on my CRM", "prove it on my data".
  The skill is read-only — it never writes to Salesforce. It learns the customer's close-won
  pattern (winning industries, winning personas), then measures every dimension of their CRM
  against that pattern: open-pipeline persona coverage, contact freshness + completeness,
  account-level duplicates and enrichment, and intent signals from Onfire's data lake. The
  output is a single self-contained interactive HTML file the customer can hand to their
  manager as a value-prop deliverable.
  Always trigger this skill when the user provides a tenant name and asks for any value-preview,
  pre-sync, self-serve, or "show me what Onfire would do" analysis.
compatibility:
  tools:
    - Onfire MCP (get_tenant_settings, integration_proxy, match_company, match_person, contact_data_enrichment, ai_prospecting)
    - Salesforce via integration_proxy (SOQL — preferred path; Metabase execute_query is unreliable)
    - Snowflake (sql_exec_tool — GOLD.ENTITIES.PEOPLE, GOLD.ENTITIES.COMPANIES.TECHNOLOGIES, SILVER.SIGNALS.ARTIFACTS, SILVER.SIGNALS.JOB_POST)
---

# CRM Value Preview Skill

## Overview

This skill produces a customer-facing **CRM Value Preview** for a given tenant as a single
self-contained interactive HTML file. The audience is the customer's evaluator — not internal Onfire
staff. The report is the deliverable they hand to their manager to close the buying decision.

The report has five sections, all in one page (navigated via a sticky top nav):

1. **The Numbers** — funnel snapshot (3 hero ARR + win rate), CRM volume, the gap tiles
   (each gap tile shows raw count + an "Onfire →" uplift line), plus a strip of live signal
   examples across all six signal types.
2. **Open Pipeline** — the section that ties everything to revenue. Derive the close-won
   pattern (winning industries, winning personas, avg security contacts per won account),
   measure each top open opp against the pattern, show per-account persona-coverage gaps
   with named missing roles, show per-account contact-freshness gaps, then sum a concrete
   ARR uplift estimate.
3. **Contact Data Gap** — freshness (job + company changes), completeness (empty / stale email
   + phone), top intent signals on existing contacts (diverse types).
4. **Accounts** — duplicates first (true cluster count, pure dups only), then a wide enrichment
   table with real per-account persona counts from Snowflake + verified tech stack + competitor
   detection, then specific gaps (close-lost trace-back, look-alike scoring, empty-field fills).
5. **Buyers & Champions** — a live AI Prospecting drill on one open opp where the win-pattern
   reveals a missing persona. Full prospect cards with reasoning, scores, warm-intro paths.

The user provides only a **tenant name**. The skill resolves all integration details, samples,
field mappings, and signal sources dynamically.

---

## Core Principles

**Read-only — never writes.** No `POST` / `PATCH` to Salesforce. The customer trusts us because
nothing changes in their CRM.

**Customer-facing framing.** Plain language, no Onfire jargon in the body. Never say "Matchbox",
"MCP", "ai_prospecting", "tenant_settings", "Snowflake", "integration_proxy", or any function
name. Never write "on file" — say "in the record" or omit. No "Live MCP run" / no "SF integration #X"
in the header.

**Learn the win pattern first.** Don't pitch generic "more contacts = more deals." Derive the
customer's actual close-won industries and personas from their SF data, then frame every gap
analysis against that derived pattern.

**Real numbers, not projections, wherever possible.** Persona counts per account come from
Snowflake `GOLD.ENTITIES.PEOPLE`. Tech stack from `GOLD.ENTITIES.COMPANIES.TECHNOLOGIES`. Open-opp
contact counts from live SOQL. Show the customer their actual data, not estimates.

**Open pipeline is the headline.** That's where revenue lives. The Open Pipeline tab gets the
deepest treatment: derived win pattern + per-account gap rows + named missing roles per deal +
freshness cases + 2-lift uplift math.

**Salesforce queries go through `integration_proxy`, not Metabase.** The Metabase `execute_query`
tool is unreliable in current MCP setups (frequently returns "Illegal base64 character 20").
Use SOQL via `integration_proxy(integration_id, method=GET, relative_url='query', params={q: ...})`.

**Signals come from Snowflake `SILVER.SIGNALS.*`, not Metabase.** The platform `signals` table
is only accessible via Metabase which is unreliable. Use Snowflake artifacts/job-post tables
with `TENANT = '<tenant_id>'` filter. Different tenants have different signal-type coverage —
Torq only has website-visitor artifacts; others have more.

**Six signal types to surface, diversified.** Website visit, product-page intent, event speaker
mention, competitor mention, job-change on champion, hiring signal. Don't show only one type.

**Customer-facing copy guardrails.**
- Never claim a specific count like "2,769 signals in 60 days" unless it's directly material —
  prefer "live examples of the signal types Onfire tracks."
- Never use the term "on file" — say "in the record" or omit.
- Never include "Same role, different employer" or similar explanatory subtext for the
  freshness column — let the data speak.
- For competitor tools, always name them explicitly (Cortex XSOAR, Swimlane, IBM QRadar, Tines,
  Splunk SOAR), not just "competitor tech."

---

## Step 1 — Resolve Tenant

Call `get_tenant_settings(tenant_id='<tenant>')`. Extract and cache for the rest of the run:

- `crm.type` — must be `salesforce`. If not, stop and tell the user v1 supports SF only.
- `crm.integration_id` — used in every `integration_proxy` SOQL call.
- `account_research.golden_persona` — the ICP persona name (e.g. `soc_specialist`).
- `account_research.queries_sections.competitors` — competitor list to track in Onfire signals.
- `account_research.queries_sections.technologies` — tech-stack list to track per account.
- `account_research.queries_sections.organization` — the buying-committee personas.
- `signals_settings.excluded_companies` — competitor domains to exclude from signal results.
- `aifire.enabled` — flag for whether automatic CRM enrichment is already running.

The tenant_id is also used as the `TENANT` column filter on Snowflake signals tables.

---

## Step 2 — Funnel & Volume Snapshot (SOQL)

All SOQL goes through `integration_proxy`. Use `relative_url='query'` (not `services/data/...`)
because the integration_proxy prepends the API path. Bracket `IsDeleted = false` everywhere.

```
# Volume
SELECT COUNT(Id) FROM Account WHERE IsDeleted = false
SELECT COUNT(Id) FROM Contact WHERE IsDeleted = false
SELECT COUNT(Id) FROM Lead WHERE IsDeleted = false AND IsConverted = false
SELECT COUNT(Id) FROM Opportunity WHERE IsDeleted = false

# Funnel ARR (open pipeline)
SELECT COUNT(Id), SUM(Amount) FROM Opportunity WHERE IsDeleted = false AND IsClosed = false

# Funnel ARR (closed last 12mo, split by won/lost)
SELECT IsWon, COUNT(Id), SUM(Amount) FROM Opportunity
  WHERE IsDeleted = false AND IsClosed = true AND CloseDate = LAST_N_DAYS:365
  GROUP BY IsWon
```

Compute win rate by deal count and by $ ARR.

---

## Step 3 — Gap KPIs (SOQL)

```
# Stale-90d accounts
SELECT COUNT(Id) FROM Account
  WHERE IsDeleted = false AND (LastActivityDate = null OR LastActivityDate < LAST_N_DAYS:90)

# No-contact accounts
SELECT COUNT(Id) FROM Account a WHERE IsDeleted = false
  AND Id NOT IN (SELECT AccountId FROM Contact WHERE IsDeleted = false AND AccountId != null)

# Stalled open opps
SELECT COUNT(Id) FROM Opportunity
  WHERE IsClosed = false AND IsDeleted = false
  AND (LastActivityDate = null OR LastActivityDate < LAST_N_DAYS:30)

# Missing-industry accounts
SELECT COUNT(Id) FROM Account WHERE IsDeleted = false AND (Industry = null OR Industry = '')

# Contacts missing email / phone
SELECT COUNT(Id) FROM Contact WHERE IsDeleted = false AND (Email = null OR Email = '')
SELECT COUNT(Id) FROM Contact WHERE IsDeleted = false
  AND (Phone = null OR Phone = '') AND (MobilePhone = null OR MobilePhone = '')

# True duplicate count (group by website)
SELECT COUNT(Id), COUNT_DISTINCT(Website) FROM Account
  WHERE IsDeleted = false AND Website != null AND Website != 'Unknown'
# Redundant records = total - distinct

# Top duplicate clusters (for examples)
SELECT Website, COUNT(Id) FROM Account
  WHERE IsDeleted = false AND Website != null AND Website != 'Unknown'
  GROUP BY Website HAVING COUNT(Id) > 1 ORDER BY COUNT(Id) DESC LIMIT 200
```

**SOQL pitfalls to avoid:**
- Subqueries inside aggregate-projection contexts ("only aggregate expressions use field aliasing"
  / "only root queries support aggregate expressions") — split into multiple queries.
- `NOT IN (SELECT field FROM SameObject)` — Salesforce requires inner+outer on different objects.
- Field aliases in non-aggregate queries — not supported.

When filtering duplicates for **display examples**, exclude legitimate parent/subsidiary
structures: Accenture (regional offices), NBA (team subsidiaries), MLB (team subsidiaries),
EY (regional service lines), BT (regional units). Keep only pure-name dupes:
HCA Florida, Infinigate, AdventHealth, Auburn School District, Washington College of Law,
Quadax, Elite Technology, Cardinal Health, KPMG, PwC, Marriott, Hilton, U.S. Bank, plus the
UnitedHealth Group "United Health Group" + "UnitedHealth Group" pair.

---

## Step 4 — Win-Pattern Analysis (the load-bearing section)

This is the section the customer cares most about. Three derived constants drive the entire
Open Pipeline tab.

### 4a. Winning industries

```
SELECT Account.Industry, COUNT(Id), SUM(Amount)
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = true AND IsWon = true
GROUP BY Account.Industry
ORDER BY SUM(Amount) DESC NULLS LAST LIMIT 10
```

Identify the **top-3 industries by won ARR**. Almost universally they'll sum to ~60–75% of
total closed-won ARR. That's the customer's ICP signature.

### 4b. Winning personas

```
SELECT Title, COUNT(Id)
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN (SELECT AccountId FROM Opportunity WHERE IsWon = true AND IsClosed = true)
  AND (Title LIKE '%CISO%' OR Title LIKE '%Security%' OR Title LIKE '%SOC%'
       OR Title LIKE '%Cyber%' OR Title LIKE '%DevSec%'
       OR Title LIKE '%Detection%' OR Title LIKE '%Threat%'
       OR Title LIKE '%Information Security%')
GROUP BY Title ORDER BY COUNT(Id) DESC LIMIT 30
```

The persona filter list above is for SOAR/SOC customers (Torq's profile). For other tenants,
adjust based on `account_research.queries_sections.organization`. The query intentionally
filters to ICP-relevant titles only — generic titles like "Account Executive" or
"Client Manager" show up in raw won-account contacts but aren't the buyers.

Roll up into 4–5 persona buckets:
- **CISO leadership** (CISO + Chief Information Security Officer + Deputy CISO)
- **Security Engineers** (Sr / Principal / Lead / Information Security / Cyber Security Engineer)
- **Security Analysts** (Cyber / Info Sec / SOC / Senior)
- **Security Ops leadership** (SOC Manager / Security Ops Director / Information Security Manager)
- **DevSecOps / Architects** (DevSecOps / DevOps Engineer / Security Architect)

### 4c. Win-pattern average

```
SELECT AccountId, COUNT(Id)
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN (SELECT AccountId FROM Opportunity WHERE IsWon = true AND IsClosed = true)
GROUP BY AccountId ORDER BY COUNT(Id) DESC LIMIT 200
```

Compute the median + mean count of security-persona contacts per won account. The median is
the right "win-pattern target" to compare open opps against (mean is distorted by outliers like
Accenture / consulting firms with hundreds of contacts).

For most tenants in Onfire's profile, this lands around **~5 security contacts per won account**:
CISO + 2 Sec Engineers + 1–2 SOC + 1 supporting. Treat the **minimum** as `CISO + at least one
Security Engineer or DevSecOps`.

---

## Step 5 — Open Pipeline Gap Analysis (the load-bearing section)

Pull the top 15 open opps by ARR with their contact counts:

```
SELECT Id, Name, Amount, StageName, CloseDate, AccountId,
       Account.Name, Account.Website, Account.Industry
FROM Opportunity
WHERE IsClosed = false AND IsDeleted = false AND Amount > 200000
ORDER BY Amount DESC LIMIT 30
```

Then for each opp's AccountId, pull both total and security-only contact counts (batch the
AccountIds into a single `IN (...)` query for each metric):

```
# Total contacts per account
SELECT AccountId, COUNT(Id) FROM Contact
WHERE IsDeleted = false AND AccountId IN ('<id1>', '<id2>', ...)
GROUP BY AccountId

# Security-persona contacts per account
SELECT AccountId, COUNT(Id) FROM Contact
WHERE IsDeleted = false AND AccountId IN ('<id1>', ...)
  AND (Title LIKE '%CISO%' OR Title LIKE '%Security%' OR Title LIKE '%SOC%'
       OR Title LIKE '%Cyber%' OR Title LIKE '%DevSec%' OR Title LIKE '%Detection%'
       OR Title LIKE '%Threat%' OR Title LIKE '%Information Security%')
GROUP BY AccountId
```

For each opp, flag the gap:
- **covered** — security contacts ≥ win-pattern avg
- **thin coverage** — security contacts < win-pattern avg but ≥ minimum (CISO + Eng)
- **below minimum** — missing CISO or Security Engineer
- **outside top-3 won industries** — orthogonal flag, may co-exist

The 5–6 lowest-coverage open opps become the table rows in the "Persona coverage — who's missing
on each open deal" section. For each one, run `ai_prospecting(action='run', company_linkedin_url=...)`
to return real named missing-role candidates (cache results — these calls are expensive).

For contact-freshness on open pipeline, run `match_person` on a small sample (3–5 contacts) per
top-5 opp and check for `company_name` mismatch or `job_title` change. Surface 5 specific stale
contacts across the top open deals.

---

## Step 6 — Account Enrichment with Real Per-Account Numbers (Snowflake)

The Accounts tab's enrichment table is the single biggest credibility moment. Every number must
be real — not projections.

### 6a. Per-account persona counts from Snowflake

```sql
SELECT JOB_COMPANY_LINKEDIN_URL AS co,
       COUNT_IF(REGEXP_LIKE(JOB_TITLE, '.*(ciso|chief information security officer|chief security officer).*', 'i')) AS cisos,
       COUNT_IF(REGEXP_LIKE(JOB_TITLE, '.*(security engineer|cyber security engineer|cybersecurity engineer|information security engineer).*', 'i')) AS sec_engs,
       COUNT_IF(REGEXP_LIKE(JOB_TITLE, '.*(soc analyst|security analyst|cyber security analyst|cybersecurity analyst|information security analyst).*', 'i')) AS sec_analysts,
       COUNT_IF(REGEXP_LIKE(JOB_TITLE, '.*(devsecops|devops engineer).*', 'i')) AS devsecops,
       COUNT_IF(REGEXP_LIKE(JOB_TITLE, '.*(security architect).*', 'i')) AS sec_archs
FROM GOLD.ENTITIES.PEOPLE
WHERE JOB_COMPANY_LINKEDIN_URL IN ('linkedin.com/company/walmart', ...)
GROUP BY 1
```

**Snowflake REGEXP_LIKE pitfalls:**
- The `(?i)` inline flag is rejected. Pass `'i'` as the 3rd argument instead.
- Pattern must start with `.*` and end with `.*` to match anywhere — `REGEXP_LIKE` is
  anchored by default.

### 6b. Per-account tech stack from Snowflake

```sql
SELECT LINKEDIN_URL, NAME,
       FILTER(TECHNOLOGIES, t -> REGEXP_LIKE(t:technology::STRING,
         '.*(splunk|crowdstrike|sentinelone|microsoft sentinel|qradar|chronicle|cortex xsoar|tines|swimlane|elastic security|sumo logic|exabeam).*', 'i')) AS sec_tech
FROM GOLD.ENTITIES.COMPANIES
WHERE LINKEDIN_URL IN (...)
```

Parse the result and split each row into:
- **Detected security stack** (Splunk, SentinelOne, CrowdStrike, Microsoft Sentinel, Exabeam, etc.)
- **Competitor tool detected** (Cortex XSOAR, Swimlane, Tines, IBM QRadar, Splunk SOAR — these are
  the ones in the tenant's `account_research.queries_sections.competitors` list)

Tag each account row in the enrichment table with explicit competitor names — never just
"competitor tech."

### 6c. Picking the sample of 12–15 accounts to display

Pick a mix that tells a story:
- 3–4 brand-name big accounts (Walmart / Amazon / Apple equivalents)
- 3–4 from your closed-lost top-5 (re-opening candidates)
- 3–4 from open-pipeline accounts where the deal is live
- 1–2 no-contact ICP accounts (look-alike to wins)
- 1–2 parent/subsidiary cases (to show the linking story)

The columns to display (right-aligned headers + values for numeric):

| Account | Employees CRM→Onfire | CISO | Sec Eng | SOC Analyst | DevSecOps | Detected security stack | Competitor tool detected |

Do **not** include an "Onfire match" column — it carries no information for the customer.
Drop the "Size band" column — it's redundant given the employee count.

---

## Step 7 — Signals from Snowflake (six diversified types)

Metabase access to the platform `signals` table is unreliable. Use Snowflake instead:

```sql
SELECT a.ARTIFACT_TIME::DATE AS day, a.COMPANY_LINKEDIN_URL,
       a.CONTACT_LINKEDIN_URL, t.ARTIFACT_TYPE_DISPLAY_NAME, t.ARTIFACT_TYPE,
       SUBSTR(a.ARTIFACT_TEXT, 1, 500) AS artifact_text, a.SOURCE_LINK
FROM SILVER.SIGNALS.ARTIFACTS a
LEFT JOIN SILVER.SIGNALS.ARTIFACT_TYPES t ON a.ARTIFACT_TYPE_ID = t.ARTIFACT_TYPE_ID
WHERE a.TENANT = '<tenant>'
  AND a.ARTIFACT_TIME >= DATEADD(day, -60, CURRENT_DATE())
  AND a.ARTIFACT_TEXT IS NOT NULL
  AND a.COMPANY_LINKEDIN_URL IS NOT NULL
ORDER BY a.ARTIFACT_TIME DESC LIMIT 25
```

**Important:** `SUMMARY` is often NULL — use `ARTIFACT_TEXT` instead.

Different tenants have different signal-type coverage. For Torq, only `account_website_visitor`
and `contact_website_visitor` artifacts exist. Other signal types come from:

- **Event speaker mentions** — surface from `ai_prospecting` output's `events` field (per-prospect
  event attendance / speaking).
- **Job changes on champions** — surface from `match_person` results where `company_name` ≠ CRM
  account name.
- **Hiring signals** — query `SILVER.SIGNALS.JOB_POST` filtered by company LinkedIn URL + role
  keywords from the tenant's win-pattern personas.
- **Competitor mentions** — within website visitors, flag any visit from a contact whose
  `company_linkedin_url` matches the tenant's competitor exclude-list.

The Hero signal strip should show **6 cards across 2 rows** with diversified types:
website visit, product-page intent, event speaker, competitor mention, job change, hiring signal.
Never claim a specific total count like "2,769 signals" — say "live examples of the signal
types Onfire tracks."

The Contact Data Gap tab's signal strip shows **3 cards** with 1 visit + 1 product-page intent +
1 event. Don't repeat the same Hero signals.

---

## Step 8 — Buyers & Champions (the live AI Prospecting drill)

Pick **one** open opportunity from Step 5 where the win-pattern reveals a *specific* missing
persona — not just "no contacts." The most compelling story is: "your CRM has the CISO and SOC
team, but you're missing the DevSecOps / Platform Engineering champion who actually drives
Technical Validation."

Steps:
1. From the top-15 open opps, find one in Technical Validation or Business Validation stage
   with strong total coverage but a clear persona-type gap. (For Torq, this was Deutsche Bank.)
2. Pull the existing CRM security contacts on that account.
3. Run `ai_prospecting(action='run', company_linkedin_url=...)` and consume the top 4–5 prospects.
4. Render 4 full prospect cards (white background, NOT light grey — use `.prospect-card` from
   the template). Each card: composite score, score breakdown (Buyer/Tech-champion/Receptiveness/
   Urgency), warm-intro tier (GOLD/SILVER/COLD), named connector, then the AI reasoning with
   block-quoted evidence verbatim, then a "How a rep would use this" green-callout box.
5. Add a header card showing 3 columns: "Already in your CRM" (list the security contacts),
   "Win-pattern check" (✓/✗ per persona role), "What Onfire returned" (summary of the AI
   Prospecting output).

**Score glossary** (must include as an inline alert at the top of the section):
- Authority 1–5 (5 = C-Level, 4 = VP/Director, 3 = Manager, 2 = Specialist, 1 = IC)
- Warm-intro: GOLD = direct overlap with current Onfire colleague; SILVER = shared past company;
  COLD = no path yet.
- Buyer / Tech-champion / Receptiveness / Urgency: scoring dimensions from AI Prospecting,
  each 0–250-ish.

Drop the "Same call runs for every account..." copy. Replace with a concrete forward-looking
card: "After this preview — what changes on the [Account] deal. With 4 named [persona]
champions added, the [industry] win-pattern committee is complete. Same shape ready for every
account in your $XM open pipeline the same day you sync."

---

## Step 9 — Render

Output filename: `<tenant>_preview_<YYYYMMDD>.html`. Single self-contained file. All CSS
inlined. No external assets except Google Fonts (Plus Jakarta Sans). See
[`references/render-contract.md`](references/render-contract.md) for the full HTML structure,
brand tokens, and per-section rendering rules. The skeleton is in
[`assets/template.html`](assets/template.html).

Open the file in the user's default browser at the end (`open ~/Downloads/<filename>.html`).

---

## Verification (run after every change)

End-to-end against Torq (the reference tenant):

1. Invoke this skill: *"Run CRM Value Preview for Torq"*.
2. The Numbers tab confirms: $182.1M open pipeline, 12.1% win rate, 28,203 accounts,
   34,541 contacts, 21,062 no-contact accounts (74.7%), 937 redundant records (3.3%), 877
   missing emails, 5,297 missing phones. Hero signal strip shows 6 diversified cards.
3. The Open Pipeline tab shows: 3 win-pattern industries summing to ~70% of won ARR, ~5 avg
   security contacts per won account, top-15 open opps with live coverage flags, persona-coverage
   table with 5–6 named missing roles, freshness table with stale contacts on top opps,
   ~$4.5M–$6.5M uplift math.
4. The Accounts tab shows: 937 dup records framed correctly, pure-dup examples only (no Accenture
   /NBA /MLB), enrichment table with real per-account persona counts and tech stacks.
5. The Buyers & Champions tab shows: Deutsche Bank live drill with 4 named DevSecOps prospects,
   each with reasoning + warm-intro path + green "how a rep would use this" callout.
6. Print the page → PDF. Confirm sections break cleanly.
7. Confirm zero internal jargon in the customer-visible body. No "MCP", no "match_company",
   no "integration_proxy", no "Snowflake", no "tenant_settings", no "on file."

---

## What this skill does NOT do (v1)

- Does not support HubSpot, Pipedrive, or any non-Salesforce CRM.
- Does not write back to the CRM.
- Does not run server-side PDF rendering — browser print is the v1 export path.
- Does not host the HTML — the operator emails / shares the file directly.
- Does not invoke poc-intelligence as a sub-skill — the close-won pattern is derived inline
  from raw Salesforce queries (cheaper and more reliable).
