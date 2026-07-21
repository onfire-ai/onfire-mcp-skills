---
name: community-join-signals
description: Find people and companies that joined an online community (a Slack workspace, Discord server, Reddit community, LinkedIn group, GitHub org, or X/Twitter) using the `ask_onfire` tool against the `evidence` entity. Use when the user asks who is a member of a SPECIFIC named community, wants to enumerate a community's members, wants community-presence signals for an account or individual, or wants a per-community breakdown — phrases like "pull the members of the Artifex community", "who joined the Artifex Slack", "members of the DevSecOps Discord", "find everyone from Northwind who's in any Kubernetes community", "who joined any security Slack since January", "which communities are Acme's employees in", or any community-membership lookup. The specific community's name, platform, URL, and join date ARE queryable.
---

# community-join-signals

Structured lookup against the **`evidence`** entity via the **`ask_onfire`**
tool. `ask_onfire` takes a structured **QueryIR** (not SQL). Community-membership
records are the **`community_members`** evidence type, one row per
(person, community) join. Each carries the **community's name, platform,
URL, and join timestamp** as queryable fields, so you can enumerate the members
of a *specific named community* and break membership down per community.

`ask_onfire` shape:

```
ask_onfire(query={
  entity: "evidence",
  select: ["<field>", ...],          // attributes / dimensions / measures on evidence
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  joins: [{entity, filters, insight_filters}],  // filter-only single-hop
  group_by: ["<field>", ...],        // aggregate mode (per-community breakdown)
  aggregations: [{name, fn, field}], // fn: count | count_distinct | sum | avg | min | max
  distinct_by: "<field>",
  order_by: [{field, direction}],
  limit: <int>,                      // ROW BUDGET — see Billing
  confirmed: <bool>
})
```

## When to use this

- **"Pull the members of the Artifex community"** — enumerate a named
  community's members (filter `community_name`).
- "Who joined the Artifex Slack?" (named community + platform)
- "Which communities are Meridian Bank's employees in, and how many in each?"
  (per-community breakdown)
- "Does this person carry a community-membership signal?" (scope by person)
- "Find everyone from Northwind who's in any community" (scope by company)
- Any question about community membership at the person, company, **or specific
  community** level.

Skip this for:
- Sentiment *within* community messages → use `community-messages-sentiment`
- People search by job title / company → use `entity-people-search`

## What this skill can and cannot answer (read first)

The `evidence` entity exposes a governed surface. For community membership, the
community's identity **is** available — name, platform, URL, and join time are
parsed out as scalar dimensions. The raw upstream record as a whole stays
internal, but you do **not** need it for any normal community question.

> The community-identity fields (`community_name` / `community_type` /
> `community_url` / `community_joined_at`) are populated **only** for
> community-membership evidence, so **always pair them with
> `evidence_type = "community_members"`**.

**Expressible** (real dimensions / attributes / measures on `evidence`):

| Logical field | Kind | Notes |
|---------------|------|-------|
| `community_name` | dimension | The community's name. Matches **case-insensitively**; use `op: "contains"` for fuzzy names (e.g. `"artifex"` matches `ArtifexSecurity`). |
| `community_type` | dimension | The platform: `slack` / `discord` / `reddit` / `linkedin` / `github` / `twitter`. Case-insensitive. |
| `community_url` | dimension | The community's URL (a real workspace URL for Slack; a label for some platforms). |
| `community_joined_at` | dimension | ISO `YYYY-MM-DD HH:MM:SS` string — use `gte`/`lte` for a join-date window. |
| `person_url` | dimension | LinkedIn URL of the person (any URL format is normalized). |
| `company_url` | dimension | LinkedIn URL of their employer at time of the signal. |
| `evidence_type` | dimension (bound) | Resolved server-side by **name** — use `"community_members"` for community joins. |
| `entity_kind` | dimension (closed) | `'1'` = people, `'2'` = company. Filter `'1'` to enumerate community **members**. |
| `start_date` / `end_date` | attribute (TEXT) | Signal window — TEXT, not real DATEs. |
| `created_at` | attribute | When the evidence was recorded. |
| `evidence_count` | measure | `COUNT(*)`. |

Joins (filter-only, single-hop): `contact`, `company`.

**Still NOT expressible:**

- **The raw upstream record as a whole** — internal only. You never need it; the
  fields above cover every normal community question.
- **One community appears once per platform.** "ArtifexSecurity" can exist as a
  separate LinkedIn group, GitHub org, and Slack — they are distinct rows with
  the same/similar `community_name` but different `community_type`. Decide
  whether the user means one platform (add a `community_type` filter) or all of
  them, and de-duplicate people across platforms with `distinct_by: "person_url"`.

## The fixed pattern for every pull

1. **Always filter `evidence_type = "community_members"`.** Without it you mix in
   all evidence kinds (job experience, profile, hiring manager, …), and the
   community-identity fields will be empty.
2. **Name the community (and optionally the platform).** Filter `community_name`
   with `op: "contains"` (case-insensitive, fuzzy). Add `community_type` if the
   user means a specific platform ("the X **Slack**").
3. **For members, filter `entity_kind = "1"`** (people) and de-dup with
   `distinct_by: "person_url"` so one person isn't returned once per platform.
4. **Scope big pools.** `evidence` is ~495M rows — a named-community filter is
   selective, but for "any community" questions also constrain by
   `person_url` / `company_url`.
5. **Set a small explicit `limit`** (see Billing) and submit. Confirm field names
   with `describe_onfire_schema(["evidence"])` if unsure.

## Billing — read before calling

`ask_onfire` **bills the client 1 credit per row returned**.

- Always set an explicit `limit`. Never leave it unset unless you want a free count.
- If the response is `needs_confirmation` (`stage: "row_budget"`), nothing was
  billed and no rows came back — the match is bigger than your budget. Lower
  `limit`, or set `confirmed: true` **only** after the user agrees to pull (and
  pay for) that many rows. Do not reflexively set `confirmed: true`.
- For a count without paying for rows: select `evidence_count` with `limit: 1`,
  or leave `limit` unset to let the gate return the match size for free.

## QueryIR recipes

### Pull the members of a named community (with their profiles)
Join from `contact` so you get names / titles, constrained to people who carry a
membership signal for that community:
```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "linkedin_url", "current_company_name"],
  joins: [{entity: "evidence", filters: [
    {dimension: "evidence_type", op: "eq", value: "community_members"},
    {dimension: "community_name", op: "contains", value: "Artifex"}
  ]}],
  limit: 50
})
```

### Members of a named community (evidence-level, with platform + join date)
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "community_name", "community_type", "community_joined_at"],
  filters: [
    {dimension: "evidence_type", op: "eq", value: "community_members"},
    {dimension: "entity_kind", op: "eq", value: "1"},
    {dimension: "community_name", op: "contains", value: "Artifex"}
  ],
  distinct_by: "person_url",
  order_by: [{field: "community_joined_at", direction: "desc"}],
  limit: 50
})
```
Add `{dimension: "community_type", op: "eq", value: "slack"}` to restrict to one
platform ("the Artifex **Slack**").

### Per-community breakdown for an account (how many members in each community)
Aggregate mode — `select` stays empty; results are the group keys + the count:
```
ask_onfire(query={
  entity: "evidence",
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  group_by: ["community_name", "community_type"],
  aggregations: [{name: "members", fn: "count_distinct", field: "person_url"}],
  order_by: [{field: "members", direction: "desc"}],
  limit: 50
})
```

### Members who joined since a date
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "community_name", "community_joined_at"],
  filters: [
    {dimension: "evidence_type", op: "eq", value: "community_members"},
    {dimension: "community_name", op: "contains", value: "Artifex"},
    {dimension: "community_joined_at", op: "gte", value: "2026-01-01"}
  ],
  order_by: [{field: "community_joined_at", direction: "desc"}],
  limit: 25
})
```
- **Caveat:** `community_joined_at` is an ISO string, so `gte`/`lte` is a
  lexicographic comparison. It is exact for `'YYYY-MM-DD'` bounds.

### Does a specific person carry a community-membership signal (and which)?
```
ask_onfire(query={
  entity: "evidence",
  select: ["community_name", "community_type", "community_joined_at"],
  filters: [
    {dimension: "person_url", op: "eq", value: "https://www.linkedin.com/in/alice-smith"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  limit: 25
})
```

## Output handling

`ask_onfire` returns inline preview rows plus a persisted `dataset` handle.

1. Show the preview rows as a table (community name, platform, join date, person).
2. State the match count. Offer `download_dataset` for the full CSV.
3. **Disambiguate the community.** A fuzzy `contains` can match more than one
   community (e.g. a Slack and a separate LinkedIn group). Show the distinct
   `community_name` / `community_type` values you matched, and offer to narrow to
   one platform if that's what the user meant.
4. Common follow-ups answerable from the persisted dataset via `query_datasets`:
   - "Most recent joiners" → `ORDER BY community_joined_at DESC LIMIT 10`
   - "People in more than one community" →
     `GROUP BY person_url HAVING COUNT(DISTINCT community_name) > 1`

## Common pitfalls

- **Forgetting `evidence_type = "community_members"`** — without it you mix in all
  evidence kinds and the community-identity fields come back empty. Always include
  it whenever you touch a `community_*` field.
- **Counting one person multiple times** — the same person can appear once per
  platform for the "same" community. Use `distinct_by: "person_url"` for a member
  count, or `count_distinct` on `person_url` in aggregate mode.
- **Over-narrow exact match on the name** — community names have inconsistent
  casing/spacing (`ArtifexSecurity` vs `Artifex Security`). Use `op: "contains"`
  (it is case-insensitive), not `eq`.
- **Selecting profile fields from `evidence`** — it has none. Join from `contact`
  (filter-only) to get names / titles.
- **Re-running for follow-up slices** — use `query_datasets` on the existing
  `dataset` handle instead of re-billing a new pull.
