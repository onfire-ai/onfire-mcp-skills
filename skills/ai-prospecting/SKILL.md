---
name: ai-prospecting
description: Run AI prospecting against a target company (rank likely buyers/champions) or score a single named person at a company using the Onfire `ai_prospecting` tool. Use when the user wants prospects for an account, a ranked list of who to talk to, a score on a specific person ("is X worth a meeting"), or a batch run across multiple companies. Covers both `action='run'` and `action='get_prospect'`, the dataset-backed response and how to query it, the polling pattern for long runs, and the shadow-schema test mode.
---

# ai_prospecting (atomic)

Phoenix is the prospecting engine. This tool either ranks prospects for a company (`action="run"`) or scores one named person at a company (`action="get_prospect"`).

## When to use this

- The user wants buyers / champions / a "who should I talk to" list at a company.
- The user names a person and asks if they're worth pursuing → `action="get_prospect"`.
- A batch run across many companies (still uses `action="run"`).

Don't use this for identity resolution alone (use `match-company` / `match-person`) or for emails / phones (use `contact-data-enrichment`).

## Inputs you need first

Both actions require a **company LinkedIn URL**. `get_prospect` also requires a **person LinkedIn URL**.

If you don't have them, run the upstream atomic first:
- Missing company LinkedIn → `match-company`.
- Missing person LinkedIn → `match-person` (it usually returns the company LinkedIn URL too — reuse it).

## action="run" — rank prospects for a company

Pass either a single URL or a batch list.

```python
# Single company
ai_prospecting(action="run", company_linkedin_url="https://linkedin.com/company/datadog")

# Batch
ai_prospecting(action="run", linkedin_urls=[
    "https://linkedin.com/company/datadog",
    "https://linkedin.com/company/snowflake",
    ...
])
```

`linkedin_urls` (list) takes precedence over `company_linkedin_url` (single) when both are passed.

**Optional flags:**
- `use_cache=True` — let Phoenix return cached results from a recent identical run instead of recomputing. Use only when it's clearly a re-run of something already executed in this conversation. Default `False`.
- `activate_shadow_run=True` — run against the caller's shadow schema instead of the live team schema. Use when the user is iterating on schema config via `manage-ai-prospecting`. Default `False`. **404 from this means there is no shadow yet — call `create_shadow` first via `manage-ai-prospecting`.**

## action="get_prospect" — score one person

```python
ai_prospecting(
    action="get_prospect",
    company_linkedin_url="https://linkedin.com/company/snowflake",
    person_linkedin="https://linkedin.com/in/lana-patel"
)
```

Both URLs required. `linkedin_urls`, `use_cache`, and `activate_shadow_run` don't apply here.

## The polling pattern (don't skip this)

Phoenix runs can take a few minutes. The MCP server polls Phoenix internally and may return:

```json
{"status": "still_running", "message": "...", "companies": ["..."]}
```

When you see this, **call the tool again with identical arguments**. Keep calling until you get a `status="completed"` payload back. The server deduplicates — you will not trigger a duplicate run by retrying. Don't change arguments between polls (changing them will look like a new request).

## Output shape (action="run", completed)

A completed run returns a **dataset handle plus agent-facing accelerators** — not the full prospect list inline. The whole prospect set is persisted as a short-lived MCP dataset (auto-expires); the tool response is intentionally compact so it never blows past the per-tool output token budget, even for large batch runs.

**The response is self-describing — but the full contract lives outside the response by default.** Every completed-run payload includes:

- `field_index` — the sorted list of every field name documented in the glossary. This is your **safety-net check**: if every field you encounter in the response is in `field_index`, you already have the contract loaded; if you see something new, the schema has evolved and you should re-fetch.
- `field_glossary_resource_uri` — pointer to the full glossary (`onfire://ai_prospecting/field_glossary`).
- `field_glossary` — only present when the caller passed `include_field_glossary=True` on the call (legacy path; see below).

The full glossary (~12 KB JSON) is reachable three ways, all backed by the same in-memory dict so they never drift:

1. **`ai_prospecting_field_glossary` tool** (recommended). Zero-argument MCP tool that returns the glossary JSON. Call it once before — or right after — your first `ai_prospecting` run this conversation. Works on every MCP client.
2. **As an MCP resource** at `onfire://ai_prospecting/field_glossary`. MCP clients that support resource injection (auto-loading server-attached metadata into the agent's context at session start) will pick this up automatically — you'll see the contract in your available context without making any explicit call.
3. **Legacy inline opt-in** via `include_field_glossary=True` on an `ai_prospecting` call. Still supported for backward compatibility but no longer the preferred path — it couples glossary fetching to a run call, which makes it awkward when you want the contract *before* deciding what to run. Prefer `ai_prospecting_field_glossary` instead.

**Decision tree for the agent:**

```
Is the glossary already in your context (resource auto-loaded by the host)?
├── Yes  → proceed normally; rely on field_index to detect drift
└── No   → call ai_prospecting_field_glossary() ONCE this conversation.
           After that, omit the call and rely on field_index to confirm
           nothing new appeared.
```

The content is byte-stable within a server version, so re-fetching mid-conversation is pure waste. One call per conversation is the cap.

**The glossary is the source of truth for field semantics; this skill is the playbook for using them.**

```json
{
  "status": "completed",
  "dataset": {
    "id": "ds_abc123…",
    "source": "ai_prospecting",
    "row_count": 42,
    "columns": ["FULL_NAME", "LINKEDIN_URL", "TITLE_NAME", "MASTER_SCORE_PRIORITY", "MASTER_SCORE_REASON", "SCORE_WARM_INTRO", "WORKED_IN_CLIENT_COMPANY_IN_PAST", "CONNECTING_EMPLOYEE_NAME", "product_talking_points", "ai_reasoning", "..."],
    "schema": [{"name": "FULL_NAME", "type": "string"}, ...],
    "created_at": "...",
    "expires_at": "...",
    "facets": { "MASTER_SCORE_PRIORITY": {"1": 38, "2": 4}, "SCORE_WARM_INTRO": {"PLATINUM": 15, "GOLD": 4, "COLD": 23}, ... }
  },
  "top_picks": [ /* slim "start here" top 3, ranked by Phoenix's rank_position */ ],
  "priority_summary": {
    "tier_1_prospects": 38,
    "platinum_warm_intros": 15,
    "gold_warm_intros": 4,
    "existing_customer_alumni": 5,
    "with_named_connector": 39,
    "tech_champions": 1
  },
  "preview_rows": [ /* up to 5 already-projected full prospect rows, scored order */ ],
  "facets": { "MASTER_SCORE_PRIORITY": {...}, "SCORE_WARM_INTRO": {...}, "WORKED_IN_CLIENT_COMPANY_IN_PAST": {...}, "prospect_tags": {...}, "CURRENT_PERSONAS": {...}, "COMPANY_LINKEDIN_URL": {...} },
  "total_prospects": 67,
  "filtered_prospects": 42,
  "ranking_method": "individual",
  "message": "Full AI prospecting results (42 prospect(s)) are available via query_datasets / describe_dataset using dataset_id='ds_abc123…'. Use top_picks for a ranked \"start here\" subset and priority_summary for the tier distribution at a glance."
}
```

### top_picks (lead with this)

Slim top-N projection ranked by Phoenix's canonical `rank_position` (which already weights warm-intro tier above raw composite — a PLATINUM direct-alumni connection outranks a higher-composite GOLD). Each top-pick row carries only the prioritization-driving fields:

- `FULL_NAME`, `TITLE_NAME`, `LINKEDIN_URL`
- `MASTER_SCORE_PRIORITY` (tier 1/2/3 — lower is higher priority)
- `MASTER_SCORE_REASON` (human-readable why — e.g. "TIER 1: PLATINUM warm intro (direct alumni)")
- `SCORE_WARM_INTRO` (`PLATINUM` / `GOLD` / `COLD`)
- `CONNECTING_EMPLOYEE_NAME` + `SHARED_COMPANY` (the warm-intro path)
- `WORKED_IN_CLIENT_COMPANY_IN_PAST` (alumni flag)
- `prospect_tags`
- `product_talking_points` (Phoenix's pre-written, product-keyed openers — use these directly)

The heavy `ai_reasoning` blob is NOT in top_picks — it's in `preview_rows` and the dataset. Top_picks is sized for "lead with these three" framing.

### priority_summary (the BDR-facing lede)

Pre-computed count histograms that let you write the one-line summary without re-reading every row. Paraphrase naturally, e.g. "5 PLATINUM warm intros and 5 alumni — start there." All values are integers.

### preview_rows (the full sanity-check sample)

Up to 5 full projected prospect rows in scored order. This is what you render after the top_picks lede when the user wants to see the next few without a dataset round-trip.

### Full projected field set

Each prospect row in the dataset (and in `preview_rows`) carries the broad field set Phoenix actually computes — identity, ranking + tier, persona classification, warm-intro path, signals + ready-made talking points, career momentum, narrative reasoning, and filter transparency. Notable named fields:

| Group | Fields |
|---|---|
| Identity | `FULL_NAME`, `LINKEDIN_URL`, `TITLE_NAME`, `HEADLINE`, `LOCATION_COUNTRY`, `LOCATION_REGION`, `COMPANY_NAME_DISPLAY`, `COMPANY_LINKEDIN_URL` |
| Ranking + tier | `rank_position`, `MASTER_SCORE_PRIORITY`, `MASTER_SCORE_REASON`, `AUTHORITY_SCORE`, `COMPOSITE_SCORE`, `SCORE_BUYER`, `SCORE_TECH_CHAMPION`, `SCORE_RECEPTIVENESS`, `SCORE_URGENCY`, `SCORE_WARM_INTRO` |
| Persona | `CURRENT_PERSONAS`, `prospect_tags`, `RELEVANT_IC` |
| Warm-intro path | `WORKED_IN_CLIENT_COMPANY_IN_PAST`, `TITLE_AT_CLIENT_COMPANY`, `PAST_COMPANIES_USED_CLIENT_TECH`, `CONNECTING_EMPLOYEE_NAME`, `SHARED_COMPANY`, `CONNECTION_STRENGTH_SCORE` |
| Signals + outreach payload | `signals`, `events`, `product_talking_points`, `PROSPECT_CURR_CLIENT_TECH_TEXT` |
| Career momentum | `MONTHS_SINCE_LAST_PROMOTION`, `BUDGET_MANAGEMENT_EXPERIENCE` |
| Narrative | `ai_reasoning`, `relevancy_reasoning` |
| Filter transparency | `should_filter_reason` |

**Don't promise fields outside this set** — no emails, no phones, no full tenure history. If the user asks for emails/phones, that's `contact-data-enrichment`.

If Phoenix returns zero prospects the response is the same shape with `dataset: null`, `top_picks: []`, `priority_summary: {}`, and `preview_rows: []`.

`failed_companies` (always present on `action="run"`) is a list of any company URLs that failed during the batch fan-out — each entry has `linkedin_url`, `error`, and `status_code` (when the failure came back as an HTTP error from Phoenix). On a fully-successful run it's `[]`. If the user passed N URLs and some are listed here, mention them — those companies were *not* prospected. If every URL failed, the tool returns `status="error"` with the same `failed_companies` list and no dataset.

## Working with the dataset

The full ranked list lives in the dataset, not in `preview_rows`. Use the dataset companion tools to inspect or slice it without paying its context cost:

- **`describe_dataset(dataset_id)`** — schema + a head sample. Good first call before writing SQL.
- **`query_datasets({alias: dataset_id}, sql, row_limit=N)`** — read-only DuckDB SQL against the dataset. Filter, count, slice, or pull a specific page.
- **`download_dataset(dataset_id)`** — mint a short-lived URL the user can click to download the dataset as CSV. Use whenever the user asks for the file ("send me the CSV", "download the results", "export this", "give me the spreadsheet"). Surface the returned `download_url` directly in the chat — that link IS the deliverable.
- **`list_datasets()`** — surface earlier datasets from this conversation (e.g. to compare a live run vs a shadow run).

Useful patterns:

```python
# Top 20 prospects, ranked
query_datasets(
    datasets={"p": "ds_abc123"},
    sql="SELECT * FROM p LIMIT 20",
    row_limit=20,
)

# Just US-based engineering leads
query_datasets(
    datasets={"p": "ds_abc123"},
    sql="""
        SELECT FULL_NAME, TITLE_NAME, LINKEDIN_URL, ai_reasoning
        FROM p
        WHERE LOCATION_COUNTRY = 'US'
        AND TITLE_NAME ILIKE '%engineer%'
        LIMIT 50
    """,
    row_limit=50,
)

# How are prospects spread across companies in a batch run?
query_datasets(
    datasets={"p": "ds_abc123"},
    sql="""
        SELECT COMPANY_LINKEDIN_URL, COUNT(*) AS prospect_count
        FROM p
        GROUP BY COMPANY_LINKEDIN_URL
        ORDER BY prospect_count DESC
    """,
)
```

`facets` on the response are pre-computed distribution counts over the prioritization-driving dimensions: `MASTER_SCORE_PRIORITY` (tier histogram), `SCORE_WARM_INTRO` (PLATINUM/GOLD/COLD counts), `WORKED_IN_CLIENT_COMPANY_IN_PAST` (alumni count), `prospect_tags` (which product/category tags appear), `CURRENT_PERSONAS` (persona match distribution), and `COMPANY_LINKEDIN_URL` (per-company breakdown for batch runs). Use these for quick "what's the shape of this run?" answers without a `query_datasets` round-trip. **Location facets were intentionally removed** — `LOCATION_COUNTRY`/`LOCATION_REGION` are still per-row fields in the dataset but aren't what a BDR prioritizes on; if a user really wants a geographic breakdown, run `query_datasets` with `GROUP BY LOCATION_COUNTRY`.

## Output shape (action="get_prospect")

A single scored prospect record returned **inline** (no dataset — it's just one row). Same trimmed field set as the run dataset, plus the AI score and reasoning for that person specifically.

## The bold sentinel — convert before display

`ai_reasoning` strings contain `$$-onfire-bold-$$` markers around emphasized phrases. **Convert each pair to markdown `**bold**` before showing the user.** Left as-is they look like a rendering bug. The conversion applies to `preview_rows`, to rows pulled via `query_datasets` / `describe_dataset`, and to `get_prospect` responses.

```
"This is a $$-onfire-bold-$$strong fit$$-onfire-bold-$$ because..."
→ "This is a **strong fit** because..."
```

## Default rendering

The response gives you four ranked layers — use them in this order. Flat-dumping `preview_rows` as a list is the failure mode; that's what generic contact-database tools produce. Onfire's edge is pre-computed prioritization, so the rendering must lead with it.

### Step 1 — Open with the priority_summary lede (one line)

Paraphrase `priority_summary` into a single BDR-facing sentence before any list. Examples:

> "5 PLATINUM warm intros and 5 alumni connections to start with — out of 42 total prospects."
> "No warm intros on this run, but 3 prospects scored as true tech champions."
> "All 20 are tier-1; warm-intro paths skew GOLD (15) vs. PLATINUM (5)."

Pick whichever count is highest-signal for the run. Order of preference: `existing_customer_alumni` > `platinum_warm_intros` > `gold_warm_intros` > `tech_champions` > `tier_1_prospects`. If everything is zero, just give the total count.

### Step 2 — Render top_picks as the "start here" ranked list

For each row in `top_picks` (typically 3), render:

- **Name as a link to `LINKEDIN_URL`** — first line
- **Title** — second line
- **The why** — paraphrase `MASTER_SCORE_REASON` into one line. Examples:
  - `"TIER 1: PLATINUM warm intro (direct alumni)"` → "Direct Fortinet alumni, PLATINUM warm-intro path."
  - `"TIER 1: GOLD warm intro + strong credentials (tech:398, buyer:80.0)"` → "GOLD warm intro plus strong technical credentials."
  - `"TIER 1: True tech champion (tech:501, relevant_ic:RELEVANT)"` → "True tech champion — high technical score, relevant IC."
- **Warm-intro path if any** — "Connect via `CONNECTING_EMPLOYEE_NAME` (shared `SHARED_COMPANY`)." Skip if `CONNECTING_EMPLOYEE_NAME` is empty.
- **Alumni callout if `WORKED_IN_CLIENT_COMPANY_IN_PAST=TRUE`** — "Former employee of your company — start here for an expansion conversation."
- **Suggested opener** — pull one talking point from `product_talking_points` (it's a dict keyed by product line, take the first value of the first key). Phoenix already wrote the opener; you don't need to invent one.

### Step 3 — Mention the rest of preview_rows + the dataset

After the top_picks block, briefly note that `preview_rows` carries the next few in scored order, and that the full `filtered_prospects` count is in the dataset (`dataset_id`). Don't render preview_rows row-by-row unless the user explicitly asks — top_picks already gave them the prioritized lede, so a flat dump is redundant.

### Step 4 — Make the enrichment + download offers (next section)

These are still required after every run. See below.

### Multi-company / batch runs

The same four-step flow applies, but the lede should mention per-company spread when relevant ("12 prospects across 3 accounts; the alumni connections cluster at Acme"). For a per-company breakdown, the `COMPANY_LINKEDIN_URL` facet has the counts; for full grouping, `query_datasets` with `GROUP BY COMPANY_LINKEDIN_URL`.

### Long lists / pagination

Pull additional pages via `query_datasets({"p": dataset_id}, "SELECT * FROM p ORDER BY rank_position LIMIT N OFFSET K")` — note the explicit `ORDER BY rank_position` so pagination respects Phoenix's canonical order. If the user wants the file rather than a paged view, call `download_dataset(dataset_id)` and surface the returned `download_url` — that's the canonical CSV. For a download of just a slice (e.g. "top 50 by score"), run the slice through `query_datasets(..., persist_as_dataset=True)` first to get a new `dataset_id`, then `download_dataset` on that.

## The enrichment offer (required, not optional)

After **every** run — single, batch, get_prospect, no matter what — tell the user they can pull verified emails and phones for any of the returned prospects. Not just the top N you displayed in `preview_rows`; **all** of them are available to enrich. Most of the workflow's value is downstream of contact data, and users frequently assume contact data is gated to whatever's on screen.

Phrase it naturally:

> "I can pull verified emails and phone numbers for any of these — top 5, all 42, or a subset you pick. Just say which."

The dataset_id from the run can be passed straight to `contact_data_enrichment(dataset_id="ds_…", ...)` to enrich the entire run set without rebuilding contact dicts; for a custom subset, build dicts from the rows the user picked. See `contact-data-enrichment`.

This is part of the playbook, not a polite extra.

## The download offer (also required)

In the same breath as the enrichment offer, mention they can grab the full ranked list as a CSV. Most users want the file — `preview_rows` is a smell test, not the deliverable.

> "I can also send you the full <total>-row CSV — say the word and I'll drop a download link."

If the user already asked for a file (any phrasing — "send", "export", "download", "give me the spreadsheet"), skip the offer and just call `download_dataset(dataset_id)`. Surface the returned `download_url` directly. The link is short-lived (default 1 hour, max 24 hours), so don't sit on it.

## Hard rules

- **Never pass `target_tenant_id`.** Tenant comes from OAuth. The override is super-tenant only and will error for everyone else.
- **Polling is mandatory** — `{"status": "still_running"}` means call again with identical args.
- **Don't invent fields outside the projected set.** The dataset carries the field set documented in the table above — no emails, no phones, no full tenure history. If the user asks for those, route to `contact-data-enrichment`.
- **Lead with `top_picks` + `priority_summary`, not `preview_rows`.** A flat list of preview_rows is the failure mode; it's what generic contact tools produce. Onfire's edge is the pre-computed prioritization layer — surface it.
- **Convert `$$-onfire-bold-$$` sentinels** before display.
- **Don't try to re-fetch the full prospect list by re-running.** Use the returned `dataset_id` with `query_datasets` / `describe_dataset` instead — it's free, fast, and doesn't trigger a Phoenix run.
- **Don't set `use_cache=True`** unless it's plausibly a re-run of something already executed this session.
- **`activate_shadow_run=True`** only when the user is iterating on schema (and a shadow exists).

## Common pitfalls

- **Flat-dumping `preview_rows` instead of leading with `top_picks` + `priority_summary`.** This is the single biggest failure mode. The whole point of the response shape is that prioritization is pre-computed for you — surface it. A list of 5 rows with no lede looks like ZoomInfo on a bad day; the lede ("5 PLATINUM warm intros — start there") is what makes Onfire useful.
- **Inventing opener prose when `product_talking_points` exists.** Phoenix already wrote product-specific openers for each prospect. Use them. Don't paraphrase `ai_reasoning` into an opener and pretend you did the work.
- **Ignoring the warm-intro path.** If `CONNECTING_EMPLOYEE_NAME` is populated, name them in the output. That's the warm-intro contact the user can ping; burying it inside `ai_reasoning` is wasteful.
- **Missing the alumni callout.** `WORKED_IN_CLIENT_COMPANY_IN_PAST=TRUE` is the highest-value expansion signal in the response. If any row has it, lead with that row.
- **Treating `still_running` as an error.** It's the documented async signal. Just call again.
- **Treating `preview_rows` as the full list.** It's capped at 5; the rest is in the dataset. Use `query_datasets` for the rest.
- **Re-running `ai_prospecting` to "see more."** Use the dataset tools instead — the run already produced the full list.
- **Mixing `linkedin_urls` and `company_linkedin_url`.** Pick one — `linkedin_urls` wins if both are set, but it's clearer to use only the one you need.
- **Skipping the enrichment offer.** It's the single most important post-run behavior; users keep asking "can I get emails?" because we forgot to tell them yes.
- **Rendering `$$-onfire-bold-$$` literally.** Always converted to `**bold**`.
- **Forgetting to mention `total_prospects` / `filtered_prospects`** when only the top_picks are rendered. The user should know there's more in the dataset.

## Worked examples

**Single company by name.**
```
1. match-company on "Datadog" → linkedin_url
2. ai_prospecting(action="run", company_linkedin_url=<url>)
3. If still_running, call again until status="completed".
4. Open with the priority_summary lede (one line: tier-1 count, warm-intro
   tier, alumni count — whichever is highest-signal).
5. Render top_picks (3 rows) with the why + warm-intro path + opener pulled
   from product_talking_points. Convert $$-onfire-bold-$$ sentinels.
6. Mention the next-N preview_rows briefly + name the dataset_id and the
   filtered_prospects total so the user knows there's more.
7. Make the enrichment + download offers.
```

**Score a specific person.**
```
1. match-person on "Lana Patel, VP Eng at Snowflake" → person + company linkedin urls
2. ai_prospecting(action="get_prospect", company_linkedin_url=..., person_linkedin=...)
3. Show score + reasoning (inline, no dataset). Make the enrichment offer.
```

**Batch run, 30 accounts.**
```
1. match-company on the list (one call, ≤100 entries) → linkedin URLs.
2. ai_prospecting(action="run", linkedin_urls=[...]) — possibly poll.
3. Lede: priority_summary + per-company spread from the
   COMPANY_LINKEDIN_URL facet. Example: "42 prospects across 8 accounts;
   alumni cluster at 2 of them."
4. Render top_picks (3 rows) as the cross-account "start here" list. If
   the user wants per-company grouping, query_datasets with
   GROUP BY COMPANY_LINKEDIN_URL.
5. Offer xlsx export — pull the full set with query_datasets(
   "SELECT * FROM p ORDER BY rank_position LIMIT max").
6. Make the enrichment offer.
```

**Drilling in after a run.**
```
1. ai_prospecting(action="run", ...) → dataset_id="ds_abc"
2. User: "Just the alumni ones, ranked"
3. query_datasets(
     datasets={"p": "ds_abc"},
     sql="""SELECT FULL_NAME, TITLE_NAME, LINKEDIN_URL,
            MASTER_SCORE_REASON, CONNECTING_EMPLOYEE_NAME, SHARED_COMPANY,
            ai_reasoning
            FROM p
            WHERE WORKED_IN_CLIENT_COMPANY_IN_PAST = 'TRUE'
            ORDER BY rank_position""",
   )
4. Render the slice (same prioritization rendering as top_picks).
   Re-iterate the enrichment offer.
```

**Enriching the whole run.**
```
1. ai_prospecting(action="run", ...) → dataset_id="ds_abc", filtered_prospects=42
2. User says "get emails and phones for all of them"
3. contact_data_enrichment(
     contacts=[],                       # phase 1: consent (>10)
     total_count=42,
     dataset_id="ds_abc",
     linkedin_url_column="LINKEDIN_URL",
     account_website_column="COMPANY_LINKEDIN_URL",
     person_name_column="FULL_NAME",
   )
4. Show user_facing_message verbatim. Stop. After yes, phase 2 in batches of ≤20 with the same dataset_id + confirmation_token.
```

**Iterating on schema config.**
```
1. manage-ai-prospecting create_shadow / update_shadow per user edits.
2. ai_prospecting(action="run", activate_shadow_run=True, company_linkedin_url=...) → dataset_id_shadow
3. ai_prospecting(action="run", company_linkedin_url=...) (live) → dataset_id_live
4. Compare with query_datasets({"shadow": ds_shadow, "live": ds_live}, "SELECT ...") if useful.
5. Promote with manage-ai-prospecting ship_shadow when satisfied.
```

## What this skill does NOT do

- It doesn't resolve LinkedIn URLs — that's `match-company` / `match-person`.
- It doesn't return contact info — that's `contact-data-enrichment`.
- It doesn't edit schema config — that's `manage-ai-prospecting`.
- It doesn't analyse the dataset for you — that's `query_datasets` / `describe_dataset` (companion tools to the dataset handle).
