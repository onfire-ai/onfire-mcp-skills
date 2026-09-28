# Gong Engage — read/query reference

`settings.sep.type == "gong"`.

**Docs:** <https://help.gong.io/docs/gong-engage-api-capabilities>. The full Gong API
reference requires a signed-in Gong session at `us.app.gong.io/settings/api/documentation`,
so the public Engage page is the citable source.

For **writing** flow assignments with per-step content overrides, use
`gong-create-and-push-to-flow` — it owns the `overrides` schema and the flow-id rules. This
file is the read/query side.

---

Always rely on the provider's current official documentation where it is available.
The notes below are fixes we have found to work in practice, for when you hit
something the docs do not explain.

---

## Path form — keep the `v2/` prefix

**Every Gong path must carry `v2/`.** Gong is the one provider where the version prefix is
yours to supply.

| | |
|---|---|
| write | `v2/flows`, `v2/flows/prospects`, `v2/data-privacy/data-for-email-address` |
| never write | `flows`, `calls`, `users` — these do not resolve |

Gong's own docs write every endpoint with the `/v2/` prefix. If a Gong call 404s, add `v2/`
before changing anything else.

---

## Endpoints

| method | path | purpose | scope |
|---|---|---|---|
| GET | `v2/flows` | company flows, plus personal and shared flows | `api:flows:read` |
| GET | `v2/flows/folders` | flow folders (company / personal / shared) | `api:flows:read` |
| POST | `v2/flows/prospects` | flows assigned to the given prospects | `api:flows:read` |
| POST | `v2/flows/prospects/assign` | assign prospects to a flow | `api:flows:write` |
| POST | `v2/flows/prospects/unassign-flows-by-crm-id` | remove by CRM id | `api:flows:write` |
| POST | `v2/flows/prospects/unassign-flows-by-instance-id` | remove by flow instance id | `api:flows:write` |
| POST | `v2/flows/steps` | steps for up to 20 flow ids |  |
| POST | `v2/data-privacy/data-for-email-address` | person lookup by email |  |
| GET | `v2/users` | users |  |

### Two reads are POSTs

`v2/flows/prospects` and `v2/data-privacy/data-for-email-address` are reads that Gong models
as POST. `sales_engagement_read` will not accept them — send them through
`sales_engagement_write`.

---

## Query and body conventions

**Gong takes almost nothing in the query string.** Its Engage endpoints are POST-with-body.
Fields placed in `params` instead of `json_body` produce errors like
`flowId should be a valid Long`, `flowInstanceOwnerEmail: null is not a valid email address`,
or `crmProspectsIds is empty`.

Person lookup — **one scalar email per call**; there is no documented batch form, so do not
send a list:

```
sales_engagement_write(http_method="POST",
          relative_url="v2/data-privacy/data-for-email-address",
          json_body={"emailAddress": "jane@acme.com"})
```

The identifier you want is at `customerData[].objects[].externalId` (and `mirrorId`).

Flow listing takes **`flowOwnerEmail`** as a query parameter — `flowEmailOwner`, which
also appears in circulation, is not accepted. Omitting it returns
`400 flowOwnerEmail parameter is missing`. The value must be a real Gong user's email.

```
sales_engagement_read(relative_url="v2/flows", params={"flowOwnerEmail": "rep@example.com"})
```

**Batch limits:** 100 prospects per assign; 100 flows per unassign-by-instance-id; 20 flow
ids per `v2/flows/steps`.

**Pagination:** none is documented for the flows endpoints. Gong's call endpoints use cursor
pagination with a 100-record page, and those cursors are time-limited — restart pagination
on each run rather than reusing a cursor.

---

## Failure notes

| symptom | cause |
|---|---|
| `404 routeNotFound` on `flows` / `cadences` / `sequences` | a missing `v2/` prefix, or another provider's resource name |
| `404 "Flow not found"` with a correct-looking id | Gong flow ids are 19-digit values. Sent as a JSON **number** they are rounded and stop resolving. **Always send flow ids as strings** |
| `404 "User with the given email ... wasn't found"` | the `flowOwnerEmail` is not a Gong user — the path is fine |
| `403 "does not have the required scopes"` | missing `api:flows:read` / `api:flows:write`. **Stop** — needs reconnecting by an admin |
| `400` naming a body field while your fields are in `params` | move every field into `json_body` |
| `200` but your override was ignored | an unknown key was dropped silently. Check the name in `gong-create-and-push-to-flow` |
| `CRM_UPLOAD_REQUIRED` on `v2/flows/prospects/assign` | CRM-first. Gong matches on `crm_id`, never email — see SKILL.md |
| call data denied | Gong call endpoints need their own scopes, separate from Engage |
