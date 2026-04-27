---
name: onfire-ai-prospecting
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

A completed run returns a **dataset handle plus a small preview** — not the full prospect list inline. The whole prospect set is persisted as a short-lived MCP dataset (auto-expires); the tool response is intentionally compact so it never blows past the per-tool output token budget, even for large batch runs.

```json
{
  "status": "completed",
  "dataset": {
    "id": "ds_abc123…",
    "source": "ai_prospecting",
    "row_count": 42,
    "columns": ["LINKEDIN_URL", "TITLE_NAME", "ai_reasoning", "..."],
    "schema": [{"name": "LINKEDIN_URL", "type": "string"}, ...],
    "created_at": "...",
    "expires_at": "...",
    "facets": { "LOCATION_COUNTRY": {"US": 30, "DE": 12}, ... }
  },
  "preview_rows": [ /* up to 5 already-projected prospects, scored order */ ],
  "facets": { "LOCATION_COUNTRY": {"US": 30, "DE": 12}, "LOCATION_REGION": {...}, "COMPANY_LINKEDIN_URL": {...} },
  "total_prospects": 67,
  "filtered_prospects": 42,
  "ranking_method": "individual",
  "message": "Full AI prospecting results (42 prospect(s)) are available via query_datasets / describe_dataset using dataset_id='ds_abc123…'."
}
```

Each prospect row in the dataset (and in `preview_rows`) carries only these seven fields:

- `LINKEDIN_URL`
- `TITLE_NAME`
- `ai_reasoning`
- `LOCATION_COUNTRY`
- `LOCATION_REGION`
- `COMPANY_LINKEDIN_URL`
- `FULL_NAME`

**Don't promise the user other fields.** No seniority number, no email, no phone, no tenure — those aren't in the response. If the user asks for emails/phones, that's `contact-data-enrichment`.

If Phoenix returns zero prospects the response is the same shape with `dataset: null` and `preview_rows: []`.

## Working with the dataset

The full ranked list lives in the dataset, not in `preview_rows`. Use the dataset companion tools to inspect or slice it without paying its context cost:

- **`describe_dataset(dataset_id)`** — schema + a head sample. Good first call before writing SQL.
- **`query_datasets({alias: dataset_id}, sql, row_limit=N)`** — read-only DuckDB SQL against the parquet. Filter, count, slice, or pull a specific page.
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

`facets` on the response are the same kind of distribution counts pre-computed for `LOCATION_COUNTRY`, `LOCATION_REGION`, and `COMPANY_LINKEDIN_URL` — use those for quick "where do these sit?" answers without a `query_datasets` round-trip.

## Output shape (action="get_prospect")

A single scored prospect record returned **inline** (no dataset — it's just one row). Same trimmed field set as the run dataset, plus the AI score and reasoning for that person specifically.

## The bold sentinel — convert before display

`ai_reasoning` strings contain `$$-onfire-bold-$$` markers around emphasized phrases. **Convert each pair to markdown `**bold**` before showing the user.** Left as-is they look like a rendering bug. The conversion applies to `preview_rows`, to rows pulled via `query_datasets` / `describe_dataset`, and to `get_prospect` responses.

```
"This is a $$-onfire-bold-$$strong fit$$-onfire-bold-$$ because..."
→ "This is a **strong fit** because..."
```

## Default rendering

**Single company:** render the `preview_rows` inline as a ranked list — name links to `LINKEDIN_URL`, then title, then location (Region, Country), then `ai_reasoning` (with bolds converted) underneath. Mention the total count from `total_prospects` / `filtered_prospects` and the `dataset_id` so the user knows there's more available.

**Batch / multi-company:** preview is still scored order across all companies. If the user wants per-company grouping, run `query_datasets` with `GROUP BY COMPANY_LINKEDIN_URL` (or `ORDER BY COMPANY_LINKEDIN_URL` for a flat grouped list).

**Long lists / pagination:** pull additional pages via `query_datasets({"p": dataset_id}, "SELECT * FROM p LIMIT N OFFSET K")`. Offer xlsx / csv export for the full set; the dataset is the canonical source.

## The enrichment offer (required, not optional)

After **every** run — single, batch, get_prospect, no matter what — tell the user they can pull verified emails and phones for any of the returned prospects. Not just the top N you displayed in `preview_rows`; **all** of them are available to enrich. Most of the workflow's value is downstream of contact data, and users frequently assume contact data is gated to whatever's on screen.

Phrase it naturally:

> "I can pull verified emails and phone numbers for any of these — top 5, all 42, or a subset you pick. Just say which."

The dataset_id from the run can be passed straight to `contact_data_enrichment(dataset_id="ds_…", ...)` to enrich the entire run set without rebuilding contact dicts; for a custom subset, build dicts from the rows the user picked. See `contact-data-enrichment`.

This is part of the playbook, not a polite extra.

## Hard rules

- **Never pass `target_tenant_id`.** Tenant comes from OAuth. The override is super-tenant only and will error for everyone else.
- **Polling is mandatory** — `{"status": "still_running"}` means call again with identical args.
- **Don't promise the seven prospect fields are exhaustive.** They are; don't invent extras.
- **Convert `$$-onfire-bold-$$` sentinels** before display.
- **Don't try to re-fetch the full prospect list by re-running.** Use the returned `dataset_id` with `query_datasets` / `describe_dataset` instead — it's free, fast, and doesn't trigger a Phoenix run.
- **Don't set `use_cache=True`** unless it's plausibly a re-run of something already executed this session.
- **`activate_shadow_run=True`** only when the user is iterating on schema (and a shadow exists).

## Common pitfalls

- **Treating `still_running` as an error.** It's the documented async signal. Just call again.
- **Treating `preview_rows` as the full list.** It's capped at 5; the rest is in the dataset. Use `query_datasets` for the rest.
- **Re-running `ai_prospecting` to "see more."** Use the dataset tools instead — the run already produced the full list.
- **Mixing `linkedin_urls` and `company_linkedin_url`.** Pick one — `linkedin_urls` wins if both are set, but it's clearer to use only the one you need.
- **Skipping the enrichment offer.** It's the single most important post-run behavior; users keep asking "can I get emails?" because we forgot to tell them yes.
- **Rendering `$$-onfire-bold-$$` literally.** Always converted to `**bold**`.
- **Forgetting to mention `total_prospects` / `filtered_prospects`** when only the 5-row preview is rendered. The user should know there's more.

## Worked examples

**Single company by name.**
```
1. match-company on "Datadog" → linkedin_url
2. ai_prospecting(action="run", company_linkedin_url=<url>)
3. If still_running, call again until status="completed".
4. Render preview_rows (bolds converted, location shown), name the dataset_id, give the total.
5. Make the enrichment offer — mention all <total> are available, not just the preview.
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
3. Render preview_rows. If user wants per-company breakdown, query_datasets with GROUP BY COMPANY_LINKEDIN_URL.
4. Offer xlsx export — pull the full set with query_datasets("SELECT * FROM p LIMIT max").
5. Make the enrichment offer.
```

**Drilling in after a run.**
```
1. ai_prospecting(action="run", ...) → dataset_id="ds_abc"
2. User: "Just the US ones, sorted by job title"
3. query_datasets(
     datasets={"p": "ds_abc"},
     sql="SELECT FULL_NAME, TITLE_NAME, LINKEDIN_URL, ai_reasoning FROM p WHERE LOCATION_COUNTRY='US' ORDER BY TITLE_NAME",
   )
4. Render the slice. Re-iterate the enrichment offer.
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
