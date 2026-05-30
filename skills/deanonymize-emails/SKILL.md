---
name: deanonymize-emails
description: Identify the person and company behind a list of email addresses — name, LinkedIn URL, current title, employer, location — using the Onfire `deanonymize_emails` tool. Use when the user has a list of emails (work or personal: Gmail, iCloud, Yahoo) and wants to know who they belong to. PAID per successful match — has a strict two-phase consent flow above 10 emails. Lists larger than 25 emails must be split into batches of 25 per call.
---

# deanonymize_emails (atomic)

Reverse-enriches email addresses into people: name, LinkedIn URL, current title, employer, location. Works on personal addresses (Gmail, iCloud, Yahoo) as well as work email. **Paid: 5 credits per successful match. Misses are free.**

## Communication style

Never expose implementation internals to the user. Do not mention thresholds, batch sizes, consent phases, confirmation tokens, or any other mechanics of how the tool works. The user should only see: the results, or (when required) the cost confirmation message from phase 1. Nothing else about how the tool decides what to do.

**Wrong:** "Only 3 emails — well under the 10-email threshold, so I can call directly without the consent phase."
**Right:** Just call the tool and show the results.

**Wrong:** "I'll need to split these into batches of 25 and run 4 API calls."
**Right:** Just do it silently and present the combined results.

## When to use this

- User has a list of email addresses and wants to know who owns them.
- You need to tie an inbound email to a company or role.
- Pre-step before reaching out — you have addresses but no identity context.

## Input shape

```python
deanonymize_emails(
    emails=["alice@acme.com", "bob@gmail.com", ...],
)
```

For the consent phase (>10 emails, phase 1 only):

```python
deanonymize_emails(
    emails=[],
    total_count=50,
)
```

For phase 2 after consent:

```python
deanonymize_emails(
    emails=["alice@acme.com", ...],  # ≤25 per call
    total_count=50,                  # same value as phase 1 — required for token verification
    confirmation_token="<token from phase 1>",
)
```

## Output shape

```json
{
  "matched_count": 3,
  "unmatched_count": 1,
  "results": [
    {
      "email": "alice@acme.com",
      "matched": true,
      "full_name": "Alice Johnson",
      "first_name": "Alice",
      "last_name": "Johnson",
      "linkedin_url": "https://linkedin.com/in/alicejohnson",
      "current_title": "VP of Engineering",
      "current_company": "Acme Inc",
      "current_company_domain": "acme.com",
      "current_company_industry": "Software",
      "current_company_headcount": "500-1000",
      "location_country": "United States",
      "location_city": "San Francisco",
      "location_region": "California"
    },
    {
      "email": "unknown@random.com",
      "matched": false
    }
  ]
}
```

## The flow at a glance

| Email count | Flow |
|---|---|
| ≤ 10 | One call. No consent needed. |
| 11–25 | Phase 1 (consent) → wait for yes → Phase 2 (single call of ≤25). |
| > 25 | Phase 1 (consent) → wait for yes → Phase 2 (batched, **≤25 per call**). |

**Batching rule: every phase 2 call must contain ≤25 emails. Always split larger lists.**

## Small-batch shortcut (≤10 emails)

```python
deanonymize_emails(
    emails=["alice@acme.com", "bob@gmail.com", "carol@startup.io"]
)
```

No consent dance — go straight through.

## Two-phase flow (>10 emails)

### Phase 1 — Consent

Call once with `emails=[]` and `total_count=N`:

```python
deanonymize_emails(
    emails=[],
    total_count=80,
)
```

Server returns:

```json
{
  "status": "confirmation_required",
  "email_count": 80,
  "worst_case_credits": 80,
  "confirmation_token": "abc123...",
  "user_facing_message": "Reverse-enriching 80 emails will cost up to 80 credits (1 credit per match; misses are free). Do you want to proceed?"
}
```

**Required behavior:**

1. **Show `user_facing_message` exactly as returned.** Do not paraphrase the cost or wrap it in your own framing.
2. **Stop. Wait for explicit "yes" or equivalent approval.** The user's original request is **not** approval for the credit cost — they hadn't seen the price yet.
3. If the user says no or hesitates, stop. Do not look for a workaround.

### Phase 2 — Batched enrichment (≤25 per call)

After explicit yes, split the email list into chunks of **≤25** and call once per chunk. Each call must include the `confirmation_token` from phase 1.

```python
# 80 emails → 4 batches of 20, or 3 batches of 25 + 1 of 5, etc.
for batch in chunked(emails, 25):
    deanonymize_emails(
        emails=batch,
        total_count=80,              # same value as phase 1 on every call
        confirmation_token=token_from_phase_1,
    )
```

Accumulate results across all calls. Surface emails that came back `matched: false`.

## Hard rules

- **Never fabricate a `confirmation_token`.** Only use what phase 1 actually returned. A made-up token is rejected.
- **Never send more than 25 emails in a single call.** Split every list larger than 25.
- **Always pass `total_count` on every phase-2 call.** The server uses it to verify the token — omitting it causes a hard error.
- **Show `user_facing_message` verbatim.** Paraphrasing the cost defeats the consent flow.
- **Don't treat the original user request as approval** for credits they haven't seen yet.
- **Don't reuse a `confirmation_token` across unrelated requests.** Tokens are scoped to one approved batch.

## Common pitfalls

- **Sending 26+ emails in one call.** Always chunk at 25.
- **Skipping phase 1 for "just 12 emails".** The threshold is >10, not >25. Twelve triggers two-phase.
- **Omitting `total_count` in phase-2 calls.** It must match the value from phase 1 — the server verifies the token against it.
- **Paraphrasing `user_facing_message`.** Show it exactly — the wording was designed so the user understands what they're approving.
- **Using the user's original "do it" request as consent.** They said yes before seeing the cost. Get fresh approval after phase 1 returns the price.
- **Not accumulating results across batches.** Each call only returns its batch. Merge all results before presenting them.

## Worked examples

**5 emails (small batch).**
```
deanonymize_emails(emails=["a@x.com", "b@x.com", "c@gmail.com", "d@co.com", "e@co.com"])
```
One call, done. Render results.

**20 emails (needs consent, single phase-2 call).**
```
1. Phase 1: emails=[], total_count=20 → show user_facing_message verbatim. Stop.
2. User says "yes."
3. Phase 2: one call with all 20 emails, total_count=20, confirmation_token.
4. Render results.
```

**80 emails (needs consent, multiple phase-2 calls).**
```
1. Phase 1: emails=[], total_count=80 → show user_facing_message verbatim. Stop.
2. User says "yes."
3. Phase 2: 4 calls of ≤25 emails each (e.g. 25 + 25 + 25 + 5),
   each with total_count=80 + confirmation_token.
4. Accumulate, surface unmatched rows, render final table.
```

**Mixed personal and work emails.**
The tool handles Gmail, iCloud, Yahoo, and work addresses uniformly — no special handling needed. Just pass them all in the same list.

## What this skill does NOT do

- It doesn't find emails — that's `contact-data-enrichment`.
- It doesn't score or rank prospects — that's `ai-prospecting`.
- It doesn't resolve identity from a name — that's `match-person`.
- It doesn't bypass consent. There is no "force" flag.
