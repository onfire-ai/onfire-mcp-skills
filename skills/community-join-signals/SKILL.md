---
name: community-join-signals
description: Find people and companies that joined an online community (a Slack workspace, Discord server, Reddit community, LinkedIn group, GitHub org, or X/Twitter) using the `ask_onfire` tool against the `evidence` and `insight_evidence` entities. Use when the user asks who joined communities about a product, vendor or technology, wants community-presence signals for an account or individual, or wants a breakdown by subject or platform — phrases like "who joined the Artifex community", "who's in Kubernetes Slack communities", "find everyone from Northwind who's in any Kubernetes community", "who joined a security Slack since January", "which communities are Acme's employees in", or any community-membership lookup. Queryable: what the community is about (its subject), the platform, and the join date. The community's own name and URL are NOT exposed.
---

# community-join-signals

Structured lookup via the **`ask_onfire`** tool, which takes a structured
**QueryIR** (not SQL). Community-membership records are the
**`community_members`** evidence type, one row per (person, community) join.
Each carries the **platform** and **join timestamp**, and is linked to the
**subject** the community is about (a product, vendor or technology — e.g.
`Kubernetes`, `Artifex`). The community's own name and URL are never exposed,
so a community is identified by *subject + platform*, not by name.

`ask_onfire` shape:

```
ask_onfire(query={
  entity: "evidence",                // or "insight_evidence" / "contact"
  select: ["<field>", ...],          // attributes / dimensions / measures
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  joins: [{entity, filters, insight_filters}],  // filter-only single-hop
  group_by: ["<field>", ...],        // aggregate mode (breakdowns)
  aggregations: [{name, fn, field}], // fn: count | count_distinct | sum | avg | min | max
  distinct_by: "<field>",
  order_by: [{field, direction}],
  limit: <int>,                      // ROW BUDGET — see Billing
  confirmed: <bool>
})
```

## When to use this

- **"Who joined the Artifex community?"** — members of communities about a
  subject (`insight_value = "Artifex"`).
- "Who joined a Kubernetes **Slack**?" (subject + platform)
- "Which communities are Meridian Bank's employees in, and how many in each?"
  (breakdown by subject or by platform)
- "Does this person carry a community-membership signal?" (scope by person)
- "Find everyone from Northwind who's in any community" (scope by company)
- Any question about community membership at the person, company, or
  subject level.

Skip this for:
- Sentiment *within* community messages → use `community-messages-sentiment`
- People search by job title / company → use `entity-people-search`

## What this skill can and cannot answer (read first)

Two entities carry community membership, and you will usually need both:

| Entity | Carries | Use it for |
|--------|---------|------------|
| `evidence` | `community_type` (platform), `community_joined_at` (join timestamp) | Who joined, on which platform, when |
| `insight_evidence` | `insight_value` (the community's subject), `start_date` / `end_date` (real DATEs) | What the community is about; breakdowns by subject |

`evidence` joins to `insight_evidence` (filter-only), so "members of Kubernetes
communities on Slack" is one query on `evidence` with a join filtered on
`insight_value`.

**Expressible:**

| Logical field | Entity | Kind | Notes |
|---------------|--------|------|-------|
| `insight_value` | `insight_evidence` | dimension | The community's subject. Matched **verbatim** — resolve the user's wording with `resolve_insights(concepts=[...], kind="technology")` first and use the canonical value. |
| `community_type` | `evidence` | dimension | The platform: `Slack` / `Discord` / `Reddit` / `Linkedin` / `Github` / `Twitter` / `Discourse` / `StackOverflow`. Filter case-insensitively. |
| `community_joined_at` | `evidence` | dimension | ISO `YYYY-MM-DD HH:MM:SS` string — use `gte`/`lte` for a join-date window. |
| `person_url` | both | dimension | LinkedIn URL of the person (any URL format is normalized). |
| `company_url` | both | dimension | LinkedIn URL of their employer at time of the signal. |
| `evidence_type` | both | dimension (bound) | Filter by **name** — `"community_members"` for community joins. Selected values come back as the name too. |
| `entity_kind` | `evidence` | dimension (closed) | `'1'` = people. Filter `'1'` to enumerate community **members**. |
| `evidence_count` | both | measure | `COUNT(*)`. |

**NOT expressible:**

- **The community's name or URL.** Name the subject and platform instead: "a
  community about Artifex on Slack", never "the ArtifexSecurity Slack". If the
  user names a specific community, resolve what it is about and say that you
  matched by subject and platform.
- **One community has several subjects.** A Kubernetes-cost Slack can be linked
  to `Kubernetes`, `AWS` and `Cluster AutoScaler` at once, so subject counts
  overlap — never sum them into a total.
- **One subject spans several communities and platforms.** De-duplicate people
  with `distinct_by: "person_url"`, and add a `community_type` filter when the
  user means one platform.

## The fixed pattern for every pull

1. **Always filter `evidence_type = "community_members"`.** Without it you mix in
   all evidence kinds (job experience, profile, hiring manager, …), and
   `community_type` / `community_joined_at` come back empty.
2. **Name the subject.** Resolve it with `resolve_insights(kind="technology")`,
   then filter `insight_value` — directly on `insight_evidence`, or through the
   `insight_evidence` join from `evidence` / `contact`. Add `community_type` if
   the user means a specific platform ("a Kubernetes **Slack**").
3. **For members, filter `entity_kind = "1"`** on `evidence` (people) and de-dup
   with `distinct_by: "person_url"`.
4. **Scope big pools.** `evidence` is ~495M rows and `insight_evidence` ~1B — a
   subject filter is selective, but for "any community" questions also constrain
   by `person_url` / `company_url`.
5. **Set a small explicit `limit`** (see Billing) and submit. Confirm field names
   with `describe_onfire_schema(["evidence", "insight_evidence"])` if unsure.

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

### Pull the members of communities about a subject (with their profiles)
Query from `contact` so you get names / titles, constrained to people who carry
a membership signal for that subject:
```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "linkedin_url", "current_company_name"],
  joins: [{entity: "insight_evidence", filters: [
    {dimension: "insight_value", op: "eq", value: "Artifex"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ]}],
  limit: 50
})
```

### Members of communities about a subject (with platform + join date)
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "community_type", "community_joined_at"],
  filters: [
    {dimension: "evidence_type", op: "eq", value: "community_members"},
    {dimension: "entity_kind", op: "eq", value: "1"}
  ],
  joins: [{entity: "insight_evidence", filters: [
    {dimension: "insight_value", op: "eq", value: "Artifex"}
  ]}],
  distinct_by: "person_url",
  order_by: [{field: "community_joined_at", direction: "desc"}],
  limit: 50
})
```
Add `{dimension: "community_type", op: "eq", value: "slack"}` to restrict to one
platform ("an Artifex **Slack**").

### Breakdown for an account: which subjects, how many members
Aggregate mode — `select` stays empty; results are the group keys + the count:
```
ask_onfire(query={
  entity: "insight_evidence",
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  group_by: ["insight_value"],
  aggregations: [{name: "members", fn: "count_distinct", field: "person_url"}],
  order_by: [{field: "members", direction: "desc"}],
  limit: 50
})
```
For the same breakdown by platform, run it on `evidence` with
`group_by: ["community_type"]`.

### Members who joined since a date
```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "community_type", "community_joined_at"],
  filters: [
    {dimension: "evidence_type", op: "eq", value: "community_members"},
    {dimension: "community_joined_at", op: "gte", value: "2026-01-01"}
  ],
  joins: [{entity: "insight_evidence", filters: [
    {dimension: "insight_value", op: "eq", value: "Artifex"}
  ]}],
  order_by: [{field: "community_joined_at", direction: "desc"}],
  limit: 25
})
```
- **Caveat:** `community_joined_at` is an ISO string, so `gte`/`lte` is a
  lexicographic comparison. It is exact for `'YYYY-MM-DD'` bounds.

### Does a specific person carry a community-membership signal (and about what)?
Two calls, since the join is filter-only. The subjects:
```
ask_onfire(query={
  entity: "insight_evidence",
  filters: [
    {dimension: "person_url", op: "eq", value: "linkedin.com/in/example-jane-doe"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  group_by: ["insight_value"],
  aggregations: [{name: "member_since", fn: "min", field: "start_date"}],
  limit: 25
})
```
Then the platforms and join dates — the same filters on `evidence`, selecting
`community_type` and `community_joined_at`.

## Output handling

`ask_onfire` returns inline preview rows plus a persisted `dataset` handle.

1. Show the preview rows as a table (person, subject, platform, join date).
2. State the match count. Offer `download_dataset` for the full CSV.
3. **Describe a community by subject and platform** — "joined a community about
   Artifex on Slack in March 2026", never a bare "active in a community".
4. Common follow-ups answerable from the persisted dataset via `query_datasets`:
   - "Most recent joiners" → `ORDER BY community_joined_at DESC LIMIT 10`
   - "People on more than one platform" →
     `GROUP BY person_url HAVING COUNT(DISTINCT community_type) > 1`

## Common pitfalls

- **Forgetting `evidence_type = "community_members"`** — without it you mix in all
  evidence kinds and the community fields come back empty. Always include it
  whenever you touch a `community_*` field.
- **Passing the user's wording as `insight_value`** — it matches verbatim.
  Resolve it with `resolve_insights` first; `"k8s"` will not match `Kubernetes`.
- **Counting one person multiple times** — the same person can appear once per
  community and platform. Use `distinct_by: "person_url"` for a member count, or
  `count_distinct` on `person_url` in aggregate mode.
- **Summing subject counts** — one community carries several subjects, so the
  per-subject counts overlap.
- **Selecting profile fields from `evidence`** — it has none. Query from
  `contact` with a filter-only join to get names / titles.
- **Re-running for follow-up slices** — use `query_datasets` on the existing
  `dataset` handle instead of re-billing a new pull.
