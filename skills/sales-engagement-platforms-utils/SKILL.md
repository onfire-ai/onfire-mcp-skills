---
name: sales-engagement-platforms-utils
description: >-
  Best practices for reading a tenant's connected sales engagement platform — Outreach,
  Salesloft, Gong Engage or Reply.io — through the Onfire `sales_engagement_read` /
  `sales_engagement_write` tools.
  Use when you need to look up or query SEP data — find a person or prospect by email, list
  cadences/sequences/flows, read cadence memberships or sequence states, pull
  tasks/actions/calls/mailboxes/users, page through a large collection, filter by date range,
  or trim a response to the fields you need. Also use when a SEP call has just failed and you
  need the right next move — a 404 routeNotFound, an empty result, a 403 scope error, a 422
  "already been taken", or CRM_UPLOAD_REQUIRED. Carries the correct path form for each
  provider, the query-parameter and pagination syntax each one expects, a resource-name
  translation table, and which failures to stop retrying. For ENROLLING a person into a
  cadence/sequence/flow or any multi-step SEP write workflow use `sep-cadence-enrollment`;
  for composing Outreach sequence emails use `outreach-sequence-email-composer`; for Gong
  flow content overrides use `gong-create-and-push-to-flow`.
---

# Sales engagement platforms — query utilities

The same business object has a different name, path and filter syntax on each SEP. Which one
applies is a property of the **tenant**, not of the question you were asked. Resolve the
provider first, then use that provider's grammar — everything else here follows from those
two steps.

## Use a different skill when

| you want to… | use |
|---|---|
| enroll someone in a cadence / sequence / flow; any multi-step SEP write | `sep-cadence-enrollment` |
| compose or stage Outreach sequence emails | `outreach-sequence-email-composer` |
| push to a Gong flow with per-step content overrides | `gong-create-and-push-to-flow` |
| read or write the tenant's CRM | `crm_read` / `crm_write` |

## Step 1 — resolve the provider, before composing anything

```
get_tenant_settings()  ->  settings.sep.type  in {outreach, salesloft, gong, replyio}
```

Do this once per conversation and reuse the answer; a tenant has exactly one SEP. Re-run it
only if you switch tenants.

**Never infer the provider from the user's wording.** "Cadence" is ordinary English, not a
sign the tenant runs Salesloft — plenty of Outreach users say it. Composing a path from the
user's vocabulary is the most common way to get a 404 here.

Read `settings.crm.enabled` in the same call — you need it before any write.

## Step 2 — write the path in that provider's form

| provider | write | never write |
|---|---|---|
| Outreach | `prospects`, `sequences` | `api/v2/prospects` |
| Salesloft | `people`, `cadences` | `v2/people` |
| **Gong** | **`v2/flows`, `v2/flows/prospects`** | **`flows`** |
| Reply.io | `sequences`, `contacts` | `v3/sequences` |

Three of the four take a bare resource name with no version prefix. **Gong is the exception
and needs its `v2/` prefix on every path** — a bare Gong path will not resolve. If a Gong
call 404s, add `v2/` before changing anything else.

## Resource names, provider by provider

| concept | Outreach | Salesloft | Gong | Reply.io |
|---|---|---|---|---|
| the campaign | `sequences` | `cadences` | `v2/flows` | `sequences` |
| a person on one | `sequenceStates` | `cadence_memberships` | flow assignment | `sequence-contacts` |
| the person record | `prospects` | `people` | CRM-mirrored only | `contacts` |
| the steps | `sequenceSteps` | `steps?cadence_id=` | `v2/flows/steps` | `sequences/<id>/steps` |
| rep's to-dos | `tasks` | `actions` | — | — |
| find a person by email | `prospects` + `filter[emails]` | `people` + `email_addresses[]` | `v2/data-privacy/data-for-email-address` (POST) | `contacts` + `email` |

## Calling the tools

```
sales_engagement_read (relative_url, http_method="GET", json_body=None, params=None)
sales_engagement_write(http_method, relative_url, json_body=None, params=None)
```

- `sales_engagement_read` is for GET. Treat it as GET-only on a SEP.
- Gong models two of its reads as POST (`v2/flows/prospects` and the email lookup). Send
  those through `sales_engagement_write` — it is the only route that accepts them.
- `sales_engagement_write` takes POST / PATCH / PUT. DELETE is not available.
- Both are scoped to the caller's own tenant; there is no integration or tenant argument.
- A `params` value may be a string or a list of strings. A list becomes the **same key
  repeated** — so put any brackets the provider expects into the key yourself
  (`"email_addresses[]"`), because they are not added for you.
- Put body fields in `json_body`, not `params`. A `json_body` on a GET is ignored silently.

**Talk to the user in business terms** — sequences, prospects, cadences, flows. Keep REST
paths, API versions, HTTP methods and vendor API names out of anything user-visible.

## Query grammar at a glance

Read the reference file for the connected provider before anything non-trivial.

| | Outreach | Salesloft | Gong | Reply.io |
|---|---|---|---|---|
| several values | `filter[id]=1,2,3` (comma-joined, one key) | `email_addresses[]` repeated | body fields | — |
| range | `filter[updatedAt]=2026-01-01..inf` | `due_on[gte]` / `due_on[lte]` | — | — |
| paging | `page[size]` cursor, or `page[limit]` + `page[offset]` | `per_page` + `page` | cursor, 100/page | `top` + `skip` |
| totals | `count=true` | `include_paging_counts=true` | — | — |
| trim the response | `fields[prospect]=firstName,lastName` | — | — | — |
| email lookup | comma-joined string | list under a `[]` key | one scalar email per call | one scalar email per call |

- `references/outreach-api.md` — JSON:API filters, `newFilterSyntax`, paging, sparse fieldsets
- `references/salesloft-api.md` — parameters per resource, `.json` suffix, the `users` gotcha
- `references/gong-api.md` — endpoints and scopes, body-not-params rules, flow-id handling
- `references/replyio-api.md` — paths and `top`/`skip` paging

Two habits worth keeping: **page explicitly** — no cursor is followed for you, so walk
`links.next` or increment offsets yourself — and on Outreach **always send `fields[type]`**,
the largest single reduction in response size available to you.

## Before a write: CRM first

When `settings.crm.enabled` is true, a person must exist in the CRM before you can create
them in the SEP. Attempting the SEP write first is refused with `CRM_UPLOAD_REQUIRED`.

```
crm_write(entity_type="prospect", ...)  ->  poll crm_write_status to a terminal state
   ->  crm_write_results(job_id)        <-  required; this is what clears the way
   ->  sales_engagement_write(...)
```

`crm_write_results` is not optional — polling the status alone leaves the write blocked. The
match is made on `linkedin_url` (Outreach, Salesloft, Reply.io) or `crm_id` (Gong) and
**never on email**, so a body carrying only an email address cannot satisfy it. Send the
LinkedIn URL exactly as the CRM step recorded it.

Only POST to the person resource is affected; PATCH of an existing record is not. Two things
to check before telling a user this will work: the tenant needs `crm_write` granted, and a
CRM batch whose first record is not a prospect will not clear anything — send prospects in
their own batch. `sep-cadence-enrollment` covers the full flow.

## When a call fails

| symptom | what it means | do this |
|---|---|---|
| `404 routeNotFound` | wrong provider's resource name, a repeated version prefix, or a missing Gong `v2/` | re-check `sep.type`, fix the path, retry **once** |
| `404` HTML page | no such resource on this provider | check the resource table; don't retry the same path |
| `Tool 'sales_engagement_read' is not enabled for this tenant` | not entitled | **stop.** Say so — it's a configuration answer, not missing data |
| `403 ... does not have the required scopes` | the connection lacks a scope | **stop.** Needs reconnecting by an admin; retrying cannot fix it |
| `422 "has already been taken"` | the person already exists | **treat as success.** Look them up and carry on |
| `422 "is already in progress for this person"` | already enrolled | **treat as success.** Carry on |
| `CRM_UPLOAD_REQUIRED` | CRM-first, above | run the CRM steps, then retry |
| `"is a read-shaped request"` | a GET sent to `sales_engagement_write` | resend via `sales_engagement_read` |
| `"This tool is read-only"` | a write sent to `sales_engagement_read` | resend via `sales_engagement_write` — Gong's two POST reads belong there too |
| `400` naming a body field | fields went into `params` | move them into `json_body` |
| empty result, no error | no match, or a filter that's too narrow | widen one filter at a time. An empty SEP result is common and usually means what it says |
| `200` but a field you set was ignored | the provider dropped an unknown key | check the field name in the reference before retrying |
| `5xx` | transient on the provider side | retry once, then report it rather than looping |

## Vendor documentation

| provider | docs |
|---|---|
| Outreach | <https://developers.outreach.io/api/making-requests> · <https://developers.outreach.io/api/common-patterns> · <https://developers.outreach.io/api> |
| Salesloft | <https://developers.salesloft.com/> · per-resource `https://developers.salesloft.com/docs/api/<resource>-index/` |
| Gong | <https://help.gong.io/docs/gong-engage-api-capabilities> · full reference requires a signed-in Gong session at `us.app.gong.io/settings/api/documentation` |
| Reply.io | <https://apidocs.reply.io/> · <https://docs.reply.io/api-reference/> · <https://docs.reply.io/api-reference/bundled.yaml> (OpenAPI, fetchable as text) |

Salesloft's and Reply.io's portals render in JavaScript and return nothing to a plain
fetch — open them in a browser, or use Reply.io's OpenAPI file.
