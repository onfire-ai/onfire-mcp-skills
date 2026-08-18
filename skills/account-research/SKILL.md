---
name: account-research
description: Generate a full account research report for any company. The Onfire MCP `account_research` tool fetches the core data sources - tenant config, 10-K extracts, employee technology footprint, intent signals, and AI-scored prospects - in one call and returns a rendering contract alongside the data. This skill enriches it with additional warehouse signals via `ask_onfire` (hiring momentum, event attendance, persona/technology growth trends, dated deployment proof, active hiring managers), enforces the rendering contract, and produces the final customer-facing A4 HTML file. Use whenever a user asks to "generate a report", "research an account", "build a BDR brief", "run account research", or mentions a company domain alongside words like "signals", "prospects", "10-K", "hiring", "events", "growth", "use cases", or "tenant".
---

# Account Research Report

## What this skill does

The Onfire MCP owns the data pipeline. This skill owns the rendering, and
owns the two derivations the orchestrator does lossily: the tenant's use-case
taxonomy and its vendor/persona resolution (Step 1a).

Given a **company website** (e.g. `meridianbank.com`) and a **tenant ID**
(e.g. `ironwall`), this skill:

1. Calls `account_research` for the non-prospect data sources: tenant
   config + derived use cases, 10-K extracts, LinkedIn footprint, intent
   signals, and the inline `render_spec` that defines the rendering
   contract.
2. **Re-derives the tenant's taxonomy** (Step 1a). The envelope's
   `derived_use_cases` and `footprint_keywords` are coarser than the tenant's
   own configuration and their resolution is not match-quality gated, so the
   skill resolves the tenant's personas and vendor list itself, behind a
   match-tier gate.
3. Takes the prospect set from the envelope when it is already complete, and
   only calls `ai_prospecting` directly to poll a run that is still going.
4. **Enriches the report with warehouse signals the orchestrator does not
   pre-pull** - hiring momentum, active hiring managers, growth direction,
   the real competitor/technology footprint, and golden-persona contacts -
   via a fixed set of structured `ask_onfire` queries (Step 1d). These feed
   the Why-Now, Confirmed-deployment, and Key-contacts sections.
5. Builds the company card from warehouse firmographics when the account is
   not an SEC filer (Step 1e), instead of narrating unsourced figures.
6. Enforces the rendering contract on a self-contained A4 HTML file.
7. Runs the pre-delivery checklist before delivery.
8. Handles follow-up questions by slicing the datasets already produced, or
   by calling `ask_onfire` / one of the narrow typed tools when the user asks
   for genuinely new data.

The skill **never** writes raw SQL and never touches Snowflake or the
signals database directly. All data plumbing lives inside the Onfire
MCP. `ask_onfire` is part of that MCP surface: it takes a structured
query (a `QueryIR` of entity + filters, never SQL), validates it against
the semantic model server-side, and never exposes schema, table names,
or vendors — so authoring `ask_onfire` queries is consistent with that
principle, not an exception to it.

---

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `company_website` | Yes | `meridianbank.com` |
| `tenant_id` | Yes | `ironwall` |
| `company_linkedin_url` | Optional | `https://www.linkedin.com/company/meridian-bank/` |

---

## Step 1 - Call the orchestrator for non-prospect data

```
Onfire MCP: account_research(
  company_website="<company_website>",
  tenant_id="<tenant_id>",
  company_linkedin_url="<url>",   # optional but enables footprint
  telemetry={intent: "Account research report for tenant <tenant_id>"}
)
```

The `filings_10k`, `linkedin_footprint`, and `intent_signals` blocks are
always complete on the first call. The `prospects` block is the output of the
orchestrator's own `ai_prospecting` run - read it (Step 1b) rather than
re-running prospecting from scratch.

Fire `ai_prospecting_field_glossary` (Step 1c) concurrently with this call. It
has no dependency on the envelope, and waiting for prospects before loading it
adds a round trip for nothing.


## Step 1a - Resolve the tenant's real taxonomy and vendor list (REQUIRED)

`tenant_config.derived_use_cases` and `tenant_config.footprint_keywords` arrive
pre-computed, but both are coarser than what the tenant's own configuration
supports:

- The use-case set is a generic security-category mapping. It does not always
  contain the category the tenant actually sells, and a card can be produced by
  a loose keyword hit rather than real evidence.
- The keyword list is resolved without a match-quality gate and is truncated, so
  it can under-cover a tenant's competitors while over-matching on broad
  infrastructure terms. Nothing in the envelope flags either case.

Neither is a reason to distrust the envelope's data blocks - they are the reason
to derive the *taxonomy* yourself, in two calls:

1. `get_tenant_settings(tenant_id)` - returns the full
   `account_research.queries_sections` (`competitors`, `organization`,
   `technologies`, `cloud_providers`), plus `golden_persona` and
   `display_names_mapping`.
2. `resolve_insights(concepts=[...], kind="technology")` - ONE call carrying
   every `competitors` + `technologies` value, **with the trailing `" Insight"`
   suffix stripped**. Tenant config stores vendors with that suffix and it is
   not part of any catalog name, so leaving it on drops every concept to the
   `partial` tier - where the top candidate may be the wrong kind entirely (a
   suffixed `Datadog` ranks the persona `data` first), too broad, or right but
   unverified. Stripped, the same vendors resolve `match: "exact"`. See the
   worked before/after tables in `references/ask-onfire-signals.md`.

Then resolve the personas the same way with `kind="persona"`: every
`queries_sections.organization` value plus `golden_persona`.

**Match-tier gate (non-negotiable).** Every candidate carries a `match` tier.
Keep `exact` and `synonym`. Treat `partial` and `fuzzy` as unresolved and never
search on them. Do not try to judge a `partial` candidate by whether its value
looks plausible - some are right and some are a persona wearing a technology's
name; the tier is the signal, not the value. Never render the unresolved list in
the customer report; it is an internal detail.

### Use cases: prefer the tenant's own taxonomy

Build the use-case set from the resolved `organization` personas, labelled via
`display_names_mapping` (the tenant already ships human labels, e.g.
`email_security` -> "Email Security Specialist"). Keep 3-5, ordered by the
evidence you actually found for this account in Step 1d.

This deliberately overrides `tenant_config.derived_use_cases`. When you do:

- Colors come **only** from `render_spec.use_case_palette`. Assign an existing
  palette entry per card; never invent a hex, never emit a tag class that is not
  a palette key.
- Never render a card whose only evidence is a single partial keyword match.
- Every card must position the tenant on the product it actually sells. If a
  card has no honest tie to that product, drop the card - do not manufacture an
  angle.
- Fall back to the orchestrator's `derived_use_cases` when
  `get_tenant_settings` errors or the tenant has no `organization` list.


## Step 1b - Prospect set: read the envelope first, poll only if needed

The orchestrator already runs `ai_prospecting(action="run", use_cache=True)`
inside its own fan-out, so the envelope's `prospects` block is that tool's
output, not a lesser copy of it.

- `envelope.prospects.status == "completed"` -> **use it as-is.** Do not re-call
  `ai_prospecting`; that spends another round trip of up to 50s for rows you
  already hold.
- `still_running`, `skipped`, or an `error` -> poll with
  `ai_prospecting(action="run", company_linkedin_url="<url>")`, re-calling with
  the returned `run_ids` (or identical arguments) until `status="completed"`.
  Phoenix dedups server-side, so this joins the in-flight run instead of
  starting a second one.
- Prospecting needs the company LinkedIn URL. Resolve it with the
  `match-company` skill first when the envelope has none.

Render every prospect from whichever response completed - both the inline
`prospects` array and the preview-shape `top_picks` + `preview_rows`. Treat its
`dataset.id` as the authoritative prospect dataset for `query_datasets` slicing
and for `download_dataset`.

When `prospecting_enabled` is false, or the completed response carries zero
prospects, do **not** drop Section 8. Fill it from the Step 1d contact sources:
active hiring managers and golden-persona contacts, each labelled with where it
came from.


## Step 1c - Load the prospecting field glossary (REQUIRED when prospects are present)

**Fetch this concurrently with Step 1**, not after prospects land - it has no
dependency on either.

The `ai_prospecting` response carries fields whose meaning is non-obvious
and easy to invert (e.g. `MASTER_SCORE_PRIORITY` is a tier where **lower
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

The `ai_prospecting` response also carries:
- `field_glossary_resource_uri` - the MCP resource URI for the same
  glossary. Clients that auto-inject resources will load it without
  an explicit call; on other clients fall back to the tool.
- `field_index` - the sorted list of every field name as a fast
  schema-drift check. If a field in `top_picks` is missing from
  `field_index`, treat it as unverified and skip rendering it rather
  than guessing.

When `ai_prospecting` returned zero prospects, do not call the
glossary -- there's nothing to interpret yet.

## Step 1d - Enrich with `ask_onfire` warehouse signals (REQUIRED)

The orchestrator pulls four blocks (filings, footprint, intent signals,
prospects). Several signal surfaces that materially decide whether this report
is worth reading are **not** in the envelope. Pull them, scoped to the account
by its LinkedIn URL.

This step used to be optional and self-selected, which is why two runs of the
same account produced different reports. The mandatory set below is now fixed.

`ask_onfire` takes a structured `QueryIR` (entity + filters + insight_filters +
limit), validates it against the semantic model, and returns rows. **Read
`references/ask-onfire-signals.md` for the exact per-entity recipes.** Never
guess field names and never write SQL.

### Schema lookups: one call, not one per entity

`describe_onfire_schema` accepts a **list**. When you need to confirm fields,
make a single `describe_onfire_schema(["job_post", "hiring_manager_signal",
...])` call rather than one per entity.

### Mandatory pulls

| Pull | Entity | Feeds |
|---|---|---|
| Open roles / hiring momentum | `job_post` | Why-Now (Section 3), use-case account-signals |
| Active hiring managers (decision-makers) | `hiring_manager_signal` | Key contacts (Section 8), Why-Now |
| Growth direction | `growth_insight_monthly` or `headcount_monthly` | Why-Now, company card |
| **Competitor / technology footprint** (the Step 1a resolved list) | `contact` + `insight_filters` `kind=technology` | Confirmed deployment (Section 4) |
| **Golden-persona contacts** | `contact` + `insight_filters` `kind=persona` | Key contacts (Section 8), use-case cards |

The last two exist because the orchestrator's own footprint searched a truncated,
badly resolved keyword list. Yours searches the vendors the tenant actually
competes with and the persona it actually sells to.

### Optional pulls - only when a section is still thin

`event_company` / `event_contact` (event presence), `insight_evidence` (dated
"in production since" proof), `product_adoption` (incumbent adoption quarter and
likely renewal quarter - **BETA, both dates are estimates**, so any figure from
it must be labelled as an estimate), `github_member` (developer engagement),
`people_experiences` (alumni / warm-path context).

### Two mechanics that matter

1. **OR in a single call.** An `insight_filters` entry accepts a **list** as its
   `value`, so the whole competitor set is one query, not one per vendor:
   `insight_filters: [{kind: "technology", value: ["CrowdStrike",
   "SentinelOne", "Microsoft Defender"]}]`. Separate entries AND together; a
   list inside one entry ORs.
2. **Always set an explicit `limit`.** A direct `ask_onfire` call returns rows
   per the limit you set; 5-10 is plenty for report evidence, 25-30 for the
   competitor footprint. If the response is `needs_confirmation`
   (`stage: "row_budget"`) it returned no rows - tighten a filter or lower
   `limit` and resubmit. Do not blindly set `confirmed: true`.

Requires `company_linkedin_url` (reuse `company.linkedin_url` from the envelope,
or resolve via the `match-company` skill). Without it, skip this step and render
from the orchestrator blocks alone.

## Step 1e - Company profile when the account is not an SEC filer

`filings_10k.found = false` is the common case, not the exception - non-US and
privately held companies have no 10-K. When it is false, do **not** narrate
figures you cannot source. Build the company card from:

- `ask_onfire` on `company` for firmographics (industry, HQ, size band, type),
- `get_company_headcount` for current headcount,
- the Step 1d `headcount_monthly` pull for direction,
- `search_offices` when geographic footprint is relevant.

Any figure that does not come from one of those must carry its source inline in
the card, or be left out. An empty stat is better than an uncited one.


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
  "linkedin_footprint": {
    // INSIGHT-BASED: people at the company who CARRY the tenant's
    // technology insights (the orchestrator resolves the tenant's
    // tech/competitor keywords to canonical technology insight_names
    // and pulls active employees carrying each, via the semantic layer).
    dataset, preview_rows, top_profiles,
    "facets": { "by_keyword": { /* keyed by resolved insight name */ } },
    "resolved_technologies": [ /* canonical insight names searched */ ],
    "unresolved_keywords":  [ /* tenant keywords not in the catalog */ ],
    "total_matched": 0   // present only when more matched than returned
    // each top_profiles / preview row carries: matched_keyword (the
    // resolved technology insight), matched_insights (list), evidence_term,
    // and evidence_sentence (BEST-EFFORT — may be null; see Section 4)
  },
  "intent_signals": { dataset, preview_rows, facets, total_count },
  "prospects": { /* the orchestrator's own ai_prospecting run - see Step 1b */ },
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

## Use the inline `render_spec` (and the fixed Onfire palette)

The orchestrator ships the rendering contract inline. Do not invent your
own section order, palette, or rules. Read each from `render_spec`:

- `render_spec.section_order` - the canonical section order
- `render_spec.hard_rules` - every constraint you must apply
- `render_spec.use_case_palette` - the only colors allowed for use case tags
- `render_spec.page_setup` - A4 dimensions, font stack, print-color-adjust CSS
- `render_spec.pre_delivery_checklist` - the server's baseline checks; Step 3
  runs those plus the skill's own (see Step 3)

**The report's color palette is Onfire's, not the tenant's.** The
`--brand` (navy) / `--accent` (purple) tokens are hard-coded in the CSS
block in `references/report-structure.md` and do not vary per tenant.
Ignore `tenant_config.brand.primary` if present — it's legacy. The only
tenant-driven content in the header bar is the display name and logo:

| Render value | Source | Fallback when absent |
|---|---|---|
| Tenant display name (header + footer) | `tenant_config.tenant_id`, title-cased | always apply — no display_name field exists |
| Tenant logo (header + footer) | not available in tenant config | always omit logo; render text wordmark only |

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
   grid, overview. When `filings_10k.found` is false, build the stat grid
   from the Step 1e warehouse pulls; every figure carries a source or is
   dropped. Never narrate an uncited financial number.
3. **Why this account - why now** - 3-5 points sourced from
   `filings_10k.filings[].sections`, `intent_signals.preview_rows`,
   the footprint dataset, **and the Step 1d `ask_onfire`
   enrichment** — open-role surges (`job_post`, with `date_posted`),
   active hiring managers (`hiring_manager_signal`, with `signal_date`),
   event presence (`event_company` attendee counts, with the event
   year), and rising adoption (`growth_insight_monthly` /
   `headcount_monthly`, citing the month + growth direction). Every
   point carries a parenthetical date or "current role" citation. Render
   either as numbered prose rows or as a severity-tinted alert stack
   (see `references/report-structure.md` Section 3 Style A vs B).
4. **Confirmed technology deployment** - render from the **Step 1d
   competitor/technology footprint pull**, plus the orchestrator's
   footprint **dataset** (not its `top_profiles`).
   `top_profiles` is a **small inline preview**, not the result set - it
   commonly carries 3 rows where the account matched dozens of people. The
   dataset holds the full pull; slice it instead. It typically yields 20-30
   evidence-backed rows:
   ```
   query_datasets(
     datasets={"footprint": "<envelope.datasets.linkedin_footprint>"},
     sql="SELECT full_name, linkedin_url, job_title, location_name,
                 matched_keyword, evidence_sentence
          FROM footprint WHERE evidence_sentence IS NOT NULL"
   )
   ```
   Dataset slicing is free, so there is no reason to render only 3.
   **Confirm only what resolved cleanly.** A confirmation label may name a
   vendor only if it came back `exact` or `synonym` from Step 1a. If a row's
   `matched_keyword` is not a **product name** - a hardware architecture, a
   networking or infrastructure category, an analysis-technique acronym, or a
   vendor's parent brand where the config named a specific product - it is not
   a deployment confirmation. Drop the row instead of claiming a vendor is in
   place. Test: could you say "the account runs <matched_keyword>" to their
   CISO without it sounding wrong? If not, drop it.
   Each person genuinely carries the insight, and `matched_keyword` is the
   **canonical technology name** (use it for the confirmation label, e.g.
   "CrowdStrike confirmed"). `evidence_sentence` is **best-effort and may be
   null** (the insight tag does not require the literal term in the bio):
   - When present, quote it **verbatim** in the evidence block (same
     rule as before).
   - When null, render the confirmation from the matched technology
     without a fabricated quote — state the person carries the
     deployment signal; do NOT invent a sentence.
   Optionally strengthen an entry with a Step 1d `insight_evidence` pull
   to add a "in production since [start_date]" date. Skip the whole
   section only when both the Step 1d pull and the dataset are empty.
5. **Intent signals** - render `intent_signals.preview_rows` with each
   signal's `message_text` quoted **verbatim** in a grey evidence block.
   See "Quote, never rewrite" below. Omit the entire section when
   there are zero signals - do not render a negative-state placeholder.
   This block is scoped by an exact `account_website` match and is
   genuinely sparse (commonly 0-2 rows per account), so a thin or absent
   section here is normal. Do not compensate by promoting Step 1d
   enrichment into it and labelling it an intent signal - hiring activity
   is hiring activity. If the account may be filed under a sibling domain,
   one extra `query_intent_signals` call with that domain is worthwhile.
6. **Solution fit divider + section head** - hairline divider followed
   by a single eyebrow line "Solution fit - [Tenant Display Name] use
   cases at [Account Display Name]" introducing the use case cards
   (no separate title/subtitle).
7. **Use case cards** - one per entry in the **Step 1a derived use-case
   set** (which overrides `tenant_config.derived_use_cases`; see Step 1a
   for why), ordered by the evidence actually found for this account.
   Keep 3-5. Drop any card whose only evidence is a single partial keyword
   match, and any card with no honest tie to what the tenant sells - a
   shorter report beats a wrong one. Every card's alignment column
   positions the tenant on **its own product**; never argue an adjacent
   security category the tenant does not sell. Each card pulls relevant
   signals + verbatim talking-point
   quote (10-K, LinkedIn profile, public talk, or any other verifiable
   source - see `report-structure.md` "Talking-points source citation")
   + prospect rows that map to that use case. The right column is
   brand-named: render its label as "[Tenant Display Name] solution
   alignment" (e.g. "Artifex solution alignment"). Tag colors come from
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
   **Active hiring managers** from the Step 1d `hiring_manager_signal`
   pull are a complementary contact source: a person actively building a
   team is a live decision-maker / budget owner. Surface them alongside
   the `ai_prospecting` contacts (tag them "actively hiring -
   [job_post_title]"), mapping each to its use case via the role being
   hired for.
   **Golden-persona contacts** from the Step 1d persona pull are the second
   complementary source: people at the account carrying the tenant's
   `golden_persona` are its literal buying persona. Tag them with the
   persona's `display_names_mapping` label.
   When prospecting is disabled or returns zero, these two sources carry
   Section 8 on their own. Label each contact with the source it came from,
   and never print a bare "no prospect list available this cycle" line as
   the section's only content - if all three sources are empty, omit the
   section.

When surfacing prospect rows in sections 7 and 8, interpret every
field through the `ai_prospecting_field_glossary` contract loaded
in Step 1c - never invent score semantics.

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
- **Brand colors are fixed Onfire tokens** - `var(--brand)` (navy
  `#0A2540`) and `var(--accent)` (purple `#7C5CFF`) are hard-coded in
  the CSS block. Do not hardcode hex literals; do not pull
  `tenant_config.brand.primary` to override them. The report is
  Onfire-branded; tenant brand surfaces only as text/logo content in
  the header bar.
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

The same rule applies to every `evidence_sentence` - from `top_profiles`,
from the sliced footprint dataset, or from a Step 1d pull.

### Page setup (from `render_spec.page_setup`)

- `@page { size: A4; margin: 16mm 18mm 18mm 18mm }`
- `body { width: 174mm }`
- Font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif`
- All font sizes in `pt`: body 9pt, labels 7pt, headings 11-15pt
- `print-color-adjust: exact` rule in `@media print` (preserves background colors when printing)
- Every `.card` has `break-inside: avoid`
- Key contacts sections have `break-before: page`

### Use case palette (from `render_spec.use_case_palette`)

Only use the tag classes that appear in the palette. The palette is the
**colour** contract; Step 1a owns the **card set**. So: render the Step 1a
use cases, and assign each one an existing `use_case_palette` entry.

- Never invent a colour and never emit a tag class that is not a palette key.
- Reuse a palette entry whose semantics are closest to the card, or simply
  assign entries in order. The palette has 7 slots; keep to 3-5 cards.
- Never assume a fixed list of use cases (no hardcoded "four canonical
  use cases").
- If a card has no sensible palette entry, fall back to the neutral
  `--low-bg` / `--low-text` tokens rather than guessing a hex.

---

## Step 3 - Pre-delivery checklist (from `render_spec.pre_delivery_checklist`)

Before saving the final HTML and calling `present_files`, run every check
below. All must pass.

1. **Use case tags constrained to the palette**
   `grep -oE 'class="tag" style="background:var\\(--[a-z]+-bg' report.html`
   Every tag class must be one of the palette keys in
   `render_spec.use_case_palette`. No invented tags.

2. **No internal tool names, no em dashes outside verbatim quotes**
   One pass does both:
   `grep -niE 'phoenix|metabase|mcp|onfire|—' report.html`
   Zero matches, except a U+2014 inside a `class="evidence"` /
   `class="quote"` block (those preserve `message_text` byte-for-byte).

3. **Why Now evidence references**
   Every `<div class="why-row">` body must contain a parenthetical in
   its bold strong tag - `(... [date] / [date range] / "current role")`
   - with one of the acceptable source types (10-K, LinkedIn profile,
   conference, community Slack/Discord, LinkedIn post, company-change
   records). No date-less Why Now points.

4. **Prospect field interpretation**
   If the `ai_prospecting` response from Step 1b carries real rows
   (not `still_running` / zero-result), confirm
   `ai_prospecting_field_glossary` was loaded and every
   prospect-derived rendering decision (tier label, warm-intro
   wording, score commentary) traces to a `what_it_means` /
   `how_to_use` entry in the glossary. If you cannot point to the
   glossary entry that justifies a phrase, remove the phrase.

5. **Prospect source provenance**
   Every prospect must come from a **completed** `ai_prospecting` response -
   either the envelope's block (Step 1b, preferred) or the standalone poll.
   Never render rows from a `still_running` response.

6. **Vendor confirmations traced to a clean resolution**
   Every "X confirmed" label in the Confirmed-deployment section names a
   vendor that resolved `exact` or `synonym` in Step 1a, and the label names a
   product - never a hardware architecture, an infrastructure category, an
   analysis-technique acronym, or a parent brand standing in for a specific
   product. If you cannot point at the resolution that justifies a label,
   remove the row.

7. **Deployment section not needlessly truncated**
   If the footprint dataset holds more evidence-backed rows than the report
   renders, you rendered the inline preview instead of slicing the dataset.
   Go back to Section 4.

8. **Use cases are the tenant's own, and honestly positioned**
   Each card traces to a Step 1a persona (or to the documented fallback),
   no card rests on a single partial keyword match, and no card argues a
   product category the tenant does not sell.

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

The orchestrator ships three dataset IDs in `envelope.datasets`
(`filings_10k`, `linkedin_footprint`, `intent_signals`). The
`ai_prospecting` call from Step 1b ships the fourth — the prospects
dataset — on its own response (`dataset.id`). Every slicing question
reuses those datasets via `query_datasets` - no re-orchestration, no
new SQL.

### Slice already-pulled data (zero-cost follow-ups)

For questions like "break down signals by source", "show me only SecureCon
attendees", "give me all the prospects, not just the top 10":

```
query_datasets(
  dataset_id="<envelope.datasets.intent_signals | envelope.datasets.filings_10k
               | envelope.datasets.linkedin_footprint
               | ai_prospecting_response.dataset.id>",
  sql="SELECT ... FROM dataset WHERE ..."
)
```

Common patterns:
- Signal source mix: `SELECT source_name, COUNT(*) FROM dataset GROUP BY 1`
- Filter signals by event: `WHERE source_name = 'SecureCon 2026'`
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
| Employees carrying a different product / competitor | `ask_onfire` — `entity=contact`, filter `current_company_url eq <url>`, `insight_filters=[{kind:technology, value:[<product>, ...]}]` — a **list ORs in one call** (NOT a raw `JOB_SUMMARY` ILIKE) |
| People in a given role / persona at the account | `ask_onfire` — `entity=contact`, filter `current_company_url eq <url>`, `insight_filters=[{kind:persona, value:<resolved persona>}]` |
| When the incumbent was adopted / when they renew | `ask_onfire` — `entity=product_adoption`, filter `company_linkedin_url eq <url>` (BETA - estimates, label them) |
| Firmographics for a company with no 10-K | `ask_onfire` — `entity=company`, filter `linkedin_url eq <url>`, plus `get_company_headcount` |
| More employee-footprint rows than the report showed | `query_datasets` on `envelope.datasets.linkedin_footprint` — free, no row budget |
| Open roles / what the company is hiring for | `ask_onfire` — `entity=job_post`, filter `company_url eq <url>` (+ `job_function`/`seniority`/`open`) |
| Who is actively hiring (decision-makers) | `ask_onfire` — `entity=hiring_manager_signal`, filter `company_url eq <url>` (+ `person_seniority`) |
| Who attended an event / company event presence | `ask_onfire` — `entity=event_contact` (who) or `event_company` (counts), filter `event eq <resolved>` + `company_url eq <url>` |
| Is a persona/tech adoption growing at the account | `ask_onfire` — `entity=growth_insight_monthly`, filter `company_url eq <url>` + `insight eq <resolved>`, order by `month` |
| Headcount growth trend | `ask_onfire` — `entity=headcount_monthly`, filter `company_url eq <url>`, order by `month` |
| Since-when / proof behind a signal | `ask_onfire` — `entity=insight_evidence`, filter `company_url eq <url>` + `insight_value eq <resolved>` |
| Developers engaging with an OSS repo | `ask_onfire` — `entity=github_member`, filter `repo_name`/`activity`, join `contact` |
| Where a person worked before / alumni of the account | `ask_onfire` — `entity=people_experiences`, filter `company_url eq <url>` + `current=false` |

See `references/ask-onfire-signals.md` for the full worked `QueryIR` of
each recipe, the bound-concept resolution step, and the per-row billing
rule. Each tool/query returns its own dataset, so its output is also
further sliceable via `query_datasets`.

---

## Error handling

| Situation | Action |
|-----------|--------|
| `account_research` returns `status="still_running"` solely because of prospecting | Use the completed non-prospect blocks and poll prospects per Step 1b. Do not re-call the orchestrator. |
| `get_tenant_settings` fails or the tenant has no `organization` list | Fall back to `tenant_config.derived_use_cases`, and treat the resulting use-case set as generic rather than tenant-specific. |
| Every vendor in Step 1a resolves only `partial` / `fuzzy` | Run no technology footprint pull. Render Confirmed deployment from the orchestrator dataset only, and only for rows whose `matched_keyword` is a real vendor. Never confirm a vendor off a partial match. |
| Step 1d competitor footprint returns zero rows | Normal for a small or thinly covered account. Fall back to the orchestrator's footprint dataset; if that is empty too, omit the section. |
| Golden-persona pull returns zero rows | Section 8 falls back to hiring managers, then to prospects. If all are empty, omit Section 8. |
| `linkedin_footprint.skipped` is `true` | Skip the "Confirmed deployment" section silently. |
| `linkedin_footprint` returns zero people (`total_count` 0), or every tenant keyword is in `unresolved_keywords` | Fall back to the Step 1d pull; skip the section only if both are empty. Never render `unresolved_keywords` in the customer report (internal detail). An empty `top_profiles` alone is NOT an empty footprint - it is only a preview; check `total_count` and the dataset. |
| `linkedin_footprint` row has a null `evidence_sentence` | Render the confirmation from `matched_keyword` without a quoted evidence block; never fabricate a sentence. |
| `intent_signals.total_count` is 0 | Omit the Intent signals section entirely (per Section 5). Common and expected - do not backfill it with Step 1d enrichment. |
| Step 1d `ask_onfire` returns `needs_confirmation` (`stage: "row_budget"`) | No rows billed. Lower `limit` to what the section needs and resubmit; do not blindly set `confirmed: true`. |
| Step 1d `ask_onfire` returns zero rows or an `error` | Skip that enrichment silently; render from the orchestrator blocks. Never fail the report. |
| `ai_prospecting` returns `status="still_running"` | Re-call with the returned `run_ids` (or identical args). Phoenix dedups server-side. |
| `ai_prospecting` returns zero prospects (`top_picks: []`) or `tenant_config.prospecting_enabled` is `false` | Drop the prospect columns in Section 7 cards, but keep Section 8 and fill it from the Step 1d hiring-manager and golden-persona pulls. Omit Section 8 only when all three sources are empty. |
| Company has no LinkedIn URL even after `match-company` | Skip Steps 1b and 1d entirely; render from `company_website`-scoped blocks only. Step 1a still runs - the taxonomy is tenant-scoped, not account-scoped. |
| `filings_10k.found` is false | Expected for non-US and private companies. Run Step 1e and source every company-card figure. |
| One of `*.error` keys is set | Skip that section; never fail the whole report. |

---

## Reference files

- `references/report-structure.md` - Full HTML template, CSS, layout rules
- `references/ask-onfire-signals.md` - Step 1a resolution gate + Step 1d `ask_onfire` QueryIR recipes (hiring, events, growth, dated proof, github, alumni, competitor footprint, golden-persona contacts, product adoption, firmographics) + row-budget rules
- `references/persona-to-usecase.md` - Map prospect titles -> use cases for the use-case-cards section
- `references/pdf-generation.md` - PDF conversion instructions
- `references/use-case-mapping.md` - (informational) the keyword-bucket mapping the orchestrator uses server-side; the skill no longer applies this mapping itself
- `references/10k-extraction.md` - (informational) the substring-extraction rules the orchestrator applies server-side; the skill no longer extracts 10-K sections itself
