# Config, origin derivation, and the setup interview

Config is **per rep**, never per tenant and never hardcoded. Two reps on the same
tenant get different ICPs, their own state file, their own artifact, and their own
plan workbook.

Resolution order, stopping at the first hit:

1. Memory, key `weekly_territory_plan:<rep_owner>`.
2. The setup interview below, for anything missing.

There is deliberately **no committed `config.example.json`**. A committed example
becomes a second source of truth that drifts, and a plausible-looking tenant slug
sitting in a file is invisible to the PII gate. The worked example lives here instead.

---

## Schema

```jsonc
{
  "schema_version": 2,
  "rep_owner": "rep@yourcompany.com",
  "tenant_id": null,                    // omit on a normal session; see below

  "warm_intro_origin": {                // DERIVED, never asked when derivable
    "tenant_id": null,
    "company_linkedin_url": null,
    "source": null,                     // get_current_tenant | config | asked
    "resolved_at": null
  },

  "plan_shape": {
    "accounts_per_run": 5,
    "people_per_account": 5,
    "fit_floor": 70,
    "cadence_label": "week"
  },

  "rep_profile": {
    "geography": [],                    // prefer states / metros / cities, or a named list
    "excluded_geos": [],
    "territory_breadth": null,          // DERIVED at save: "granular" | "broad"
    "named_accounts": [],
    "size_band": { "min": null, "max": null },
    "verticals": [],
    "public_private": "any",
    "icp_angles": [],                   // ranked; seeded from the tenant's use cases
    "competitive_watchlist": [],         // seeded from the tenant's configured competitors
    "technologies_watchlist": [],        // seeded from the tenant's configured technologies
    "self_sourced_titles": [],           // the deterministic title pull
    "ai_sourced_titles": [],             // what prospecting should widen to
    "seniority_floor": "director+",
    "hidden_signal_layers": [],          // post-first-run tuning only; never set at setup
    "dimension_weights": {
      "icp_fit": 0.20,
      "signal_strength": 0.25,
      "use_case_relevance": 0.20,
      "committee_reachability": 0.15,
      "trigger_freshness": 0.15,
      "momentum": 0.05
    },
    "custom_dimensions": []              // see scoring notes in account-resolver.md
  },

  "external_inputs": {
    "approved_sheet": {
      "enabled": false,
      "file_id": null,
      "account_key_column": "domain",
      "approved_column": "approved",
      "owner_column": "owner",
      "notes_column": "notes"
    },
    "crm": {
      "enabled": false,
      "owner_field": null,
      "account_object": null,
      "exclude_stages": [],
      "stale_days": 14
    }
  },

  "state": {
    "state_file_path": "territory-state-<rep-slug>.md",
    "artifact_id": "weekly-territory-plan-<rep-slug>",
    "plan_workbook_path": "Territory_Plan_<rep-slug>.xlsx",
    "report_path": "Weekly_Plan_<rep-slug>.html"
  },

  "plan_format": {
    "display_name": "5x5",               // drives every rep-facing string
    "banner": "TERRITORY PLAN",
    "touchpoints": [
      "Personalized Email",
      "Event Invite",
      "Partner Engagement",
      "Marketing Content",
      "Sequence Cadence"
    ],
    "palette": { "banner": "EFECE3", "week": "34D399", "account": "0B3B2E" }
  },

  "branding": { "internal_mode": true, "shareable_mode": "customer_facing" },
  "enrichment_policy": "on_demand",      // fixed; not a user setting
  "contact_data_offer": true,            // offer the batch after each interactive run
  "schedule": { "cron": "0 7 * * 1", "timezone": null, "scheduled_task_id": null },
  "last_run": { "week_of": null, "run_id": null }
}
```

### Fields worth explaining

**`tenant_id` — leave it unset.** The server resolves the tenant from the
authenticated session. The internal slug does not track a company's brand name or
its current email domain and may differ from both, so guessing it is worse than
omitting it. Set it **only** on a super-tenant session that is deliberately acting
for another tenant.

**`plan_format.display_name`** is the rep's word for this routine, default `5x5`.
Every rep-facing string reads from it: the artifact heading, the KPI subline, the
workbook banner, the report filename, and the scheduled-task prompt. The folder is
named after the deliverable; the rep sees their own vocabulary.

**`plan_shape.accounts_per_run` is a ceiling, not a target.** Nothing in the run may
pad toward it.

**Every signal layer runs. There is no layer-selection setting.** The full catalog in
`account-resolver.md` runs on every account, every week. A rep cannot switch a layer
off at setup, because choosing between layers they have never seen is not a choice
they are equipped to make: the ones they drop are the ones they would never discover,
and a plan missing half its evidence reads as a thin product rather than a thin
configuration. Reps tune from what they have *seen*, not from a menu.

`hidden_signal_layers` therefore exists for one narrow job — a rep who has watched a
layer appear for a few weeks and does not want it on the page any more. It suppresses
**rendering only**, never collection: a hidden layer still scores, still feeds the
ranking, and still counts toward the relevance floor. It may only be set through the
config-change grammar, only after that layer has appeared in a delivered plan, and
never during setup.

**Migrating a v1 config.** On load, drop `desired_signal_layers` if present — the
field no longer exists and an empty one used to mean "everything", which is now the
only behaviour. Preserve a non-empty `hidden_signal_layers`: those were deliberate
choices about a specific layer. Reset an empty one and write back `schema_version: 2`.

**`enrichment_policy` is fixed at `on_demand`.** It is in config to be *read*, not
changed. Nothing is ever enriched as a side effect of building a plan.

**`contact_data_offer` decides who speaks first, and defaults to `true`.** The two are
easy to confuse, so keep them apart: the *policy* governs whether a build may enrich —
it may not, ever. The *offer* governs whether the skill volunteers afterwards.

With it on, the skill finishes an interactive run and offers verified emails and
phones for the people it just surfaced. Accepting runs the ordinary consent flow, so
the rep sees the real count and the server's own wording before anything is pulled and
can still say no. Nothing about the guardrail moves — the rep simply stops having to
remember that the capability exists.

It defaults on because the opposite default was inherited from a single
credit-conscious customer and quietly became everyone's. A rep who wants the old
behaviour says so once and gets it.

**The offer never fires on a scheduled run.** Nobody is present to approve a paid
action, which is the same reason writes are barred there.

**`geography` should be granular, but a broad one is not a refusal.** Reps mostly
own narrow patches, and a granular geography is the single most useful gate there
is. Some reps genuinely own a continent, though, so the rule is about *total gate
strength*, not about geography alone — see "Gate sufficiency" below.

---

## Deriving `warm_intro_origin`

The warm-intro origin is *the rep's own company* — who on their team can make the
introduction. Getting this wrong produces confidently wrong connector names, which
is worse than producing none.

`detect_warm_intros` resolves the origin from tenant settings **itself**. So there is
nothing to configure in the normal case, and the field exists only as a cache plus an
escape hatch. Run this ladder at preflight on **every** run:

1. **Normal (non-super) tenant session.** The origin is that tenant. Record
   `source: "get_current_tenant"`. Resolve `company_linkedin_url` from tenant
   settings, falling back to `match_company` on the tenant's own domain. **Do not ask
   the rep.** This covers effectively every real rep session.
2. **Super-tenant session** — the session can act for another tenant, so the origin
   is genuinely ambiguous (a solutions engineer running on a customer's behalf). Use
   `config.tenant_id` if set. If not, this is the **only** case where the interview
   asks: *"Which team's relationship network should warm paths be computed from?"*
   Record `source: "asked"`.
3. **Cache, but revalidate.** On each run, if the session tenant no longer matches
   the stored `tenant_id` and the session is not a super tenant, re-derive **and tell
   the rep the origin changed.** Silent drift here is the failure mode to avoid.
4. **Never** accept an origin from the rep's free-text ICP answers, and never let a
   config-change command overwrite it on a non-super session.

Pass `origin_company_linkedin_url` to `detect_warm_intros` only in case 2.

---

## The setup interview

Run on the first run for a rep, and whenever they ask to change their ICP. The goal
is to understand **this rep's narrow patch** well enough that every run surfaces
accounts and people they actually own.

### Rules

- **Every question must change what the plan surfaces.** No generic CRM, tooling, or
  "how do you like to sell" questions.
- **Ask for fine resolution on territory, and accept what comes back.** Push for
  states, metros, cities, or a named-account list — "Bay Area plus Pacific Northwest"
  beats "North America" every time. But a rep who answers "NA and EMEA" gets a plan,
  not a lecture. Run the gate-sufficiency check below instead of refusing.
- **Never ask the rep to resolve a contradiction the interview created.** If two
  configured choices conflict, resolve it in favour of showing *more* data and note it
  internally. Asking "your play depends on a layer you told me to hide — what should I
  do?" exposes wiring the rep should never have been made responsible for.
- **Seed every pick-list from the tenant's own configuration**, not from a built-in
  list. Read the tenant's configured use cases, competitors, technologies, and
  buying-committee personas first, then offer those as options the rep confirms or
  edits. This is what keeps the skill tenant-agnostic — the questions are generic, the
  options are the tenant's.
- **Group questions into a few short messages.** Not one wall of text.
- **Log every question you ask** to the setup log in `state-file.md` — the question,
  the options offered, the answer, and whether it was the default. Then use it: a
  question every rep answers with the default is not gathering information, it is
  spending patience, and it should be retired in favour of the default. Review that
  before adding a question, not after.
- **Do not ask about the warm-intro origin** unless the ladder above reached case 2.
- End by summarising the captured profile and asking the rep to confirm before saving.

### Gate sufficiency

The resolver needs enough **hard gates** to narrow the universe before it spends
anything on scoring. Geography is the most convenient gate, not the only one — so
judge the profile as a whole rather than rejecting one answer.

Count the gates that are actually populated:

| Strength | Gate |
|---|---|
| **Strong** | `geography` at state / metro / city resolution |
| **Strong** | a non-empty `named_accounts` list |
| **Strong** | `crm.enabled` with an `owner_field` — the rep's book *is* a territory |
| **Medium** | a non-empty `verticals` list |
| **Medium** | a `size_band` with both bounds set |
| **Medium** | a non-empty `competitive_watchlist` or `technologies_watchlist` |

A profile is sufficient with **one strong gate, or two medium ones**. Set
`territory_breadth` to `"granular"` when it clears, `"broad"` when it does not.

**When it does not clear, do not refuse.** Say plainly what a plan built on it would
be — with almost no gates the resolver ranks on raw signal strength across most of
the world, which produces something that looks like a real plan and is noise. Then
offer the three narrowings that actually fix it:

1. a named-account list, if the rep works one
2. a vertical, even a broad one
3. a tighter employee range

If the rep supplies one, re-run the check. **If they decline, proceed anyway** with
`territory_breadth: "broad"` saved on the profile — the resolver compensates by
raising the bar rather than by asking again (`account-resolver.md`). Say which you
did, once, and get on with it.

### Questions

**A. Territory — required**
1. What is your exact patch? States, metros, or cities. If you work a named-account
   list instead of a geography, paste it or point me at it.
2. Anything explicitly outside your patch that I should exclude?

**B. Segment and firmographics**
3. Employee range you own, and any ARR band.
4. Which verticals do you focus on? Narrow is good.
5. Any preference on public versus private, PE-backed, or post-IPO?

**C. Which of your company's angles you sell on**
6. *(Offer the tenant's configured use cases as a ranked pick-list.)* Which of these
   matter most to you? Rank the top three.
7. *(Offer the tenant's configured competitors and technologies.)* Which of these do
   you most want to watch or displace?

**D. Titles — split what you source yourself from what the engine should find**
8. Which titles do you want to hunt yourself every week? This becomes the
   deterministic title pull.
9. Which additional roles should prospecting go find beyond your list, to widen the
   buying committee?
10. Seniority floor — director and above, or include managers and team leads?

**E. Scoring emphasis**
11. Which two or three signals should weigh most when I rank your accounts?
12. Is there a measured metric specific to how you qualify that I should score on?
    *(If yes, capture it as a custom dimension — see `account-resolver.md`.)*

**F. Cadence**
13. What day and time should the refresh run? Default is Monday 07:00 your time.
14. Each week, once your plan is built, I'll offer verified emails and phones for the
    people I surfaced — you'll see exactly how many and what it costs, and you can say
    no. Want me to skip that offer? *(Sets `contact_data_offer`. Ask it this way round:
    the previous phrasing asked the rep to confirm a restriction, which is not a
    decision so much as a nudge to keep whatever the default happened to be.)*

There is deliberately **no question asking which signal layers to show.** Every layer
runs — see the field note above. Question 11 asks which signals should carry the most
*weight*, which is a different question and one the rep can answer: it tunes the
ranking without hiding anything from the page.

### Saving

Write everything to that rep's own `rep_profile`. The tenant's configuration only
fills gaps the rep did not specify. Run the gate-sufficiency check before saving and
record the resulting `territory_breadth` — a profile with no real gates is the single
biggest cause of an irrelevant plan, and the resolver needs to know which kind it got.

---

## Config-change grammar

Recognise these as CONFIG CHANGE, apply the edit, show a **before/after diff**, save,
confirm, and stop. Do not rebuild the plan unless the rep also asks to run it.

| Rep says | Change |
|---|---|
| "use sheet `<id>`" / "my tracker is `<id>`" | the relevant `state` or `approved_sheet` id |
| "change my ICP / segment / territory / verticals" | the matching `rep_profile` fields; re-run interview sections as needed |
| "add / drop `<title>`" | `self_sourced_titles` or `ai_sourced_titles` |
| "weight `<signal>` higher" | `dimension_weights`, then re-normalise to 1.0 |
| "stop showing `<layer>`" | move it to `hidden_signal_layers` — **only** once that layer has appeared in a delivered plan, and it suppresses rendering only, never collection |
| "only director and above" | `seniority_floor` |
| "reschedule to `<time>`" | `schedule.cron`; **update** the existing task, never create a second |
| "show me my current setup" | render the profile read-only; change nothing |
| "call it `<name>`" | `plan_format.display_name` |
| "stop offering contact data" / "ask me about emails each week" | `contact_data_offer` |

**Escalation:** if `rep_profile` is missing `geography`, `size_band`, or
`self_sourced_titles`, a request to *run* escalates to a partial interview for exactly
those fields. Never run on defaults — a plan built on a default ICP is
indistinguishable from a real one at a glance, and worse than no plan.
