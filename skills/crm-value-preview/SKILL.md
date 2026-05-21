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
  This skill is tenant-generic — invoke as "Run CRM Value Preview for <tenant>" and the report
  adapts to that customer's CRM shape, ICP, and signal coverage. Always trigger when the user
  provides a tenant name and asks for any value-preview, pre-sync, self-serve, or
  "show me what Onfire would do" analysis.
compatibility:
  tools:
    - Onfire MCP (get_tenant_settings, integration_proxy, match_company, match_person, contact_data_enrichment, ai_prospecting)
    - Salesforce via integration_proxy (SOQL — preferred path; Metabase execute_query is unreliable)
    - Snowflake (sql_exec_tool — GOLD.ENTITIES.PEOPLE, GOLD.ENTITIES.COMPANIES.TECHNOLOGIES, SILVER.SIGNALS.ARTIFACTS, SILVER.COMMUNITY_MESSAGES.INT_MESSAGES_WITH_LINKEDIN, SILVER.JOB_POST.STG_JOB_POSTS)
  sibling_skills:
    - poc-intelligence — sister skill that produces a deeper internal-facing CRM analysis with 4 named plays and a 6-phase POC playbook. This skill (crm-value-preview) is the customer-facing pre-sync version of the same idea. They share the win-pattern derivation pattern, the persona-coverage analysis, and the field-candidate taxonomy; this skill borrows poc-intelligence's reference docs (see "Reuse from poc-intelligence" below).
---

# CRM Value Preview Skill

## Overview

This skill produces a customer-facing **CRM Value Preview** for any tenant as a single
self-contained interactive HTML file. The audience is the customer's evaluator — not internal Onfire
staff. The report is the deliverable they hand to their manager to close the buying decision.

**Tenant-generic by design.** The user invokes the skill with a tenant name (e.g. *"Run CRM
Value Preview for cerby"* / *"…for fortinet"* / *"…for torq"*). The skill discovers the
customer's CRM shape, ICP, persona definitions, competitor list, and signal coverage from
`get_tenant_settings` + live Salesforce describes — never hardcoded.

Five customer-facing sections:

1. **The Numbers** — funnel snapshot, CRM volume, gap tiles each with an "Onfire →" uplift
   line, plus a 6-card strip of diversified signal examples.
2. **Open Pipeline** — the section that ties everything to revenue. Derived close-won pattern
   (winning industries, winning personas, avg buying-committee contacts per won account),
   per-opp gap measurement, named missing roles from live AI Prospecting, freshness cases,
   ARR uplift estimate.
3. **Contact Data Gap** — freshness (job + company changes), completeness (empty / stale email
   + phone), top diversified intent signals on existing contacts.
4. **Accounts** — duplicates first, then a wide enrichment table with real per-account persona
   counts + verified tech stack + competitor detection, then specific gaps.
5. **Buyers & Champions** — live AI Prospecting drill on one open opp where the win-pattern
   reveals a specific missing persona.

---

## Core Principles

**Read-only.** No `POST` / `PATCH` to Salesforce.

**Customer-facing framing.** Plain language, zero Onfire jargon in the body. Never say "MCP",
"match_company", "ai_prospecting", "integration_proxy", "tenant_settings", "Snowflake",
"Metabase", "SOQL". Never write "on file" — say "in the record" or omit. No internal IDs
("SF integration #1131", "Live MCP run") in the header.

**Tenant-generic.** Every persona keyword, every competitor name, every industry mention is
derived at run time from `tenant_settings`. **No Torq-specific copy.** The same skill produces
the same shape of report for any tenant — only the data differs.

**Schema-discover first, query second.** Every CRM is configured differently. Some tenants
don't have an Opportunity table at all (deal status lives on Account custom fields). Some use a
custom `Deal__c` object. Some split renewals from new business. Always run schema discovery
(Step 2) before any KPI query, build an in-memory field map, then route queries through Path A
(Opportunity-based) or Path B (Account-based) per `sf-query-patterns.md`.

**Learn the win pattern first.** Don't pitch generic "more contacts = more deals." Derive the
customer's actual close-won industries and personas from their data, then frame every gap
analysis against that derived pattern.

**Real numbers, not projections, wherever possible.** Persona counts per account from Snowflake
`GOLD.ENTITIES.PEOPLE`. Tech stack from `GOLD.ENTITIES.COMPANIES.TECHNOLOGIES`. Signals from
the three Snowflake signal tables (artifacts + community messages + job posts) filtered to the
last 90 days.

**Open pipeline is the headline.** Deepest treatment, the lift math lives here.

**Salesforce queries go through `integration_proxy`, not Metabase.** Metabase `execute_query`
returns "Illegal base64 character 20" intermittently and is unreliable.

**Signals come from three Snowflake tables, last 90 days, never from a single table:**
- `SILVER.SIGNALS.ARTIFACTS` (joined to `SILVER.SIGNALS.ARTIFACT_TYPES` for type names)
- `SILVER.COMMUNITY_MESSAGES.INT_MESSAGES_WITH_LINKEDIN`
- `SILVER.JOB_POST.STG_JOB_POSTS`

The 11 canonical signal types live in `ARTIFACT_TYPES` — pull them at run time, don't hardcode.
See [`signals-from-snowflake.md`](references/signals-from-snowflake.md).

**Six diversified signal types in the Hero strip.** Competitor mention + product-page intent +
website visit + event speaker + job change on champion + hiring signal. Never claim a specific
total volume.

---

## Reuse from poc-intelligence

This skill is the customer-facing twin of [`poc-intelligence`](../poc-intelligence/SKILL.md).
Both produce a CRM analysis for a tenant; the difference is audience and depth:

| | `poc-intelligence` | `crm-value-preview` (this skill) |
|---|---|---|
| Audience | Internal Onfire AEs preparing for a POC | The customer themselves (pre-sync) |
| Length | 16+ sections, exhaustive | 5 sections, focused on the buying decision |
| Framing | Internal field names OK in the appendix | Zero internal jargon anywhere |
| Plays | 4 named plays with 3 examples each | One live AI-Prospecting drill on one open opp |
| Runtime | 10+ min per tenant | 3–5 min per tenant |
| Output | A4 HTML with appendix | 1280px interactive HTML |

**Reuse these references directly — do not duplicate their content:**

- [`../poc-intelligence/references/sf-soql-patterns.md`](../poc-intelligence/references/sf-soql-patterns.md)
  — canonical Salesforce field-candidate tables (Amount / Stage / Owner / Last Activity / ARR
  field aliases across tenants).
- [`../poc-intelligence/references/persona-taxonomy.md`](../poc-intelligence/references/persona-taxonomy.md)
  — canonical Onfire persona-bucket taxonomy.
- [`../poc-intelligence/references/play-templates.md`](../poc-intelligence/references/play-templates.md)
  — canonical Onfire play structures.

**Optional sub-skill invocation.** When the customer specifically requests more depth, invoke
`poc-intelligence` once and consume its plays + persona distribution. Strip its internal-facing
copy before injection. By default, derive inline — cheaper and easier to explain.

---

## Step 1 — Resolve Tenant

Call `get_tenant_settings(tenant_id='<tenant>')`. Extract and cache for the rest of the run:

- `crm.type` — must be `salesforce` (v1). If not, stop and tell the user.
- `crm.integration_id` — used in every `integration_proxy` call.
- `account_research.golden_persona` — the ICP persona name.
- `account_research.queries_sections.competitors` — competitor list (for signals + enrichment).
- `account_research.queries_sections.technologies` — tech-stack list to track.
- `account_research.queries_sections.organization` — the buying-committee personas (drives
  win-pattern persona filtering).
- `account_research.display_names_mapping` — friendly names for the personas in the customer-
  facing report (e.g. `secops` → "SecOps", `soc_specialist` → "SOC Specialist").
- `signals_settings.excluded_companies` — competitor domains to flag in signals.
- `aifire.enabled` — whether automatic CRM enrichment is already running.
- `email_domains` — the customer's own domain (used to filter self-visits out of signals).

The `tenant_id` is also the `TENANT` column filter on Snowflake signal tables.

---

## Step 2 — CRM Schema Discovery (mandatory before any KPI query)

Every CRM is different. Discover what the customer has, then route queries accordingly.

### 2a. List available objects

```
integration_proxy(method=GET, relative_url='sobjects/')
```

Confirm whether `Opportunity` exists. If absent, check for `Deal__c`, `Pipeline__c`,
`Engagement__c`, `Booking__c`. If none of those, drop to Path B (Account-based).

### 2b. Describe core objects

```
integration_proxy(method=GET, relative_url='sobjects/Account/describe')
integration_proxy(method=GET, relative_url='sobjects/Opportunity/describe')   # if exists
integration_proxy(method=GET, relative_url='sobjects/Contact/describe')
integration_proxy(method=GET, relative_url='sobjects/Lead/describe')
```

Build an in-memory **field map** keyed by concept. Use poc-intelligence's
[`sf-soql-patterns.md`](../poc-intelligence/references/sf-soql-patterns.md) field-candidate
table as the lookup. The concepts to resolve:

| Concept | Standard | Common custom |
|---|---|---|
| Deal stage | `Opportunity.StageName` | `Stage__c`, `Deal_Stage__c`, `Sales_Stage__c` |
| ARR / deal value | `Opportunity.Amount` | `ARR__c`, `Net_New_ARR__c`, `ACV__c`, `TCV__c`, `MRR__c` |
| Won flag | `Opportunity.IsWon` | `Status__c`, `Won__c` |
| Closed flag | `Opportunity.IsClosed` | `Final_Status__c` |
| Last activity | `LastActivityDate` | `Last_Touch__c`, `Last_Contact_Date__c` |
| Loss reason | — | `Loss_Reason__c`, `Closed_Lost_Reason__c` |
| Industry | `Account.Industry` | `Industry__c`, `Vertical__c`, `Sector__c` |
| Account-level deal status (Path B fallback) | — | `Account.Customer_Status__c`, `Account.Tier__c`, `Account.Lifecycle_Stage__c` |
| Account-level ARR (Path B fallback) | — | `Account.ARR__c`, `Account.MRR__c`, `Account.Booking_Amount__c` |

### 2c. Decide the funnel path

- **Path A — Opportunity-based.** Default. Most SF-using customers.
- **Path B — Account-based.** When `Opportunity` is absent or empty. Funnel KPIs come from
  `Account.Customer_Status__c` (or equivalent) + `Account.ARR__c` (or equivalent).
- **Path C — Hybrid.** Some customers track net-new on `Opportunity` and renewals on `Account`.
  Sum across both sources.

**Surface the choice in the report.** Add a small-print footnote on the Hero: "Your CRM tracks
deal status [at the account level / on the Opportunity object / across both] — the funnel
figures below come from [field names]." Customers want to trust the numbers.

See [`sf-query-patterns.md`](references/sf-query-patterns.md) for full SOQL templates per path.

---

## Step 3 — Funnel & Volume KPIs

Execute via `integration_proxy` SOQL, branching on the Step 2 path decision. All SOQL templates
in [`sf-query-patterns.md`](references/sf-query-patterns.md).

Compute and cache:
- Open pipeline ARR + count
- Closed-won / closed-lost ARR + count for the last 12 months
- Win rate by deal count and by $ ARR
- Avg deal size (won)
- Account / Contact / Lead / Opp (or alt) counts

---

## Step 4 — Gap KPIs

Single batched pass via SOQL:
- Stale-90d accounts
- No-contact accounts
- Stalled 30d+ opps (or stalled accounts if Path B)
- Missing-industry accounts
- Contacts missing email
- Contacts missing both phone fields
- True duplicate count: `COUNT(Id) - COUNT_DISTINCT(Website)` from Account
- Top duplicate clusters (LIMIT 200, ORDER BY count DESC) — for display examples

Filter the duplicate-display examples to pure dups only — exclude legitimate regional
structures (Accenture regional offices, NBA team subsidiaries, MLB teams, EY regional service
lines, BT regional units). Keep identical-name dupes + same-domain dupes.

---

## Step 5 — Win-Pattern Analysis (load-bearing)

See [`win-pattern-analysis.md`](references/win-pattern-analysis.md) for the full method. Three
sub-queries:

### 5a. Winning industries (top-3 by ARR)

Adapt the SQL to Path A or Path B. Identify the top-3 industries by summed won ARR — they'll
usually cluster to 60–75% of total.

### 5b. Winning personas (filtered to ICP titles)

**The persona-keyword filter comes from `tenant_settings.account_research.queries_sections.organization`** — NOT hardcoded. Build the SOQL `LIKE` clauses dynamically from the tenant's own ICP definition.

For a SOAR/SOC tenant the keywords map to: `%CISO%`, `%Security%`, `%SOC%`, `%Cyber%`,
`%DevSec%`, `%Detection%`, `%Threat%`, `%Information Security%`.

For a DSPM tenant the keywords would be: `%Data%`, `%Privacy%`, `%Compliance%`, `%CDO%`,
`%Governance%`, `%DPO%`.

For an IAM/IGA tenant: `%Identity%`, `%Access%`, `%IAM%`, `%CIAM%`, `%PAM%`.

Roll the raw titles into 4–6 persona buckets, using the canonical taxonomy from
[`../poc-intelligence/references/persona-taxonomy.md`](../poc-intelligence/references/persona-taxonomy.md).

### 5c. Win-pattern average

Pull the contacts-per-won-account distribution. Use the **median**, not the mean. The number
represents "buying-committee contacts per won account, filtered to ICP titles only."

---

## Step 6 — Open Pipeline Gap Analysis (load-bearing)

Top 15 open opps by ARR (Path A) or top 15 active accounts (Path B). For each, pull total
contacts + ICP-persona contacts in two batched IN-clause queries.

Flag each opp:
- **covered** — ICP contacts ≥ win-pattern avg
- **thin coverage** — < avg but ≥ minimum (golden_persona + at least one supporting role)
- **below minimum** — missing the golden persona or a technical champion
- **outside top-3 won industries** — orthogonal flag

The 5–6 lowest-coverage opps become the table rows in the persona-coverage sub-section. For
each, run `ai_prospecting(action='run', company_linkedin_url=<url>)` to return real named
missing-role candidates with warm-intro paths. Cache results — these calls are expensive.

For contact-freshness on open pipeline, run `match_person` on 3–5 contacts per top-5 opp and
check for `company_name` mismatch or title change. Surface 5 specific stale contacts across
the top opps.

---

## Step 7 — Account Enrichment with Real Per-Account Data (Snowflake)

The Accounts tab's enrichment table is the credibility moment.

### 7a. Per-account persona counts

Build the regex from the tenant's ICP keywords (Step 5b). Bucket into 4–6 categories matching
the persona taxonomy.

```sql
SELECT JOB_COMPANY_LINKEDIN_URL,
       COUNT_IF(REGEXP_LIKE(JOB_TITLE, '.*<bucket1_pattern>.*', 'i')) AS bucket1,
       COUNT_IF(REGEXP_LIKE(JOB_TITLE, '.*<bucket2_pattern>.*', 'i')) AS bucket2,
       ...
FROM GOLD.ENTITIES.PEOPLE
WHERE JOB_COMPANY_LINKEDIN_URL IN ('linkedin.com/company/<co1>', ...)
GROUP BY 1
```

Snowflake REGEXP_LIKE: use `'i'` as the 3rd arg (the inline `(?i)` flag is rejected). Patterns
must start with `.*` and end with `.*`.

### 7b. Per-account tech stack

```sql
SELECT LINKEDIN_URL, NAME,
       FILTER(TECHNOLOGIES, t -> REGEXP_LIKE(t:technology::STRING,
         '.*(<tech1>|<tech2>|<competitor1>|<competitor2>).*', 'i')) AS sec_tech
FROM GOLD.ENTITIES.COMPANIES
WHERE LINKEDIN_URL IN (...)
```

The tech/competitor keyword list comes from `tenant_settings.account_research.queries_sections.technologies`
+ `.competitors`. Split detected tools into:
- **Detected security stack** (the customer's tracked technologies)
- **Competitor tool detected** (the customer's tracked competitors)

### 7c. Sample composition

Pick 12–15 accounts that tell a story:
- 3–4 brand-name accounts (for credibility)
- 3–4 from your closed-lost top 5 (re-opening candidates)
- 3–4 from open-pipeline accounts
- 1–2 no-contact ICP accounts
- 1–2 parent/subsidiary cases (to show linking)

Required columns:
- Account in your CRM
- Employees (CRM → Onfire)
- Persona-bucket counts (one column per bucket; right-aligned)
- Detected security stack (comma-separated, real verified tools)
- Competitor tool detected (explicit names with ⚠ icon)

Drop: "Onfire match" column, "Size band" column.

---

## Step 8 — Signals from Snowflake (last 90 days)

Three signal sources, all filtered `>= DATEADD(day, -90, CURRENT_DATE())`. See
[`signals-from-snowflake.md`](references/signals-from-snowflake.md) for full queries.

### 8a. `SILVER.SIGNALS.ARTIFACTS` joined to `ARTIFACT_TYPES`

Pulls 11 canonical signal types: change_company, new_hire, promotion, role_change,
hiring_manager, account_website_visitor, contact_website_visitor, event_attendee,
github_repo_activity, plus any tenant-specific types (e.g. `customer_champion_island`).

### 8b. `SILVER.COMMUNITY_MESSAGES.INT_MESSAGES_WITH_LINKEDIN`

LinkedIn-identified messages from Reddit / HN / Stack Overflow / community forums. Filter
`MESSAGE_TEXT` by the tenant's ICP keywords (competitors + technologies + organization). This is
gold for high-intent + competitor-mention signals.

### 8c. `SILVER.JOB_POST.STG_JOB_POSTS`

Job postings. Filter `JOB_POST_TITLE` against the tenant's win-pattern persona keywords. When
a company in the customer's CRM is hiring for an ICP-relevant role, that's a buying-intent
signal.

### 8d. Pick 6 diversified signals for the Hero strip

Across all three sources, pick one example per type for the 6-card hero strip:
1. Competitor mention (artifacts where visitor company ∈ excluded_companies)
2. Product-page intent (artifacts mentioning specific URL paths)
3. Generic website visit
4. Event speaker / attendee (artifacts type 9, or from AI Prospecting `events` field)
5. Job change / promotion on a champion (artifacts type 2/3/4/5)
6. Hiring signal (stg_job_posts row OR artifacts type 6)

Never claim a specific total volume ("X signals in last N days"). Say "Live examples of the
signal types Onfire tracks for you."

---

## Step 9 — Buyers & Champions (live AI Prospecting drill)

Pick **one** open opportunity from Step 6 where the win-pattern reveals a *specific* missing
persona — not just "no contacts." The most compelling story is: "your CRM has the buyer and
the operations team, but you're missing the technical champion who actually drives Technical
Validation."

Steps:
1. From the top-15 open opps, find one in Technical Validation / Business Validation stage
   with strong total coverage but a clear persona-type gap.
2. Pull the existing CRM contacts on that account.
3. Run `ai_prospecting(action='run', company_linkedin_url=...)` and consume the top 4–5 prospects.
4. Render 4 full prospect cards (white background, `.prospect-card` class). Each card:
   - Name, title, location, LinkedIn link
   - Authority tag (1–5 → C-Level / VP/Director / Manager / Specialist / IC)
   - Warm-intro tier (GOLD / SILVER / COLD) + connector name + shared company
   - Score breakdown axes (Buyer · Tech-champion · Receptiveness · Urgency)
   - `.pc-reasoning` block with Summary / Buyer signal / Technical fit / Warm intro
     sub-headings, each followed by verbatim AI Prospecting evidence in `<blockquote>`s
   - `.pc-howto` green callout with a concrete "How a rep would use this" sentence

**Do not display the composite score.** Earlier versions showed a large headline number
(e.g. "472" / "415" / "402") at the top-right of each card. It's not meaningful to the
customer — they don't have context for what 472 vs 339 means. Remove the big number; keep the
4-axis breakdown (Buyer / Tech-champion / Receptiveness / Urgency) which the alert glossary
at the top explains.

Add a header card showing 3 columns: "Already in your CRM", "Win-pattern check" (✓/✗ per
persona role), "What Onfire returned" (summary).

Close with a forward-looking card: "After this preview — what changes on the [Account] deal."
Concrete next-step framing, not generic "same call runs for every account."

---

## Step 10 — Render

Output filename: `<tenant>_preview_<YYYYMMDD>.html`. Single self-contained file. All CSS
inlined. No external assets except Google Fonts (Plus Jakarta Sans). See
[`references/render-contract.md`](references/render-contract.md) for the full HTML structure,
brand tokens, and per-section rendering rules. The template is in
[`assets/template.html`](assets/template.html). Worked examples for the Torq tenant are in
[`output/`](output/) — use them as reference for what a real run looks like, not as a template
to copy literally.

Open the file in the user's default browser at the end (`open ~/Downloads/<filename>.html`).

---

## Verification per tenant

Each tenant run must satisfy:

1. **Zero hardcoded tenant references.** No "Torq" / "Fortinet" / etc. literals in the
   template or code paths — all from `tenant_settings`.
2. **Schema-discovered field map.** Funnel KPIs labeled with their actual source: "from your
   Opportunity table" or "from your Account.Customer_Status__c field," whichever applies.
3. **Tenant-specific persona keywords.** The win-pattern title regex was built from the
   customer's own `queries_sections.organization`, not the SOC/SOAR default.
4. **Three signal sources hit.** Artifacts + community messages + job posts all queried, all
   filtered to last 90 days, all surfaced in the report.
5. **Hero signal strip has 6 diversified types.** Not 6 website visits.
6. **No composite scores on Buyers & Champions cards.** Big headline number removed; only the
   4-axis breakdown remains.
7. **Customer-facing copy clean.** No "MCP", "match_person", "integration_proxy", "Snowflake",
   "Metabase", "on file", "Live MCP run", or any specific signal-volume count.

---

## What this skill does NOT do (v1)

- Does not support HubSpot, Pipedrive, or any non-Salesforce CRM.
- Does not write back to the CRM.
- Does not run server-side PDF rendering — browser print is the v1 export path.
- Does not host the HTML — the operator emails / shares the file directly.
- Does not invoke `poc-intelligence` by default — close-won pattern derived inline. See
  "Reuse from poc-intelligence" for when to invoke it as an optional sub-skill.
- Does not hardcode any tenant-specific data — the entire report adapts to whichever tenant
  the user provides at invocation.
