---
name: search-contact-by-email
description: >-
  Find the contact profile behind a list of business email addresses — name, LinkedIn URL, current title, employer, location — using the Onfire `search_contact_by_email` tool. Use when the user has a list of work email addresses and wants to know who they belong to. Business domains only: personal mailboxes (Gmail, iCloud, Yahoo and other consumer providers) are declined and never charged for. PAID per successful match — has a strict two-phase consent flow above 10 addresses.
---

# search_contact_by_email (atomic)

Reverse email lookup: turns a business email address into the contact profile behind it — name, LinkedIn URL, current title, employer, location. **Paid: 5 credits per successful match. Misses are free.**

## Business domains only

The tool looks up company email addresses. A personal mailbox — Gmail, iCloud, Yahoo, Outlook, Proton and the other consumer providers — is declined before the lookup runs: it is never resolved to a person and never charged for, and it comes back in a `skipped` block rather than as a failed match.

Send mixed lists as they are. There is no need to filter them first, and no cost to leaving a personal address in.

## Communication style

Never expose implementation internals to the user. Do not mention thresholds, batch sizes, consent phases, confirmation tokens, or any other mechanics of how the tool works. The user should only see: the results, the skipped addresses, or (when required) the confirmation message from phase 1.

**Wrong:** "Only 3 addresses — well under the 10-address threshold, so I can call directly without the consent phase."
**Right:** Just call the tool and show the results.

**Wrong:** "The tool returned a `skipped` block with 4 entries."
**Right:** "Four of these are personal addresses, which this doesn't cover — here's who the other eleven are."

Skipped addresses are a result, not a mechanic. The user asked who those people are, so tell them which ones could not be looked up and why. Never present a skipped address as an unidentified person: it was not searched for.

## When to use this

- User has a list of work email addresses and wants to know who owns them.
- You need to tie an inbound email to a company or role.
- Pre-step before reaching out — you have addresses but no identity context.

## Input shape

```python
search_contact_by_email(
    emails=["alice@acme.com", "dana@example.com", ...],
)
```

For the consent phase (>10 addresses, phase 1 only):

```python
search_contact_by_email(
    emails=[],
    total_count=50,
)
```

For phase 2 after consent:

```python
search_contact_by_email(
    emails=["alice@acme.com", ...],  # up to 500 per call
    total_count=50,                  # same value as phase 1 — required for token verification
    confirmation_token="<token from phase 1>",
)
```

## Output shape

```json
{
  "matched_count": 2,
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
  ],
  "skipped": {
    "count": 1,
    "emails": ["bob@gmail.com"],
    "reason": "Personal mailbox address. This tool looks up business-domain addresses only, so these were not looked up and were not charged."
  }
}
```

`skipped` is present only when the list contained a personal address.

## The flow at a glance

| Business addresses | Flow |
|---|---|
| ≤ 10 | One call. No consent needed. |
| > 10 | Phase 1 (consent) → wait for yes → Phase 2. |
| > 500 | Phase 1, then split phase 2 into calls of ≤500. |

**The threshold counts the business addresses only.** A list of twelve where ten are Gmail is two lookups, so it goes straight through with no consent phase.

## Small-batch shortcut (≤10 business addresses)

```python
search_contact_by_email(
    emails=["alice@acme.com", "dana@example.com", "carol@startup.io"]
)
```

No consent dance — go straight through.

## Two-phase flow (>10 business addresses)

### Phase 1 — Consent

Call once with `emails=[]` and `total_count=N`:

```python
search_contact_by_email(
    emails=[],
    total_count=80,
)
```

Server returns:

```json
{
  "status": "confirmation_required",
  "email_count": 80,
  "confirmation_token": "abc123...",
  "user_facing_message": "You're about to look up 80 email addresses — that's a large batch. Want to go ahead, or start with a smaller set first?"
}
```

**Required behavior:**

1. **Show `user_facing_message` exactly as returned.** Do not paraphrase it or wrap it in your own framing.
2. **Stop. Wait for explicit "yes" or equivalent approval.** The user's original request is **not** approval — they had not seen the volume yet.
3. If the user asks what it costs, answer accurately: 5 credits per successful match, misses and skipped addresses free. Do not volunteer a credit figure the tool did not give you.
4. If the user says no or hesitates, stop. Do not look for a workaround.

### Phase 2 — Enrichment

After explicit yes, send the addresses with the `confirmation_token` from phase 1. Up to 500 per call; split anything longer.

```python
search_contact_by_email(
    emails=all_addresses,            # ≤500; chunk a longer list
    total_count=80,                  # same value as phase 1 on every call
    confirmation_token=token_from_phase_1,
)
```

Accumulate results across calls. Surface addresses that came back `matched: false`, and the `skipped` list separately.

## While the job is still running

A large batch may come back mid-flight:

```json
{
  "status": "still_running",
  "continuation_token": "...",
  "pending_batches": 2
}
```

Call the tool again with that token and an empty list to keep polling the same job. It does not re-submit and is not charged again:

```python
search_contact_by_email(emails=[], continuation_token="<token from the response>")
```

Repeat until you get a response carrying `matched_count` / `results`. Wait a few seconds between calls.

## Hard rules

- **Never fabricate a `confirmation_token` or a `continuation_token`.** Only use what the server actually returned. A made-up token is rejected.
- **Never send more than 500 addresses in a single call.** Split every longer list.
- **Always send `total_count` on every phase-2 call.** The server uses it to verify the token — omitting it causes a hard error.
- **Show `user_facing_message` verbatim.** Paraphrasing defeats the consent flow.
- **Don't treat the original user request as approval** for a volume they haven't seen yet.
- **Don't reuse a `confirmation_token` across unrelated requests.** Tokens are scoped to one approved batch.
- **Don't try to route a personal address around the restriction.** There is no flag for it, and guessing a work address for the same person is not the same answer.

## Common pitfalls

- **Counting personal addresses toward the threshold.** Only the business ones are looked up, so only they decide whether consent is needed.
- **Reporting a skipped address as "not found".** It was never searched. Say it is a personal address and that the tool covers work addresses.
- **Skipping phase 1 for "just 12 addresses".** The threshold is >10. Twelve business addresses trigger two-phase.
- **Omitting `total_count` in phase-2 calls.** It must match the value from phase 1 — the server verifies the token against it.
- **Paraphrasing `user_facing_message`.** Show it exactly.
- **Treating `still_running` as a failure.** It is a job in flight; poll it with the continuation token.
- **Not accumulating results across batches.** Each call only returns its own; merge before presenting.

## Worked examples

**5 business addresses (small batch).**
```
search_contact_by_email(emails=["a@x.com", "b@x.com", "c@co.com", "d@co.com", "e@co.com"])
```
One call, done. Render results.

**20 business addresses (needs consent).**
```
1. Phase 1: emails=[], total_count=20 → show user_facing_message verbatim. Stop.
2. User says "yes."
3. Phase 2: one call with all 20, total_count=20, confirmation_token.
4. Render results.
```

**800 business addresses (needs consent, multiple phase-2 calls).**
```
1. Phase 1: emails=[], total_count=800 → show user_facing_message verbatim. Stop.
2. User says "yes."
3. Phase 2: 2 calls (500 + 300), each with total_count=800 + confirmation_token.
4. Accumulate, surface unmatched rows, render final table.
```

**Mixed personal and work addresses.**
```
search_contact_by_email(emails=["alice@acme.com", "bob@gmail.com", "carol@startup.io"])
```
Send them all. Alice and Carol are looked up; Bob comes back under `skipped` and costs nothing. Tell the user that Bob's is a personal address and this covers work addresses — don't present him as unidentified.

## What this skill does NOT do

- It doesn't look up personal mailboxes. That is out of scope by design, not a limitation to work around.
- It doesn't find emails — that's `contact-data-enrichment`.
- It doesn't score or rank prospects — that's `ai-prospecting`.
- It doesn't resolve identity from a name — that's `match-person`.
- It doesn't bypass consent. There is no "force" flag.
