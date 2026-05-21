# Render Contract

This file defines the exact HTML structure, section order, brand tokens, customer-facing copy
guardrails, and client-side interactivity for the CRM Value Preview report. The skeleton lives in
[`../assets/template.html`](../assets/template.html); this file documents the rules the skill
must follow when filling it.

## Output

- **Filename:** `<tenant>_preview_<YYYYMMDD>.html`
- **Single self-contained file:** all CSS inlined in `<style>`. No external assets except
  Google Fonts (Plus Jakarta Sans).
- **Width:** 1280px max, centered.
- **Print:** `@media print` collapses the nav, hides interactive buttons, ensures sections
  break cleanly on their own pages.

## Brand tokens

Use the poc-intelligence light-theme palette. The `:root` block from the template:

```
--navy   #003049    --navy2  #1B4A6B    --navy3  #4A7A96
--teal   #0BA3A3    --teal2  #5BBFBF    --teal3  #C5E8E8    --sky #E8F4FF
--purple #7C5CFC    --p2     #A07FFC    --p3     #EDE9FF
--green  #16A34A    --g2     #DCFCE7
--red    #DC2626    --r2     #FEE2E2
--amber  #B45309    --a2     #FEF3C7
--bg     #EEF6FF    --card   #FFFFFF
--border rgba(0,48,73,0.09)   --b2 rgba(0,48,73,0.15)
--text   #003049    --t2     #2A5C75    --t3     #6A9DB5
```

Body uses radial gradients + a 48px grid pattern as background. Header bar is navy with a
subtle teal gradient overlay on the right. Nav strip is sticky with `var(--nav-h) = 46px`.

## Sticky-nav scroll fix

**Mandatory.** Every `<section class="section">` must have `scroll-margin-top:
calc(var(--nav-h) + 24px)` so that when nav buttons trigger `scrollIntoView`, the section title
isn't hidden under the sticky nav. The tab-switch JS also wraps the scroll call in a 50ms
setTimeout so the section is fully visible before the scroll fires.

## Top header

Customer-facing only. The pills in the header should contain **only**:
- `Tenant: <name>`
- `Read-only — nothing changed in your Salesforce`

Do **not** include any of these in the header:
- "Live MCP run"
- "SF integration #1131" or any integration ID
- "Golden persona: <name>" — that's internal
- "Generated 06:45 UTC" timestamp with seconds — date only is fine

The `hdr-eye` line is short and dated: `Generated for <tenant> · <month> <year>`.

## Section order (top to bottom)

1. **The Numbers** (`#snapshot`) — funnel, volume, gaps, signals.
2. **Open Pipeline** (`#workflow-pipeline`) — close-won pattern, open-opp gap table, persona
   coverage on open opps, contact freshness on open opps, uplift math.
3. **Contact Data Gap** (`#workflow-contacts`) — freshness, completeness, top intent signals.
4. **Accounts** (`#workflow-accounts`) — duplicates first, then enrichment, then specific gaps.
5. **Buyers & Champions** (`#workflow-prospects`) — live AI Prospecting drill.

The nav button order matches.

## The Numbers — section detail

Three labeled bands stacked top-to-bottom:

1. **"Your funnel today"** — 6 tiles in a `g6` grid: Open pipeline ARR · Closed-lost ARR (12mo) ·
   Win rate (12mo) · Closed-won ARR (12mo) · Avg deal size (won) · Win rate by $.
2. **"Your CRM today — volume"** — 4 tiles in a `g4` grid: Accounts · Contacts · Leads ·
   Open opps.
3. **"Where your CRM has gaps — and what Onfire would add"** — 3 rows of 3 tiles each
   (`g3 × 3`). Each gap tile has a dashed-divider `.stat-uplift` line at the bottom showing the
   Onfire action sized against the actual gap number.

Then the **signal strip block-label**: "Live examples of the signal types Onfire tracks for you"
(NOT "X signals in last N days" — never claim a specific total). Two rows of 3
`.signal-card` cards, each with `border-left` colored by type:
- `.re-src` red — competitor mention
- `.pu-src` purple — high-intent (product page, event, job change, hiring)
- `.tl-src` teal — generic website visit

The 6 cards must cover diversified signal types: **website visit, product-page intent,
event speaker, competitor mention, job change on champion, hiring signal.**

After the strip, a footer line listing the six signal types and explaining Onfire combines them
into "one routed inbox per rep."

## Open Pipeline — section detail (the headline section)

Five sub-sections:

1. **"What's working — the close-won pattern"** — two cards side by side in a `g2` grid:
   - Industries that close (top 7 by ARR)
   - Personas that buy (top 5–6 buckets)
   Then three derived constants in a `g3` of `.stat` tiles: Win-pattern average (~5),
   Win-pattern minimum (CISO + Eng), Top-3 industries (% of ARR).

2. **"Your top 10 open deals — measured against the win pattern"** — the table with columns:
   Open opportunity · Industry · ARR · Total contacts · Security contacts (vs win avg) · Gap
   per win pattern. Color-code the gap column: `.tag.gr covered`, `.tag.am thin coverage`,
   `.tag.re below minimum / no CISO`.

3. **"Persona coverage — who's missing on each open deal (live)"** — table with rows for the
   5–6 lowest-coverage open opps. Columns: Open opp · Has on deal · Missing per win pattern ·
   Named candidates Onfire returns. The "Missing per win pattern" column uses `.hl-red`
   highlights on the specific persona name. The "Named candidates" column references the
   AI Prospecting output for that opp.

4. **"Contact freshness — stale contacts on your live deals"** — table with rows for 5
   contacts on top-pipeline accounts who have moved, been promoted, or have stale emails.
   Columns: Open opp · Stale contact · What changed · Onfire fix.

5. **"Expected uplift on your open pipeline"** — two `.stat.green` tiles in a `g2`:
   Lift 1 (Contact-data freshness +3–5% / +$1.5M–2.5M) and Lift 2 (Persona coverage +6–8% /
   +$3M–4M). Then a teal-bordered `.action-box` summing to **+$4.5M–$6.5M** total uplift on
   the open pipeline.

**Only two lifts.** Earlier versions had a 3rd "intent signal routing" lift — explicitly dropped.

## Contact Data Gap — section detail

Three sub-sections:

1. **"Freshness — same person, different job, different company"** — 5-row table with the
   live match_person findings. Columns: Contact · Your CRM says · They're actually at ·
   What changed. The "What changed" column uses tag pills: `.re Company changed`,
   `.pu Promoted`, `.am Title changed`, `.gr Current`. No subtext like "Same role,
   different employer" — the tags carry the meaning.

2. **"Completeness — empty phones and emails Onfire fills"** — two `.stat` tiles
   (missing email count + missing phone count). Then a 5-row table mixing two kinds of fixes:
   stale-email-replaced (e.g. James Zhou) AND empty-field-filled (e.g. Vlad Chiriloiu at
   Deutsche Bank with no prior email). The "Type of fix" column has tag pills:
   `.re Stale email replaced`, `.gr Empty field filled`, `.am Phone added`.

   **Do not** include a "Live waterfall — sample hit rate ~745 / ~3,975" tile — the user
   found it confusing. The coverage projection lives in the .action-box at the bottom instead.

3. **"Top intent signals on your existing contacts"** — exactly 3 cards in a `.signal-strip`,
   with diverse types: 1 website visit + 1 product-page intent + 1 event speaker. Don't repeat
   the same examples from The Numbers hero strip.

**Persona-coverage analysis is NOT here.** It lives in the Open Pipeline tab where it ties
to revenue. Earlier versions duplicated it — explicitly moved.

## Accounts — section detail

Three sub-sections, in this exact order:

1. **"Duplicates — your CRM has N redundant account records"** — duplicates come first because
   they distort everything downstream. Lead with the real number (e.g. 937 for Torq), then a
   `.alert.danger` with the most embarrassing real duplicate pair. Then a table of pure-dup
   clusters only (NO regional structures). Then an action-box explaining parent/subsidiary
   linking vs collapsing.

2. **"Enrichment overview — what Onfire adds per account (real numbers)"** — the credibility
   moment. Wide table with **right-aligned numeric columns and right-aligned headers**.
   Required columns:
   - Account in your CRM (left-aligned)
   - Employees CRM→Onfire (with inline `.crm` strikethrough above `.onfire` green count)
   - CISO (numeric)
   - Sec Eng (numeric)
   - SOC Analyst (numeric)
   - DevSecOps (numeric)
   - Detected security stack (compact: "Splunk · CrowdStrike · SentinelOne")
   - Competitor tool detected (explicit names: `⚠ Cortex XSOAR + Swimlane + QRadar` OR
     `— no direct competitor` in green)

   **Do NOT include:** "Onfire match" column (no information value), "Size band" column
   (redundant given employee count).

   All persona counts must come from a live Snowflake query against `GOLD.ENTITIES.PEOPLE`.
   Tech stack from `GOLD.ENTITIES.COMPANIES.TECHNOLOGIES`. Never invent or estimate these
   per-account numbers.

   Below the table, a small-print footer explaining what "Competitor tool detected" means
   (verified using a tracked competitor in last 30 days) and calling out empty-CRM employee
   fills + wildly-wrong corrections (e.g. Walmart 2.1M → 452K, Foxconn 900K → 98K).

3. **"Specific gaps — and what Onfire does about each one"** — three nested cards:
   - A. Closed-lost — name top-5 lost accounts ($147M, 1,898 deals) with industry-fit tags,
     existing contact summary, and what Onfire would add per row.
   - B. Look-alike accounts to wins — 21,062 (74.7%) no-contact total, with 5 named examples
     scored by win-signature match + Onfire signals + what Onfire adds.
   - C. Empty-field accounts — table of fields (Industry, Employees, Revenue, Country, HQ City,
     LinkedIn URL) with Empty-in-CRM count, expected Onfire fill rate, residual count.

## Buyers & Champions — section detail

**The cards have a white background** — use the template's `.prospect-card` class which has
`background: var(--card)` plus border and shadow matching the other cards. Earlier versions
used a translucent grey — explicitly changed.

Structure:
1. A "Where [Account] stands today" `.card` with 3 columns: existing CRM contacts list,
   win-pattern check (✓/✗ per persona), what Onfire returned summary.
2. A `.alert.info` glossary explaining Authority 1–5, warm-intro tiers (GOLD/SILVER/COLD),
   and the Buyer/Tech-champion/Receptiveness/Urgency score axes.
3. Four full `.prospect-card`s with:
   - Name + linked LinkedIn URL + title + location
   - Meta tag pills: Authority · Warm-intro tier · Connector name + shared company · Budget management ✓
   - Right-side score column: composite score, Buyer/Tech-champion breakdown, Receptiveness/Urgency
   - `.pc-reasoning` block with **Summary / Buyer signal / Technical fit / Warm intro**
     sub-headings, each followed by the verbatim AI Prospecting evidence in `<blockquote>`s
   - `.pc-howto` green callout: "How a rep would use this:" with a concrete next-action sentence
4. A closing `.card` titled "After this preview — what changes on the [Account] deal" — concrete
   forward-looking statement. **Do not** include a "Same call runs for every account in your
   pipeline" generic block — replaced with the deal-specific forward statement.

## Customer-facing copy guardrails

**Never use** these terms in customer-visible body:
- "MCP", "match_company", "match_person", "ai_prospecting", "contact_data_enrichment",
  "integration_proxy", "tenant_settings", "Snowflake", "Metabase", "SOQL"
- "Matchbox" — say "Onfire's matching engine" or just "matching"
- "On file" — say "in the record" or omit
- "Live MCP run" — never in the header
- "Same role, different employer" or similar redundant subtext on diff tables — the tag pills
  speak for themselves
- "2,769 signals in 60 days" or any specific signal-volume claim — replace with "live examples
  of the signal types Onfire tracks"

**Always use** explicit competitor names (Cortex XSOAR, Swimlane, IBM QRadar, Tines, Splunk SOAR),
not generic "competitor tech."

**Numbers formatting:**
- ARR: `$182.1M`, `$1.4M`, `$214.9K` (not `$182,100,000`)
- Counts: comma thousands separator (`28,203`, `34,541`)
- Percentages: integer or 1-decimal (`74.7%`, `12.1%`)
- Diff in tables: `.crm` strikethrough above `.onfire` green value, not a `→` arrow

## Interactivity

- **Tab switch:** clicking a nav button toggles `.active`, hides all `.workflow` divs, shows
  the target. Snapshot (#snapshot) is always-rendered above the workflows. Uses a 50ms
  `setTimeout` before `scrollIntoView` to avoid scroll-before-render.
- **Collapse / expand:** clicking the `.subsection > header` toggles `.collapsed`. Anchor
  clicks inside the header don't trigger the toggle.
- **Export PDF:** `window.print()`.
- **Share link:** `navigator.clipboard.writeText(window.location.href)`.

No local storage. No backend. No external fetches at runtime.
