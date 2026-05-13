---
name: prospect-demo-signals
description: Show an Onfire prospect (a company a BDR/AE is selling Onfire TO) 3-5 strong NEW-BUSINESS buying-intent signals about that prospect's *own* market - competitor-vs-competitor comparisons, named-incumbent dissatisfaction, vendor-shopping conversations - pulled live from Metabase and Onfire MCP, with each public-company signal auto-enriched by a verbatim quote from the account's latest SEC 10-K (via Snowflake EDGAR). Use whenever a BDR/AE provides a prospect identifier they are selling Onfire to - **a company name, a domain, or a LinkedIn URL all work** (e.g. "wiz", "Datadog", "wiz.io", "demo signals for crowdstrike.com", "what would Onfire have shown CrowdStrike this morning"). Names are resolved to a canonical domain via the Onfire `match_company` tool (Matchbox2 vector search), so fuzzy and partial names work. Each output must include at least 1 Slack-or-Discord signal, 1 Reddit signal, and 1 LinkedIn signal where someone names a competitor in a comparison context. NEVER surface signals where the account already uses the prospect's product (those are expansion signals, not new-business), signals that praise the prospect's product, or signals where the account is the prospect itself.
---

# Prospect demo signals

## Purpose

You are an Onfire BDR / AE selling Onfire to a third-party company (e.g. Wiz, Snyk, CrowdStrike, Lacework). You want to walk into the demo with **a handful of public signals their own sales team would have killed to see this morning** — practitioners openly shopping in their category, naming competitors, complaining about incumbents.

This skill produces 3-5 of those signals, in chat, with these slots:
- **1 Slack / Discord** (practitioner community chat — treat both as equivalent)
- **1 Reddit**
- **1 LinkedIn** (strict — see Step 4)
- Remaining slots: best score across any bucket

---

## Inputs

| Input | Required | Default | Example |
|-------|----------|---------|---------|
| `prospect` | Yes | — | `Wiz`, `wiz.io`, `Datadog`, `https://crowdstrike.com`, `https://linkedin.com/company/snowflake-computing` |
| `lookback_months` | No | `5` | `3` |
| `count` | No | `5` (clamp 3-5) | `4` |

**Accepts name, domain, or LinkedIn URL.** Whatever the BDR types, the skill first runs Onfire's `match_company` (Matchbox2 — vector search + AI matching) to resolve to a canonical domain + LinkedIn URL + firmographics. Names are first-class inputs — fuzzy spelling, partial names, and casing all work. Internally the skill always operates on the canonical domain after Step 1.

---

## What "strong buying intent" means

In priority order:

1. **Vendor-vs-vendor comparison** — "X vs Y", "X or Y, which is better?", someone publicly weighing two named competitors.
2. **Looking for an alternative** — "alternative to X", "switching from X", "moving off X".
3. **Named-incumbent dissatisfaction** — "Our current [category] tool (X) failed to…", "X tripled pricing", "lost confidence in X's incident response".
4. **Multi-vendor tool sprawl** — "we run X + Y + Z and can't reconcile" (3+ named competitors in one breath).
5. **Active evaluation of a single competitor** — "trialing X for [use case], anyone benchmarked it?".

Generic category interest ("we're hiring DevSecOps") **does not qualify** for this skill — that's already in the prospect's standard outreach. This skill is for signals that would make their AE drop their coffee.

---

## Net-new only — NEVER surface expansion signals

This skill exists to help the prospect's **new-business** AE/BDR org. Onfire's customers run their own CSM/expansion motion separately. A signal where the account is already using the prospect's product is an **expansion signal, not a new-business signal** — drop it.

**Drop the signal if the account appears to already be a customer of the prospect.** Concrete heuristics, applied to `short_summary` and `message_text`:

- Signal text contains the prospect's brand name in a possessive / first-person-plural context: `"our <Prospect>"`, `"we use <Prospect>"`, `"we run <Prospect>"`, `"our <Prospect> APM/SIEM/CNAPP"`, `"in <Prospect>, I can…"`, `"my <Prospect> dashboard"`.
- Signal text describes hands-on configuration, debugging, or operational work inside the prospect's product (e.g. "Datadog APM tracer fragmentation", "Wiz misconfiguration alerts triggered on us", "our Snyk scan flagged…").
- `source_name` is the prospect's own community / support channel (e.g. `Datadog` Slack, `Snyk` Slack, `Wiz Customers` channel) — those are existing customers asking the vendor for help.
- Any seller_indicators term appears next to a "we / our / my / in our" pronoun.

**Keep the signal only if** the account looks like a customer of a *competitor* or an open-source alternative — typically:
- Active use of a named competitor ("our New Relic…", "running Splunk for…", "we're on Lacework")
- Shopping language ("alternative to <Competitor>", "switching from <Competitor>", "evaluating <Competitor A> vs <Competitor B>")
- Open-source / DIY observability/security stack the prospect could displace ("Prometheus + Grafana + ELK", "homegrown CSPM")

## What else to NEVER surface

- Signals that praise the prospect's product or feature names (look up `seller_indicators` from the library).
- Signals where `account_website` is the prospect's own domain or any alias — those are their own employees posting.
- Signals about the prospect's job postings, partner press, acquisition news, conference talks.
- Signals where the prospect is mentioned *only as the winner* of a comparison ("X was great, much better than Y") — flattering, not actionable.
- Generic "vs" matches unrelated to the prospect's category (e.g. "VS Code vs JetBrains" when prospect sells cloud security).

---

## Step 1 — Resolve via Onfire `match_company` (always run, regardless of input shape)

The skill operates on a canonical **domain** throughout. Resolve to that first using Onfire's `match_company` tool (Matchbox2 engine — vector search + AI matching). This makes names, fuzzy spellings, and partial inputs first-class — no need to ask the BDR for a domain.

### 1a — Build the match_company input

Map whatever the BDR typed into the right signal field:

```python
match_company(companies=[
    {
        "names": [<raw_input>] if input looks like a company name,
        "websites": [<normalized_domain>] if input looks like a domain or URL,
        "linkedin_urls": [<linkedin_url>] if input is a LinkedIn URL
    }
])
```

If the BDR clearly gave you **two signals at once** (e.g. "Datadog (datadoghq.com)"), put **both** in the same entry under `names` and `websites` — Matchbox2 produces materially better matches with multiple signals.

URL normalization for the `websites` field: strip protocol, path, query, `www.`, trailing slash → bare host (`https://www.wiz.io/platform` → `wiz.io`).

### 1b — Inspect the result

You get back:
```
matched: true/false
website: "datadoghq.com"
linkedin_url: "https://linkedin.com/company/datadog"
linkedin_id: "..."
size: "5001-10000"
found_employee_count: 7842
cosine_similarity: 0.94
match_type: "semantic_match"
match_reason: "..."
```

Three branches:

- **`matched: true` and `cosine_similarity >= 0.85`** → high confidence. Use `website` as the canonical `prospect_domain`. Cache `linkedin_url` and `size` for later (Step 7 uses size for enterprise-escalation; the LinkedIn URL is useful for the LinkedIn-bucket dataset query).

- **`matched: true` but `0.6 <= cosine_similarity < 0.85`** → confirm with the BDR before proceeding. One inline message:
   > *"I think you mean <returned name> (<returned website>) — confirm or did you mean something else? (e.g. apollo.io the sales tool vs apollographql.com the GraphQL platform)"*

- **`matched: false`, or `cosine_similarity < 0.6`, or `match_reason` flags it weak** → stop and ask the BDR. Do NOT proceed with low-confidence identity — wrong prospect resolution corrupts every downstream signal.

### 1c — Library lookup (keyed on the resolved domain)

Now with `prospect_domain` in hand, read sibling `icp_library.json`:
- Match `prospect_domain` against top-level keys
- If no exact match, scan `aliases` arrays for a hit
- **If found**, use the stored `category`, `competitors`, `category_keywords`, and `seller_indicators`.

### 1d — If not in library, derive on the fly

- WebSearch `"<prospect_domain> competitors 2026"` and `"<prospect_domain> product category"`. Searching the domain (rather than the bare name) returns the company's own product pages first — cleaner category read.
- Extract 5-15 competitor names (well-known vendors only — ignore generic categories like "open source tools").
- Identify the product category in 3-6 words (e.g. "Cloud security / CNAPP", "Code SAST / AppSec").
- List 4-8 `category_keywords` people in this market actually use in Slack/Reddit (e.g. CNAPP, CSPM, K8s security, AI-SPM).
- List 2-4 `seller_indicators` — product names or branded features only the prospect owns (used to filter out praise and current-customer signals).
- Append the derived profile to `icp_library.json` keyed on `prospect_domain` — **and include the `linkedin_url`, `name`, and `size` fields returned by `match_company` so the next BDR gets richer cached context.**

### 1e — Cache match_company output across the run

Carry these fields from the match_company response through the rest of the skill:

| Field | Used later in |
|---|---|
| `website` (→ `prospect_domain`) | Step 3 self-drop filter, library key |
| `linkedin_url` | Step 4 LinkedIn-posts dataset query (filter by company LinkedIn ID) |
| `linkedin_id` | Step 4 (preferred over URL string match) |
| `size` / `found_employee_count` | Step 8 enterprise-escalation rule (>10K employees → escalate to AE, never cold-outreach) |
| `name` | Output header ("Demo signals for <name>") |

---

## Step 2 — Discover the signals table

Do not hardcode table IDs.

```
metabase:search(term_queries=["signals"])
```

Pick the table whose `name` is exactly `signals` (Postgres engine, most recently updated). Then:

```
metabase:get_table(id=<table_id>, with-fields=true)
```

Cache field IDs for: `signal_type`, `short_summary`, `message_text` (if present), `account_website`, `date`, `source_type`, `source_name`, `source_link`, `name`, `intent_holder_linkedin_url`, `tenant_id`.

---

## Step 3 — Pull candidate signals from Metabase

Run these queries in parallel. Date filter: `date >= today - lookback_months`.

**Query A — one per competitor name** (loop the `competitors` list):

```
metabase:query(
  table_id=<id>,
  fields=[signal_type, short_summary, message_text, account_website, date,
          source_type, source_name, source_link, name, intent_holder_linkedin_url],
  filters=[
    {field_id: <date>, operation: "greater-than-or-equal", value: "<today minus lookback>"},
    {field_id: <short_summary>, operation: "string-contains", value: "<competitor_name>"}
  ],
  order_by=[{field_id: <date>, direction: "desc"}],
  limit=25
)
```

**Query B — shopping-pattern queries** (`alternative`, `switching from`, ` vs `, `evaluating`):

Same query shape, swap the value. After fetching, **post-filter in code**: keep only rows whose `short_summary` *also* mentions at least one item from `competitors` or `category_keywords`. This kills off-topic noise (Drizzle vs Prisma ORM, VS Code vs JetBrains, etc.).

**Prefer `message_text`** for filtering and evidence when the field is present and non-empty. Fall back to `short_summary` otherwise. Never paraphrase — quote verbatim (you may trim with `…`).

---

## Step 4 — Enrich the LinkedIn slot via Onfire MCP

LinkedIn buying-intent signals are sparse in the Metabase table. Augment from Onfire MCP. The LinkedIn slot is **strict**: the post or comment must explicitly name a competitor in a comparison context. Hiring posts and leadership-move signals do **NOT** qualify for this slot.

1. `onfire:list_datasets()` — find any dataset that looks like LinkedIn-sourced posts or comments (look for `linkedin`, `posts`, `comments`, `social` in dataset names/descriptions).
2. `onfire:describe_dataset(dataset_id=<id>, sample_rows=5)` — confirm columns and platform tagging.
3. `onfire:query_datasets(dataset_id=<id>, ...)` filtered to:
   - Post/comment dated in the lookback window
   - Text contains any competitor name
   - Source platform = LinkedIn (or whatever the dataset's platform column calls it)
   - **Exclude posts from anyone employed at the prospect's company** — use the `linkedin_id` cached from Step 1's `match_company` response to filter out the prospect's own employees posting praise / launches / partner news
4. If Onfire MCP returns nothing relevant, fall back to Metabase rows where `source_type` matches `Linkedin` / `LinkedIn` / `linkedin` AND `short_summary` contains a competitor name AND `signal_type = High Intent`.
5. If **still** nothing qualifies, do **not** silently substitute from Slack. Surface "No qualifying LinkedIn signal in the last N months" inline in the output and offer to widen the window or accept a hiring-post fallback.

---

## Step 5 — Filter, dedupe, score

**Drop** a candidate if any of:

- `account_website` equals `prospect_domain` exactly. (This is why domain-first matters — the Metabase signals table uses `account_website` as its account key, so an exact-match drop is reliable.) Also drop if it matches any entry in the library's `aliases` array for this prospect.
- **Account looks like an existing customer of the prospect** (see "Net-new only" section above). Run the possessive / first-person-plural check on every candidate before scoring. When in doubt, drop.
- Any `seller_indicators` entry appears in the signal text **and** the surrounding sentiment is positive ("love", "great", "winning", "best", "switched to"). Use judgment — if it's clearly praise of the prospect, drop it.
- The "vs" / "alternative" match doesn't actually involve the prospect's category. Re-check that at least one item from `competitors` or `category_keywords` is in the text.
- Duplicate by `(account_website, date, first 60 chars of evidence)` — keep the row with the richest `message_text` and the most recent date.

**Score** the remaining rows:

| Pattern | Score |
|---------|-------|
| Explicit "X vs Y" between two of the prospect's competitors | 10 |
| "Looking for alternative to X" / "Switching from X" | 9 |
| Named-incumbent dissatisfaction ("X failed to…", "X tripled pricing", "lost confidence in X") | 8 |
| Multi-competitor sprawl (3+ named competitors complained about together) | 7 |
| Evaluation of one competitor with intent language ("trialing X for…", "is X worth the cost") | 5 |
| Hiring post that explicitly names competitors (LinkedIn fallback only) | 3 |

---

## Step 6 — Bucket and pick

Buckets:

- **Slack / Discord** (treat as one — both are practitioner community chats): `source_type in ('Slack', 'Discord')`
- **Reddit**: `source_type = 'Reddit'`
- **LinkedIn (strict)**: only signals that passed Step 4

Pick the **highest-scoring** signal from each required bucket. Fill remaining slots up to `count` from the highest-scored leftovers across all buckets.

If a required bucket is empty after Step 5, **say so explicitly** in the output — do not pad.

---

## Step 7 — Public-company 10-K enrichment (auto, silent for private)

For each of the 3-5 signals that survived Step 6, try to enrich the BDR talking point with **one short, verbatim quote from the account's latest SEC 10-K**. When the account is a public US company, this gives the AE a board-level talking point on top of the practitioner signal. The enrichment is fully automatic:

- **Public US company** → 10-K quote appears as an italic line beneath the talking point.
- **Private company / foreign-listed / pre-IPO** → no 10-K, no mention, no padding.
- **Snowflake unavailable** → entire step is skipped silently; the rest of the output is unaffected.

Run the per-signal 10-K lookups **in parallel** to keep latency down.

### 7a — Check `is_public`

For each signal's `account_website`:

```sql
SELECT website, name, ticker, cik, is_public
FROM gold.entities.organizations
WHERE website = '<account_website>'
LIMIT 1
```

If `is_public IS NULL`, `false`, or the row is missing — skip this account's 10-K step. Move on to the next signal.

### 7b — Pull the latest 10-K (only if public)

```sql
SELECT
  COMPANY_NAME,
  TICKER,
  FILING_TYPE,
  FILING_DATE,
  FULL_MARKDOWN
FROM bronze.edgar_reports.edgar_latest_view
WHERE website = '<account_website>'
  AND FILING_TYPE = '10-K'
ORDER BY FILING_DATE DESC
LIMIT 1
```

If zero rows, skip — many non-US public companies (UK-listed, Frankfurt-listed, ADR-only, etc.) don't file with the SEC and that's expected.

### 7c — Extract one relevant snippet

Inside `FULL_MARKDOWN`, target the 10-K section most relevant to the prospect's `category` and `category_keywords`:

| Prospect category | 10-K section to target | Keyword anchors to search inside |
|---|---|---|
| Cloud security / CNAPP / AppSec | Item 1A Risk Factors | `cyber`, `cybersecurity`, `data breach`, `cloud`, `third-party`, `supply chain` |
| Observability / APM / logs | Item 7 MD&A or Item 1A Risk Factors | `infrastructure`, `cloud spend`, `operational efficiency`, `reliability`, `incident` |
| AI / ML platforms / data | Item 1 Business or Item 1A Risk Factors | `AI`, `artificial intelligence`, `machine learning`, `model risk`, `LLM` |
| Identity / IAM / PAM | Item 1A Risk Factors | `unauthorized access`, `privileged`, `credential`, `identity` |
| FinOps / cloud cost | Item 7 MD&A | `cloud cost`, `infrastructure spend`, `operating expenses`, `cost optimization` |
| Default fallback | Item 1A Risk Factors | use the prospect's `category_keywords` array directly |

Pick the **single shortest verbatim sentence (or two-sentence span)** that contains a keyword anchor and is recognizably about the prospect's category. You may trim with leading/trailing `…`, but **never paraphrase**. Max 250 characters in the trimmed span. If nothing in the 10-K matches the category, skip this signal's enrichment — do not force a bad quote.

### 7d — Embed in the BDR talking point

Append a single italic line directly under the existing `*BDR talking point:*` line, using this format:

```
*10-K context (FY<filing year>, <ticker>):* "<verbatim trimmed snippet>"
```

Example for a Verisk signal when prospect = Datadog:

```
*BDR talking point:* Verisk's listed obs stack is Splunk + Dynatrace — no Datadog. Hiring an SRE whose JD names your two biggest competitors.
*10-K context (FY2024, VRSK):* "…cybersecurity threats and operational disruptions to our cloud infrastructure could materially impact our ability to deliver analytics services to customers…"
```

That single quote turns a practitioner-level signal into something the AE can quote to a CFO.

---

## Step 8 — Output (chat only)

The output is built for a BDR to scan in under 15 seconds and know **(a) what the signal is** and **(b) what to do next**. Card layout, blockquotes for any verbatim text, numbered concrete actions, paste-ready openers.

### Top header (once per run)

```
# Demo signals for <Prospect>

<count> net-new buying-intent signals from the last <lookback> months.

**Scan covered:** <competitor list separated by " · ">
**Source mix:** Slack/Discord <✓ or ✗> · Reddit <✓ or ✗> · LinkedIn <✓ or ✗ — with one-word caveat if weak>
```

### One card per signal (this exact structure)

```
---

## Signal N of <total> — <Slack | Discord | Reddit | LinkedIn>

**Account:** <Company name> (<domain>)<optional qualifier in italics: *public (TICKER)*, *Fortune 100*, *EU-based enterprise*, etc.>
**Where:** <community name with one-line context, e.g. "DataHub Slack (open-source data catalog community)">
**Posted:** <YYYY-MM-DD>
**Why this is in the list:** <one sentence, ≤25 words, says why the account is a net-new fit>

**What they said**
> "<verbatim short_summary or trimmed message_text>"

[Open the <Slack | Reddit | LinkedIn | Discord> thread](<source_link>)

**Your move — <estimated minutes, e.g. "5 minutes">**
1. <first concrete action>
2. <second concrete action>
3. Send this opener:
   > *"<paste-ready opener — 1-2 sentences, ends with a specific meeting ask>"*
```

### Optional 10-K block (only if Step 7 produced a snippet)

Append immediately under `Your move` for that signal, no blank line between:

```
**Bonus context (auto-pulled from <TICKER>'s 10-K, FY<year>)**
> "<verbatim trimmed 10-K snippet>" — *gives the AE a CFO-level talking point.*
```

Omit the entire block if there's no snippet. Never write "(no 10-K)" placeholders.

### Enterprise-escalation rule

If the account is Fortune 500 / Global 2000 / otherwise too senior for cold BDR outreach (>10K employees, public mega-cap), the `Your move` block **must** explicitly:
- Tell the BDR to forward to the enterprise AE: "Forward this to your enterprise AE covering <vertical>. **Do not cold-outreach yourself.**"
- Provide the AE-level talking point in the same numbered list rather than a BDR opener.

### Bottom triage section (once per run)

```
---

# What to do with this list

- **Top priority right now:** Signals <list> (fresh, personalized openers ready to send).
- **Forward to enterprise team:** Signals <list> (warm-intro required, no cold BDR outreach).
- **Add to CRM as account-tier signals:** Signals <list> (softer intent — hiring posts, multi-vendor stacks).

Want me to enrich these accounts with verified buyer emails, push them into your sequencer, or queue them as a live artifact you can re-open each morning?
```

### Style rules (enforce strictly)

- **Blockquotes (`> "…"`) are reserved for verbatim text only** — the signal text from the source, the 10-K snippet, and the paste-ready opener (which is in italics inside the quote). Never paraphrase what the prospect said.
- **Action steps are numbered, concrete, time-boxed.** Each step ≤20 words. No vague verbs like "consider" or "think about."
- **Openers are paste-ready.** 1-2 sentences, reference the signal directly, end with a specific meeting ask ("20 min next week?").
- **No Onfire infrastructure names anywhere** in the BDR-facing output. Say "intent feed" or "buying-intent stream" — never "Metabase", "Snowflake", "signals table", "Onfire MCP".
- **No emojis** in the output unless the prospect's culture explicitly uses them (rare; default off).
- **Account qualifiers go in italics next to the domain.** Examples: *public (NYSE: TRV)*, *Fortune 100*, *EU-based mid-market*, *AI-native startup*.
- **The "Why this is in the list" line is the BDR's at-a-glance.** It must answer "why this account, why now" in one line, no padding.

### Skip-the-card scenarios

If a bucket (Slack/Discord, Reddit, LinkedIn) had zero qualifying signals after Step 5 + 6, do **not** create a card with a fake signal. Instead, in the top header line for that bucket, mark it `✗` and add a one-line note **just under the source mix line**:

```
**Note:** No qualifying LinkedIn signal in the last <lookback> months — widen window or accept a hiring-post fallback?
```

### Opener style

The paste-ready opener in step 3 of every card is the most important text in the output — it's what determines whether the BDR sends or doesn't. Style rules:

- **First sentence references the signal directly.** Names the source community, the topic, sometimes the year. ("Saw your r/dataengineering thread on Iceberg zero-copy cloning…")
- **Second sentence ties it to the prospect's product.** One short clause, no jargon. ("Polaris ships this natively.")
- **End with a specific meeting ask.** Time-bounded, low-commitment. ("20 min next week?" / "30 min with our principal architect?")
- **Length:** 1-2 sentences, ≤45 words total.
- **Voice:** practitioner-to-practitioner, not vendor-to-buyer. Skip "synergize", "leverage", "in alignment with your strategic priorities".

Three reference openers for different buckets:

- *Reddit, individual practitioner:* "Saw your r/dataengineering thread on Iceberg zero-copy cloning. Polaris does this natively — happy to show you the 5-line version of what you're hand-rolling. 20 min next week?"
- *Slack community, mid-market account:* "Saw your S3 vs Delta vs Iceberg question on the OpenMetadata Slack. If Iceberg is the direction, Polaris is an Iceberg-native catalog that ships with the warehouse — 20-min architecture walkthrough?"
- *LinkedIn hiring post, enterprise account:* "Saw Guidewire is hiring to optimize Redshift + EMR + Glue + Spark cost. Snowflake customers your size typically see 30-50% TCO reduction on the same workload — 30 min with our insurance vertical lead?"

**Never** name internal infrastructure (Metabase, Snowflake the connector, Onfire MCP, signals table, EDGAR, etc.) in the BDR-facing output. Use phrases like "intent feed", "buying-intent stream", "what Onfire would have surfaced".

---

## Error handling

| Situation | Action |
|-----------|--------|
| `match_company` returns `matched: false` | Ask the BDR for a domain or LinkedIn URL — do not guess |
| `match_company` returns `0.6 ≤ cosine_similarity < 0.85` | Confirm with BDR inline ("I think you mean X — yes / no?") before proceeding |
| `match_company` returns multiple plausible candidates with overlapping similarity | Surface both, ask BDR to pick |
| `match_company` not available (Onfire MCP not connected) | Fall back to: treat input as already-canonical if it looks like a domain; otherwise WebSearch `"<input> official website"` and use top result |
| Prospect not in library AND web search yields no clear competitors | Ask the BDR inline to paste 3-5 competitor names, then continue |
| Metabase signals table not found | Halt; report that the intent feed is disconnected |
| 0 candidate signals after filtering | Widen lookback to 2x and rerun once; if still 0, return "No demo-quality signal this period — widen to <X> months or pick a different prospect" |
| LinkedIn bucket empty after Step 4 | Note it inline; offer hiring-post fallback or wider window — never silently fill from Slack |
| Onfire MCP not connected | Skip Step 4's MCP queries; rely on Metabase LinkedIn rows only |
| Snowflake not connected | Skip Step 7 entirely and silently; deliver signals without 10-K context. Do not mention Snowflake to the BDR |
| `gold.entities.organizations` returns no row for an account | Treat account as private; skip 10-K for that signal only |
| Public company but no 10-K in `edgar_latest_view` | Skip 10-K for that signal only (typical for foreign-listed) |

---

## Sibling file

`icp_library.json` — curated prospect profiles. **Primary key is the prospect's domain.** Schema:

```json
{
  "<prospect_domain>": {
    "name": "Human-readable name",
    "linkedin_url": "https://linkedin.com/company/...",
    "linkedin_id": "...",
    "size_band": "5001-10000",
    "aliases": ["alternate spellings", "common shorthands"],
    "category": "...",
    "category_keywords": ["...", "..."],
    "competitors": ["...", "..."],
    "seller_indicators": ["...", "..."]
  }
}
```

`linkedin_url`, `linkedin_id`, and `size_band` come from the `match_company` response in Step 1 — they make subsequent runs faster (skip the match_company round-trip on a cache hit) and richer (the size band drives the enterprise-escalation rule in Step 8).

The library is seeded with `wiz.io` and `datadoghq.com`. Append new entries as they're derived — that's how the library grows and the next BDR gets a faster lookup. Always key on the resolved `prospect_domain`, never on the bare name.
