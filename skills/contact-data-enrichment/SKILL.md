---
name: onfire-contact-data-enrichment
description: Append verified professional emails and phone numbers to contact records using the Onfire `contact_data_enrichment` tool. Use when the user asks for emails, phones, or "contact info" for prospects, when enriching a CSV / CRM list, or as the standing follow-up to any `ai_prospecting` run. PAID per contact per data type — has a strict two-phase consent flow above 10 contacts. This skill enforces that flow.
---

# contact_data_enrichment (atomic)

Adds verified emails and phones to contact records. **Paid: 1 credit per contact per data type.** Misusing the consent flow costs the user money.

## When to use this

- User asks for emails or phones for a list of people.
- Standard follow-up after `ai_prospecting` ("yes, pull emails for the top 10").
- Enriching CRM rows that already have LinkedIn URLs.

If the rows don't have LinkedIn URLs yet, run `match-person` first to fill them in — this tool needs LinkedIn URLs to do its best work.

## Required arguments (every call)

These four are required by the schema, even on the consent phase:

- `contacts` — list of contact dicts (empty list `[]` for phase 1).
- `linkedin_url_column` — name of the column in `contacts` that holds the person's LinkedIn URL.
- `account_website_column` — name of the column that holds the person's company website.
- `person_name_column` — name of the column that holds the person's full name.

The column-name params tell the tool how to read your contact dicts. Pass the keys you actually used in `contacts`.

## Optional arguments

- `total_count` — required for phase 1 and every phase 2 call when contacts > 10.
- `confirmation_token` — required on every phase 2 call. Server-issued in phase 1.
- `include_email` *(default `True`)*
- `include_phone` *(default `True`)* — turn one off if the user only wants the other; halves the cost.
- `dataset_id`, `limit`, `offset` — pagination over a saved dataset (most calls don't need these).
- **Never pass `target_tenant_id`** — tenant comes from OAuth.

## The flow at a glance

| Contact count | Flow |
|---|---|
| ≤ 10 | One call with the contacts. No `total_count`, no `confirmation_token` needed. |
| > 10 | Phase 1 (consent), wait for explicit yes, then phase 2 (batched, ≤20 per call). |

## Small-batch shortcut (≤10 contacts)

```python
contact_data_enrichment(
    contacts=[
        {"name": "John Smith", "linkedin": "https://linkedin.com/in/...", "website": "acme.com"},
        ...  # up to 10
    ],
    linkedin_url_column="linkedin",
    account_website_column="website",
    person_name_column="name"
)
```

No consent dance — go straight through.

## Two-phase flow (>10 contacts)

### Phase 1 — Consent

Call once with `contacts=[]` and `total_count=N`:

```python
contact_data_enrichment(
    contacts=[],
    total_count=150,
    linkedin_url_column="linkedin",
    account_website_column="website",
    person_name_column="name"
)
```

Server returns:

```json
{
  "status": "confirmation_required",
  "user_facing_message": "...",
  "credits_to_consume": 300,
  "confirmation_token": "...",
  "max_batch_size": 20
}
```

**Required behavior:**

1. **Show `user_facing_message` exactly as returned.** Don't paraphrase the cost. Don't wrap it in your own framing. The wording was chosen so the user understands what they're approving.
2. **Stop. Wait for explicit "yes" or equivalent approval to that message.** The user's original request ("enrich all of them") is **not** approval for the cost — they hadn't seen the price yet.
3. If the user says no or hesitates, **stop**. Don't look for a workaround. The flow is designed to prevent that.

### Phase 2 — Batched enrichment

After explicit yes, send contacts in batches of **≤20 per call**. Each call must include the `confirmation_token` from phase 1 and the same `total_count`.

```python
# 150 contacts → 8 batches
for batch in chunked(contacts, 20):
    contact_data_enrichment(
        contacts=batch,
        total_count=150,
        confirmation_token=token_from_phase_1,
        linkedin_url_column="linkedin",
        account_website_column="website",
        person_name_column="name"
    )
```

Loop until everyone is processed. **Accumulate results across calls.** Flag any contacts the service couldn't resolve.

## Hard rules

- **Never fabricate a `confirmation_token`.** Only use what phase 1 actually returned. A made-up token gets rejected.
- **Don't reuse a `confirmation_token` across unrelated requests.** Tokens are scoped to one approved batch.
- **Never bundle more than 20 contacts in a phase-2 call.** The server rejects it.
- **Show `user_facing_message` verbatim.** Paraphrasing the cost defeats the consent flow.
- **Don't treat the original user request as approval** for the dollar amount they haven't seen yet.
- **Never pass `target_tenant_id`.**

## Common pitfalls

- **Forgetting the column-name params.** They're required even on the empty-contacts consent call.
- **Skipping phase 1 for "just 12 contacts".** The threshold is >10, not >20. Twelve triggers two-phase.
- **Sending phase 2 with the wrong `total_count`.** It must match phase 1.
- **Re-confirming the same batch silently after a server timeout.** Re-use the existing `confirmation_token`; don't kick off a fresh phase 1 unless the user genuinely wants to redo the request.
- **Not turning off `include_phone`** when the user only asked for emails. You'll charge them double.

## Worked examples

**8 contacts (small batch).**
```
contact_data_enrichment(
    contacts=[...8 dicts...],
    linkedin_url_column="linkedin",
    account_website_column="website",
    person_name_column="name"
)
```
Done in one call. Render results.

**150 contacts.**
```
1. Phase 1: contacts=[], total_count=150, column params. Show user_facing_message verbatim. Stop.
2. User says "yes."
3. Phase 2: 8 calls of ≤20, each with the same total_count and confirmation_token.
4. Accumulate, surface unresolvable rows.
```

**Top 10 from a 50-prospect run.**
```
After ai_prospecting returns 50 prospects, the user picks the top 10:
contact_data_enrichment(
    contacts=[...10 dicts built from prospect rows...],
    linkedin_url_column="LINKEDIN_URL",   # use whatever key you used
    account_website_column="company_website",
    person_name_column="FULL_NAME"
)
```
≤10, so single call.

**Emails only, 80 contacts.**
```
Phase 1 with include_phone=False, total_count=80 → user sees the (lower) cost → yes → phase 2 (4 batches).
```

## What this skill does NOT do

- It doesn't resolve identities — that's `match-person` (run first if rows lack LinkedIn URLs).
- It doesn't score or rank — that's `ai-prospecting`.
- It doesn't bypass consent. There is no "force" flag. If the user won't approve, the answer is no.
