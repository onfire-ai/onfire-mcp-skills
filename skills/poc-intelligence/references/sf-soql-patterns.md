# Salesforce SOQL Patterns Reference

## Pagination

Salesforce caps query results at 2000 rows. For large orgs, always paginate using `queryMore` or OFFSET:

```
GET services/data/v62.0/query?q=SELECT+Id+FROM+Opportunity+LIMIT+2000
```

If `done: false` in the response, follow `nextRecordsUrl` until `done: true`.

For Metabase SQL queries (when CRM is mirrored), use standard SQL LIMIT/OFFSET - no special handling needed.

---

## Object describe (schema inspection)

```
GET services/data/v62.0/sobjects/Opportunity/describe
GET services/data/v62.0/sobjects/Account/describe
GET services/data/v62.0/sobjects/Contact/describe
GET services/data/v62.0/sobjects/Lead/describe
GET services/data/v62.0/sobjects/Task/describe
```

The response `fields` array contains all field metadata. Key properties to read per field:
- `name` - API field name (use this in SOQL)
- `label` - human-readable label
- `type` - field type (string, picklist, reference, currency, datetime, etc.)
- `nillable` - whether null is common
- `picklistValues` - for stage/status fields, this lists all valid values

---

## List all custom objects

```
GET services/data/v62.0/sobjects
```

Filter response for objects where `custom: true` and name contains pipeline-related terms.

---

## Quarter date ranges (SOQL)

Current quarter:
```sql
WHERE LastActivityDate = THIS_QUARTER
```

Previous quarter:
```sql
WHERE LastActivityDate = LAST_QUARTER
```

Both combined (SOQL does not support OR on date literals directly - use a date range):
```sql
WHERE LastActivityDate >= <first_day_of_previous_quarter>
AND LastActivityDate <= TODAY
```

Compute dates dynamically in the skill based on current date.

---

## Count by field value (for ambiguity resolution)

```sql
SELECT COUNT(Id) total FROM Opportunity WHERE BDR_Owner__c != null
SELECT COUNT(Id) total FROM Opportunity WHERE OwnerId != null
```

Pick the field with the higher non-null count as primary.

---

## Stage distribution with velocity

```sql
SELECT StageName,
       COUNT(Id) opp_count,
       SUM(ARR__c) total_arr,
       AVG(Amount) avg_deal,
       AVG(CloseDate - CreatedDate) avg_days
FROM Opportunity
WHERE IsDeleted = false AND IsClosed = false
GROUP BY StageName
ORDER BY COUNT(Id) DESC
```

Note: date arithmetic in SOQL is limited. For velocity calculations, pull `CreatedDate` and `CloseDate` raw and compute in the skill logic.

---

## Last touch per account (Task fallback)

```sql
SELECT WhatId, MAX(ActivityDate) lastTouch
FROM Task
WHERE WhatId IN (SELECT Id FROM Account)
AND ActivityDate >= LAST_N_DAYS:180
GROUP BY WhatId
```

Join to Account.Id in skill logic.

---

## Contact/Lead union pattern

When both Contact and Lead objects are populated, pull separately and union in skill logic:

Contacts:
```sql
SELECT Id, AccountId, Title, CreatedDate, 'Contact' as source_type
FROM Contact WHERE IsDeleted = false
```

Leads:
```sql
SELECT Id, ConvertedAccountId, Title, CreatedDate, 'Lead' as source_type
FROM Lead WHERE IsDeleted = false
```

Union on account ID: use `AccountId` for Contacts, `ConvertedAccountId` for converted Leads. For unconverted Leads, match by `Company` field to Account `Name` as a fuzzy fallback.
