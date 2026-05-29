---
name: match-person
description: Resolve a person (from name, email, and/or company context) to a verified LinkedIn profile plus current title and employer using the Onfire `match_person` tool. Use when you have a person reference but no LinkedIn URL, when CRM contacts need identity resolution before enrichment, or as the upstream step before `ai_prospecting(action="get_prospect")` or `contact_data_enrichment` on rows missing LinkedIn URLs.
---

# match_person (atomic)

Resolves people via Onfire's Matchbox2 engine. Vector search + AI matching, so it handles "Lana P. at Frostbyte" or just an email alias.

## When to use this

- You have a person but no LinkedIn URL and need to score them.
- A list of CRM contacts needs LinkedIn URLs before enrichment.
- You want to verify the person at a company (e.g. confirm they still work there).

Skip this if you already have a clean person LinkedIn URL and the user isn't asking you to verify identity.

## Input shape

```python
match_person(entities=[
    {"person_full_name": "John Smith", "company_name": "Acme Inc"},
    {"person_email": "jane@techcorp.com"},
    {"person_full_name": "Lana Patel", "company_name": "Frostbyte", "job_title": "VP Eng"},
    {"person_full_name": "Alex K.", "company_name": "Northwind", "company_linkedin_url": "https://linkedin.com/company/northwind"},
])
```

Available fields per entry:

- `person_full_name`
- `person_email`
- `company_name`
- `job_title` *(improves accuracy)*
- `company_linkedin_url` *(improves accuracy)*
- `company_website` *(improves accuracy)*

**Minimum:** at least one of `person_full_name` or `person_email`. If you only have a name (no email), `company_name` is **required** — the matcher refuses name-only lookups because they're too ambiguous.

**Batch cap: 100 entries per call.**

## Output shape

```json
{
  "total_count": N,
  "matched_count": M,
  "results": [
    {
      "matched": true,
      "linkedin_url": "https://linkedin.com/in/...",
      "full_name": "John Smith",
      "job_title": "VP Sales",
      "company_name": "Acme Inc",
      "company_linkedin_url": "https://linkedin.com/company/acme",
      "company_website": "acme.com",
      "match_score": 0.91,
      "match_type": "semantic_match"
    },
    ...
  ]
}
```

Same-order alignment with the input. The output already includes `company_linkedin_url` — if you got it back, you usually don't need a separate `match_company` call before `ai_prospecting`.

## Hard rules

- Batch ≤ 100 per call.
- Name without email **requires** `company_name`.
- Surface low-confidence matches (`match_score` low, `matched: false`). Ask the user to confirm rather than silently picking the top result.
- Pass every signal you have. `job_title` and `company_linkedin_url` materially improve accuracy.

## Common pitfalls

- **Skipping `company_name` on a name-only lookup.** The tool will refuse — fix the input rather than retrying blindly.
- **Throwing away the returned `company_linkedin_url`.** It saves you a `match_company` call when you go on to `ai_prospecting(action="get_prospect")`.
- **Conflating low `match_score` with "no such person".** Often it just means the signals were thin. Add `job_title` or company website and retry.

## Worked examples

**Person + score in one shot.**
```
match_person(entities=[{
    "person_full_name": "Lana Patel",
    "company_name": "Frostbyte",
    "job_title": "VP Eng"
}])
```
Use the returned `linkedin_url` and `company_linkedin_url` for `ai_prospecting(action="get_prospect", ...)`.

**Bulk CRM resolve.**
```python
match_person(entities=[
    {"person_full_name": row["name"], "person_email": row["email"], "company_name": row["account"]}
    for row in csv_rows
])
```
Then filter `matched: true` rows for the next step.

**Email-only.**
```
match_person(entities=[{"person_email": "ceo@startup.io"}])
```
Works without name or company. Useful for inbound lead lists.

## What this skill does NOT do

- It doesn't score the person — that's `ai-prospecting` (action `get_prospect`).
- It doesn't resolve companies on their own — that's `match-company`.
- It doesn't return emails or phones — that's `contact-data-enrichment`.
