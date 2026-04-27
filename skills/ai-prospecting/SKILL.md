---
name: onfire-ai-prospecting
description: Run AI prospecting against a target company (rank likely buyers/champions) or score a single named person at a company using the Onfire `ai_prospecting` tool. Use when the user wants prospects for an account, a ranked list of who to talk to, a score on a specific person ("is X worth a meeting"), or a batch run across multiple companies. Covers both `action='run'` and `action='get_prospect'`, the polling pattern for long runs, and the shadow-schema test mode.
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
{"status": "still_running"}
```

When you see this, **call the tool again with identical arguments**. Keep calling until you get prospects back. The server deduplicates — you will not trigger a duplicate run by retrying. Don't change arguments between polls (changing them will look like a new request).

## Output shape (action="run")

A ranked list of prospects, already in scored order. Each prospect has:

- `LINKEDIN_URL`
- `TITLE_NAME`
- `ai_reasoning`
- `LOCATION_COUNTRY`
- `LOCATION_REGION`
- `COMPANY_LINKEDIN_URL`
- `FULL_NAME`

**Don't promise the user other fields.** No seniority number, no email, no phone, no tenure — those aren't in the response. If the user asks for emails/phones, that's `contact-data-enrichment`.

## Output shape (action="get_prospect")

A single scored prospect record with the same trimmed field set plus the AI score and reasoning for that person specifically.

## The bold sentinel — convert before display

`ai_reasoning` strings contain `$$-onfire-bold-$$` markers around emphasized phrases. **Convert each pair to markdown `**bold**` before showing the user.** Left as-is they look like a rendering bug.

```
"This is a $$-onfire-bold-$$strong fit$$-onfire-bold-$$ because..."
→ "This is a **strong fit** because..."
```

## Default rendering

**Single company:** ranked list. Name links to `LINKEDIN_URL`, then title, then location (Region, Country), then `ai_reasoning` (with bolds converted) underneath.

**Batch / multi-company:** group by `COMPANY_LINKEDIN_URL`. Within each group, the order is already scored.

**Long lists (~10–15+):** render the first batch inline, offer xlsx / csv export for the full set.

## The enrichment offer (required, not optional)

After **every** run — single, batch, get_prospect, no matter what — tell the user they can pull verified emails and phones for any of the returned prospects. Not just the top N you displayed; **all** of them are available to enrich. Most of the workflow's value is downstream of contact data, and users frequently assume contact data is gated to whatever's on screen.

Phrase it naturally:

> "I can pull verified emails and phone numbers for any of these — top 5, all of them, or a subset you pick. Just say which."

This is part of the playbook, not a polite extra. See `contact-data-enrichment` for the actual call.

## Hard rules

- **Never pass `target_tenant_id`.** Tenant comes from OAuth. The override is super-tenant only and will error for everyone else.
- **Polling is mandatory** — `{"status": "still_running"}` means call again with identical args.
- **Convert `$$-onfire-bold-$$` sentinels** before display.
- **Don't promise prospect fields not in the seven** listed above.
- **Don't set `use_cache=True`** unless it's plausibly a re-run of something already executed this session.
- **`activate_shadow_run=True`** only when the user is iterating on schema (and a shadow exists).

## Common pitfalls

- **Treating `still_running` as an error.** It's the documented async signal. Just call again.
- **Mixing `linkedin_urls` and `company_linkedin_url`.** Pick one — `linkedin_urls` wins if both are set, but it's clearer to use only the one you need.
- **Skipping the enrichment offer.** It's the single most important post-run behavior; users keep asking "can I get emails?" because we forgot to tell them yes.
- **Rendering `$$-onfire-bold-$$` literally.** Always converted to `**bold**`.

## Worked examples

**Single company by name.**
```
1. match-company on "Datadog" → linkedin_url
2. ai_prospecting(action="run", company_linkedin_url=<url>)
3. If still_running, call again until prospects come back.
4. Render ranked list, bolds converted, location shown.
5. Make the enrichment offer.
```

**Score a specific person.**
```
1. match-person on "Lana Patel, VP Eng at Snowflake" → person + company linkedin urls
2. ai_prospecting(action="get_prospect", company_linkedin_url=..., person_linkedin=...)
3. Show score + reasoning. Make the enrichment offer.
```

**Batch run, 30 accounts.**
```
1. match-company on the list (one call, ≤100 entries) → linkedin URLs.
2. ai_prospecting(action="run", linkedin_urls=[...]) — possibly poll.
3. Group results by company, offer xlsx if long, make the enrichment offer.
```

**Iterating on schema config.**
```
1. manage-ai-prospecting create_shadow / update_shadow per user edits.
2. ai_prospecting(action="run", activate_shadow_run=True, company_linkedin_url=...)
3. Compare to a live run if useful.
4. Promote with manage-ai-prospecting ship_shadow when satisfied.
```

## What this skill does NOT do

- It doesn't resolve LinkedIn URLs — that's `match-company` / `match-person`.
- It doesn't return contact info — that's `contact-data-enrichment`.
- It doesn't edit schema config — that's `manage-ai-prospecting`.
