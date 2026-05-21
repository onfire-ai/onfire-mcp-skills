# Signals from Snowflake

The platform `signals` table is only accessible via Metabase. Metabase `execute_query` returns
"Illegal base64 character 20" intermittently in current MCP setups. **Always use Snowflake.**

## Tables

| Snowflake table | Purpose |
|---|---|
| `SILVER.SIGNALS.ARTIFACTS` | Website-visitor + (a few other) artifact signals per tenant. Filter on `TENANT = '<tenant_id>'`. |
| `SILVER.SIGNALS.ARTIFACT_TYPES` | Lookup for artifact-type display names. Join on `ARTIFACT_TYPE_ID`. |
| `SILVER.SIGNALS.JOB_POST` | Global (tenant-agnostic) job posts. Filter by `COMPANY_LINKEDIN_URL` + role keywords from the tenant's `queries_sections.organization`. |
| `GOLD.ENTITIES.PEOPLE` | Used to derive job-change signals via `match_person` comparison. |

## The base query for website-visitor + product-page signals

```sql
SELECT a.ARTIFACT_TIME::DATE AS day,
       a.COMPANY_LINKEDIN_URL,
       a.CONTACT_LINKEDIN_URL,
       t.ARTIFACT_TYPE_DISPLAY_NAME,
       t.ARTIFACT_TYPE,
       SUBSTR(a.ARTIFACT_TEXT, 1, 500) AS artifact_text,
       a.SOURCE_LINK
FROM SILVER.SIGNALS.ARTIFACTS a
LEFT JOIN SILVER.SIGNALS.ARTIFACT_TYPES t
  ON a.ARTIFACT_TYPE_ID = t.ARTIFACT_TYPE_ID
WHERE a.TENANT = '<tenant_id>'
  AND a.ARTIFACT_TIME >= DATEADD(day, -60, CURRENT_DATE())
  AND a.ARTIFACT_TEXT IS NOT NULL
  AND a.COMPANY_LINKEDIN_URL IS NOT NULL
ORDER BY a.ARTIFACT_TIME DESC
LIMIT 25
```

**Pitfalls:**
- `SUMMARY` column is often NULL — use `ARTIFACT_TEXT` instead.
- Different tenants have different signal-type coverage. Torq only has `account_website_visitor`
  (2,186 / 60d) and `contact_website_visitor` (583 / 60d). No artifacts of type
  community-message, blog-post, podcast, etc. for Torq.
- Don't filter on `CONTACT_LINKEDIN_URL IS NOT NULL` if you want all signals — many
  account-level visits don't have a contact resolved yet.

## The six signal types the Hero strip must show

The report deliberately surfaces six diversified signal types. Some come from artifacts, some
from other Onfire surfaces:

| # | Type | Source | Card border |
|---|---|---|---|
| 1 | ⚠ Competitor mention | Artifact where the visitor's `COMPANY_LINKEDIN_URL` matches the tenant's `signals_settings.excluded_companies.linkedin_urls` (competitor list) | `.re-src` red |
| 2 | ★ High-intent product page | Artifact where `ARTIFACT_TEXT` mentions a specific product URL (`/use-case/...`, `/ai-soc-automation/`, etc.) | `.pu-src` purple |
| 3 | → Website visit | Generic visitor artifact, no special tag | `.tl-src` teal |
| 4 | ★ Event speaker mention | `ai_prospecting` output's `events` array on a sampled prospect (e.g. "listed on the official agenda to speak at Google Next 2026") | `.tl-src` teal |
| 5 | ★ Job change — champion moved | `match_person` result where `company_name` ≠ CRM AccountName, picked from the sampled contact run | `.pu-src` purple |
| 6 | ★ Hiring signal | `SILVER.SIGNALS.JOB_POST` filtered by ICP-relevant role keywords on a top-pipeline / top-won-industry account | `.pu-src` purple |

For Torq's signal strip in the Hero, we used the actual data found in the live run:
1. David Irwin @ Swimlane (competitor) — from artifacts
2. Kripal P. @ Bloomberg on /ai-soc-automation/ — from artifacts (product-page intent)
3. Ryan Ettl, CISSP @ Infoblox — from artifacts (generic visit)
4. Jacob Silva @ Walmart speaking at Google Next 2026 — from AI Prospecting `events`
5. James Zhou moved Meet Group → noom — from `match_person` result
6. United Health Group posting Detection Engineer + SOAR roles — from hiring signal pattern

## Never claim a specific signal count in the Hero

Don't write "2,769 intent signals in the last 60 days." The user explicitly rejected that.
Instead use: "Live examples of the signal types Onfire tracks for you." Let the cards speak.

## The Contact Data Gap signal strip (3 cards, separate examples)

Don't reuse the Hero strip's examples. The Contact Data Gap section's signal strip shows
**exactly 3 cards** with diverse types:
- 1 website visit
- 1 product-page intent (use-case page)
- 1 event speaker

For Torq we used: Sean Roche @ Obsidian (/blog/), Lya Kimbrough @ Urban League (/use-case/JIT/),
Jacob Silva @ Walmart (Google Next 2026 speaker).

## When metabase `execute_query` *does* work

If a future run shows Metabase access returning real results, the canonical signals query from
the user is:

```sql
SELECT acc.name, acc.website, acc.industry, acc.employees, acc.headquarters, acc.linkedin_url,
       s.long_summary, s.intent_holder_linkedin_url, s.date, s.source_type, s.source_link,
       s.message_text, c.name AS contact_name, c.job_title, c.location, acc.last_update_date
FROM accounts acc
LEFT JOIN signals s ON acc.tenant_id = s.tenant_id AND acc.website = s.account_website
LEFT JOIN contacts c ON acc.tenant_id = c.tenant_id AND acc.website = c.account_website
                    AND c.reason = 'Intent' AND s.intent_holder_linkedin_url = c.contact_linkedin_url
WHERE acc.tenant_id = '<tenant>'
```

That returns prettier `long_summary` text (the platform's curated signal summary) versus the
raw `ARTIFACT_TEXT` from Snowflake. Prefer it when available — fall back to Snowflake when
Metabase fails.
