# The people layer

Up to `people_per_account` people per account. The order matters: **deterministic
first, then AI-augmented, then warm-scored**. Reversing it produces a list ranked by
whoever the model found most interesting rather than by who actually owns the problem.

```
title pull (deterministic)  ->  prospecting (augment + rank)  ->  dedupe
   ->  guarantee committee coverage  ->  warm paths  ->  attach why-now
```

No enrichment happens anywhere in this sequence. People surface with a profile link
only.

---

## Step 1 — the deterministic title pull

This is how the *right* people arrive, rather than whoever happened to post a message.
Titles come from two places, combined:

- `rep_profile.self_sourced_titles` — the titles this rep hunts personally.
- The tenant's configured **buying-committee personas**, read from tenant settings at
  preflight.

Neither is hardcoded in this skill. A committee baked into a skill file is a committee
that is wrong for every tenant but one.

One query per persona, because `insight_filters` AND together:

```
ask_onfire(query={
  entity: "contact",
  select: ["full_name", "job_title", "linkedin_url", "location"],
  filters: [{dimension: "current_company_url", op: "eq", value: "<account linkedin url>"}],
  insight_filters: [{kind: "persona", value: "<resolved committee persona>"}],
  limit: 5
})
```

Resolve each persona through `resolve_insights` first, carrying `kind`. Confirm the
exact field names with `describe_onfire_schema(["contact"])` before authoring —
in particular, **check whether `contact` exposes a seniority dimension** for the
`seniority_floor` gate. A seniority dimension is documented on
`hiring_manager_signal` (`seniority_executive` / `seniority_director` /
`seniority_teamlead`), so an analogue is plausible but must be verified rather than
assumed. If it does not exist, apply the floor by inspecting `job_title` and say so
internally.

The actively-hiring managers found in the resolver's broad phase belong in this merged
set too. They are, by construction, people with a live budget and a stated need.

---

## Step 2 — prospecting, to augment and rank

```
ai_prospecting(action="run", company_linkedin_url="<account linkedin url>")
```

- **`action="run"` is the only action.** There is no single-person scoring path.
- **Never pass `target_tenant_id`.** The tenant comes from the session.
- **Polling:** a `still_running` response returns `run_ids`. Re-call with
  `ai_prospecting(action="run", run_ids=[...])`, or with the identical arguments —
  the server dedups and never creates a duplicate run. Keep polling until complete.
- **Two response shapes.** A small result set arrives inline as a `prospects` array —
  use it directly. A larger one arrives as `top_picks` plus `preview_rows` plus a
  dataset id; slice the remainder with `query_datasets` against that id rather than
  re-running the tool. Re-running to see more rows is the expensive mistake here.

Run it whenever the title pull is thin, and to rank the merged set. If prospecting is
unavailable on the tenant, fall back to the title pull and the hiring-manager rows,
note it in the internal summary, and **never surface the limitation to a customer** —
that is our capability detail, not their problem.

### Interpreting the fields — load the glossary first

**Call `ai_prospecting_field_glossary` before rendering any score, tier, or warm
field.** These fields are easy to invert: at least one score is a tier where *lower is
better*, and the warm-intro field is an enum rather than a number. Getting one
backwards produces a confidently wrong ranking.

The binding rule: **if you cannot point to the glossary entry that justifies a phrase,
remove the phrase.** The repo's own skills disagree slightly about which score fields
are returned, so the glossary — not this file and not another skill — is the authority
for the session you are in.

---

## Step 3 — dedupe

Merge the title pull with the prospecting rows, keyed on the **normalised** LinkedIn
URL (lowercase, no scheme, no `www.`, no query, no trailing slash — see
`state-file.md`).

On a collision, **prefer the prospecting row**: it carries the reasoning, the persona
labels, and the warm-path fields that the title pull does not.

Then drop anyone in `worked_contacts` or the suppression list. Net-new only.

---

## Step 4 — guarantee committee coverage

Across the merged set, fill one seat per configured committee persona, plus a
**signal-holder seat** — the person who authored the account's why-now message, if they
are not already covered. The signal holder is often the warmest technical entry to an
account precisely because they have already said the problem out loud in public.

If no real person exists for a key seat, emit a **labelled TBD entry showing the title
to target**. A visible gap is useful; an invented name is not. It tells the rep exactly
what to go and find.

Take **up to** `people_per_account`. Fewer is correct when fewer genuinely fit — the
same "never pad" rule as the account layer, and the workbook builder enforces it too.

---

## Step 5 — warm paths

A warm path is a relationship route into a person, relative to the rep's **own**
company. The origin is resolved from tenant settings by the tool itself — see the
derivation ladder in `config-and-setup.md`.

For a shortlist of five people per account, **people mode is the right call**:

```
detect_warm_intros(
  tenant_id=<the origin tenant>,
  person_linkedin_urls=[<the shortlisted profile urls>]
)
```

Every supplied person gets a verdict, so there is no row-budget guessing and no
possibility of missing someone who was outside a company-mode limit. Supply at most
100 URLs; a list longer than 50 requires explicit confirmation, which a per-account
shortlist will never approach.

Company mode — `target_company_linkedin_url` with `limit` unset — belongs in the
**resolver**, where the free count of warm paths is a scoring input. Do not use it
here; it answers a different question.

### Tier words never leave the building

The tool returns a strength tier. **It is internal.** Never render it, never put it in
the workbook, never say it out loud to a customer. What the rep sees instead:

> Introduced by <connector name>, who overlapped with them at <shared company>
> from <start> to <end>.

Rank warm and contact-verified people above cold ones **within the same committee
tier** — never across tiers. A warm junior contact does not outrank a cold economic
buyer.

The warm angle must appear in **both** deliverables: on the person's card in the report
and appended to that person's Notes cell in the workbook. And when a connector exists,
the drafted first touch opens with it — that is the whole point of finding it.

### The degradation ladder

This skill is **never blocked** on the warm-intro tool. In order:

1. **Prospecting's own warm fields.** Prospecting rows already carry a connecting
   employee name, a shared company, a connection-strength score, and flags for having
   previously worked at the rep's company. That is a complete substitute for the warm
   block — confirm the exact field names against the glossary.
2. **Alumni overlap via `ask_onfire`.** People currently at the target who previously
   worked at the origin company: query `entity: "contact"` filtered to the account,
   joined to `people_experiences` filtered to the origin company URL with
   `is_primary: false`.
3. **Omit silently.** No warm block on the card; the warm sub-score of
   `committee_reachability` becomes `null` and its weight redistributes.

**Never surface "warm intro unavailable"** on a customer-facing surface. An empty state
on the card is fine and honest; naming our missing capability is not.

---

## Step 6 — attach the why-now

Every person carries the specific thing that ties them to this account, this week:

- The verbatim message and its date, or
- the footprint, event, hiring, promotion, role-movement, or developer-activity fact
  from the resolver that put the account on the list.

**Quotes are reproduced byte-for-byte.** Never tidied, never truncated mid-sentence to
fit, never paraphrased into something cleaner. If it is too long for the card the
template truncates it for display and shows it in full in the modal — that is a
rendering concern, not a licence to rewrite the source.

Then draft one personalised first touch per person, grounded in **that person's**
signal, the account hypothesis, and the warm path if one exists. Value propositions
come from the tenant's configuration, not from this skill — every claim in a draft
must trace to tenant config or to a signal in this run.

Attach the touchpoint plan from `plan_format.touchpoints`.

---

## What must not happen here

- **No enrichment during the build.** Not for one person, not "just to check". Contact
  values are revealed only by an explicit rep action, through the consent flow in
  `guardrails.md`.
- **No invented people.** A labelled TBD seat is the only acceptable filler.
- **No invented reasoning.** If prospecting returned no explanation for a person, say
  what the title pull knows and stop. A fabricated rationale is worse than a thin one
  because the rep cannot tell it apart.
- **No tier words**, anywhere a customer might read them.
- **No cross-tier reordering** to favour a warm path.

---

## Error handling

| Situation | Action |
|---|---|
| Prospecting returns `still_running` | Re-call with the returned `run_ids`. The server dedups; a repeat call is not a second run. |
| Prospecting returns zero prospects, or is disabled | Fall back to the title pull plus hiring managers. Note internally; never surface it to a customer. |
| Prospecting returns a preview shape | Slice the dataset id with `query_datasets`. Never re-run to see more rows. |
| The title pull returns zero rows for a persona | Leave that seat as a labelled TBD. Do not widen the persona to fill it. |
| `resolve_insights` cannot resolve a persona | Skip that persona and note it; never pass the raw term as a filter value. |
| The account has no LinkedIn URL even after `match_company` | Skip the people layer for that account entirely — every recipe here is scoped by company URL. |
| The warm-intro tool errors or is unavailable | Walk the degradation ladder. Never fail the run. |
| A person has no LinkedIn URL | Do not surface them as a named contact — they cannot be deduped or enriched. Use a TBD seat. |
| Fewer than the target number of people genuinely fit | Correct behaviour. Deliver fewer. |
