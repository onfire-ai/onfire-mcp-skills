---
name: community-join-signals
description: Find people and companies that carry a community-membership signal (joined a Slack workspace, Discord server, Reddit community, LinkedIn group, or GitHub org) using the `ask_onfire` tool against the `evidence` entity. Use when the user asks who is a member of an online community, wants community-presence signals for an account or individual, or wants to find people from a company who joined any community — phrases like "who joined the Artifex Slack", "members of the DevSecOps Discord", "find everyone from Northwind who's in any Kubernetes community", "who joined any security Slack since January", or any community-membership lookup. NOTE: the specific community's identity (which Slack/Discord/Reddit) is NOT a queryable field — see "What this skill can and cannot answer".
---

# community-join-signals

Structured lookup against the **`evidence`** entity (the agent-surface alias
of `ONFIRE.EVIDENCES`) via the **`ask_onfire`** tool. `ask_onfire` takes a
structured **QueryIR** (not SQL). The `evidence` entity captures raw evidence
records; community-membership records are the `community_members`
evidence type. It is the source for community-presence intent signals tied
to a person and/or company.

`ask_onfire` shape:

```
ask_onfire(query={
  entity: "evidence",
  select: ["<field>", ...],          // attributes / dimensions / measures on evidence
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  joins: [{entity, filters, insight_filters}],  // filter-only single-hop
  distinct_by: "<field>",
  order_by: [{field, direction}],
  limit: <int>,                      // ROW BUDGET — see Billing
  confirmed: <bool>
})
```

## When to use this

- "Who joined any community from Meridian Bank?" (scope by company)
- "Does this person carry a community-membership signal?" (scope by person)
- "Find everyone from Northwind who's in any community"
- "How many community-membership signals does Acme's workforce carry?"
- Any question asking about community membership / join presence **at the
  person or company level**

Skip this for:
- Sentiment *within* community messages → use `community-messages-sentiment`
- People search by job title / company → use `entity-people-search`
- A specific community's name/platform/URL — **not expressible here**, see below.

## What this skill can and cannot answer (read first)

The `evidence` entity exposes a small, governed surface. The raw upstream
record — the `PAYLOAD` — is **denied** (internal-only, never selectable):
exposing it would reveal data provenance. Everything about the *specific
community* (its name, platform type, URL, member id, join timestamp) lives
only in that denied payload.

**Expressible** (real dimensions / attributes on `evidence`):

| Logical field | Kind | Notes |
|---------------|------|-------|
| `person_url` | dimension | LinkedIn URL of the person (any URL format is normalized) |
| `company_url` | dimension | LinkedIn URL of their employer at time of the signal |
| `evidence_type` | dimension (bound) | Concept resolved server-side by **name** — use `"community_members"` for community joins |
| `entity_kind` | dimension (closed) | `'1'` = people, `'2'` = company |
| `start_date` | attribute (TEXT) | When the signal began — stored as TEXT, not a real DATE |
| `end_date` | attribute (TEXT) | TEXT |
| `created_at` | attribute | When the evidence was recorded |
| `evidence_count` | measure | `COUNT(*)` |

Joins (filter-only, single-hop): `contact`, `company`.

**NOT expressible** (these lived only in the SQL `PAYLOAD` and are gone):

- **Which community** — "the Artifex Slack", "the Keep Security Discord",
  "any Kubernetes community", "any security Slack". Community name, platform
  type (Slack/Discord/Reddit/…), and community URL are all in the denied
  payload. You **cannot** filter or select by them. Do not fabricate a
  `community_name` / `community_type` dimension — they do not exist on the
  entity.
- **Per-community breakdown / member counts by community** — needs
  `GROUP BY community_name`, which requires the denied payload. (`ask_onfire`
  also cannot express arbitrary GROUP BY distributions.)

So a request like "who joined the **Artifex** Slack" must be downgraded to
the expressible question: "**which people / companies carry a
community-membership signal**" (optionally scoped to a company or person).
When the user names a specific community or platform, **say plainly** that
Onfire can confirm community-membership presence for a person/company but
cannot, through this surface, identify *which* community it was — then run
the scoped query below. Do not silently pretend the community filter applied.

## The fixed pattern for every pull

1. **Scope to a person or company.** Filter `person_url` or `company_url`
   `eq` (or `in`) the target LinkedIn URL. The `evidence` entity is ~495M
   rows — **always** constrain by a url and/or `evidence_type`.
2. **Pass the evidence type as a concept.** `evidence_type` is a bound
   dimension: filter it by its human name and the server resolves the name
   to its stored id. Use `value: "community_members"` for community joins.
   (If unsure of the exact vocabulary term, `resolve_insights` / the
   evidence-types vocabulary lists the legal values.)
3. **Confirm field names if unsure.** Call
   `describe_onfire_schema(["evidence"])` for the exact dimension / attribute
   / measure names before authoring. Never guess a field name.
4. **Set a small explicit `limit`** (see Billing) and submit.

## Billing — read before calling

`ask_onfire` **bills the client 1 credit per row returned**.

- Always set an explicit `limit`. For a typical presence check **5–25 rows**
  is plenty. Never leave `limit` unset unless you want a free count.
- If the response is `needs_confirmation` (e.g. `stage: "row_budget"`),
  nothing was billed and no rows came back — the match is bigger than your
  budget. Either lower `limit`, or set `confirmed: true` only after the user
  agrees to pull (and pay for) that many rows. Do **not** reflexively set
  `confirmed: true` to push a large pull through.
- To get a count without paying for the rows, select the `evidence_count`
  measure with `limit: 1`, or leave `limit` unset to let the gate return the
  match size for free.

## QueryIR recipes

### Who from a company carries a community-membership signal
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "company_url", "start_date"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  distinct_by: "person_url",
  order_by: [{field: "start_date", direction: "desc"}],
  limit: 25
})
```

To name the people (resolve profiles), join from `contact` instead — the
`evidence` entity has no profile fields to select:
```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "linkedin_url"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  joins: [{entity: "evidence", filters: [
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ]}],
  limit: 25
})
```
(Filter-only join: you constrain `contact` to people who carry a
community-membership signal, but still cannot recover *which* community.)

### Does a specific person carry a community-membership signal?
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "start_date", "created_at"],
  filters: [
    {dimension: "person_url", op: "eq", value: "https://www.linkedin.com/in/alice-smith"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  limit: 10
})
```

### Did any of several people join a community?
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "start_date"],
  filters: [
    {dimension: "person_url", op: "in", value: [
      "https://www.linkedin.com/in/alice-smith",
      "https://www.linkedin.com/in/bob-jones"
    ]},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  limit: 10
})
```

### Date-bounded (signals since a specific date)
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "company_url", "start_date"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "evidence_type", op: "eq", value: "community_members"},
    {dimension: "start_date", op: "gte", value: "2025-01-01"}
  ],
  order_by: [{field: "start_date", direction: "desc"}],
  limit: 25
})
```
- **Caveat:** `start_date` is **TEXT**, not a real DATE, so `gte` is a string
  comparison. It works for clean `'YYYY-MM-DD'` values but is not a true date
  window. Sanity-check the returned dates rather than trusting the bound
  blindly.

### Count community-membership signals at a company (free-ish, 1 row)
```
ask_onfire(query={
  entity: "evidence",
  select: ["evidence_count"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  limit: 1
})
```
- This is a single aggregate row. **Not expressible:** a *per-community*
  breakdown (which community, how many in each) — that needs the denied
  payload plus a GROUP BY distribution.

## Output handling

`ask_onfire` returns inline preview rows plus a persisted `dataset` handle.

1. Show the preview rows as a table.
2. State the match count. Offer `download_dataset` for the full CSV.
3. **Always caveat** that the community's identity (name / platform / URL) is
   not available from this signal — only that a community-membership signal
   exists for the person/company.
4. Common follow-ups answerable from the persisted dataset via
   `query_datasets`:
   - "Who has the most recent signal?" → `ORDER BY start_date DESC LIMIT 10`
   - "Which people appear more than once?" →
     `GROUP BY person_url HAVING COUNT(*) > 1`

## Common pitfalls

- **Asking for the community name / platform / URL** — these are in the
  denied `PAYLOAD` and are not queryable. Downgrade to a presence check and
  flag the limitation; never invent `community_name` / `community_type`
  fields.
- **Forgetting the `evidence_type` filter** — without
  `evidence_type = "community_members"` you mix in all evidence kinds (job
  experience, profile, hiring manager, …). Always include it, and always also
  constrain by a `person_url` / `company_url` (the entity is ~495M rows).
- **Treating `start_date` as a real DATE** — it is TEXT; `gte`/`lte` are
  string comparisons, not true date math.
- **Selecting profile fields from `evidence`** — it has none. Join from
  `contact` (filter-only) to get names / titles.
- **Re-running for follow-up slices** — use `query_datasets` on the existing
  `dataset` handle instead of re-billing a new pull.
