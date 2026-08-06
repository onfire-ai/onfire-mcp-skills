# The account-selection resolver

This is the hard core of the skill. Assembling the right handful of accounts is the
step reps find hardest and the one that carries the differentiated value — the
artifact is comparatively easy once this input is right.

The resolver is a funnel that gets narrower and more expensive at each stage, so the
expensive stages only ever see a handful of candidates:

```
universe (free)  ->  hard gates (free)  ->  broad scoring layers
                 ->  shortlist (2x the target)  ->  per-finalist layers
                 ->  score, floor, cut  ->  up to N accounts, never padded
```

---

## Stage 0 — preflight, and fail loudly

All of this is free. Run it every time, in this order, and **stop with the specific
missing key** rather than degrading. A plan built on missing config looks identical to
a real one at a glance, which is precisely why silent degradation is the failure mode
worth engineering against.

1. `get_current_tenant()` — establishes the session tenant. If this errors, stop:
   there is no way to know whose plan this is.
2. `get_tenant_settings()` — read the account-research configuration block: the
   buying-committee personas, the configured competitors and technologies. **Omit
   `tenant_id`** unless this is a super-tenant session acting for another tenant.
3. Derive `warm_intro_origin` per the ladder in `config-and-setup.md`.
4. `describe_onfire_schema(show_catalog=True)` — **once per session, before the first
   `ask_onfire` call.** Assert that every entity this file names actually exists in
   the live catalog. Entities come and go; a layer built on a missing entity must be
   skipped, not guessed at.
5. `resolve_insights` for every persona, technology, competitor, and event term that
   will appear in a filter, carrying `kind`. A concept is not a literal.
6. `describe_onfire_schema([...])` for any entity whose field names you are not
   certain of. **Never guess a field name.**

| Preflight condition | Action |
|---|---|
| No tenant resolvable | **Stop.** "I can't determine which workspace I'm authenticated to." |
| No account-research config block | **Stop**, naming the missing key. |
| Prospecting unavailable | Do **not** proceed silently. State that the people layer will be title-pull-only and ask whether to continue. |
| Buying-committee personas empty | State that committee coverage cannot be guaranteed; offer to proceed on the tenant's golden persona alone. |
| An entity named here is absent from the catalog | Skip that layer, score its dimension `null`, redistribute the weight, note it internally. |
| A concept fails to resolve | Drop that concept, note it internally. Never pass an unresolved term as a literal. |

---

## Stage 1 — the candidate universe

Never "all companies". The universe is always bounded, and three of the four sources
are free.

| Source | Cost | How |
|---|---|---|
| The rep's named accounts | free | `rep_profile.named_accounts` — always candidates. |
| The rep's CRM book | free | `admin_onfire_integration_read`, filtered to the rep on `external_inputs.crm.owner_field`, with a small page size. |
| An approved partner or co-sell sheet | free | Drive `read_file_content` on `approved_sheet.file_id`; keep rows whose `approved_column` is truthy. Flag rows newly ticked since the last run — those are the strongest candidates in the set. |
| Signal-sourced companies | **billed** | The only billed generator. Bounded per layer, below. |

Which of these leads is a **per-rep configuration choice**, not a built-in default —
`resolver_inputs` orders them. Whether ICP score, live CRM state, or a partner sheet is
the right primary input differs by rep and is still being validated, so the resolver
takes it as input rather than assuming.

---

## Stage 2 — hard gates

Zero cost, and they run **before any scoring pull**. Excluding a candidate is free;
scoring one is not.

Before running them, check `rep_profile.territory_breadth` (derived at save time by
the gate-sufficiency rule in `config-and-setup.md`). A `"broad"` profile still runs —
it is compensated for at stage 6, not blocked here.

1. **Net-new only.** Drop anything in `worked_accounts` or the suppression list
   (`state-file.md` for the normalisation rules). Suppression outranks score: an
   account the rep explicitly removed never returns, however well it would score.
2. **Geography.** `rep_profile.geography`, minus `excluded_geos`.
3. **Size band.** `rep_profile.size_band`.
4. **CRM state.** Drop `crm.exclude_stages` — typically closed-won, an active
   opportunity owned by someone else, and anything marked do-not-contact.
5. **Approval.** When `approved_sheet.enabled`, only approved rows survive.

---

## The layer catalog

Every layer below runs. This is a **rendering list, not a menu** — there is no
configuration that switches one off, because a rep choosing between layers they have
never seen drops the ones they would never discover, and a plan missing half its
evidence reads as a thin product rather than a thin config.

A layer that returns nothing is not a failure: its dimension scores `null` and the
weight redistributes, exactly as in stage 6. Several layers legitimately return
nothing for a given rep — `tender` is public-sector only, `github_member` is
meaningful mainly for engineering-led sales — and that is a correct outcome, not a
gap to apologise for.

| Layer | Source | Feeds |
|---|---|---|
| Buying-intent messages | `query_intent_signals` `["High Intent"]` | `signal_strength` |
| Community messages — pain, competitor chatter | `search_community_messages` | `signal_strength`, `use_case_relevance` |
| Community sentiment | `community_messages_sentiment` | `use_case_relevance` |
| Community joins | `evidence`, community-membership type | `trigger_freshness` |
| Community-member intent | `query_intent_signals` `["Community Members"]` | `trigger_freshness` |
| Open roles | `job_post` | `signal_strength`, `momentum` |
| Active hiring managers | `hiring_manager_signal` | `committee_reachability`, `trigger_freshness` |
| Job-post intent | `query_intent_signals` `["Linkedin Job Post"]` | `trigger_freshness` |
| Event presence | `event_company` / `event_contact` | `trigger_freshness` |
| Event-attendee intent | `query_intent_signals` `["Event Attendee"]` | `trigger_freshness` |
| Developer-community activity | `github_member` | `use_case_relevance` |
| Technology footprint | `contact` + technology `insight_filters` | `use_case_relevance` |
| Competitor footprint | `contact` + competitor `insight_filters` | `use_case_relevance` |
| Adoption trend | `growth_insight_monthly` | `momentum` |
| Headcount trend | `headcount_monthly` | `momentum` |
| Dated deployment proof | `insight_evidence` | `use_case_relevance` |
| Role movement and alumni | `people_experiences` | `trigger_freshness` |
| Leadership change | `query_intent_signals` `["Company Change"]` | `trigger_freshness` |
| Promotion | `query_intent_signals` `["Promotion"]` | `trigger_freshness` |
| **Contract renewals and open tenders** | `tender` | `trigger_freshness`, `use_case_relevance` |
| **Extended workforce** | `extended_workforce` | `icp_fit` |
| Annual-filing language | `query_company_filings` | `use_case_relevance` |
| Office footprint | `search_offices` | `icp_fit` |
| Firmographics | `match_company`, `get_company_headcount` | `icp_fit` |
| Warm-intro path | `detect_warm_intros` | `committee_reachability` |

**Catalog-gate every one of them.** `describe_onfire_schema(show_catalog=True)` is the
authority on what exists this session; entities come and go. A layer whose entity is
absent is skipped, its dimension scored `null`, its weight redistributed — never
guessed at and never silently dropped from the internal run notes.

---

## Stage 3 — broad scoring layers

These run across all surviving candidates and feed four of the six dimensions. Prefer
**aggregate/measure selects** here: when a value feeds a *score* rather than a quote,
a count costs a fraction of the rows behind it. Reserve row-level pulls for evidence
you will actually quote.

Every recipe below is scoped to the account by its company-URL dimension, which is
what keeps each pull small and on-topic.

### Buying-intent and community signals

```
query_intent_signals(
  tenant_id=<omit on a normal session>,
  account_website="<domain>",
  keyword_match=[<the rep's ICP terms, resolved>],
  signal_types=["High Intent"]
)
```

Run a second pull for the rep's other configured angles rather than widening one
keyword set. Also worth their own pulls, each a distinct trigger type:
`["Company Change"]` and `["Promotion"]` (a new or newly-promoted owner is a fresh
trigger), `["Linkedin Job Post"]`, `["Event Attendee"]`, `["Community Members"]`.

For pain and competitor chatter that a keyword set misses, use
`search_community_messages` with the tenant's competitors and pain themes. Keep the
window recent and the limit tight.

### Open roles — a budget and build-out signal

```
ask_onfire(query={
  entity: "job_post",
  select: ["job_post_title", "job_function", "seniority", "location", "date_posted"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "application_active", op: "eq", value: 1}
  ],
  order_by: [{field: "date_posted", direction: "desc"}],
  limit: 10
})
```

For the score rather than the evidence, use the measure instead — one row, one credit:
`select: ["post_count"]`, same filters, `limit: 1`.

`job_function` is messy multi-value free text. Use `contains`, never `eq`.

### Active hiring managers — a live budget owner

```
ask_onfire(query={
  entity: "hiring_manager_signal",
  select: ["full_name", "person_job_title", "job_post_title", "short_summary", "signal_date", "contact_url"],
  filters: [{dimension: "company_url", op: "eq", value: "<account linkedin url>"}],
  distinct_by: "contact_url",
  order_by: [{field: "signal_date", direction: "desc"}],
  limit: 10
})
```

`distinct_by` matters: one person can carry several signals, and without it the same
manager consumes the whole budget. Optional seniority gate on `person_seniority`
(`seniority_executive` / `seniority_director` / `seniority_teamlead`).

These people feed the **people layer** as well — when prospecting is unavailable, an
actively-hiring manager is often the strongest real contact on the account.

### Event presence

```
ask_onfire(query={
  entity: "event_company",
  select: ["event", "attendee_count"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "event", op: "eq", value: "<event name, resolved>"}
  ],
  limit: 5
})
```

`attendee_count` is pre-aggregated per company and event — read it, never re-aggregate.
The stored event form is prefixed; pass the human term and let it resolve.

### Technology and competitor footprint

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "job_summary", "linkedin_url"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  insight_filters: [{kind: "technology", value: "<resolved technology>"}],
  limit: 10
})
```

**`insight_filters` AND together — they never OR.** One query per concept, merged
client-side. Expecting an OR here silently returns the intersection, which reads as
"no footprint" when the truth is "no single person carries all three".

### Developer-community activity

`github_member` has no company column, so scope through a `contact` join:

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  joins: [{entity: "github_member", filters: [
    {dimension: "repo_name", op: "eq", value: "<bare repo name>"},
    {dimension: "activity", op: "eq", value: "star"}
  ]}],
  limit: 10
})
```

`repo_name` is the **bare** name, not `owner/repo`. `activity` is `star` or `fork`.
Joins are filter-only — you cannot select a joined column.

### Role movement

```
ask_onfire(query={
  entity: "people_experiences",
  select: ["company_name", "title_name", "start_date", "end_date", "person_url"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "is_primary", op: "eq", value: false}
  ],
  limit: 20
})
```

`is_primary: false` is a past role; `true` is current. `start_date` and `end_date` are
TEXT (`YYYY-MM`) on this entity, not real dates — do not sort them as dates.

A departed owner of a relevant technology is one of the strongest triggers available:
the work still needs doing and nobody owns it.

### Community joins

```
ask_onfire(query={
  entity: "evidence",
  select: ["person_url", "community_name", "community_type", "community_joined_at"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "evidence_type", op: "eq", value: "community_members"}
  ],
  limit: 10
})
```

Four things this entity will punish you for:

- **It is roughly 495 million rows.** Always constrain by `company_url`, `person_url`,
  or `evidence_type`. An unconstrained pull is the most expensive mistake available in
  this file.
- **`evidence_type` is filtered by its human name**, not by an id — the server resolves
  the name against its vocabulary. Do not pass the stored numeric value.
- **The community fields are populated only for community-membership evidence**, so
  the `evidence_type` filter is not optional garnish; without it they come back null.
- **`start_date` / `end_date` here are TEXT (`YYYY-MM`), not dates.** `community_joined_at`
  is a full ISO timestamp string and is the one to date a join with. When you need a
  real date window, use `insight_evidence`, whose columns are actual DATEs.

`community_type` is the platform — slack, discord, reddit, linkedin, github, twitter.

### Contract renewals and open tenders

A dated contract renewal is the strongest trigger in this file: it is a buying window
with a date on it, and it names the incumbent to displace.

Scoped to one account it is a **per-finalist** layer (stage 5). Dropping the
`buyer_linkedin_url` filter and filtering on `insight_name` plus a renewal window
instead turns it into a **candidate generator** for stage 1 — every public-sector buyer
with a relevant contract expiring in the next two quarters. Bound it like any other
billed generator: free count first, then a small explicit limit.

```
ask_onfire(query={
  entity: "tender",
  select: ["signal_type", "notice_title", "buyer_name", "winner_name",
           "renewal_date", "renewal_date_confidence", "tender_deadline", "source_url"],
  filters: [
    {dimension: "buyer_linkedin_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "renewal_date", op: "gte", value: "<today, YYYY-MM-DD>"}
  ],
  order_by: [{field: "renewal_date", direction: "asc"}],
  limit: 10
})
```

- **Public-sector scope only** (EU TED and US USAspending). For a rep who sells purely
  into private companies this layer returns nothing and scores `null` — correct, not a
  failure.
- **The buyer is the account; the winner is the incumbent.** They are different
  companies. `winner_name` / `winner_linkedin_url` are set only on awarded contracts —
  that name is the displacement angle, and the account's own firmographics come from
  the `company` join, never from the winner.
- `renewal_date` and `renewal_date_confidence` apply to awarded contracts;
  **open tenders use `tender_deadline` instead**, so read whichever matches
  `signal_type`. Carry the confidence through to the evidence — a `low`-confidence
  renewal date is a lead, not a deadline.
- `insight_name` is a best-effort tag. Match it loosely and keyword-search
  `notice_title` / `lot_title` alongside it rather than relying on it alone.
- `buyer_country` is an ISO-3 code (`USA`, `DEU`), not a country name.
- The entity's own examples describe named filters such as `biddable_open` and
  `upcoming_renewals`. **Those are prose, not QueryIR fields** — there is no
  `named_filter` key. Express them as explicit `signal_type` and date filters, as above.

### Extended workforce

Companies running more workers than their LinkedIn footprint shows — contingent,
1099, outsourced, franchise. Company-grain, **one row per account**, so it runs
**per-finalist** (stage 5) and refines `icp_fit` at the re-score:

```
ask_onfire(query={
  entity: "extended_workforce",
  select: ["severity", "signal_count", "reasons", "linkedin_size_band",
           "employee_count", "annual_revenue_range"],
  filters: [{dimension: "company_linkedin_url", op: "eq", value: "<account linkedin url>"}],
  limit: 1
})
```

`reasons` is an array of plain-English sentences carrying the real numbers, written to
be read — it renders directly as the dimension's evidence with no rewriting. To filter
on one specific signal use the matching `flag_*` boolean
(`flag_high_revenue_low_headcount`, `flag_thin_linkedin_footprint`,
`flag_staffing_outsourcing_industry`, and three more) rather than parsing `reasons`.

Two properties that change how it scores:

- **It is presence-only.** A company absent from this entity is *not flagged* — that is
  a finding, not missing data. So absence scores low; it does not score `null`. This is
  the one layer where the "no data → `null`" rule in stage 6 does not apply, and
  getting it backwards silently rewards every unflagged account.
- **It infers from firmographic contradiction; it does not prove.** `reasons` is
  undated, so this layer feeds `icp_fit` and can never on its own lift a dimension past
  the 50 cap in stage 6, which requires two *dated* evidence items. Hedge the language
  in anything rep-facing: "likely runs", not "runs".

### Free relationship strength

```
detect_warm_intros(
  tenant_id=<the origin tenant>,
  target_company_linkedin_url="<account linkedin url>"
  # limit deliberately UNSET
)
```

With `limit` unset this returns `needs_confirmation` plus the number of matched warm
paths, **with no rows and nothing billed**. That count is a genuine scoring input at
zero cost. Do not set a limit here — this stage wants the number, not the people. A
limit above 50 additionally requires explicit confirmation, which is not something to
spend on a candidate that may not make the shortlist.

### Live CRM state

`admin_onfire_integration_read` per candidate: does the account exist (and is it the
right company, not a name collision), who owns it, are there open opportunities and at
what stage, and when was the last activity. Rank new accounts first, then those with
no open opportunity, then those with no activity in `crm.stale_days`.

---

## Stage 4 — the shortlist gate

Rank on the broad dimensions and take the top `accounts_per_run × 2` as finalists.

This single step is the largest cost saving in the resolver. Everything in stage 5 is
per-account and several of those layers are time series, so running them across an
unfiltered candidate set costs an order of magnitude more than running them on twice
the number you will actually deliver.

---

## Stage 5 — per-finalist layers

Only finalists reach these.

**Adoption trend** — is a relevant persona or technology spreading inside the account:

```
ask_onfire(query={
  entity: "growth_insight_monthly",
  select: ["month", "num_on_insight", "growth_rate"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "insight", op: "eq", value: "<resolved concept>"}
  ],
  order_by: [{field: "month", direction: "desc"}],
  limit: 12
})
```

**Headcount trend** — growing or contracting, which drives an expansion versus a
consolidation angle. Same shape on `headcount_monthly`, no insight filter, one series
per company.

Both are time series where **deltas are not computed server-side**. Read the latest
row's `growth_rate` (positive is growing), or compare first and last month yourself.

**Dated proof** — how long a signal has held, which is what turns a claim into
evidence:

```
ask_onfire(query={
  entity: "insight_evidence",
  select: ["start_date", "end_date"],
  filters: [
    {dimension: "company_url", op: "eq", value: "<account linkedin url>"},
    {dimension: "insight_value", op: "eq", value: "<resolved concept>"}
  ],
  order_by: [{field: "start_date", direction: "asc"}],
  limit: 5
})
```

**Always** constrain by both company URL and insight — this table is on the order of a
billion rows. Earliest `start_date` is "in place since"; a null `end_date` means still
active.

**Annual-filing language** — `query_company_filings(website, keywords=[...])` for
public companies only. Note that a tight limit can return a minor filing rather than
the annual report; check what came back before quoting it.

**Firmographics** — `match_company` to confirm identity and resolve the LinkedIn URL,
`get_company_headcount(company_linkedin_urls=[...], months=1)` for current size.

**Contract renewals** (`tender`) and **extended workforce** (`extended_workforce`) —
both recipes are in stage 3 alongside the layers they belong with conceptually, but
both are per-account and so run here. `extended_workforce` refines `icp_fit` at the
re-score; a renewal date lands in `trigger_freshness` and is usually the strongest
dated trigger an account has.

**Custom dimensions** — see below. These run here, never in the broad phase.

---

## Stage 6 — score, floor, cut

### The dimensions

Tenant-agnostic. Weights come from `rep_profile.dimension_weights` and default to:

| Key | What it measures | Default |
|---|---|---|
| `icp_fit` | firmographic match to the rep's profile | 0.20 |
| `signal_strength` | count, recency, and on-ICP-ness of live signals | 0.25 |
| `use_case_relevance` | evidence tied to **this tenant's** configured use cases and technologies | 0.20 |
| `committee_reachability` | are the tenant's committee personas present, above the seniority floor, and warm-reachable | 0.15 |
| `trigger_freshness` | discrete dated triggers: leadership change, promotion, open roles, event, filing, community join, developer activity | 0.15 |
| `momentum` | direction of headcount, persona, or technology adoption | 0.05 |

### Custom dimensions

Some reps qualify on a measured metric specific to how they sell. That belongs in
config, not in this file:

```jsonc
{
  "key": "builder_density",
  "label": "Share of engineering who ship code",   // rep-facing; no internal terms
  "weight": 0.20,
  "measure": {
    "kind": "roster_share",
    "entity": "contact",
    "match_terms": ["code_contributor"],
    "denominator": "engineering_headcount"
  },
  "scale": [[0.60, 85], [0.45, 75], [0.30, 60], [0.15, 50], [0.0, 40]]
}
```

`scale` maps a measured ratio to a 0-100 score, interpolated between points.

**A share metric needs a denominator, and a denominator is expensive.** Counting a
full roster row by row costs one credit per employee — for a mid-size account that is
hundreds of credits, per account. So: obtain the denominator as a **count measure**, or
the dimension scores `null` and its weight redistributes. Never page a full roster to
compute a percentage.

**Check the catalog before building one of these at all.** A custom dimension is for a
metric Onfire does not already model. Contractor and contingent-workforce share is the
obvious trap: it looks like a textbook roster-share, and computing it that way would
cost hundreds of credits per account — but `extended_workforce` already answers it at
company grain for one row and one credit, with display-ready reasons. Reach for a
custom dimension only after `describe_onfire_schema(show_catalog=True)` shows nothing
that covers it.

### Four rules that make the blend honest

1. **Weights re-normalise to 1.0** after custom dimensions are added. Adding one at
   0.20 scales the six base dimensions by 0.80. Weights that sum to something other
   than 1.0 produce scores that cannot be compared between reps.
2. **A dimension with no data scores `null` and is dropped, its weight redistributed
   proportionally. It does not score 0.** "No data" and "bad" are different findings.
   Scoring an unavailable roster as 0 penalises the account for a gap in our coverage.
   The exception is a **presence-only** surface such as `extended_workforce`, where
   absence is itself the answer — an unflagged company scores low, not `null`. Check
   which kind a layer is before deciding what its silence means.
3. **No dimension exceeds 50 without at least two dated evidence items.** Inference
   alone is capped. This is the rule that stops a plausible narrative becoming a 90.
4. **Every dimension emits `evidence[]`** — verbatim text or a measured fact, each with
   a date and a source. That array is what renders behind the clickable breakdown, and
   a score a rep cannot audit is a score they will not trust.

### The floor

Include an account only if **both** hold:

- `weighted_fit >= plan_shape.fit_floor` (default 70), **and**
- `signal_strength` or `trigger_freshness` scored at least 60 **with dated evidence**.

The second clause is what makes "there is a real reason to act now" computable rather
than a matter of taste. A high ICP fit with no live trigger is a good account to know
about, not a good account to work this week.

**A broad territory raises the bar rather than blocking the run.** When
`rep_profile.territory_breadth == "broad"`, add 10 to the effective floor (70 → 80)
and require **two** dated triggers instead of one.

This is the arithmetic behind accepting a continent. Weak gates mean a large
candidate set, and a large set will always throw up something that scores well by
chance — which is exactly how a plan ends up looking real and being noise. A bigger
universe is a reason to be pickier, so the compensation is mechanical rather than a
matter of judgement. Say so in the delivery summary: the territory was broad, the
floor was raised, here is what still cleared it. If little clears, that is the honest
answer and the argument for narrowing the patch.

Then take **up to** `accounts_per_run`.

- **Never pad.** Three strong accounts beat five with two weak ones. Deliver fewer and
  say so in the summary and the KPI strip.
- **Never lower the floor to fill the slate.** If that is tempting, the finding is that
  the patch is too narrow or the week is quiet — both useful things to tell the rep.
- **If nothing clears**, deliver zero accounts plus a short "why nothing cleared this
  week" block naming the closest three and each one's blocking dimension. That is a
  signal to widen the ICP, and far more useful than five accounts the rep will ignore.

---

## Billing discipline

`ask_onfire` **bills one credit per row returned.** Three consequences:

- **Set a small explicit `limit` when you know what you need.** Five to ten rows is
  plenty for evidence.
- **When the count itself is the signal**, leave `limit` unset deliberately. The call
  bounces with `needs_confirmation` and `stage: "row_budget"`, returning the match size
  with **no rows billed**. Use this to size a candidate set, and for the free
  warm-path count. Confirm this behaviour on first use in a session.
- **Never reflexively set `confirmed: true`** to force a large pull through. A bounce
  means the match is bigger than the budget; the right response is almost always a
  smaller budget, not a bigger one.

Aggregate selects (a `post_count` or an `attendee_count`) cost a fraction of the rows
behind them. Use them wherever the number feeds a score rather than a quote.

Skip any pull whose dimension already has enough evidence. Enrichment is additive; a
pull that changes no decision is wasted credit.

---

## Error handling

Never fail the run on a single layer. Every row below degrades.

| Situation | Action |
|---|---|
| `needs_confirmation` with `stage: "row_budget"` when you wanted rows | Nothing billed. Lower `limit` to what the dimension needs and resubmit. |
| A layer returns zero rows | Score that dimension `null`, redistribute the weight, continue. |
| A layer errors | Same as zero rows, and note it internally. |
| An entity is absent from the catalog | Skip the layer entirely; do not substitute a guess. |
| A concept fails to resolve | Drop that concept; never pass the raw term as a literal filter value. |
| The CRM read fails | Skip the CRM inputs and the state gate; continue on the remaining sources. |
| The approved sheet is unreachable | Skip it; continue. Never fail the run on an optional external input. |
| `match_company` finds no confident match | Drop the candidate — an unresolvable company cannot be scoped or scored. |
| Fewer candidates survive the gates than the target | Correct behaviour. Deliver what cleared. |
