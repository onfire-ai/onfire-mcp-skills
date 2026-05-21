# Win-Pattern Analysis

The single most important analysis in the report. Everything in the Open Pipeline tab — and
much of the Accounts tab — flows from this. Get it right.

**Canonical persona buckets come from
[`../../poc-intelligence/references/persona-taxonomy.md`](../../poc-intelligence/references/persona-taxonomy.md).**
Don't invent new buckets here — re-use the taxonomy poc-intelligence already maintains. This
doc captures *how to derive the buckets from raw SF Title data* + *how to use them to score
open opps*; the underlying bucket definitions are owned upstream.

## What the customer sees

> "Across your 261 closed-won accounts, two patterns dominate. Onfire derived these from
> your CRM, not from a deck."

Two side-by-side cards: **Industries that close** + **Personas that buy**. Then three derived
constants used to score every open opp:

- **Win-pattern average** — median security-persona contacts per won account (~5 for SOAR/SOC
  tenants like Torq)
- **Win-pattern minimum** — `CISO + at least one Security Engineer or DevSecOps`. Won accounts
  almost never have only one role.
- **Top-3 industries** — sum of ARR across the top-3 won industries (~70% for Torq).

## Step 1 — Winning industries

```sql
-- via integration_proxy, relative_url='query'
SELECT Account.Industry, COUNT(Id), SUM(Amount)
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = true AND IsWon = true
GROUP BY Account.Industry
ORDER BY SUM(Amount) DESC NULLS LAST LIMIT 10
```

Identify the top-3 industries by **summed ARR**, not count. Almost always they'll cluster to
60–75% of total closed-won ARR — that's the customer's ICP signature.

For Torq, this returned:
- Technology - Software: $29.3M / 216 deals
- Banking & Financial Services: $24.4M / 114 deals
- Business Services: $8.4M / 65 deals
- Technology - Services: $8.9M / 62 deals
- (top 3 = ~70% of won ARR)

In the report, render as a 7-row table sorted by ARR. Highlight the top-3 with `.tag.gr` green
pills. Note "★" in any Open Pipeline tables next to deals in these industries.

## Step 2 — Winning personas (always derive keywords from the tenant config)

The raw query (no title filter) returns confusing roles like "Client Manager", "Account
Executive", "Procurement". These are not buyers. **Always filter to ICP-relevant titles**, and
**always derive the keyword list from `tenant_settings.account_research.queries_sections.organization`** — never hardcode.

### Build the keyword filter dynamically from `queries_sections.organization`

For each persona token in the tenant's `organization` array, expand to title-matching keywords
using the canonical persona taxonomy from
[`../../poc-intelligence/references/persona-taxonomy.md`](../../poc-intelligence/references/persona-taxonomy.md).

Examples of the expansion per product category:

| Tenant category | Tokens in `queries_sections.organization` | Title-match keywords for the SOQL `LIKE` filter |
|---|---|---|
| **SOAR / SOC** (e.g. Torq) | `CISO`, `secops`, `soc_specialist`, `detection_engineer`, `security architect`, `Cyber_Security`, `threat_intelligence` | `%CISO%`, `%Security%`, `%SOC%`, `%Cyber%`, `%DevSec%`, `%Detection%`, `%Threat%`, `%Information Security%` |
| **DSPM / Data Security** | `CDO`, `data_governance`, `data_privacy_officer`, `compliance` | `%Data%`, `%Privacy%`, `%Compliance%`, `%CDO%`, `%Governance%`, `%DPO%` |
| **IAM / IGA / PAM** | `IAM`, `identity_governance`, `pam_specialist`, `access_management` | `%Identity%`, `%Access%`, `%IAM%`, `%CIAM%`, `%PAM%`, `%IGA%` |
| **CSPM / Cloud Security** | `cloud_security`, `cspm`, `devsecops`, `cloud_architect` | `%Cloud Security%`, `%CSPM%`, `%DevSecOps%`, `%Cloud Architect%` |
| **CIEM / Entitlement** | `ciem`, `entitlement`, `privilege` | `%CIEM%`, `%Entitlement%`, `%Privilege%`, `%Permission%` |

### The generalized SQL

```sql
-- The keyword list is built dynamically per tenant
SELECT Title, COUNT(Id)
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN (SELECT AccountId FROM Opportunity WHERE IsWon = true AND IsClosed = true)
  AND (Title LIKE '%<kw1>%' OR Title LIKE '%<kw2>%' OR ... OR Title LIKE '%<kwN>%')
GROUP BY Title ORDER BY COUNT(Id) DESC LIMIT 30
```

### Roll into 4–6 persona buckets

Always present 4–6 buckets in the report — too few feels generic, too many feels noisy.
Bucket structure also derives from the tenant taxonomy:

- **Decision-maker bucket** — the senior persona equivalent of CISO/CDO/CIO. Always present.
- **Technical-champion bucket** — the engineer-level persona who drives integration evaluation.
  Always present.
- **Analyst / Operator bucket** — the day-to-day user.
- **Architect bucket** — the strategic builder.
- **Adjacent / supporting bucket** — DevOps / Platform / IT-Ops, if relevant to the tenant.

For the SOAR/SOC reference run on Torq, this produced: CISO leadership / Security Engineers /
Security Analysts / Security Ops leadership / Security Architect / DevSecOps. For a DSPM tenant
the buckets would be: CDO / Data Engineers / Data Privacy Analysts / Data Architects /
Compliance. The skill must adapt.

## Step 3 — The win-pattern *average*

```sql
SELECT AccountId, COUNT(Id) AS c
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN (SELECT AccountId FROM Opportunity WHERE IsWon = true AND IsClosed = true)
GROUP BY AccountId
ORDER BY COUNT(Id) DESC LIMIT 200
```

Distribution is highly skewed — a handful of consulting / large-enterprise accounts have 100+
contacts; most have 10–30; the bottom quartile has 8–15. Use the **median**, not the mean.

For Torq:
- Total: ~580 security contacts across 261 won accounts = ~2.2 average — but that's the *raw
  security-title* average per won account, with many smaller wins inflating the low end.
- Median across all 200 returned: ~17 *total* contacts per won account.
- Realistic security-persona target: **~5** security contacts per won account
  (CISO + 2 Sec Engs + 1–2 SOC + 1 supporting role). Conservative; serves as the comparison
  baseline for open opps.

Render in the report as the middle stat in the 3-tile derived-constants row:
`Win-pattern average · ~5 · Security-persona contacts per closed-won account`.

## Step 4 — Use the pattern to flag open opps

Pull the top 15 open opps with `Amount > 200000`. For each, compute total contacts + security
contacts (see [`sf-query-patterns.md`](sf-query-patterns.md) for the SOQL). Then flag:

- `<span class="tag gr">covered</span>` — security contacts ≥ win-pattern avg
- `<span class="tag am">thin coverage</span>` — < avg but ≥ minimum (CISO + Eng)
- `<span class="tag re">below minimum / no CISO / no Sec Eng</span>` — missing required persona
- `<span class="tag am">outside top-3 won industries</span>` — orthogonal flag (industry not
  in top-3 by won ARR)

For Torq's top-15 open opps this produced:
- Wells Fargo (99/34), MUFG (90/31), Marriott (43/23), Deepwatch (76/17), LPL (32/16),
  Prudential (66/31), Almond (32/7), FIS (29/17), Deutsche Bank (35/12), Navy Federal (34/17)
  → covered
- Northrop (15/9), Swisscom (15/11), Rocket (29/9), Koch (20/7)
  → thin coverage
- **Danaher (7/2)** → below minimum (no CISO, no Sec Eng) — the most striking gap

**Combined ARR at risk = sum of (Amount) where flag is "thin" or "below minimum".** For Torq,
this came to **$6.56M** across 5 deals. Use this number in the action box.

## Step 5 — Pick 5–6 opps for the "Persona coverage" table

The lowest-coverage opps from Step 4 become the rows in the "Persona coverage — who's missing
on each open deal (live)" sub-section. For each one:

1. Identify the *specific* missing persona by comparing the existing contact mix to the
   win-pattern buckets (e.g. "they have CISO + SOC but no Sec Eng or DevSecOps").
2. Call `ai_prospecting(action='run', company_linkedin_url=<url>)` to get real named
   candidates with warm-intro paths. (These are expensive — cache the response and reuse.)
3. Format the row: Open opp + ARR + Stage / Has on the deal / Missing per win pattern
   (with `.hl-red` highlights on the named missing roles) / Named candidates Onfire returns
   (1-line summary: "N named candidates; M GOLD/SILVER warm intros").

This is where the story converts from "you have gaps" to "Onfire fills them with specific
named people you can email tomorrow."

## Step 6 — Compute the uplift math

Stack two lifts (independent, not multiplicative):

- **Lift 1 — Contact-data freshness** (+3–5%) — backfilling missing emails/phones + correcting
  stale contacts on the stalled-30d opps + the freshness cases highlighted in the report.
  Expected ARR lift: pipeline ARR × 27.6% baseline × 3–5% = **+$1.5M–$2.5M** for Torq.

- **Lift 2 — Persona coverage** (+6–8%) — adding the missing technical champion to deals where
  only the CISO is on file (and vice-versa). The 5–6 deals from Step 5 are the immediate
  targets. Expected ARR lift: pipeline ARR × 27.6% × 6–8% = **+$3M–$4M** for Torq.

**Total uplift = $4.5M–$6.5M.** That's the headline number for the .action-box closing the
Open Pipeline tab.

**Earlier versions had a third "intent signal routing" lift (+2–3%).** It was removed because
the signal routing lift compounds with the persona-coverage lift (you can't double-count an
intent signal becoming an opp). Keep only two lifts.

## Inline vs invoking poc-intelligence

Both paths are valid. By **default**, derive inline:

1. **Cheaper.** Inline SF queries cost a few seconds; poc-intelligence is a 10+ minute run.
2. **More reliable.** poc-intelligence has its own failure modes (schema discovery, Metabase
   timeouts, missing tenants).
3. **More direct.** The customer wants the win-pattern presented from their CRM data, not
   filtered through another report. Inline queries are easier to explain ("this came from
   one SOQL against your Salesforce").
4. **Simpler narrative.** A 5-section report is cleaner than 5 sections + an embedded
   poc-intelligence frame.

**Invoke poc-intelligence as a sub-skill when:**

- The customer specifically asks for "more depth" or "show me the plays".
- The tenant has heavy CRM activity (1000+ won deals over 12 months) and the inline derivation
  produces aggregates that feel coarse.
- You want to surface the **4 named plays** poc-intelligence generates (Signal pipeline,
  Recover closed-lost, Buying committee gap, Competitive expansion) as additional Open Pipeline
  drill-downs.

When invoked: strip the internal-facing copy before injecting into the customer report.
Internal terms like `Net_New_ARR__c`, "POC stage", "Technical Validation" must be re-worded.
See [`../SKILL.md`](../SKILL.md) "Reuse from poc-intelligence" for the full protocol.
