---
name: event-attendance-signals
description: Find people who attended conferences, summits, webinars, or industry events using the `ask_onfire` tool against the `event_contact` / `event_company` entities. Use when the user wants to know who went to a specific event, find attendees from a target company, discover which events a person attended, or filter prospects by event participation — phrases like "who attended CloudCon 2025", "find people from Cloudforce at SecureCon", "which events did people from our target accounts go to", "show me Quadrant IT Symposium attendees", or any event attendance lookup.
---

# event-attendance-signals

Structured lookup against the `event_contact` entity (one row per person +
event) via `ask_onfire`. This entity records every tracked event attendance
signal — who attended which conference or industry gathering, their employer,
and their location. For per-company attendee **counts**, use the
`event_company` entity instead.

`ask_onfire` takes a single `query` argument — a structured **QueryIR**, never
SQL:

```
ask_onfire(query={
  entity: "<entity>",
  select: ["<field>", ...],          // logical fields on the entity
  filters: [{dimension, op, value}], // op: eq | in | gte | lte | contains
  joins: [{entity, filters}],        // FILTER-ONLY single-hop; cannot SELECT joined columns
  order_by: [{field, direction}],
  distinct_by: "<field>",
  limit: <int>,                      // ROW BUDGET — see Billing
  confirmed: <bool>
})
```

## When to use this

- "Who attended CloudCon 2025?"
- "Find all HackSummit 33 attendees from US-based companies"
- "Which events did people from Meridian Bank go to?"
- "Show me every event a list of LinkedIn profiles attended"
- "Who from Germany was at the MediaExpo?"
- Any question about conference attendance or event participation

Skip this for:
- GitHub star/fork activity → use `github-repo-signals`
- Community membership (Slack/Discord/Reddit) → use `community-join-signals`
- People search by current job title / company → use `entity-people-search`

## Entity structure

### `event_contact` — one row per (person, event)

| Logical field | Notes |
|---------------|-------|
| `event` | Bound concept — the event name. Stored as `Event - <name>` and resolved server-side from the events vocabulary. Pass the human term (e.g. `"CloudCon 2025"`); never `LOWER`/`LIKE` it. |
| `contact_url` | Attendee's LinkedIn URL (any URL format is normalized server-side) |
| `company_url` | Employer's LinkedIn URL at time of event |
| `contact_country` | Lowercase country (e.g. `"united states"`) |
| `contact_region` | State/province, lowercase (e.g. `"georgia"`) |
| `active_employment` | Boolean — whether the person was actively employed at this company at the time |

`event_contact` has **no profile name/title fields**. To return attendee names
and titles, query `entity: "contact"` and add a filter-only join to
`event_contact` (see the first template below).

### `event_company` — one row per (company, event)

| Logical field | Notes |
|---------------|-------|
| `event` | Same bound concept as above |
| `company_url` | The company's LinkedIn URL |
| `attendee_count` | Pre-aggregated count of that company's people at the event — read or filter it (`gte N`) directly; never re-aggregate |

## Resolving the event name

The `event` value is a **concept**, not a literal. The server resolves it from
the events vocabulary (`Event - <name>`). Pass the human term and let
`ask_onfire` resolve it; if you want to confirm the canonical wording first,
call `resolve_insights`. Never `LOWER`/`LIKE`/substring-match the event field.

## Billing — read before calling

`ask_onfire` **bills the client 1 credit per row returned**.

- Always set a small explicit `limit`. For most attendee lookups **10-50 rows**
  is plenty.
- If you do not set a `limit` (or the match is bigger than an unconfirmed
  budget over the server threshold), `ask_onfire` returns `needs_confirmation`
  with `stage: "row_budget"` — nothing is billed and no rows come back. It
  reports how many rows match so you can lower `limit` to what you need and
  resubmit. Do **not** reflexively set `confirmed: true` to push a large pull
  through.

## QueryIR templates

### Who attended a specific event (with names + titles)

`event_contact` has no profile fields, so query `contact` and filter-join to
`event_contact` on the event:

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "current_company_name", "linkedin_url"],
  joins: [{entity: "event_contact", filters: [
      {dimension: "event", op: "eq", value: "CloudCon 2025"}   // resolved to 'Event - CloudCon 2025'
  ]}],
  limit: 50
})
```

If you only need the raw attendee + employer URLs (no names), query
`event_contact` directly:

```
ask_onfire(query={
  entity: "event_contact",
  select: ["contact_url", "company_url", "contact_country", "contact_region"],
  filters: [{dimension: "event", op: "eq", value: "CloudCon 2025"}],
  limit: 50
})
```

### All events attended by people from a specific company

```
ask_onfire(query={
  entity: "event_contact",
  select: ["contact_url", "event", "contact_country", "active_employment"],
  filters: [{dimension: "company_url", op: "eq", value: "https://www.linkedin.com/company/meridian-bank"}],
  limit: 50
})
```

### Did specific people attend any events?

```
ask_onfire(query={
  entity: "event_contact",
  select: ["contact_url", "event", "company_url", "contact_country"],
  filters: [{dimension: "contact_url", op: "in", value: [
      "https://www.linkedin.com/in/alice-smith",
      "https://www.linkedin.com/in/bob-jones"
  ]}],
  limit: 50
})
```

### How many people from a company attended an event (count)

Use the `event_company` entity — `attendee_count` is pre-aggregated:

```
ask_onfire(query={
  entity: "event_company",
  select: ["event", "attendee_count"],
  filters: [
    {dimension: "company_url", op: "eq", value: "https://www.linkedin.com/company/meridian-bank"},
    {dimension: "event", op: "eq", value: "CloudCon 2025"}
  ],
  limit: 5
})
```

### Companies with the largest presence at an event

```
ask_onfire(query={
  entity: "event_company",
  select: ["company_url", "attendee_count"],
  filters: [
    {dimension: "event", op: "eq", value: "CloudCon 2025"},
    {dimension: "attendee_count", op: "gte", value: 25}
  ],
  order_by: [{field: "attendee_count", direction: "desc"}],
  limit: 20
})
```

### Attendees from a region at a specific event

```
ask_onfire(query={
  entity: "event_contact",
  select: ["contact_url", "company_url", "contact_region"],
  filters: [
    {dimension: "event", op: "eq", value: "SecureCon"},
    {dimension: "contact_country", op: "eq", value: "united states"},
    {dimension: "contact_region", op: "eq", value: "california"}
  ],
  limit: 50
})
```

## Not expressible with `ask_onfire`

`ask_onfire` cannot do GROUP BY distributions over a free dimension. Two of the
old query shapes have no direct equivalent:

- **"Which events had the most attendees from a country?"** (group by event,
  count attendees) — `event_contact` has no per-event count measure
  (`attendee_count` lives on `event_company`, keyed by company, not country).
  Workaround: name the candidate events and pull each one's
  `event_company.attendee_count` separately, or query `event_contact` filtered
  to the country with a large `limit` and tally events client-side from the
  returned dataset.
- **"Which events attracted the most attendees from a set of target
  companies?"** (group by event across many companies) — same limitation. Pull
  `event_company` rows for each target `company_url` (or each candidate
  `event`) and aggregate the `attendee_count` values yourself; there is no
  single GROUP-BY call.

## Output handling

`ask_onfire` returns a `dataset` handle + preview rows (and `total_count` when
relevant).

1. Show the preview rows as a table.
2. State `total_count`; offer `download_dataset` for the full CSV.
3. Follow-up slices ("only active employees", "who appears most") → use
   `query_datasets` against the `dataset_id` — **do not re-run** `ask_onfire`
   (re-running bills again).

## Common pitfalls

- **`event` is a bound concept** — pass the human term (`"CloudCon 2025"`); the
  server resolves it to the stored `Event - CloudCon 2025`. Never
  `LOWER`/`LIKE`/substring-match it.
- **`event_contact` has no name/title fields** — to return profiles, query
  `entity: "contact"` and filter-join `event_contact`.
- **Per-company counts live on `event_company`** (`attendee_count`,
  pre-aggregated) — do not try to `COUNT` over `event_contact`.
- **`contact_country` / `contact_region` are lowercase** — filter against
  `"united states"`, not `"United States"`.
- **Joins are filter-only** — you cannot `select` columns from a joined entity,
  only filter by them.
- **Billing** — every row costs 1 credit; set a small `limit` and slice
  follow-ups with `query_datasets` instead of re-running.
