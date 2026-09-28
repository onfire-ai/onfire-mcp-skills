# Outreach — query/filter/pagination reference

`settings.sep.type == "outreach"`. Outreach implements **JSON:API**, so its query grammar is
the most structured of the four and the least like the others.

> **Request bodies live elsewhere.** For resource creation, sequence and step schemas, the
> `stepType` enum, mailbox selection and the OAuth scope list, read
> **`../../outreach-sequence-email-composer/references/outreach-api-cheatsheet.md`**. This
> file covers the query-parameter grammar only.

**Docs:** <https://developers.outreach.io/api/making-requests> ·
<https://developers.outreach.io/api/common-patterns> · <https://developers.outreach.io/api>

---

Always rely on the provider's current official documentation where it is available.
The notes below are fixes we have found to work in practice, for when you hit
something the docs do not explain.

---

## Path form

Write bare resource names — `prospects`, `sequences`, `sequenceStates`, `sequenceSteps`,
`tasks`, `mailings`, `mailboxes`, `users`. Never prefix `api/v2/`.

---

## Filtering

Default syntax:

| form | meaning |
|---|---|
| `filter[firstName]=Sally` | exact match |
| `filter[id]=1,2,3,5,8,13` | any of these — comma-joined in **one** key |
| `filter[id]=5..10` | inclusive range |
| `filter[updatedAt]=2026-01-01..inf` | greater than or equal |
| `filter[updatedAt]=neginf..2026-01-01` | less than or equal |
| `filter[buyerIntentScore]=__null__` | is null |
| `filter[buyerIntentScore]=__notnull__` | is not null |
| `filter[account][id]=1,2,3` | filter across a relationship |
| `filter[q]=aaa` | prefix / global search |
| `filter[q]=_aaa_,custom1` | exact match within a search |

Filter on a relationship's `id`; filtering on a relationship's *attributes* is deprecated.

**New filter syntax** — opt in with `newFilterSyntax=true`. Use it when a value itself
contains a comma or a dot, which the default grammar would misparse:

| form | meaning |
|---|---|
| `filter[firstName][]=Sally&filter[firstName][]=Katie` | several values as repeated keys |
| `filter[id][gte]=5&filter[id][lte]=10` | range |
| `filter[updatedAt][gte]=2026-01-01` | one-sided range |

The email lookup uses the default comma form:

```
sales_engagement_read(relative_url="prospects",
         params={"filter[emails]": "a@acme.com,b@acme.com"})
```

Other filters in common use: `filter[state]`, `filter[owner][id]`, `filter[dueAt]`,
`filter[action]`, `filter[mailingType]`, `filter[prospect][id]`, `filter[name]`,
`filter[email]`.

---

## Sorting

`sort=firstName` ascending · `sort=-firstName` descending · `sort=lastName,-firstName` for
several criteria.

---

## Paging

**Cursor-based, Outreach's recommendation:** `page[size]=50&count=false`. The response
`links` carry `first` / `prev` / `next` with `page[after]` / `page[before]` cursors — follow
`links.next` rather than computing offsets.

**Offset-based, deprecated but still supported:** `page[limit]` (max 1000) and `page[offset]`
(max 10,000).

Nothing follows `links.next` for you. Page explicitly. If a cursor-paged call behaves
unexpectedly, `page[limit]` / `page[offset]` is a reliable fallback.

---

## Sparse fieldsets

`fields[prospect]=firstName,lastName&fields[account]=name`

Only the attributes you list come back, **so list every attribute you need** — one you
forget is absent rather than null. This is the largest response-size lever on Outreach; send
it on every read. Common: `fields[sequenceState]`, `fields[sequence]`, `fields[task]`,
`fields[prospect]`, `fields[mailing]`.

---

## Counting

`count=true` returns `"meta": {"count": 53, "count_truncated": false}`. Counting stops at
2,000,000 and sets `count_truncated: true`. Pair `count=false` with cursor paging to skip a
count you don't need.

---

## Body field names on a write

Outreach spells prospect attributes in **camelCase**, and it is strict about it:
`linkedInUrl` (capital I) is the person's LinkedIn field, and `linkedinUrl`,
`linkedin_url` or any other casing is rejected `400 permittedParams.unknownAttribute`.
The field is not optional in practice — on a CRM-connected tenant the CRM-first gate
matches a prospect create on the LinkedIn URL, so a body without one is refused before
Outreach ever sees it.

Note the two layers disagree on spelling by design: the Onfire gate normalises the key
before matching, so it accepts any casing, but **Outreach does not**. Write the key the
way Outreach wants it, not the way the gate or the CRM step names it.

---

## Failure notes

| symptom | cause |
|---|---|
| `400 fieldsParameter.unknownResourceField` | a name in `fields[type]` is not an attribute of that resource |
| `400 permittedParams.unknownAttribute` | a body attribute is not writable on that resource |
| `422 validationError` with `"source": {"pointer": "/data"}` | envelope wrong — needs `{"data": {"type": ..., "attributes": {...}}}` |
| `403 unauthorizedOauthScope` | names the missing scope. **Stop** — adding it requires reconnecting, which rotates the integration id |
| `"Sequence is locked."` on `POST sequenceStates` | the sequence is not accepting enrollments — a state of the sequence, not a bad request. **Report it, don't retry** |
| relationship ids rejected | Outreach relationship ids are **integers**, not strings |
