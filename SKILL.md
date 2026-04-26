---
name: onfire-prospecting
description: Run AI prospecting, score buyers and champions, resolve people and companies to verified LinkedIn profiles, and enrich contacts with emails and phones using the Onfire MCP. Use this skill whenever the user wants to prospect a company or list of companies, find decision makers or buyers at an account, score a specific person, look up a person or company from partial info (name, website, email), find LinkedIn URLs, get contact info (emails, phones), or inspect prospecting history — even if they don't say the word "prospecting" (e.g. "who should I talk to at Acme", "find me champions at these accounts", "get emails for this list", "what's Lana Patel's LinkedIn", "resolve these CRM accounts").
---

# Onfire Prospecting

This skill is the playbook for the Onfire MCP. It chains five tools together so a user can go from any starting state — a name, a website, a messy CRM dump, a LinkedIn URL — to a ranked, scored, optionally enriched prospect list.

The user might come in with company LinkedIn URLs, just websites, just names, a CSV from their CRM, a single person's name in passing, or a list of contacts that need emails. Your job is to read what they actually want and pick the shortest path through the tools.

## The five tools

| Tool | What it does | When to reach for it |
|---|---|---|
| `match_company` | Resolves a company from name / website / LinkedIn URL → verified LinkedIn URL + firmographics | The user gave you anything *but* a company LinkedIn URL and you need one |
| `match_person` | Resolves a person from name / email / company → verified LinkedIn URL, title, current company | The user has a person but no LinkedIn URL, or wants identity resolution on a list |
| `ai_prospecting` | Phoenix engine. `action="run"` ranks buyers/champions for a target company. `action="get_prospect"` scores one specific person at a company. | The actual prospecting work |
| `contact_data_enrichment` | Adds verified emails and phones to contact records. **Paid.** Two-phase consent flow above 10 contacts. | The user asks for contact info, or as the standing follow-up offer after a prospecting run |
| `manage_ai_prospecting` | Read-only SQL over Phoenix metadata: `runs`, `schemas`, `tenant_settings`, `prospect_tags`, `debug_prospects` | Inspecting history, config, or debugging — never to trigger a new run |

## Pick the path from intent, not from the input shape

Users say what they want; the input shape is just plumbing. Read intent first, then normalize inputs to whatever the chosen path needs.

**"Prospect this account / list of accounts."**
*Examples: "Find buyers at Acme", "Who should I sell to at acme.com", "Run prospecting on these 30 companies."*

1. Make sure you have a company LinkedIn URL for each target. If not, call `match_company` first (batch up to 100).
2. Call `ai_prospecting(action="run", company_linkedin_url=...)` for one, or pass `linkedin_urls=[...]` for a batch. Set `use_cache=True` only if it's clearly a re-run of something you already ran in this conversation.
3. Present the ranked prospects (see "Presenting prospect results").
4. Make the enrichment offer (see "The enrichment offer" — this is required, not optional).

**"Score this specific person."**
*Examples: "Is Jane Doe at Acme worth talking to?", "Score linkedin.com/in/jane-doe at Acme."*

1. Get the company LinkedIn URL — `match_company` if missing.
2. Get the person's LinkedIn URL — `match_person` if missing.
3. Call `ai_prospecting(action="get_prospect", company_linkedin_url=..., person_linkedin=...)`.
4. Make the enrichment offer.

**"Who is this person / company?" (identity only, no scoring)**
*Examples: "What's John Smith's LinkedIn at Acme?", "Resolve these 50 CRM accounts to LinkedIn URLs."*

Just `match_person` or `match_company`. Don't run prospecting unless asked.

**"Get me emails / phones."**
*Examples: "Enrich this list", "Get emails for everyone we just scored."*

1. If the rows don't have LinkedIn URLs, run `match_person` first to fill them in.
2. Then `contact_data_enrichment` — follow the two-phase flow if more than 10.

**"What did we run / how is the engine configured?"**
*Examples: "Show me last week's runs", "Why is this run failing?", "What's our prospecting schema?"*

`manage_ai_prospecting`. SELECT only, always filter by `tenant_id`. See "Phoenix metadata" below. Don't use this to trigger anything; it's read-only by design.

## Input normalization

Get to a company LinkedIn URL before any prospecting call. The matcher does the heavy lifting:

- Already have a company LinkedIn URL → use it directly.
- Website (`acme.com`, `https://acme.com/about`) → `match_company(companies=[{"websites": ["acme.com"]}])`.
- Name (`"Acme Inc"`, `"acme"`) → `match_company(companies=[{"names": ["Acme Inc"]}])`.
- Multiple signals available → pass them all in one entry. More signals = better match accuracy.
- A list / CSV / sheet → batch up to 100 per call.

Same pattern for people:

- Person LinkedIn URL → use directly.
- Email → `match_person(entities=[{"person_email": "..."}])`.
- Name only → `company_name` is required; otherwise the matcher refuses.
- Name + company (+ optional title / company website / company LinkedIn) → standard call.

If a match returns `matched: false` or a noticeably low `match_score` / `cosine_similarity`, don't silently proceed. Show the user what came back ("I think you mean X but I'm only ~60% sure — confirm or pick another?") and let them decide. A bad match silently propagating into a prospecting run wastes their time and makes the results look broken.

## Presenting prospect results

`ai_prospecting` returns a trimmed set of fields per prospect: `LINKEDIN_URL`, `TITLE_NAME`, `ai_reasoning`, `LOCATION_COUNTRY`, `LOCATION_REGION`, `COMPANY_LINKEDIN_URL`, `FULL_NAME`. Don't promise the user any other field from a run — it isn't there.

Default rendering for a single-company run: a ranked list (the API returns them in scored order) with name as a link to `LINKEDIN_URL`, title, location (Region, Country), and the reasoning underneath.

For multi-company runs, group by company.

For long lists (more than ~10–15), render the first batch inline and offer to dump the full set to xlsx or csv.

**Bold sentinels.** `ai_reasoning` contains `$$-onfire-bold-$$` markers around emphasized phrases. Convert each pair into markdown `**bold**` before showing it. Left as-is they look like rendering bugs.

## The enrichment offer (don't skip this)

After **every** prospecting run, tell the user they can pull verified emails and phones for any of the returned prospects — not just the top N you happened to render. Users frequently assume contact data is gated to whatever's on screen; it isn't, and most of the value of the workflow is downstream of contact data.

Phrasing should feel natural, not boilerplate. Something like:

> "I can pull verified emails and phone numbers for any of these — top 5, all of them, or a subset you pick. Just say which."

Make this offer regardless of how many prospects came back, and regardless of how many you displayed. The point is to make the user aware the option exists and is theirs to scope.

## Two-phase enrichment (paid — read carefully)

`contact_data_enrichment` consumes credits per contact per data type. The consent flow has rules that are easy to skip and expensive when skipped. The reasoning behind each rule is below — follow the spirit, not just the letter.

**10 or fewer contacts → small batch shortcut.** Call the tool directly with the contacts. No `total_count`, no `confirmation_token` needed.

**More than 10 contacts → two phases.**

*Phase 1 — Consent.* Call once with `contacts=[]` and `total_count=N`. The server returns a `confirmation_required` response containing a `user_facing_message`, `credits_to_consume`, `confirmation_token`, and `max_batch_size` (which is 20).

- Show `user_facing_message` **exactly as returned**. Don't rephrase the cost, don't wrap it in your own framing. The wording was chosen so the user understands what they're approving.
- Stop after showing the message. Wait for an explicit "yes" or equivalent approval to that message specifically.
- The user's original request ("enrich all of them") is **not** approval for the cost. They asked you to do the work; they haven't seen the price yet.

*Phase 2 — Batched enrichment.* After explicit approval, send contacts in batches of ≤20 per call. Each call must include the `confirmation_token` from phase 1 and the same `total_count`. Loop until everyone is processed; accumulate results across calls.

- Never fabricate a `confirmation_token` — only use what phase 1 actually returned. A made-up token will be rejected and the user's request will fail in a confusing way.
- Never bundle more than 20 in one call; the server will reject the batch.

If the user says no or hesitates, stop. Don't look for a workaround that bypasses consent — that's the one thing the flow is designed to prevent.

## Phoenix metadata (`manage_ai_prospecting`)

Read-only SELECT against:

- `tenant_settings` — tenant config (crm_settings, crm_upload_settings, system_settings). Primary key `id` = tenant_id.
- `runs` — past run history: `status`, `resulting_prospects` (JSONB), `company_linkedin_url`, `client_email`, run times, `failure_reason`. Foreign key `tenant_id`.
- `schemas` — per-tenant/team prospecting config (included regions, client technologies, ranking config, hot/cold keywords, prompt modules, prospect tags schema). Indexed on `(tenant, team)`.
- `prospect_tags` — tagging data.
- `debug_prospects` — diagnostic data.

Always filter by `tenant_id` in WHERE. The result cap is 1000 rows; if you hit truncation, narrow the query rather than asking for more.

Useful starters:

- Recent failures: `SELECT id, run_start_time, failure_reason FROM runs WHERE tenant_id = '<id>' AND status = 'failed' ORDER BY run_start_time DESC LIMIT 20`
- Active schema: `SELECT * FROM schemas WHERE tenant = '<id>'`
- Tenant config: `SELECT * FROM tenant_settings WHERE id = '<id>'`

If the user says "run X again", don't query `runs` first — just call `ai_prospecting`. `manage_ai_prospecting` is for metadata, not for fetching cached results to re-display.

## Hard rules (the things that bite)

- **Never pass `target_tenant_id`** on `ai_prospecting` or `contact_data_enrichment`. Tenant comes from the OAuth session. The override is super-tenant only (onfire / onfire-dev) and will error for everyone else.
- **`manage_ai_prospecting` is SELECT-only** and always needs `tenant_id` in the WHERE clause.
- **Batch caps:** `match_company` and `match_person` ≤100 per call. `contact_data_enrichment` phase-2 batches ≤20 per call.
- **Confirmation tokens are server-issued.** Don't fabricate or reuse across unrelated requests.
- **Don't promise prospect fields that aren't returned.** Only the seven trimmed fields are available.
- **Convert `$$-onfire-bold-$$` sentinels** in `ai_reasoning` to markdown bold before display.
- **Surface low-confidence matches** from `match_company` / `match_person`. Don't silently pick the top result and propagate ambiguity downstream.

## Worked examples

**Example 1 — Single company, name only.**

User: "Run prospecting on Datadog."

1. `match_company(companies=[{"names": ["Datadog"]}])` → get the LinkedIn URL.
2. `ai_prospecting(action="run", company_linkedin_url=<that url>)`.
3. Render the ranked list (bolds converted, location shown).
4. Close with the enrichment offer: "I can pull emails and phones for any of these — say which."

**Example 2 — A sheet of 40 accounts.**

User uploads a CSV with `company_name` and `website`. They want prospecting on all of them.

1. One `match_company` call with all 40 rows (multi-signal entries: both name and website).
2. Filter to matched rows; flag the unmatched ones for the user.
3. `ai_prospecting(action="run", linkedin_urls=[...])` with the matched LinkedIn URLs.
4. Group results by company. Offer xlsx output if the total is long. Make the enrichment offer.

**Example 3 — Person identity + score.**

User: "Score 'Lana Patel, VP Eng at Snowflake'."

1. `match_person(entities=[{"person_full_name": "Lana Patel", "company_name": "Snowflake", "job_title": "VP Eng"}])`.
2. If the match result includes `company_linkedin_url`, use it. Otherwise `match_company` for Snowflake.
3. `ai_prospecting(action="get_prospect", company_linkedin_url=..., person_linkedin=...)`.
4. Show score + reasoning. Make the enrichment offer.

**Example 4 — Enriching 150 contacts.**

User: "Get emails and phones for everyone in this list."

1. If any rows lack LinkedIn URLs, `match_person` first (batches of ≤100) to fill them in.
2. Phase 1: `contact_data_enrichment(contacts=[], total_count=150, ...)`. Show `user_facing_message` verbatim. Stop.
3. On explicit yes: phase 2, 8 batches of ≤20 with the `confirmation_token`, accumulating results.
4. Return enriched rows; flag any contacts the service couldn't resolve.

**Example 5 — History query.**

User: "What did we run last week, and which ones failed?"

`manage_ai_prospecting` with a SELECT on `runs` filtered by tenant + last-7-days timeframe, ordered by `run_start_time DESC`. Don't trigger new runs.
