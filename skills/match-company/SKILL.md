---
name: match-company
description: Resolve a company (from name, website, or LinkedIn URL) to a verified LinkedIn URL plus firmographics using the Onfire `match_company` tool. Use when you have any starting signal about a company — a name, a website, a CRM row, a LinkedIn URL you want to verify — and need a canonical identity. Also use as the upstream step before any `ai_prospecting` call that doesn't already have a company LinkedIn URL.
---

# match_company (atomic)

Resolves companies via Onfire's Matchbox2 engine. Vector search + AI matching, so partial / fuzzy / messy names work.

## When to use this

- You have a company name, website, or LinkedIn URL and need the verified LinkedIn URL.
- You need to normalize or de-dupe a CRM list against a canonical identity.
- You're about to call `ai_prospecting` and don't have a company LinkedIn URL yet — call this first.

Skip this if the user already handed you a clean company LinkedIn URL and isn't asking you to verify it.

## Input shape

```python
match_company(companies=[
    {"names": ["Acme Inc"]},
    {"websites": ["techcorp.com"]},
    {"linkedin_urls": ["https://linkedin.com/company/acme"]},
    {"names": ["StartupCo", "Startup Co."], "websites": ["startup.io"]},  # multi-signal
])
```

Each entry can mix `names`, `websites`, and `linkedin_urls` (all are arrays — accept multiple variants per field). At least one signal is required. **More signals → better match accuracy.** If the user gave you both a name and a website, pass both.

**Batch cap: 100 entries per call.** For lists longer than 100, chunk them.

## Output shape

```json
{
  "total_count": N,
  "matched_count": M,
  "results": [
    {
      "matched": true,
      "name": "Acme Inc",
      "website": "acme.com",
      "linkedin_url": "https://linkedin.com/company/acme",
      "linkedin_id": "...",
      "size": "1001-5000",
      "found_employee_count": 1247,
      "cosine_similarity": 0.94,
      "match_type": "semantic_match",
      "match_reason": "..."
    },
    ...
  ]
}
```

Results are returned **in the same order** as the input — index alignment matters when you batch.

## Hard rules

- Batch ≤ 100 per call.
- At least one of `names` / `websites` / `linkedin_urls` per entry.
- Don't silently propagate low-confidence matches. If `matched: false` or `cosine_similarity` looks weak (rough threshold ~0.7, but read `match_reason` too), surface it: *"I think you mean X but I'm only ~60% sure — confirm or pick another?"* Wrong identity here corrupts every downstream prospecting result.

## Common pitfalls

- **Sending one signal when you have two.** If the user mentioned both name and website, putting them in the same entry (not two separate entries) gives a much better match.
- **Treating `matched: false` as a hard failure.** It usually means weak signal — try again with another variant of the name, or ask the user.
- **Forgetting same-order alignment.** When you batch 80 rows from a CSV, the result array maps 1:1 to the input — don't reshuffle without the index.

## Worked examples

**Single name → LinkedIn URL.**
```
match_company(companies=[{"names": ["Pathwatch"]}])
```
Use the returned `linkedin_url` as the input to `ai_prospecting`.

**CSV of 40 accounts (name + website columns).**
```python
match_company(companies=[
    {"names": [row["company_name"]], "websites": [row["website"]]}
    for row in csv_rows
])
```
After the call, filter `results` to `matched: true` for downstream calls; surface the unmatched rows back to the user so they can fix or drop them.

**Verifying a LinkedIn URL.**
```
match_company(companies=[{"linkedin_urls": ["https://linkedin.com/company/acme-inc"]}])
```
Use the returned firmographics to confirm the user is on the right entity (size, region) before scoring.

## What this skill does NOT do

- It doesn't run prospecting — that's `ai-prospecting`.
- It doesn't resolve people — that's `match-person`.
- It doesn't enrich emails / phones — that's `contact-data-enrichment`.
