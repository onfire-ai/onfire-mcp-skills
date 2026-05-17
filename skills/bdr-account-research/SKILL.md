---
name: bdr-account-research
description: Generate a full BDR (Business Development Representative) account research report for any company. The Onfire MCP `bdr_account_research` tool fetches every data source - tenant config, 10-K extracts, employee LinkedIn footprint, intent signals, and AI-scored prospects - in one call and returns a rendering contract alongside the data. This skill enforces the rendering contract and produces the final customer-facing A4 HTML file. Use whenever a user asks to "generate a report", "research an account", "build a BDR brief", "run account research", or mentions a company domain alongside words like "signals", "prospects", "10-K", "use cases", or "tenant".
---

# BDR Account Research Report

## What this skill does

The Onfire MCP owns the data pipeline. This skill owns the rendering.

Given a **company website** (e.g. `capitalone.com`) and a **tenant ID**
(e.g. `fortinet`), this skill:

1. Calls **one MCP tool**: `bdr_account_research`. The response carries
   tenant config + derived use cases, 10-K extracts, LinkedIn footprint,
   intent signals, AI-scored prospects (when enabled), and an inline
   `render_spec` that defines the rendering contract.
2. Enforces the rendering contract on a self-contained A4 HTML file.
3. Runs the pre-delivery checklist before delivery.
4. Handles follow-up questions by slicing the datasets the orchestrator
   already pulled, or by calling one of the narrow typed tools when the
   user asks for genuinely new data.

The skill **never** queries Snowflake or the signals database directly.
All data plumbing lives inside the Onfire MCP.

---

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `company_website` | Yes | `capitalone.com` |
| `tenant_id` | Yes | `fortinet` |
| `company_linkedin_url` | Optional | `https://www.linkedin.com/company/capital-one/` |

---

## Step 1 - Call the orchestrator

```
Onfire MCP: bdr_account_research(
  company_website="<company_website>",
  tenant_id="<tenant_id>",
  company_linkedin_url="<url>",   # optional but enables footprint + prospects
  telemetry={intent: "BDR account research report for tenant <tenant_id>"}
)
```

Polling pattern: if the response carries `status="still_running"`, the
AI prospecting run hasn't finished. Re-call `bdr_account_research` with
the same arguments — Phoenix's server-side dedup picks up the in-flight
prospecting run row and the second call typically completes without
spawning a duplicate. The non-prospecting blocks (`filings_10k`,
`linkedin_footprint`, `intent_signals`) are always complete on the first
call.

## Step 1a - Load the prospecting field glossary (REQUIRED when prospects are present)

The `prospects` block carries fields whose meaning is non-obvious and
easy to invert (e.g. `MASTER_SCORE_PRIORITY` is a tier where **lower
is better**; `SCORE_WARM_INTRO` is an enum -- `PLATINUM > GOLD >
SILVER > COLD` -- not a number). Misinterpreting these silently
produces wrong reports. Before rendering any prospect, call:

```
Onfire MCP: ai_prospecting_field_glossary()
```

This returns a self-describing contract for every prospect field:
`type`, `values` (enum or bounded range), `what_it_means`, `how_to_use`,
and examples. Use it as the authoritative source for:

- **What "good" looks like** on every score (`COMPOSITE_SCORE` is
  bounded 0-1500; >800 is top-decile, <400 is a stretch).
- **Tier direction** -- `MASTER_SCORE_PRIORITY=1` is the actionable
  cohort, not tier 5.
- **Warm-intro enum ordering** -- PLATINUM (alumni at target) is the
  highest-leverage path; COLD requires cold outbound.
- **Boolean signals** -- `WORKED_IN_CLIENT_COMPANY_IN_PAST=true` is
  the alumni flag, the highest-value expansion play.
- **Which fields are ready-made copy** -- `product_talking_points` and
  `ai_reasoning` are pre-written outreach payload; never rewrite, just
  surface verbatim.

The prospects response also carries:
- `prospects.field_glossary_resource_uri` - the MCP resource URI for
  the same glossary. Clients that auto-inject resources will load it
  without an explicit call; on other clients fall back to the tool.
- `prospects.field_index` - the sorted list of every field name as a
  fast schema-drift check. If a field in `top_picks` is missing from
  `field_index`, treat it as unverified and skip rendering it rather
  than guessing.

When `prospects.skipped` is true or `prospects.status="still_running"`,
do not call the glossary -- there's nothing to interpret yet.

## Response shape (the envelope you render from)

```
{
  "status": "completed" | "still_running",
  "company": { website, linkedin_url, name, ticker, latest_filing_date, ... },
  "tenant_config": {
    "golden_persona", "prospecting_enabled",
    "derived_use_cases": [{id, label, tag, evidence_count, ...}],
    "excluded_use_cases": [...],
    "footprint_keywords": [...]
  },
  "filings_10k": { found, filings: [{sections: {...}, keyword_hits: [...]}],
                   dataset: { id, ... } },
  "linkedin_footprint": { dataset, preview_rows, top_profiles, facets },
  "intent_signals": { dataset, preview_rows, facets, total_count },
  "prospects": { dataset, top_picks, status, ... },
  "datasets": { filings_10k, linkedin_footprint, intent_signals, prospects },
  "render_spec": {
    "section_order": [...],
    "hard_rules": [...],
    "use_case_palette": {...},
    "page_setup": {...},
    "pre_delivery_checklist": [...],
    "follow_up_tools": {...}
  }
}
```

## Use the inline `render_spec` and `tenant_config.brand`

The orchestrator ships the rendering contract inline. Do not invent your
own section order, palette, or rules. Read each from `render_spec`:

- `render_spec.section_order` - the canonical section order
- `render_spec.hard_rules` - every constraint you must apply
- `render_spec.use_case_palette` - the only colors allowed for use case tags
- `render_spec.page_setup` - A4 dimensions, font stack, print-color-adjust CSS
- `render_spec.pre_delivery_checklist` - the four checks you must run

Brand (color, display name, logo) is **tenant-driven, not hardcoded**.
Pull these at render time:

| Render value | Source | Fallback when absent |
|---|---|---|
| `--brand` accent color | `tenant_config.brand.primary` | `#1A2B4A` (deep navy) |
| Brand display name (header + footer) | `tenant_config.brand.display_name` | `tenant_config.tenant_id`, title-cased |
| Brand logo (header + footer) | `tenant_config.brand.logo_data_uri` | omit logo; render text wordmark only |

If `render_spec` is missing or empty (older orchestrator version), use
the defaults documented in `references/report-structure.md` as a fallback,
but always prefer the inline contract.

---

## Step 2 - Render the report

Read `references/report-structure.md` for the full A4 HTML template and
component snippets.

### Section order (from `render_spec.section_order`)

1. **Header bar** - brand-colored full-width bar with tenant logo
   (base64, when provided), brand display name, "Account Research -
   [Company]" eyebrow, and date.
2. **Company header card** - name (LinkedIn link), ticker, HQ, stat
   grid, overview.
3. **Why this account - why now** - 3-5 points sourced from
   `filings_10k.filings[].sections`, `intent_signals.preview_rows`,
   and `linkedin_footprint.top_profiles`. Every point carries a
   parenthetical date or "current role" citation. Render either as
   numbered prose rows or as a severity-tinted alert stack
   (see `references/report-structure.md` Section 3 Style A vs B).
4. **Confirmed technology deployment** - render
   `linkedin_footprint.top_profiles` verbatim. Each entry: name +
   LinkedIn link + title + location + the `evidence_sentence` quoted
   verbatim + a label of what was proved (derived from `matched_keyword`).
5. **Intent signals** - render `intent_signals.preview_rows` with each
   signal's `message_text` quoted **verbatim** in a grey evidence block.
   See "Quote, never rewrite" below. Omit the entire section when
   there are zero signals - do not render a negative-state placeholder.
6. **Solution fit divider + section head** - hairline divider followed
   by an eyebrow + title + subtitle introducing the use case cards.
7. **Use case cards** - one per entry in `tenant_config.derived_use_cases`,
   in the order provided (highest evidence first). The set is dynamic -
   render exactly the use cases the orchestrator returned, no more, no
   fewer. Each card pulls relevant signals + 10-K quotes + prospect
   rows that map to that use case. Tag colors come from
   `render_spec.use_case_palette` keyed by the use case `tag` - never
   invent a color.
8. **Key contacts per use case** - `break-before: page`, color-coded
   from `render_spec.use_case_palette` by the use case `tag`. Each
   contact card must render the fields the
   `ai_prospecting_field_glossary` `how_to_use` guidance calls out:
   warm-intro tier + connector name + shared company, composite score
   with breakdown, top three personas from `CURRENT_PERSONAS`,
   `PAST_COMPANIES_USED_CLIENT_TECH` when non-empty, career-momentum
   signals, the `ai_reasoning` bullets verbatim, and an opener from
   `product_talking_points`. Do not drop these fields silently -
   consistency across contact cards matters.

When surfacing prospect rows in sections 7 and 8, interpret every
field through the `ai_prospecting_field_glossary` contract loaded
in Step 1a - never invent score semantics.

### Hard rules (from `render_spec.hard_rules` - non-negotiable)

- **No em dashes** anywhere outside verbatim evidence quotes. Use a
  regular hyphen `-`.
- **No internal tool names** anywhere in the HTML. Never write Metabase,
  Snowflake, Phoenix, Onfire, MCP. Use: "market intelligence", "intent
  signals", "public filings", "industry research".
- **Signal messages quoted verbatim** - never paraphrase or reframe.
  Trim with leading/trailing ellipsis only.
- **Company name is a LinkedIn link** - `<a href="[linkedin]">` with a
  1.5pt dotted underline in `var(--faint)`.
- **Brand color is a CSS variable** - `var(--brand)` injected from
  `tenant_config.brand.primary` (fallback `#1A2B4A`). Do not hardcode
  hex literals for the brand anywhere in the document.
- **Footer** - company name, Account Research, [Month Year]. Nothing else.
- **No buying committee or cold opens section.**
- **System fonts only** - no Google Fonts CDN (file:// blocks it).

### Evidence block - quote, never rewrite (CRITICAL)

For every signal with a non-empty `message_text`, render that message
in a grey evidence block as a **verbatim** excerpt. You MAY trim with
leading/trailing ellipses (...) to focus on the relevant span, but you
MUST NOT paraphrase, summarize, translate, fix typos, reflow whitespace,
or otherwise alter the characters inside the quoted span. The text
inside the quote must be a contiguous substring of `message_text`
byte-for-byte. **Never substitute `short_summary` or any other column**
- for Company Change and Promotion signals as well, the evidence block
is `message_text` or nothing. If `message_text` is empty or null,
render `(no message text on record)` or skip the evidence block; do
not fabricate or substitute another field.

The same rule applies to `linkedin_footprint.top_profiles[].evidence_sentence`.

### Page setup (from `render_spec.page_setup`)

- `@page { size: A4; margin: 16mm 18mm 18mm 18mm }`
- `body { width: 174mm }`
- Font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif`
- All font sizes in `pt`: body 9pt, labels 7pt, headings 11-15pt
- `print-color-adjust: exact` rule in `@media print` (preserves background colors when printing)
- Every `.card` has `break-inside: avoid`
- Key contacts sections have `break-before: page`

### Use case palette (from `render_spec.use_case_palette`)

Only use the tag classes that appear in the palette. The set is
tenant-driven: render exactly the use cases `derived_use_cases`
returned and color each with its `tag`'s entry from
`use_case_palette`. Never invent a color. Never assume a fixed list
(no hardcoded "four canonical use cases").

If `derived_use_cases` returns a tag that has no matching entry in
`use_case_palette` (a schema drift), skip the color and fall back to
the neutral `--low-bg` / `--low-text` tokens rather than guessing.

---

## Step 3 - Pre-delivery checklist (from `render_spec.pre_delivery_checklist`)

Before saving the final HTML and calling `present_files`, run these
four checks. All four must pass.

1. **Use case tags constrained to the palette**
   `grep -oE 'class="tag" style="background:var\\(--[a-z]+-bg' report.html`
   Every tag class must be one of the palette keys returned in
   `render_spec.use_case_palette`. No invented tags.

2. **No internal tool names**
   `grep -iE 'phoenix|metabase|mcp|onfire' report.html` -> must return zero matches.

3. **No em dashes outside verbatim quotes**
   `grep -- '-' report.html` -> must return zero matches outside text
   inside `class="evidence"` / `class="quote"` blocks (which preserve
   verbatim message_text byte-for-byte).

4. **Why Now evidence references**
   Every `<div class="why-row">` body must contain a parenthetical in
   its bold strong tag - `(... [date] / [date range] / "current role")`
   - with one of the acceptable source types (10-K, LinkedIn profile,
   conference, community Slack/Discord, LinkedIn post, company-change
   records). No date-less Why Now points.

5. **Prospect field interpretation**
   If `prospects` carries real rows (not `skipped` / `still_running`),
   confirm `ai_prospecting_field_glossary` was loaded and every
   prospect-derived rendering decision (tier label, warm-intro
   wording, score commentary) traces to a `what_it_means` /
   `how_to_use` entry in the glossary. If you cannot point to the
   glossary entry that justifies a phrase, remove the phrase.

If any check fails, fix the report and rerun all checks. Do not
deliver until all pass.

---

## Step 4 - Output

### A4 HTML file

Generate a **fully self-contained** HTML file:

- Tenant logo embedded as **base64 data URI** - no external image references
- System font stack only - no Google Fonts CDN
- `print-color-adjust: exact` CSS in `@media print`
- Save to `/mnt/user-data/outputs/account-research-<company>-<tenant>.html`
- Call `present_files`

### PDF instructions for user

Tell the user:
> "To convert to PDF: open in Chrome -> Cmd/Ctrl+P -> Save as PDF -> enable **Background graphics** -> Save."

---

## Handling follow-up questions

The orchestrator ships four dataset IDs in `envelope.datasets`. Every
slicing question reuses those datasets via `query_datasets` - no
re-orchestration, no new SQL.

### Slice already-pulled data (zero-cost follow-ups)

For questions like "break down signals by source", "show me only RSA
attendees", "give me all the prospects, not just the top 10":

```
query_datasets(
  dataset_id="<envelope.datasets.signals | filings_10k | linkedin_footprint | prospects>",
  sql="SELECT ... FROM dataset WHERE ..."
)
```

Common patterns:
- Signal source mix: `SELECT source_name, COUNT(*) FROM dataset GROUP BY 1`
- Filter signals by event: `WHERE source_name = 'RSA Conference 2026'`
- Filter prospects by team: `WHERE LOWER(TITLE_NAME) LIKE '%cloud%'`
- Pull a specific 10-K paragraph: `SELECT FULL_MARKDOWN FROM dataset` then
  substring locally.

### Pull truly new data (Layer 3 typed tools)

When the user asks for data the orchestrator didn't pull, call the
relevant narrow typed tool. **Never write raw SQL.**

| User asks for | Call |
|---------------|------|
| Signals on a topic outside the tenant's keyword set (e.g. NIS2, DORA) | `query_intent_signals(tenant_id, account_website, keyword_match=[...])` |
| A 10-K section the report didn't surface (e.g. a specific exec name) | `query_company_filings(website, keywords=[...])` |
| Employees mentioning a different product / competitor set | `query_employee_footprint(company_linkedin_slug, keywords=[...])` |

Each typed tool returns its own dataset, so its output is also further
sliceable via `query_datasets`.

---

## Error handling

| Situation | Action |
|-----------|--------|
| `bdr_account_research` returns `status="still_running"` | Re-call with the same args; the in-flight prospecting task is shared. |
| `filings_10k.found` is `false` | Skip 10-K sections silently; note non-SEC-registered company in the report header if relevant. |
| `linkedin_footprint.skipped` is `true` | Skip the "Confirmed deployment" section silently. |
| `intent_signals.total_count` is 0 | Show "No live signals found". |
| `prospects.skipped` is `true` | Skip the prospects section (no scored prospects to show). |
| One of `*.error` keys is set | Skip that section; never fail the whole report. |

---

## Reference files

- `references/report-structure.md` - Full HTML template, CSS, layout rules
- `references/persona-to-usecase.md` - Map prospect titles -> use cases for the use-case-cards section
- `references/pdf-generation.md` - PDF conversion instructions
- `references/use-case-mapping.md` - (informational) the keyword-bucket mapping the orchestrator uses server-side; the skill no longer applies this mapping itself
- `references/10k-extraction.md` - (informational) the substring-extraction rules the orchestrator applies server-side; the skill no longer extracts 10-K sections itself
