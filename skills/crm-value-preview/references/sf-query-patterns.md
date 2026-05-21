# Salesforce Query Patterns

All Salesforce queries go through `integration_proxy`, not Metabase. The Metabase
`execute_query` tool returns "Illegal base64 character 20" intermittently and is unreliable.

**Field-candidate taxonomy lives in the sibling skill:
[`../../poc-intelligence/references/sf-soql-patterns.md`](../../poc-intelligence/references/sf-soql-patterns.md).**
That doc maintains the canonical list of which SF custom fields stand for ARR / Amount / Stage
/ Owner / Last Activity across different tenants (e.g. `Net_New_ARR__c` vs `ACV__c` vs `MRR__c`).
This doc captures the *tested SOQL we know works through `integration_proxy`* + *the pitfalls we
hit during the Torq run*; field-name discovery uses poc-intelligence's canonical list.

## The canonical call shape

```
integration_proxy(
  integration_id=<from tenant_settings.crm.integration_id>,
  http_method='GET',
  relative_url='query',                                    # NOT 'services/data/v62.0/query'
  params={'q': '<SOQL>'},
  telemetry={'intent': '...'}
)
```

The proxy prepends the API base path. Passing the full `services/data/v62.0/query` results in
404 because it gets concatenated to the existing prefix.

## SOQL pitfalls we hit during the Torq run

| Error | Cause | Fix |
|---|---|---|
| `only aggregate expressions use field aliasing` | Aliasing non-aggregate fields in a relationship query | Drop the aliases; rename columns at parse time |
| `only root queries support aggregate expressions` | Subquery COUNT inside a SELECT projection | Split into two queries, join in memory |
| `The inner and outer selects should not be on the same object type` | `NOT IN (SELECT ... FROM SameObject)` | Restructure — Salesforce requires cross-object subqueries |
| `missing value at 'GROUP'` | `IN (SELECT ... GROUP BY ... HAVING ...)` — Salesforce doesn't support GROUP BY in semi-joins | Issue the GROUP BY as a top-level query, then re-query with the resulting list |

## Funnel + volume

```sql
-- Volume KPIs
SELECT COUNT(Id) FROM Account WHERE IsDeleted = false
SELECT COUNT(Id) FROM Contact WHERE IsDeleted = false
SELECT COUNT(Id) FROM Lead WHERE IsDeleted = false AND IsConverted = false
SELECT COUNT(Id) FROM Opportunity WHERE IsDeleted = false

-- Open-pipeline ARR
SELECT COUNT(Id) AS total_opps, SUM(Amount) AS total_arr
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = false

-- Closed-last-12mo split by won/lost
SELECT IsWon, COUNT(Id) AS cnt, SUM(Amount) AS amt
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = true AND CloseDate = LAST_N_DAYS:365
GROUP BY IsWon

-- True duplicate count
SELECT COUNT(Id) AS total, COUNT_DISTINCT(Website) AS clusters
FROM Account
WHERE IsDeleted = false AND Website != null AND Website != 'Unknown'
-- Redundant records = total - clusters
```

## Gap KPIs

```sql
-- Stale-90d accounts
SELECT COUNT(Id) FROM Account
WHERE IsDeleted = false
  AND (LastActivityDate = null OR LastActivityDate < LAST_N_DAYS:90)

-- No-contact accounts (this NOT-IN works because subject is Account, subquery is Contact)
SELECT COUNT(Id) FROM Account
WHERE IsDeleted = false
  AND Id NOT IN (SELECT AccountId FROM Contact WHERE IsDeleted = false AND AccountId != null)

-- Stalled open opps (30d)
SELECT COUNT(Id) FROM Opportunity
WHERE IsClosed = false AND IsDeleted = false
  AND (LastActivityDate = null OR LastActivityDate < LAST_N_DAYS:30)

-- Missing-industry accounts
SELECT COUNT(Id) FROM Account
WHERE IsDeleted = false AND (Industry = null OR Industry = '')

-- Contacts missing email
SELECT COUNT(Id) FROM Contact
WHERE IsDeleted = false AND (Email = null OR Email = '')

-- Contacts missing both phone fields
SELECT COUNT(Id) FROM Contact
WHERE IsDeleted = false
  AND (Phone = null OR Phone = '')
  AND (MobilePhone = null OR MobilePhone = '')
```

## Duplicate clusters

```sql
-- Top duplicate clusters by website (exclude placeholder "Unknown")
SELECT Website, COUNT(Id) AS cnt
FROM Account
WHERE IsDeleted = false
  AND Website != null
  AND Website != 'Unknown' AND Website != 'unknown'
GROUP BY Website
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
LIMIT 200

-- Same-(Name, Website) clusters — the most embarrassing duplicates
SELECT Name, Website, COUNT(Id) AS cnt
FROM Account
WHERE IsDeleted = false
  AND Website != null AND Website != 'Unknown'
GROUP BY Name, Website
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
LIMIT 30
```

When picking display examples, exclude regional structures: Accenture (regional offices), NBA
(team subsidiaries), MLB (teams), EY (regional service lines), BT (regional units). Keep only
pure-name duplicates.

## Close-won analysis (drives the entire Open Pipeline tab)

```sql
-- Winning industries by ARR
SELECT Account.Industry, COUNT(Id) AS cnt, SUM(Amount) AS amt
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = true AND IsWon = true
GROUP BY Account.Industry
ORDER BY SUM(Amount) DESC NULLS LAST
LIMIT 10

-- Winning personas (security-only filter; adjust per tenant)
SELECT Title, COUNT(Id) AS cnt
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN (
    SELECT AccountId FROM Opportunity
    WHERE IsWon = true AND IsClosed = true
  )
  AND (Title LIKE '%CISO%' OR Title LIKE '%Security%' OR Title LIKE '%SOC%'
       OR Title LIKE '%Cyber%' OR Title LIKE '%DevSec%' OR Title LIKE '%Detection%'
       OR Title LIKE '%Threat%' OR Title LIKE '%Information Security%')
GROUP BY Title ORDER BY COUNT(Id) DESC LIMIT 30

-- Contacts-per-won-account distribution (for win-pattern average)
SELECT AccountId, COUNT(Id) AS c
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN (
    SELECT AccountId FROM Opportunity
    WHERE IsWon = true AND IsClosed = true
  )
GROUP BY AccountId
ORDER BY COUNT(Id) DESC
LIMIT 200
```

## Top open opps + per-account coverage

```sql
-- Top open opps by ARR
SELECT Id, Name, Amount, StageName, CloseDate, AccountId,
       Account.Name, Account.Website, Account.Industry
FROM Opportunity
WHERE IsClosed = false AND IsDeleted = false AND Amount > 200000
ORDER BY Amount DESC LIMIT 30

-- Total contacts per opp's account (batch all AccountIds into one IN-clause)
SELECT AccountId, COUNT(Id) AS c
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN ('<id1>', '<id2>', ...)
GROUP BY AccountId

-- Security-persona contacts per opp's account
SELECT AccountId, COUNT(Id) AS sec_contacts
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN ('<id1>', ...)
  AND (Title LIKE '%CISO%' OR Title LIKE '%Security%' OR Title LIKE '%SOC%'
       OR Title LIKE '%Cyber%' OR Title LIKE '%DevSec%' OR Title LIKE '%Detection%'
       OR Title LIKE '%Threat%' OR Title LIKE '%Information Security%')
GROUP BY AccountId
```

## Closed-lost top accounts (for the "trace back to win pattern" table)

```sql
SELECT Account.Name, Account.Website, Account.Industry, Amount, CloseDate
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = true AND IsWon = false
  AND CloseDate = LAST_N_DAYS:365 AND Amount != null
ORDER BY Amount DESC LIMIT 5
```

## ICP accounts with zero contacts (look-alike to wins)

```sql
SELECT Name, Website, Industry, NumberOfEmployees, AnnualRevenue
FROM Account
WHERE IsDeleted = false
  AND Id NOT IN (SELECT AccountId FROM Contact WHERE IsDeleted = false AND AccountId != null)
  AND Website != null
  AND Industry IN ('<top-3 won industry 1>', '<industry 2>', '<industry 3>', '<industry 4>')
  AND NumberOfEmployees > 1000
ORDER BY AnnualRevenue DESC NULLS LAST LIMIT 5
```

## Existing security contacts on a target account (for the Buyers & Champions drill)

```sql
SELECT Id, FirstName, LastName, Title, Email
FROM Contact
WHERE IsDeleted = false
  AND AccountId = '<target_account_id>'
  AND (Title LIKE '%CISO%' OR Title LIKE '%Security%' OR Title LIKE '%SOC%'
       OR Title LIKE '%Cyber%' OR Title LIKE '%DevSec%' OR Title LIKE '%Detection%'
       OR Title LIKE '%Threat%' OR Title LIKE '%Information Security%')
ORDER BY CreatedDate DESC LIMIT 20
```

## When `mcp__metabase__execute_query` is broken

Symptom: any query, even `SELECT 1`, returns:

```
Error: Illegal base64 character 20
```

There are two Metabase MCP namespaces (`mcp__metabase__*` and `mcp__846dfc88-...__*`). Both
share the same backend and both can fail. When they fail:

- Switch volume / gap queries to SOQL via `integration_proxy`.
- Switch signals queries to Snowflake (`SILVER.SIGNALS.ARTIFACTS`) — see
  [`signals-from-snowflake.md`](signals-from-snowflake.md).
- Switch persona / tech-stack queries to Snowflake (`GOLD.ENTITIES.PEOPLE` /
  `GOLD.ENTITIES.COMPANIES.TECHNOLOGIES`).
