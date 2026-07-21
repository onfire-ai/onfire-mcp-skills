---
name: github-repo-signals
description: Find people who starred or forked GitHub repositories using the `ask_onfire` tool over the `github_member` entity. Use when the user wants to know who interacted with a GitHub repo, find developers who starred repos related to a technology or vendor, or check if people from a specific company engaged with a repo — phrases like "who starred any Artifex repo", "engineers who forked a Kubernetes repo", "did anyone from Northwind interact with our GitHub", "find developers in India interested in open-source security tools", or any GitHub repo engagement lookup.
---

# github-repo-signals

Structured lookup against the `github_member` entity via `ask_onfire`. This
entity captures every recorded GitHub star/fork event — who interacted with a
repo, their name, GitHub profile, and matched LinkedIn URL — one row per
(person, repo, activity).

`ask_onfire` takes a single `query` argument — a structured **QueryIR**, never
SQL:

```
ask_onfire(query={
  entity: "<entity>",
  select: ["<field>", ...],          // attributes / dimensions / measures on the entity
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  insight_filters: [{kind, value}],  // persona / technology concepts (resolved server-side)
  joins: [{entity, filters, insight_filters}],  // filter-only; cannot SELECT joined columns
  order_by: [{field, direction}],
  distinct_by: "<field>",
  limit: <int>                       // ROW BUDGET — see Billing
})
```

## When to use this

- "Who starred any repo with 'nexagon' in the name?"
- "Find DevOps engineers who forked Kubernetes repos"
- "Did anyone from Meridian Bank interact with any of our GitHub repos?"
- "Show me all GitHub activity from these LinkedIn URLs"
- Any question about who engaged with GitHub repos

Skip this for:
- Community membership (Slack/Discord/Reddit joins) → use `community-join-signals`
- People search by current job title / company → use `entity-people-search`

## Entity structure — `github_member`

Grain: one row per (person, repo, activity). Identity: `contact_url`.

### Dimensions (filterable)

| Dimension | Notes |
|-----------|-------|
| `contact_url` | Matched LinkedIn profile URL. Any URL format is normalized server-side. Use `op: in` for a list of profiles. |
| `repo_name` | Bare repo name (e.g. `'kubernetes'`, `'langchain'`, `'terraform'`), **not** `'owner/repo'`. Match exact (`eq`) or substring (`contains`). |
| `activity` | Closed list: `'star'` or `'fork'`. |

### Attributes (returnable in `select`, not filterable)

| Attribute | Notes |
|-----------|-------|
| `name` | Person's display name |
| `github_username` | GitHub handle |
| `github_profile_url` | Full GitHub profile URL |
| `github_repo_url` | Full URL of the repo |
| `activity_date` | **When the star/fork happened.** Returnable only — see "What this skill cannot do". |

### Measures

| Measure | Notes |
|---------|-------|
| `member_count` | `COUNT(DISTINCT linkedin)` — distinct people |
| `activity_count` | `COUNT(*)` — total star/fork events |

> Provenance/internal columns (`LINKEDIN_SOURCE`, avatar URL, collection/refresh
> timestamps) are not part of the entity surface and cannot be selected.

## QueryIR templates

### Who interacted with repos by a vendor
```
ask_onfire(query={
  entity: "github_member",
  select: ["name", "github_username", "repo_name", "activity", "github_profile_url", "contact_url"],
  filters: [{dimension: "repo_name", op: "contains", value: "nexagon"}],
  limit: 50
})
```

### Filter by repo name + activity (who starred a specific repo)
```
ask_onfire(query={
  entity: "github_member",
  select: ["name", "github_username", "repo_name", "activity", "github_profile_url", "contact_url"],
  filters: [
    {dimension: "repo_name", op: "eq", value: "scanmap"},   // bare name, not owner/repo
    {dimension: "activity", op: "eq", value: "star"}          // star | fork
  ],
  limit: 50
})
```

### Filter by LinkedIn URLs (did specific people interact with repos?)
```
ask_onfire(query={
  entity: "github_member",
  select: ["name", "github_username", "repo_name", "activity"],
  filters: [{dimension: "contact_url", op: "in", value: [
    "https://www.linkedin.com/in/alice-smith",
    "https://www.linkedin.com/in/bob-jones"
  ]}],
  limit: 50
})
```

### Scope to a company's employees (who at <company> engaged with a repo)
`github_member` has no company column, so scope via a `contact` join. Query the
`contact` entity (so you can select profile fields) and use a **filter-only**
join to `github_member` for the repo/activity constraint:
```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "current_company_name", "linkedin_url"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  joins: [{entity: "github_member", filters: [
    {dimension: "repo_name", op: "contains", value: "artifex"},
    {dimension: "activity", op: "eq", value: "star"}
  ]}],
  limit: 50
})
```

### How many people engaged with a repo (a count, not the list)
```
ask_onfire(query={
  entity: "github_member",
  select: ["member_count"],     // distinct people; use activity_count for total events
  filters: [{dimension: "repo_name", op: "contains", value: "kubernetes"}],
  limit: 1
})
```

## Billing — read before calling

`ask_onfire` **bills the client 1 credit per row returned**.

- Always set a small explicit `limit` (e.g. 50). Never leave `limit` unset — an
  unset budget (or one above the server threshold without `confirmed: true`) is
  bounced for confirmation.
- If the response is `needs_confirmation` with `stage: "row_budget"`, nothing
  was billed and no rows came back — the match is bigger than your budget. The
  response carries the matching row count, so surface it, confirm how many the
  user wants, then lower `limit` (or set `confirmed: true` only once the user
  has agreed to a large pull) and resubmit.

## Output handling

`ask_onfire` returns a `dataset` handle + `preview_rows`.

1. Show `preview_rows` as a table.
2. State the matched/total count; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only stars", "who appears most") → use `query_datasets`
   against the `dataset_id` — **do not re-run** `ask_onfire` (each run re-bills).

## What this skill cannot do (and what to do instead)

- **Date-bounded activity** ("starred since 2025-01-01"). `activity_date` is a
  returnable attribute, not a filterable dimension, so it cannot go in
  `filters`. Pull the matching rows (select `activity_date`) and filter/sort by
  date client-side on the returned `dataset` via `query_datasets`.
- **"Which repos got the most activity" (a per-repo distribution / GROUP BY
  repo_name).** QueryIR has no group-by axis, so a ranked breakdown across many
  repos is not expressible. For a *single* repo, use the `member_count` /
  `activity_count` template above to get its counts; for a true distribution,
  pull the rows and aggregate client-side with `query_datasets`.

## Common pitfalls

- **`repo_name` is the bare name**, not `owner/repo` — match `eq` or `contains`.
- **`activity` is a closed list** (`star` / `fork`) — no other values exist.
- **`activity_date` is not filterable** — it is returnable only; do date work on
  the returned dataset.
- **Re-running for follow-ups re-bills** — slice the existing dataset with
  `query_datasets` instead.
