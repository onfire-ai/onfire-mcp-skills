---
name: account-expansion-plan
description: Generate a standalone Expansion Opportunities Plan for a single account, combining live CRM data (Salesforce opportunities and products via integration proxy) with BDR account research signals (tenant config, AI prospecting, intent signals). Use this skill whenever a user says "expansion plan", "expansion opportunities", "expansion report", "upsell plan", "how do we grow this account", "what's the expansion play", or asks about growing/expanding an existing customer or winning a prospect. The skill produces a branded A4 HTML report (and optionally a PDF) with scored expansion plays, identified internal champions, and clear "how to execute" guidance - with zero revenue estimates or dollar amounts anywhere in the output. Always use this skill rather than building expansion analysis manually.
---

# Account Expansion Plan

## What this skill does

Given a **company website**, **tenant ID**, and one or more **Salesforce account IDs**, this skill:

1. Reads the tenant configuration to understand available products and use cases
2. Queries Salesforce via the integration proxy to pull all opportunities (won, lost, active) and their associated products - to understand what the account already has and what was lost to competitors
3. Queries Metabase for live intent signals at this account
4. Runs Phoenix AI prospecting to surface scored contacts
5. Synthesises everything into a standalone **Expansion Opportunities Plan** HTML file - same branding and A4 format as the Account Research report, but focused entirely on what plays to run and how to run them

---

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `company_website` | Yes | `databricks.com` |
| `tenant_id` | Yes | `jfrog` |
| `salesforce_account_ids` | Yes | One or more Salesforce account IDs (e.g. `001w000001Zw9wgAAB`) |
| `company_linkedin_url` | Optional | `https://www.linkedin.com/company/databricks/` |

---

## Hard rules - enforced throughout

1. **No dollar amounts anywhere** - not in plays, not in the CRM footprint section, not in talking points. No price, ARR, ACV, TCV, MRR, or any revenue figure - even ones pulled from Salesforce. Show product names, license tiers, seat counts, and coverage scope instead.
2. **No revenue estimates or projections** - no "estimated TAM", "potential ARR", "incremental value", or any forward-looking financial figure.
3. **No Salesforce record IDs** - never expose raw CRM IDs (e.g. `001w...`, `006w...`) in any customer-facing output.
4. **No internal tool names** - never mention Salesforce, Metabase, Phoenix, Onfire, MCP, or Snowflake by name in the HTML output. Use: "CRM records", "market intelligence", "intent signals", "buyer signals data".
5. **No em dashes** - use a regular hyphen `-` everywhere. Never use `—`.
6. **Verbatim evidence** - always quote signal `message_text` and LinkedIn profile excerpts byte-for-byte. Never paraphrase.

---

## Step 0 - Assess available connectors

Check which connectors are active:
- **Onfire MCP** - tenant config + Phoenix prospecting
- **Integration proxy (Salesforce)** - opportunity and product data
- **Metabase** - live intent signals

Run all available sources. Skip any whose connector is inactive and note the gap.

---

## Step 1 - Read tenant configuration

Run both sources in parallel. Metabase is the primary source for tenant identity; Onfire MCP provides product and prospecting config.

### 1a - Metabase tenants table (primary)

Every time - do not skip this step. Discover the `tenants` table dynamically:

```
metabase:search(term_queries=["tenants"])
```

Find the table named `tenants` (on the platform prod database), then query it:

```
metabase:execute_query(
  database_id=<discovered_db_id>,
  native_query="SELECT * FROM tenants WHERE id = '<tenant_id>'"
)
```

From the result, extract:
- Tenant display name, logo URL or base64, primary brand color
- Product catalog / enabled product lines
- Any config fields relevant to the account research or prospecting setup

If Metabase is unavailable, fall through to Onfire MCP only.

### 1b - Onfire MCP (supplementary)

```
get_tenant_settings(tenant_id=<tenant_id>)
```

Extract:
- `config.account_research.enabled` - whether Phoenix prospecting is available
- `config.account_research.golden_persona` - primary buyer persona
- `config.account_research.queries_sections` - product lines and competitors to search
- `config.account_research.buying_committee_queries` - persona groups to prioritize

Merge the two config sources. Metabase values take precedence for branding; Onfire MCP values are authoritative for prospecting config.

Use the tenant name and logo throughout the report. If a base64 logo is available embed it; otherwise use the logo URL. If neither is available, generate a text wordmark instead.

---

## Step 2 - Pull CRM data via integration proxy (Salesforce)

This is the core differentiator of this skill - understanding what the account already has and what was lost.

### 2a - Get account metadata

For each `salesforce_account_id`:

```
integration_proxy(
  integration="salesforce",
  payload={
    "method": "query",
    "soql": "SELECT Id, Name, Type, BillingCity, BillingCountry, Industry, NumberOfEmployees, Website, Description FROM Account WHERE Id = '<account_id>'"
  }
)
```

From this, establish the account's relationship type: **Customer**, **Partner**, **Prospect**, or **Former customer**. If multiple account IDs are provided, deduplicate by parent account and treat subsidiaries separately.

### 2b - Get all opportunities

```
integration_proxy(
  integration="salesforce",
  payload={
    "method": "query",
    "soql": "SELECT Id, Name, StageName, Type, CloseDate, ForecastCategoryName, Description, IsClosed, IsWon, OwnerId, Owner.Name FROM Opportunity WHERE AccountId = '<account_id>' ORDER BY CloseDate DESC LIMIT 50"
  }
)
```

Classify each opportunity:
- **Active** - open, not closed (in flight)
- **Closed Won** - `IsWon = true`
- **Closed Lost** - `IsClosed = true, IsWon = false`
- **Renewal** - `Type` contains "Renewal"
- **Upsell/Expansion** - `Type` contains "UpSell", "Expansion", "Add-on"

### 2c - Get products on won/active opportunities

```
integration_proxy(
  integration="salesforce",
  payload={
    "method": "query",
    "soql": "SELECT OpportunityId, PricebookEntry.Product2.Name, PricebookEntry.Product2.ProductCode, PricebookEntry.Product2.Family, Quantity, Description FROM OpportunityLineItem WHERE OpportunityId IN ('<opp_id_1>', '<opp_id_2>')"
  }
)
```

Build a **product footprint** - the complete list of products/modules the account currently licenses (from Closed Won and active opportunities). Also note what was proposed but lost (from Closed Lost opps with line items).

### 2d - Get CRM contacts

```
integration_proxy(
  integration="salesforce",
  payload={
    "method": "query",
    "soql": "SELECT Id, Name, Title, Email, Phone, Department, LinkedIn__c FROM Contact WHERE AccountId = '<account_id>' LIMIT 100"
  }
)
```

These are the known internal champions. Cross-reference with AI prospecting results in Step 4.

### 2e - Handling errors

If any Salesforce query fails or returns zero rows, note the gap and continue. Never fail the whole report due to a single missing CRM query.

---

## Step 3 - Query Metabase for live intent signals

Follow the same discovery pattern as the Account Research skill:

```
metabase:search(term_queries=["signals"])
```

Find the `signals` or `platform_prod_signals` table, then:

```
metabase:construct_query(
  table_id=<discovered_table_id>,
  fields=[signal_type, message_text, intent_holder_linkedin_url, date, source_type, source_name, name, product_lines, topics],
  filters=[
    {field_id: account_website, operation: "equals", value: "<company_website>"},
    {field_id: tenant_id, operation: "equals", value: "<tenant_id>"}
  ],
  order_by=[{field: date, direction: "desc"}],
  limit=100
)
```

Apply the same signal filtering rules as the Account Research skill (verbatim `message_text` only, no `short_summary`, remove unrelated signals).

---

## Step 4 - Phoenix AI prospecting (if enabled)

```
Onfire MCP:ai_prospecting(
  action="run",
  company_linkedin_url=<url>,
  use_cache=true
)
```

Poll until `status == "completed"`, then call `describe_dataset(dataset_id=<id>, sample_rows=10)`.

Cross-reference prospects against the CRM contacts from Step 2d. Flag contacts that appear in both as **High-priority champions** (they are both known to the tenant AND scored by AI as likely buyers).

---

## Step 5 - Determine account status and expansion angle

Before writing plays, establish the account's relationship:

### If the account is an active customer (has Closed Won opportunities)

- Identify **product gaps** - use cases in the tenant config that are NOT in the product footprint
- Identify **coverage gaps** - products they have but at limited scope (fewer seats, fewer regions, lower tier than available)
- Identify **renewal risk** - open renewals at low probability or long since last expansion
- Identify **subsidiary/region gaps** - other account records (from multiple account IDs) that are separate entities and not yet customers

Angle: **"How to grow this account"** - expand coverage, land adjacent products, upgrade tiers.

### If the account is not yet a customer (no Closed Won opportunities)

- Identify if there were prior Closed Lost opportunities and which competitor won
- Identify what products were evaluated
- Identify what use cases the account has shown intent signals for

Angle: **"How to win this account"** - address competitive displacement, focus on use cases with the strongest evidence.

### If the account is a mix (some subsidiaries are customers, others are not)

Handle each entity separately in the footprint and call out the cross-sell / land-and-expand angle explicitly.

---

## Step 6 - Generate expansion plays

Create **4-6 scored expansion plays** based on the analysis. Each play scores 1.0-10.0 using the scoring rubric below.

### Scoring rubric

Score each play on these factors (each 0-2, total mapped to a 10-point scale):

| Factor | 2 points | 1 point | 0 points |
|--------|----------|---------|----------|
| Evidence strength | Confirmed signal or CRM data | Weak signal or inference | No signal |
| Internal champion identified | Named contact with CRM relationship | AI prospect only | No identified contact |
| Competitive urgency | Competitor confirmed in-use | Competitor mentioned | No competitor context |
| Use-case fit | Directly mapped to tenant product | Adjacent fit | Stretch |
| Account readiness | Active engagement or renewal due | Stable/dormant | Actively blocked |

### Play types - prioritization order for customers

1. **Coverage expansion** - add products the account doesn't have yet that directly address known signals
2. **Tier/seat upgrade** - expand capacity or tier on products they already use (only if usage evidence exists)
3. **New team or subsidiary land** - bring a product already in use by one team to another that doesn't have it
4. **Competitive displacement** - replace a competitor product confirmed in use
5. **Partner or co-sell play** - leverage a shared partnership to open doors
6. **Renewal reinforcement** - proactively address an at-risk renewal before it stalls

For prospects (no customer relationship), prioritize:
1. **Competitive displacement** - address the gap left by whatever competitor lost them before
2. **High-intent entry point** - the use case with the strongest recent signal
3. **Champion-led play** - engage via the highest-scored AI prospect

### What each play must answer

Every play must answer three questions clearly and specifically:

- **What** - what product/use case, what scope (which module, which team, which region)
- **Why this account, why now** - the specific evidence that makes this play relevant right now (dated signal, CRM note, LinkedIn profile, or competitive context)
- **How to execute** - who to contact first, what conversation to open with, what obstacle to anticipate, what supporting material to bring

---

## Step 7 - Synthesise and render the report

### Report section order

1. **Branded header bar** - tenant logo (base64) + "Expansion Plan - [Company]" + date
2. **Account health score** - visual gauge + 6-factor breakdown
3. **Account status card** - relationship type, product footprint, active plays in flight, renewal dates (no amounts)
4. **Expansion readiness summary** - 3-4 bullets on why this account is ready to expand now (or what barrier to overcome for prospects)
5. **Expansion plays** - one card per play, ordered by score descending
6. **Internal champions** - CRM contacts + AI prospects mapped to plays
7. **Recommended next steps** - prioritized action list

### Account health score

Compute the health score from six factors, each 0-2 points (total /12, then multiply by 10/12 to get a 10-point score):

| Factor | 2 - Green | 1 - Amber | 0 - Red |
|--------|-----------|-----------|---------|
| **Recency** - days since last Closed Won | Under 90 days | 90-365 days | Over 365 days or never |
| **Active engagement** - open opps in Stage 3+ | Yes, in technical validation or beyond | Yes, early stage (01-02) | No open opportunities |
| **Renewal risk** - nearest renewal date + stage | 12+ months out OR high probability | 6-12 months out, mid probability | Under 6 months, low probability |
| **Champion depth** - named technical + economic buyers identified | Both technical and economic buyer named | One type only | No named champions |
| **Coverage breadth** - % of use cases in tenant config covered by footprint | Over 50% covered | 20-50% | Under 20% |
| **Partnership or co-sell track** - active partner motion | Active partner track with named contact | Historical relationship only | None |

**Score thresholds:**
- 8.0-10.0 → GREEN - Healthy, expand aggressively
- 5.0-7.9 → AMBER - Solid but gaps to address
- Below 5.0 → RED - At risk, stabilise before expanding

**HTML card for account health score:**

```html
<div class="card card-red-top" style="margin-bottom:7pt">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8pt;flex-wrap:wrap;gap:6pt">
    <span class="lbl" style="margin-bottom:0">Account health score</span>
    <!-- Gauge: color matches threshold -->
    <div style="display:flex;align-items:center;gap:8pt">
      <div style="width:80pt;height:5pt;background:var(--bg);border-radius:3pt;overflow:hidden;border:.3pt solid var(--border)">
        <div style="width:[score*10]%;height:100%;background:[green|amber|red];border-radius:3pt"></div>
      </div>
      <span style="font-family:monospace;font-size:13pt;font-weight:600;color:[green|amber|red]">[score] / 10</span>
      <span class="tag" style="background:[status-bg];color:[status-text]">[Healthy / Watch / At risk]</span>
    </div>
  </div>

  <!-- 6-factor breakdown - 2 columns of 3 -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:5pt">
    <!-- One row per factor -->
    <div style="display:flex;align-items:center;gap:6pt;padding:4pt 6pt;background:var(--bg);border-radius:4pt">
      <div style="width:8pt;height:8pt;border-radius:50%;background:[green|amber|red];flex-shrink:0"></div>
      <div>
        <div style="font-size:7pt;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em">[Factor name]</div>
        <div style="font-size:8pt;color:var(--text)">[One-line evidence - e.g. "Closed Won April 2026 - 24 days ago"]</div>
      </div>
    </div>
    <!-- repeat for all 6 factors -->
  </div>
</div>
```

Use these exact colors for the dot and bar fill:
- Green: `#22c55e`
- Amber: `#f59e0b`
- Red: `#ef4444`

And matching tag backgrounds:
- Green tag: `background:#dcfce7;color:#166534`
- Amber tag: `background:#fef3c7;color:#92400e`
- Red tag: `background:#fee2e2;color:#991b1b`

### Writing rules

- **No em dashes** - use `-` everywhere
- **No internal tool names** - use "CRM records", "market intelligence", "intent signals"
- **No dollar amounts** - not even from CRM. Show product names, tiers, seat counts, regions instead
- **No Salesforce IDs** - use company name, region, or role labels instead
- **No negative-state placeholder copy** - if a section has no data, omit it silently
- **Verbatim evidence** - quote `message_text` and LinkedIn profile text byte-for-byte
- **Present tense, active voice** - "Three Docker registries are in production. Security Essentials is not deployed." Not "it appears that..."
- **Specific over generic** - name the actual product, team, or person. "Expand Curation to cover Docker and OCI" beats "expand product adoption"

### HTML file requirements

Generate a **fully self-contained** HTML file:

- System fonts only - `-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif`
- Tenant logo embedded as base64 data URI (no external image references)
- `@page { size: A4; margin: 16mm 18mm 18mm 18mm }` and `body { width: 174mm }`
- All font sizes in `pt`; body 9pt, labels 7pt, headings 11-15pt
- Force background colors to print:
  ```css
  @media print {
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  }
  ```
- Every `.card` has `break-inside: avoid`
- Use the same full CSS block as the Account Research report (same variables, card styles, score bars, evidence blocks, section titles)
- Save to `/mnt/user-data/outputs/expansion-plan-<company>-<tenant>.html`
- Call `present_files`

### Header bar

Same styling as Account Research but with "Expansion Opportunities Plan" in the subtitle:

```html
<div class="header-bar" style="background:[tenant-primary-color];margin:0 -18mm;padding:7pt 18mm;
  display:flex;align-items:center;justify-content:space-between;margin-bottom:10pt">
  <div style="display:flex;align-items:center;gap:8pt">
    <img src="[BASE64_LOGO]" alt="[Tenant]" style="width:26pt;height:26pt;border-radius:3pt">
    <div>
      <div style="font-size:11pt;font-weight:600;color:#fff">[Tenant Name]</div>
      <div style="font-size:7.5pt;color:rgba(255,255,255,.75);margin-top:1pt">
        Expansion Opportunities Plan - [Company Name]
      </div>
    </div>
  </div>
  <div style="font-family:monospace;font-size:7pt;color:rgba(255,255,255,.65);
    text-align:right;line-height:1.5">[Month Year]<br>Confidential</div>
</div>
```

### Account status card

```html
<div class="card card-red-top">
  <span class="lbl">Account relationship</span>
  <div style="display:flex;align-items:center;gap:6pt;margin-bottom:9pt;flex-wrap:wrap">
    <!-- Customer / Prospect / Partner / Former customer -->
    <span class="tag" style="background:var(--hi-bg);color:var(--hi-text)">[Status]</span>
    <!-- One tag per region/entity if multiple account records -->
    <span class="tag" style="background:var(--bg);color:var(--muted)">[Region or entity label]</span>
  </div>

  <span class="lbl">Current product footprint</span>
  <div style="display:flex;flex-wrap:wrap;gap:4pt;margin-bottom:9pt">
    <!-- One tag per product/module confirmed in Closed Won deals -->
    <span class="tag" style="background:var(--netsec-bg);color:var(--netsec-text)">[Product Name] - [Tier if known] - [N seats/repos/etc if known]</span>
  </div>

  <!-- Only render if open opportunities exist -->
  <span class="lbl">Active opportunities</span>
  <div style="margin-bottom:9pt">
    <div style="display:flex;gap:6pt;align-items:center;padding:4pt 0;border-bottom:.4pt solid var(--border)">
      <span class="tag" style="background:var(--med-bg);color:var(--med-text)">[Stage]</span>
      <span style="font-size:8.5pt;color:var(--text)">[Opportunity name - no ID, no amount]</span>
      <span style="font-size:7.5pt;color:var(--muted);margin-left:auto">Close: [Month Year]</span>
    </div>
  </div>

  <!-- Only render if Closed Lost deals with product data exist -->
  <span class="lbl">Previously evaluated - not deployed</span>
  <div style="display:flex;flex-wrap:wrap;gap:4pt">
    <span class="tag" style="background:var(--low-bg);color:var(--low-text)">[Product Name] - [lost to Competitor if known]</span>
  </div>
</div>
```

### Expansion play card

```html
<div class="card card-accent">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;
    margin-bottom:8pt;flex-wrap:wrap;gap:6pt">
    <div>
      <div style="font-size:10pt;font-weight:600;margin-bottom:2pt">[Specific, action-oriented play title]</div>
      <div style="font-size:7.5pt;color:var(--muted)">[Play type: Coverage expansion / Competitive displacement / etc.]</div>
    </div>
    <div style="display:flex;align-items:center;gap:5pt">
      <div class="score-track">
        <div class="score-fill" style="width:[score*10]%;background:var(--ftn-red)"></div>
      </div>
      <span class="score-num" style="color:var(--ftn-red)">[score] / 10</span>
    </div>
  </div>

  <div class="two">
    <div>
      <span class="lbl">What</span>
      <p style="font-size:8.5pt">[Specific product, module, scope, team, region. No dollar amounts.]</p>
    </div>
    <div>
      <span class="lbl">Why now</span>
      <p style="font-size:8.5pt">[Specific dated evidence. Must cite source and date/timeframe.]</p>
    </div>
  </div>

  <span class="lbl">How to execute</span>
  <p style="font-size:8.5pt;line-height:1.7">[Actionable steps: who to contact first, what to lead with, what objection to anticipate, what to prepare. Specific enough that a BDR can act immediately.]</p>

  <!-- Only include if a specific signal or CRM note directly supports this play -->
  <div class="evidence">
    <div class="evidence-lbl">Evidence - [source type] - [date]</div>
    <p>&ldquo;[Verbatim message_text or LinkedIn text]&rdquo;</p>
  </div>
</div>
```

### Internal champions section

```html
<div class="section-title">Internal champions</div>
<div class="card">
  <span class="lbl" style="margin-bottom:6pt">CRM contacts and scored prospects mapped to expansion plays</span>

  <div class="pr">
    <div class="av" style="background:[uc-bg];color:[uc-text]">[Initials]</div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:6pt;flex-wrap:wrap;margin-bottom:2pt">
        <a href="[linkedin_url_or_#]" style="font-size:9pt;font-weight:600;color:var(--text);text-decoration:none">[Full Name]</a>
        <span class="tag" style="background:var(--hi-bg);color:var(--hi-text)">[CRM contact / Identified prospect / Both]</span>
        <span class="tag" style="background:var(--bg);color:var(--muted)">Play [N]: [Short play name]</span>
      </div>
      <div style="font-size:7.5pt;color:var(--muted);margin-bottom:3pt">[Title] - [Company] - [Location or Department]</div>
      <p style="font-size:8pt;line-height:1.5">[Why this person matters - what they own, what relationship they have, how to engage them]</p>
      <!-- Only show if a real named warm-intro path exists from AI prospecting -->
      <div style="font-size:7.5pt;color:var(--muted);margin-top:3pt">
        Warm intro: [Named contact at tenant] (shared [Company or experience])
      </div>
    </div>
  </div>
</div>
```

### Recommended next steps section

```html
<div class="section-title">Recommended next steps</div>
<div class="card">
  <div class="why-row">
    <span class="why-num">01</span>
    <p><strong>[Specific action - named person, named product, target timeline].</strong> [One sentence on why this is the right first move and what it unlocks.]</p>
  </div>
  <!-- 3-5 steps total, ordered by priority -->
</div>
```

### Footer

```html
<div style="margin-top:10pt;padding-top:6pt;border-top:.5pt solid [tenant-color-mid];
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4pt">
  <div style="display:flex;align-items:center;gap:5pt">
    <img src="[BASE64_LOGO]" alt="[Tenant]" style="width:14pt;height:14pt;border-radius:2pt">
    <span style="font-size:7.5pt;font-weight:600;color:[tenant-primary-color]">[Tenant Name]</span>
  </div>
  <p style="font-family:monospace;font-size:6.5pt;color:var(--faint)">
    [Company Name] - Expansion Opportunities Plan - [Month Year]
  </p>
</div>
```

---

## Pre-delivery checklist

Before saving the HTML and calling `present_files`, run all five checks. All must pass.

**1. No dollar amounts**
```bash
grep -iE '\$[0-9]|USD\b|ARR\b|ACV\b|TCV\b|\bMRR\b' output.html
```
Must return zero matches (excluding verbatim evidence blocks).

**2. No internal tool names**
```bash
grep -iE 'salesforce|metabase|phoenix|mcp|onfire|snowflake' output.html
```
Must return zero matches.

**3. No Salesforce IDs**
```bash
grep -E '[0-9]{3}[a-zA-Z][0-9]{9}[a-zA-Z0-9]{3}' output.html
```
Must return zero matches.

**4. No em dashes**
```bash
grep -- '—' output.html
```
Must return zero matches (outside verbatim evidence blocks).

**5. All plays have a non-generic "How to execute"**
Read each play card. Every "How to execute" section must name at least one specific person, product, or action. If any reads like generic advice ("reach out to the security team"), rewrite it with specifics before delivering.

Fix any failing check, then rerun all five. Do not deliver until all pass.

---

## Error handling

| Situation | Action |
|-----------|--------|
| Salesforce query fails | Note "CRM data not available" in account status card; continue with signals + prospecting |
| Zero CRM opportunities | Treat as prospect; use win-angle plays |
| Account IDs return no records | Ask user to confirm IDs; note gap in report |
| Metabase unavailable | Skip signals section |
| Phoenix disabled | Use CRM contacts only for champions |
| No CRM contacts | Use AI prospects only |
| Multiple account IDs, mixed customer/prospect | Handle each entity separately; call out land-and-expand angle |
