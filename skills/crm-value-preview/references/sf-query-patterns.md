# Salesforce Query Patterns

All Salesforce queries go through `integration_proxy`, not Metabase. The Metabase
`execute_query` tool returns "Illegal base64 character 20" intermittently and is unreliable.

**Field-candidate taxonomy lives in the sibling skill:
[`../../poc-intelligence/references/sf-soql-patterns.md`](../../poc-intelligence/references/sf-soql-patterns.md).**
That doc maintains the canonical list of which SF custom fields stand for ARR / Amount / Stage
/ Owner / Last Activity across different tenants (e.g. `Net_New_ARR__c` vs `ACV__c` vs `MRR__c`).
This doc captures the *tested SOQL we know works through `integration_proxy`* + *the pitfalls we
hit during the Torq run* + *the CRM-shape discovery patterns* needed because every customer's
CRM is configured differently.

## Every CRM is different — always discover first

Don't assume the standard SF schema. Some customers:

- Don't use the standard `Opportunity` object at all (they track deals on `Account`)
- Use a custom object like `Deal__c`, `Pipeline__c`, `Engagement__c`
- Push deal status onto `Account` via custom fields (`Account.Stage__c`,
  `Account.Customer_Status__c`, `Account.ARR__c`, `Account.MRR__c`, `Account.Tier__c`)
- Have multiple opportunity types and split renewals from new business
- Have a custom `IsWon` / `IsClosed` proxy that's not the standard boolean

**Mandatory Step 0: discover the customer's CRM shape before running any KPI query.**

## CRM schema discovery

### 0a. Confirm Opportunity object exists

```
GET /services/data/v62.0/sobjects/  (via integration_proxy with relative_url='sobjects/')
```

Look for `Opportunity` in the response. If absent, check for common alternatives:
`Deal__c`, `Pipeline__c`, `Engagement__c`, `Booking__c`.

### 0b. Describe each candidate object — find the deal-status fields

```
GET /sobjects/Opportunity/describe
GET /sobjects/Account/describe
```

(via `integration_proxy` with `relative_url='sobjects/Opportunity/describe'` etc.)

Scan the returned `fields` array for these concepts (use poc-intelligence's
`sf-soql-patterns.md` for the full field-candidate tables):

| Concept | Standard fields | Common custom fields |
|---|---|---|
| Deal stage | `StageName` | `Stage__c`, `Deal_Stage__c`, `Sales_Stage__c` |
| ARR / deal value | `Amount` | `ARR__c`, `Net_New_ARR__c`, `ACV__c`, `TCV__c`, `MRR__c` |
| Won/lost flag | `IsWon`, `IsClosed` | `Status__c`, `Won__c`, `Final_Status__c` |
| Last activity | `LastActivityDate` | `Last_Touch__c`, `Last_Contact_Date__c` |
| Loss reason | — | `Loss_Reason__c`, `Closed_Lost_Reason__c`, `Reason__c` |
| Owner | `OwnerId` | `AE_Owner__c`, `SDR_Owner__c`, `Account_Owner__c` |
| Industry | `Industry` | `Industry__c`, `Vertical__c`, `Sector__c` |
| Account ARR (if no Opportunity) | — | `Account.ARR__c`, `Account.MRR__c`, `Account.Booking_Amount__c` |
| Account stage (if no Opportunity) | — | `Account.Stage__c`, `Account.Customer_Status__c`, `Account.Tier__c` |

Build an **in-memory field map** keyed by concept → resolved field name. Every query downstream
references the field map, not a hardcoded field name.

### 0c. Fallback: account-level deal status

If `Opportunity` doesn't exist or is empty, check `Account` for deal-status custom fields:

```sql
-- via integration_proxy SOQL
SELECT FIELDS(CUSTOM) FROM Account WHERE IsDeleted = false LIMIT 1
```

(Note: `FIELDS(CUSTOM)` is SOQL syntactic sugar for "give me every custom field". The first row
is enough to see field names + sample values.)

Common patterns we've seen:
- `Account.Customer_Status__c` ∈ {Prospect, MQL, SQL, Customer, Churned, Closed Lost}
- `Account.ARR__c` numeric
- `Account.Renewal_Date__c` date
- `Account.MRR__c` numeric

Use these as the funnel/win-pattern proxy when Opportunity is unavailable.

## Building the funnel KPIs (after field-map discovery)

Use the resolved field names from Step 0b. Below assumes standard SF fields — substitute your
field map's resolved names where appropriate.

### Path A — Opportunity-based (most customers)

```sql
-- Volume KPIs
SELECT COUNT(Id) FROM Account WHERE IsDeleted = false
SELECT COUNT(Id) FROM Contact WHERE IsDeleted = false
SELECT COUNT(Id) FROM Lead WHERE IsDeleted = false AND IsConverted = false
SELECT COUNT(Id) FROM Opportunity WHERE IsDeleted = false

-- Open-pipeline ARR (use field_map.opp.amount, default Amount)
SELECT COUNT(Id), SUM(Amount) FROM Opportunity
WHERE IsDeleted = false AND IsClosed = false

-- Closed-last-12mo split by won/lost (use field_map.opp.is_won)
SELECT IsWon, COUNT(Id), SUM(Amount) FROM Opportunity
WHERE IsDeleted = false AND IsClosed = true AND CloseDate = LAST_N_DAYS:365
GROUP BY IsWon
```

### Path B — Account-based (when no Opportunity)

```sql
-- Volume (same as Path A for Account/Contact/Lead)
SELECT COUNT(Id) FROM Account WHERE IsDeleted = false

-- Pipeline ARR using account-level fields
-- (substitute your tenant's discovered fields for Status__c / ARR__c)
SELECT Customer_Status__c, COUNT(Id), SUM(ARR__c)
FROM Account
WHERE IsDeleted = false AND Customer_Status__c != null
GROUP BY Customer_Status__c

-- Annual mapping:
-- "Customer" / "Active" → closed-won bucket
-- "Prospect" / "MQL" / "SQL" / "Pipeline" → open-pipeline bucket
-- "Closed Lost" / "Churned" → lost bucket
```

If using Path B, **state it clearly in the report**: "Your CRM tracks deal status at the
account level (no Opportunity table), so the pipeline figures below come from
`Account.Customer_Status__c` and `Account.ARR__c`."

### Path C — Hybrid (some tenants mix both)

A few tenants have an Opportunity table but only use it for net-new deals; renewals live on
Account. In that case, sum:
- Open pipeline ARR = SUM(Opportunity.Amount WHERE IsClosed = false) + SUM(Account.Renewal_ARR__c WHERE Renewal_Date__c next 12mo)
- Won ARR (12mo) = SUM(Opportunity.Amount WHERE IsWon AND IsClosed) + SUM(Account.Active_ARR__c WHERE became_customer last 12mo)

Always describe the data sources in a footnote so the customer trusts the numbers.

## SOQL pitfalls hit during testing

| Error | Cause | Fix |
|---|---|---|
| `only aggregate expressions use field aliasing` | Aliasing non-aggregate fields in a relationship query | Drop the aliases; rename columns at parse time |
| `only root queries support aggregate expressions` | Subquery COUNT inside a SELECT projection | Split into two queries, join in memory |
| `The inner and outer selects should not be on the same object type` | `NOT IN (SELECT ... FROM SameObject)` | Restructure — Salesforce requires cross-object subqueries |
| `missing value at 'GROUP'` | `IN (SELECT ... GROUP BY ... HAVING ...)` — Salesforce doesn't support GROUP BY in semi-joins | Issue the GROUP BY as a top-level query, then re-query with the resulting list |

## Gap KPIs (tenant-agnostic)

```sql
-- Stale accounts (use field_map.account.last_activity)
SELECT COUNT(Id) FROM Account
WHERE IsDeleted = false
  AND (LastActivityDate = null OR LastActivityDate < LAST_N_DAYS:90)

-- No-contact accounts (NOT-IN works: Account vs Contact = different objects)
SELECT COUNT(Id) FROM Account
WHERE IsDeleted = false
  AND Id NOT IN (SELECT AccountId FROM Contact WHERE IsDeleted = false AND AccountId != null)

-- Missing industry
SELECT COUNT(Id) FROM Account WHERE IsDeleted = false
  AND (Industry = null OR Industry = '')

-- Contacts missing email / phone
SELECT COUNT(Id) FROM Contact WHERE IsDeleted = false AND (Email = null OR Email = '')
SELECT COUNT(Id) FROM Contact WHERE IsDeleted = false
  AND (Phone = null OR Phone = '') AND (MobilePhone = null OR MobilePhone = '')

-- True duplicate count (group by website)
SELECT COUNT(Id), COUNT_DISTINCT(Website) FROM Account
WHERE IsDeleted = false AND Website != null AND Website != 'Unknown'
-- Redundant = total - distinct
```

## Win-pattern queries

### Winning industries (Path A: Opportunity)

```sql
SELECT Account.Industry, COUNT(Id), SUM(Amount)
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = true AND IsWon = true
GROUP BY Account.Industry ORDER BY SUM(Amount) DESC NULLS LAST LIMIT 10
```

### Winning industries (Path B: Account-based)

```sql
SELECT Industry, COUNT(Id), SUM(ARR__c)
FROM Account
WHERE IsDeleted = false AND Customer_Status__c IN ('Customer', 'Active')
GROUP BY Industry ORDER BY SUM(ARR__c) DESC NULLS LAST LIMIT 10
```

### Winning personas — title filter adapts to tenant

The persona keyword list comes from `tenant_settings.account_research.queries_sections.organization`
joined with the customer's `golden_persona`. For a SOC/SOAR tenant the filter is security titles;
for a DSPM tenant it would be data-engineering titles; for an IAM tenant it would be identity-
governance titles. **Always derive the title regex from the tenant config, not hardcoded.**

```sql
SELECT Title, COUNT(Id)
FROM Contact
WHERE IsDeleted = false
  AND AccountId IN (
    -- Path A
    SELECT AccountId FROM Opportunity WHERE IsWon = true AND IsClosed = true
    -- OR Path B:
    -- ...substitute won-account selector
  )
  AND (Title LIKE '%<persona1>%' OR Title LIKE '%<persona2>%' OR ...)
GROUP BY Title ORDER BY COUNT(Id) DESC LIMIT 30
```

For tenant-config-driven persona keyword construction, see
[`win-pattern-analysis.md`](win-pattern-analysis.md) Step 2.

## When `mcp__metabase__execute_query` is broken

Symptom: any query, even `SELECT 1`, returns `Illegal base64 character 20`.

There are two Metabase MCP namespaces (`mcp__metabase__*` and `mcp__846dfc88-...__*`). Both
share the same backend and both can fail. When they fail:

- Switch volume / gap queries to SOQL via `integration_proxy`.
- Switch signals queries to Snowflake — see [`signals-from-snowflake.md`](signals-from-snowflake.md).
- Switch persona / tech-stack queries to Snowflake (`GOLD.ENTITIES.PEOPLE` /
  `GOLD.ENTITIES.COMPANIES.TECHNOLOGIES`).
