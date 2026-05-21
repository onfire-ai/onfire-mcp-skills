# Signals from Snowflake

All signals come from three Snowflake tables, **filtered to the last 90 days** (3 months). The
platform `signals` table is only accessible via Metabase and `mcp__metabase__execute_query` is
unreliable in current MCP setups. Always use Snowflake.

## The three signal tables

| Table | What's in it | Tenant filter | Time filter |
|---|---|---|---|
| `SILVER.SIGNALS.ARTIFACTS` | All structured signal artifacts (job changes, promotions, website visitors, event attendees, GitHub activity, hiring-manager moves) | `TENANT = '<tenant>'` | `ARTIFACT_TIME >= DATEADD(day, -90, CURRENT_DATE())` |
| `silver.community_messages.int_messages_with_linkedin` | Community + forum messages (Reddit, HN, Stack Overflow, Discord, Slack communities) with LinkedIn-identified senders | No tenant column — global. Filter by sender/company against the customer's ICP keywords from `tenant_settings`. | `TIMESTAMP >= DATEADD(day, -90, CURRENT_DATE())` |
| `silver.job_post.stg_job_posts` | Raw job postings — hiring-intent signal when a company is hiring for an ICP-relevant role | No tenant column — global. Filter by `COMPANY_LINKEDIN_URL` IN (the customer's tracked accounts) + `JOB_POST_TITLE` matching the customer's win-pattern persona keywords. | `DATE_POSTED >= DATEADD(day, -90, CURRENT_DATE())` |

## The canonical signal-type taxonomy

Pulled live from `SILVER.SIGNALS.ARTIFACT_TYPES`. Eleven types as of this writing:

| ID | `ARTIFACT_TYPE` | Display name | Use it for |
|---|---|---|---|
| 2 | `change_company` | Company Change | Champion-moved job-change signal on existing CRM contacts |
| 3 | `new_hire` | New Hire | Buyer just joined an ICP account |
| 4 | `promotion` | Promotion | Existing champion got more budget authority |
| 5 | `role_change` | Role Change | Existing CRM contact has a new title |
| 6 | `hiring_manager` | LinkedIn Job Post | Hiring-manager signal tied to a job post |
| 7 | `account_website_visitor` | Account Visitor | Account-level visit to the tenant's website |
| 8 | `contact_website_visitor` | Prospect Visitor | Contact-level visit (resolved to a LinkedIn URL) |
| 9 | `event_attendee` | Event Attendee | Speaker or attendee at a tracked event |
| 10 | `github_repo_activity` | Github Repo Activity | Starred / forked the tenant's repo |
| 101 | `customer_champion_island` | Champion Move | Tenant-specific (Island POC pattern) |
| 201 | `ex_customer_hire_island` | Ex-Customer Hire | Tenant-specific (Island POC pattern) |

Always derive the list by querying `ARTIFACT_TYPES` at run time — don't hardcode IDs. New types
get added; the customer-facing report should adapt automatically.

## The hero signal strip — six diversified types

The Hero "live examples of the signal types Onfire tracks for you" strip must show **6 cards
across 2 rows**, drawing from across the three signal sources and across multiple artifact
types. Pick one example per type, with a mix that includes at least one of each:

1. **Competitor mention** — a `contact_website_visitor` or `account_website_visitor` artifact
   where the visitor's `COMPANY_LINKEDIN_URL` matches the customer's
   `signals_settings.excluded_companies.linkedin_urls` (competitor list). Border `.re-src` red.
2. **Product-page intent** — a website-visitor artifact where `ARTIFACT_TEXT` references a
   high-intent URL path (e.g. `/use-case/`, `/pricing/`, a specific product page in the
   tenant's site). Border `.pu-src` purple.
3. **Generic website visit** — a website-visitor artifact with a high-fit visitor profile
   (CISSP / security title at an ICP company). Border `.tl-src` teal.
4. **Event speaker / attendee** — an `event_attendee` artifact OR the `events` field on an
   AI Prospecting prospect. Border `.tl-src` teal.
5. **Job change on champion** — a `change_company` / `promotion` / `role_change` artifact OR
   a `match_person` finding where the contact's current company ≠ CRM AccountName. Border
   `.pu-src` purple.
6. **Hiring signal** — a `stg_job_posts` row for an ICP account hiring an ICP-relevant role,
   OR a `hiring_manager` artifact. Border `.pu-src` purple.

Never claim a specific total volume in the Hero ("X signals in the last N days") — the user
explicitly rejected that. Use "Live examples of the signal types Onfire tracks for you."

The Contact Data Gap section shows **3 cards** (subset of the hero), diversified:
1 website visit + 1 product-page intent + 1 event speaker. Don't repeat the same
examples — pick fresh ones.

## Canonical queries

### A. Artifacts — last 3 months, all types, joined to display name

```sql
SELECT a.ARTIFACT_TIME::DATE AS day,
       a.COMPANY_LINKEDIN_URL,
       a.CONTACT_LINKEDIN_URL,
       t.ARTIFACT_TYPE,
       t.ARTIFACT_TYPE_DISPLAY_NAME,
       SUBSTR(a.ARTIFACT_TEXT, 1, 500) AS artifact_text,
       a.SOURCE_LINK
FROM SILVER.SIGNALS.ARTIFACTS a
LEFT JOIN SILVER.SIGNALS.ARTIFACT_TYPES t
  ON a.ARTIFACT_TYPE_ID = t.ARTIFACT_TYPE_ID
WHERE a.TENANT = '<tenant>'
  AND a.ARTIFACT_TIME >= DATEADD(day, -90, CURRENT_DATE())
  AND a.ARTIFACT_TEXT IS NOT NULL
ORDER BY a.ARTIFACT_TIME DESC
LIMIT 50
```

`SUMMARY` is often NULL — use `ARTIFACT_TEXT`. Some tenants only have `account_website_visitor`
+ `contact_website_visitor`; others have richer coverage. Check the type distribution first:

```sql
SELECT t.ARTIFACT_TYPE_DISPLAY_NAME, t.ARTIFACT_TYPE, COUNT(*) AS n
FROM SILVER.SIGNALS.ARTIFACTS a
LEFT JOIN SILVER.SIGNALS.ARTIFACT_TYPES t ON a.ARTIFACT_TYPE_ID = t.ARTIFACT_TYPE_ID
WHERE a.TENANT = '<tenant>'
  AND a.ARTIFACT_TIME >= DATEADD(day, -90, CURRENT_DATE())
GROUP BY 1, 2 ORDER BY n DESC
```

### B. Community messages — last 3 months, ICP-keyword filtered

```sql
SELECT m.TIMESTAMP::DATE AS day,
       m.SENDER_NAME,
       m.SENDER_LINKEDIN,
       m.COMMUNITY_NAME,
       m.COMMUNITY_TYPE,
       m.CHANNEL_NAME,
       SUBSTR(m.MESSAGE_TEXT, 1, 500) AS message_text,
       m.URL
FROM SILVER.COMMUNITY_MESSAGES.INT_MESSAGES_WITH_LINKEDIN m
WHERE m.TIMESTAMP >= DATEADD(day, -90, CURRENT_DATE())
  AND m.MESSAGE_TEXT IS NOT NULL
  AND m.SENDER_LINKEDIN IS NOT NULL
  AND (
    -- ICP keyword filter — derive from tenant_settings.account_research.queries_sections
    -- (technologies + competitors + organization), pipe-joined into one big regex
    REGEXP_LIKE(m.MESSAGE_TEXT,
      '.*(<tech1>|<tech2>|<competitor1>|<competitor2>|<persona1>).*', 'i')
  )
ORDER BY m.TIMESTAMP DESC
LIMIT 25
```

Community messages are gold for **high-intent / competitor-mention** signals — when a person on
LinkedIn posts about evaluating Splunk SOAR vs Tines, that's a buying-intent signal. Filter on
keywords from the customer's own `account_research.queries_sections` config (competitors +
technologies + buying-committee personas).

### C. Job posts — last 3 months, ICP-account filtered

```sql
SELECT j.DATE_POSTED::DATE AS day,
       j.COMPANY_NAME,
       j.COMPANY_LINKEDIN_URL,
       j.JOB_POST_TITLE,
       j.JOB_FUNCTION,
       j.SENIORITY_JOB,
       j.LOCATION,
       j.EXTERNAL_URL
FROM SILVER.JOB_POST.STG_JOB_POSTS j
WHERE j.DATE_POSTED >= DATEADD(day, -90, CURRENT_DATE())
  AND j.APPLICATION_ACTIVE = 1
  AND (
    -- Persona-keyword filter on JOB_POST_TITLE
    REGEXP_LIKE(j.JOB_POST_TITLE,
      '.*(security|ciso|soc|cyber|detection|threat|devsecops|<custom>).*', 'i')
  )
  -- Optional: restrict to customer's tracked accounts
  AND j.COMPANY_LINKEDIN_URL IN (
    -- Pull from SF Account LinkedIn URLs OR from a top-pipeline-accounts list
  )
ORDER BY j.DATE_POSTED DESC
LIMIT 25
```

The persona-keyword filter comes from the customer's own win-pattern (Step 4 of SKILL.md) —
the personas that *win* deals are the same ones whose hiring postings indicate the company is
investing in that capability.

## When `mcp__metabase__execute_query` *does* work

If a future MCP version restores Metabase, the canonical platform query is:

```sql
SELECT acc.name, acc.website, acc.industry, acc.employees, acc.headquarters, acc.linkedin_url,
       s.long_summary, s.intent_holder_linkedin_url, s.date, s.source_type, s.source_link,
       s.message_text, c.name AS contact_name, c.job_title, c.location, acc.last_update_date
FROM accounts acc
LEFT JOIN signals s ON acc.tenant_id = s.tenant_id AND acc.website = s.account_website
LEFT JOIN contacts c ON acc.tenant_id = c.tenant_id AND acc.website = c.account_website
                    AND c.reason = 'Intent' AND s.intent_holder_linkedin_url = c.contact_linkedin_url
WHERE acc.tenant_id = '<tenant>'
  AND s.date >= CURRENT_DATE - INTERVAL '90 days'
```

That returns the platform's curated `long_summary` text (cleaner than `ARTIFACT_TEXT` from
Snowflake). Prefer it when available — fall back to the three Snowflake tables when Metabase
fails.
