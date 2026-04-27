---
name: onfire-prospecting
description: Orchestrator for the Onfire MCP. Run AI prospecting, score buyers and champions, resolve people and companies to verified LinkedIn profiles, enrich contacts with emails and phones, and edit prospecting schema config. Use this skill whenever the user wants to prospect a company or list of companies, find decision makers or buyers at an account, score a specific person, look up a person or company from partial info (name, website, email), find LinkedIn URLs, get contact info (emails, phones), or iterate on prospecting schema configuration — even if they don't say the word "prospecting" (e.g. "who should I talk to at Acme", "find me champions at these accounts", "get emails for this list", "what's Lana Patel's LinkedIn", "resolve these CRM accounts", "tweak my hot keywords").
---

# Onfire Prospecting — Orchestrator

This is the orchestrator skill for the Onfire MCP. It routes work across five atomic skills (one per tool) and enforces the cross-cutting rules that span them. Read this skill first to pick the path, then drop into the atomic skill for the tool you need.

The user might come in with company LinkedIn URLs, just websites, just names, a CSV from their CRM, a single person's name in passing, a list of contacts that need emails, or a request to tweak the engine. Read intent first, then normalize inputs to whatever the chosen path needs.

## The atomic skills

| Tool | Atomic skill | One-line purpose |
|---|---|---|
| `match_company` | `skills/match-company` | Resolve a company → verified LinkedIn URL + firmographics |
| `match_person` | `skills/match-person` | Resolve a person → verified LinkedIn profile + current title/company |
| `ai_prospecting` | `skills/ai-prospecting` | Rank prospects (`run`) or score one person (`get_prospect`) |
| `contact_data_enrichment` | `skills/contact-data-enrichment` | Add verified emails/phones (paid; two-phase consent above 10) |
| `manage_ai_prospecting` | `skills/manage-ai-prospecting` | Edit the caller's schema via shadow lifecycle (draft → test → ship) |

When you've picked a path below, read the atomic skill for each tool you'll call. Atomic skills hold the input shapes, batch caps, output fields, polling rules, and pitfalls that you don't want to re-derive each time.

## Pick the path from intent, not from the input shape

**"Prospect this account / list of accounts."**
*Examples: "Find buyers at Acme", "Who should I sell to at acme.com", "Run prospecting on these 30 companies."*

1. Need company LinkedIn URLs → `match-company` (batch ≤100).
2. `ai-prospecting` with `action="run"` (single via `company_linkedin_url`, batch via `linkedin_urls`). Be ready to poll.
3. Render ranked results (atomic explains rendering + the `$$-onfire-bold-$$` conversion).
4. Make the enrichment offer (see below — required, not optional).

**"Score this specific person."**
*Examples: "Is Jane Doe at Acme worth talking to?", "Score linkedin.com/in/jane-doe at Acme."*

1. Get the company LinkedIn URL — `match-company` if missing.
2. Get the person LinkedIn URL — `match-person` if missing (it usually returns the company URL too — reuse it).
3. `ai-prospecting` with `action="get_prospect"`.
4. Make the enrichment offer.

**"Who is this person / company?" (identity only, no scoring)**
*Examples: "What's John Smith's LinkedIn at Acme?", "Resolve these 50 CRM accounts to LinkedIn URLs."*

Just `match-person` or `match-company`. Don't run prospecting unless asked.

**"Get me emails / phones."**
*Examples: "Enrich this list", "Get emails for everyone we just scored."*

1. If rows lack LinkedIn URLs, `match-person` first (batches ≤100).
2. `contact-data-enrichment` — atomic owns the two-phase consent flow.

**"Show me / change my prospecting config."**
*Examples: "What's in my schema?", "Tweak my hot keywords and test", "Promote my draft."*

`manage-ai-prospecting`. Always `get_my_schema` first before editing. Test edits with `ai-prospecting(activate_shadow_run=True, ...)`. `ship_shadow(confirm=True)` is the destructive step.

## Input normalization

Get to a company LinkedIn URL before any prospecting call. The matchers do the heavy lifting — read `match-company` and `match-person` for input shapes. The pattern:

- Already have a clean LinkedIn URL → use it.
- Anything else (name, website, email, partial info) → matcher first, multi-signal entries when you have multiple fields.
- Lists → batch up to 100 per matcher call.
- Low-confidence match → surface it. Don't silently propagate ambiguity into a prospecting run.

## The enrichment offer (don't skip this)

After **every** prospecting run, tell the user they can pull verified emails and phones for any of the returned prospects — not just the top N you happened to render. Users frequently assume contact data is gated to whatever's on screen; it isn't, and most of the value of the workflow is downstream of contact data.

Phrasing should feel natural, not boilerplate:

> "I can pull verified emails and phone numbers for any of these — top 5, all of them, or a subset you pick. Just say which."

Make this offer regardless of how many prospects came back, and regardless of how many you displayed. The point is to make the user aware the option exists and is theirs to scope.

## Hard rules (the things that bite)

- **Never pass `target_tenant_id`** on `ai_prospecting` or `contact_data_enrichment`. Tenant comes from OAuth.
- **Polling:** `ai_prospecting` may return `{"status": "still_running"}`. Call again with identical args. Don't treat it as an error.
- **Batch caps:** `match_company` / `match_person` ≤100. `contact_data_enrichment` phase-2 ≤20.
- **Confirmation tokens are server-issued.** Don't fabricate, don't reuse across unrelated requests.
- **Two-phase consent above 10 contacts.** Show `user_facing_message` verbatim. Wait for explicit yes.
- **Don't promise prospect fields not in the seven returned.** See `ai-prospecting`.
- **Convert `$$-onfire-bold-$$` sentinels** to markdown bold before display.
- **Surface low-confidence matches** from the matchers. Don't silently pick the top result.
- **`manage_ai_prospecting` is the shadow editor**, not a SQL surface. Read its atomic skill before editing.

## Worked examples (cross-tool)

**Single company, name only.**
*"Run prospecting on Datadog."*
1. `match-company` on "Datadog" → LinkedIn URL.
2. `ai-prospecting(action="run", company_linkedin_url=...)`. Poll if needed.
3. Render. Make the enrichment offer.

**A sheet of 40 accounts.**
*User uploads a CSV with `company_name` and `website`.*
1. One `match-company` call with all 40 rows (multi-signal entries: both name and website).
2. Filter matched rows; flag unmatched.
3. `ai-prospecting(action="run", linkedin_urls=[...])`. Poll if needed.
4. Group by company. Offer xlsx if long. Make the enrichment offer.

**Person identity + score.**
*"Score 'Lana Patel, VP Eng at Snowflake'."*
1. `match-person(entities=[{"person_full_name": "Lana Patel", "company_name": "Snowflake", "job_title": "VP Eng"}])`.
2. Reuse the returned `company_linkedin_url`; otherwise `match-company` for Snowflake.
3. `ai-prospecting(action="get_prospect", company_linkedin_url=..., person_linkedin=...)`.
4. Score + reasoning. Make the enrichment offer.

**Enriching 150 contacts.**
1. If rows lack LinkedIn URLs, `match-person` first (batches ≤100).
2. `contact-data-enrichment` phase 1 (consent). Show `user_facing_message` verbatim. Stop.
3. On explicit yes: phase 2, 8 batches of ≤20 with the `confirmation_token`. Accumulate. Flag unresolvable rows.

**Iterating on schema config.**
*"Try my prospecting with these new hot keywords on Acme."*
1. `manage-ai-prospecting` `get_my_schema` → show current keywords.
2. `create_shadow` if none.
3. `update_shadow(patch={"hot_keywords": [...]})`.
4. `ai-prospecting(action="run", activate_shadow_run=True, company_linkedin_url=...)`.
5. Compare with the user. `ship_shadow(confirm=True)` or `discard_shadow`.
