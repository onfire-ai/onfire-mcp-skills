# Salesloft — read/query reference

`settings.sep.type == "salesloft"`.

**Docs:** <https://developers.salesloft.com/> — per-resource pages follow
`https://developers.salesloft.com/docs/api/<resource>-index/` (list), `-show/` (fetch one),
`-create/` (create). The portal renders in JavaScript, so open it in a browser rather than
fetching it.

---

Always rely on the provider's current official documentation where it is available.
The notes below are fixes we have found to work in practice, for when you hit
something the docs do not explain.

---

## Path form

Write bare resource names — `people`, `cadences`, `cadence_memberships`. Never prefix `v2/`.

Salesloft's own docs write paths with a `.json` suffix (`/v2/people.json`). Both forms work
here: `people` and `people.json` are equivalent. Prefer the bare form.

---

## Paging — the same on every list endpoint

| param | type | notes |
|---|---|---|
| `per_page` | integer | page size |
| `page` | integer | 1-based |
| `include_paging_counts` | boolean | adds `total_pages` / `total_count`; **off by default** |

Salesloft omits the totals unless you ask, and asking costs it an extra query — so set
`include_paging_counts` only when you actually need a total. Otherwise page until a short
page comes back.

---

## `people`

| param | shape |
|---|---|
| `email_addresses[]` | array — the canonical email lookup |
| `crm_id[]` | array |
| `ids[]` | array |
| `updated_at[]` | array |
| `last_name` | scalar |
| `person_company_name` | scalar |
| `cadence_id` | scalar |
| `sort_by`, `sort_direction` | scalar |

```
sales_engagement_read(relative_url="people",
         params={"email_addresses[]": ["jane@acme.com", "john@acme.com"]})
```

A list value is sent as the repeated key
`email_addresses[]=jane@acme.com&email_addresses[]=john@acme.com`. The brackets are part of
the key you supply — they are not added for you. The unbracketed `email_addresses` also
works, but prefer the bracketed form: it matches the published spec.

**Creating one.** Salesloft's own minimum for `POST people` is a valid email address, or a
partial name plus a phone number. That minimum is not enough on a CRM-connected tenant: the
CRM-first gate matches on `linkedin_url` and never on email, so an email-only body is
refused before Salesloft sees it. Carry the LinkedIn URL through from the CRM step.

---

## `cadences` and `cadence_memberships`

`cadences` — `per_page`, `page`, `sort_by`, `sort_direction`, `include_paging_counts`, and
`name` for a lookup by name.

`cadence_memberships` — the person-to-cadence association, current and historical.

| param | shape |
|---|---|
| `person_id` | scalar integer |
| `cadence_id` | scalar integer |
| `person_id[]` | array — use this to check several people at once |
| `cadence_id[]` | array |
| `ids[]`, `updated_at[]` | array |

The spec types `person_id` and `cadence_id` as scalars; the bracketed array form is also
accepted and is the better choice for a batch.

---

## `actions` — a rep's due steps

This is where Salesloft's bracketed range syntax appears.

| param | shape |
|---|---|
| `user_guid[]` | array |
| `due_on[gte]` | `YYYY-MM-DD` |
| `due_on[lte]` | `YYYY-MM-DD` |
| `type` | scalar |
| `status` | scalar |

```
sales_engagement_read(relative_url="actions",
         params={"user_guid[]": ["<guid>"],
                 "due_on[gte]": "2026-09-01", "due_on[lte]": "2026-09-30",
                 "per_page": "100"})
```

Note the shape: `due_on[gte]` is **one literal key**, not a nested object. Salesloft uses
`field[gte]` / `field[lte]` for ranges — unlike Outreach, which uses `filter[field]=a..b`.

---

## `users`, `steps`, and others

`users` takes **`per_page` and `search` only.** An email filter is ignored and the whole
workspace comes back; only `search` narrows server-side. Filter by email yourself after
searching.

`steps` — `cadence_id` (scalar), `per_page`. This is where a cadence's steps live; there is
no `cadence_steps` resource.

Also available: `mailboxes`, `tasks`, `email_templates/<id>`,
`action_details/email_details/<id>`, `notes`.

---

## Failure notes

| symptom | cause |
|---|---|
| `404` HTML page | no such resource — e.g. `cadence_steps`; use `steps?cadence_id=` |
| `422 {"errors":{"email_address":["has already been taken"]}}` | person exists. **Treat as success** — look them up and continue |
| `422 {"errors":{"cadence_id":["is already in progress for this person"]}}` | already enrolled. **Treat as success** |
| `422 "team_cadence is not a valid field"` | field not accepted on `cadence_imports` |
| `422 "is not owned by the provided user and is not a team cadence"` | a permissions fact about the cadence, not a malformed body. Surface it and ask which cadence to use instead |
| `403 "does not have the required scopes"` | the connection is missing a scope. **Stop** — it needs reconnecting by an admin |
| the entire workspace returned from `users` | expected; use `search` and filter client-side |
