---
name: outreach-sequence-email-composer
description: End-to-end workflow to put a prospect into an Outreach sequence and have the agent compose the email for the manual-email step, grounded in Onfire data (the prospect, their company, the tenant's ICP), user input, and conversation context — then stage it as a draft and ask the user whether to send automatically or send it themselves. Works for a single prospect or many. Use whenever the user says things like "add this prospect to a sequence and draft him an email", "write a custom email for X in Outreach", "sequence these people and compose emails", "put them in my SAP Campaign and draft the outreach", "create a sequence and start emailing these accounts", or any request that combines an Outreach sequence with composing/sending a personalized email. Can also create a brand-new sequence first if the user wants one. Reads and writes your tenant's SEP via the Onfire Integrations tools.
---

# Outreach Sequence Email Composer

Take a prospect (or a list), get them into an Outreach **sequence**, and have the agent **compose the actual email** on a **Manual Email** step — personalized from Onfire data — then stage it as a draft and let the user decide whether to send it automatically or do it themselves.

This skill is the orchestration layer over the Onfire Integrations tools and the Onfire data tools. The Onfire engine owns the auth and the API plumbing; this skill owns the flow, the email composition, and the pre-flight checks that keep the whole thing from silently stalling.

## The shape of the workflow

```
Resolve tenant + integration ids
   → Choose sequence (use existing OR create new — ask the user)
   → Create / resolve the prospect in Outreach
   → Enroll the prospect (sequenceState)
   → Wait for the prospect to ACTIVATE and the manual-email DRAFT to generate
   → Compose the email from Onfire data + ICP + user input + conversation context
   → Write the email into the draft mailing (stage it)
   → Ask the user: send automatically, or leave it for them to send?
```

The single-prospect and many-prospect cases run the same steps; the batch case just loops and respects throttling. See "Many prospects" below.

## Tools this skill orchestrates

| Purpose | Tool |
|---|---|
| Get tenant config + integration ids + **ICP** | `get_tenant_settings()` |
| **Read** Outreach | `sep_read(relative_url, http_method="GET", params=…)` — **no** `integration_id` |
| **Write** to Outreach (create/enroll/draft/send) | `sep_write(http_method, relative_url, json_body=…)` — **no** `integration_id` |
| Resolve a person → LinkedIn + title/company | `match_person` |
| Resolve a company → LinkedIn + firmographics | `match_company` |
| Score the prospect + get talking points | `ai_prospecting` |
| Company narrative (10-K, footprint, intent, use cases) | `account_research` |
| Targeted signals (intent, footprint, hiring, events, growth) | `ask_onfire`, `query_intent_signals` |

Outreach's API root (`api/v2/`) is **already applied** by the engine. In `relative_url` use bare paths: `prospects`, `sequences`, `sequenceSteps`, `sequenceStates`, `sequenceTemplates`, `templates`, `mailings`, `tasks`, `mailboxes`. Never prefix `api/v2/`.

Endpoint bodies (create prospect, enroll, draft, send, create sequence/step/template) live in **`references/outreach-api-cheatsheet.md`** — read it before writing any Outreach call.

The email-writing rubric and the researched cold-email best practices live in **`references/email-playbook.md`** — read it before composing.

---

## STEP 0 — Pre-flight (do this first; it is where everything breaks)

Most failures in this flow are **not** code errors — they're configuration gates that leave a prospect silently stuck in **"pending"** with no draft to edit. Check these before promising the user anything.

1. **Confirm the provider, every session.** Call `get_tenant_settings()` and read `sep.type` — it must be `"outreach"` for this skill. If it's `salesloft`, `gong`, or `replyio`, this skill's endpoints do not apply: use **`sep-cadence-enrollment`** instead (and `gong-create-and-push-to-flow` for Gong).

   `sep_read`/`sep_write` take **no `integration_id`** — the engine resolves the tenant's Outreach integration internally, so there is no id to fetch, rotate, or go stale. (Only `crm_read` still takes one, from `crm.integration_id`.)

2. **OAuth scopes.** The flow needs: `prospects.read/write`, `sequences.read/write`, `sequenceSteps.read/write`, `sequenceStates.read/write`, `sequenceTemplates.all` (or `.read`), `templates.all` (or `.read`), `mailboxes.read`, `mailings.read/write`, `tasks.read/write`, `emailAddresses.read/write`. A missing scope returns `403 unauthorizedOauthScope` naming the exact scope. `schedules.read` is commonly **absent** — expect not to be able to read the delivery schedule via API, and diagnose schedule issues from the UI instead.

3. **Scopes need a token refresh.** Adding scopes in the Outreach app does **not** upgrade an already-issued token. The integration must be **reconnected / re-authorized** in the Onfire app before the new scopes take effect.

4. **A sendable mailbox must exist.** `GET mailboxes` and pick one where `sendState == "ENABLED"` and `sendDisabled == false`. **Sending and syncing are independent**: the "Enable sending" toggle is what matters for outbound; the "Enable syncing" toggle only governs reply tracking and does **not** block sends. Dev tenants often have mailboxes with sending disabled — surface which mailbox you'll send from and that its `from` address is what the prospect will see.

5. **The sequence must be ACTIVE.** A prospect added to an inactive/disabled sequence stays `pending` forever. Confirm `enabled == true` (or have the user click **Activate**).

6. **The delivery-schedule window gates activation.** Even a step set to trigger **Immediately** obeys the sequence's **delivery schedule** (e.g. "Weekday Business Hours" + timezone). Enroll outside that window and the prospect sits in `pending` with **no task and no draft generated** — there is nothing to write into. To make it activate now, point the sequence at a 24/7 / "every day, all hours" schedule (or wait for the window). You usually can't read the schedule via API (no `schedules.read`), so confirm hours/timezone in the UI.

7. **You can only stage a draft once it exists.** The manual-email draft mailing is created by Outreach **after** the prospect activates and reaches the manual-email step. Don't try to PATCH a mailing before it exists — poll for it (see Step 5).

If a gate isn't satisfied, **tell the user exactly what to fix** (activate the sequence, open the schedule, enable sending on the mailbox, reconnect for scopes) rather than looping on a call that will keep failing.

---

## STEP 1 — Choose the sequence (existing or new)

Ask the user which they want unless they've already said. Don't assume.

**Use an existing sequence.** `GET sequences?sort=-updatedAt` (optionally `filter[name]`), show the candidates with their step counts and `enabled` status, let the user pick. Capture the sequence `id`.

**Create a new sequence.** Get the few inputs that matter, then build it (bodies in the cheat-sheet):
- **Name** (required), description, sales motion.
- **Sequence type:** choose **"Steps by day interval"** (`sequenceType: "interval"`) so prospects auto-activate relative to when they're added — not **"by exact date/time"**, which makes every step wait for a fixed calendar date.
- **Delivery schedule:** business-hours by default; offer a 24/7 schedule if they want immediate activation (and remind them to switch it back afterward).
- Then `POST sequenceSteps` a **Manual Email** step (`stepType: "manual_email"`, `order: 1`, interval `0` = immediately) and attach a **placeholder template** (`POST templates` then `POST sequenceTemplates`). Manual Email steps require a template — but the content is a throwaway shell; the agent overwrites it per prospect. A blank-ish subject/body (e.g. subject `"draft"`, body `"placeholder"`) is fine.
- Tell the user to **Activate** the sequence (or do it if they ask) before enrolling.

Either way, the email step you target **must be a Manual Email step** — that's what produces an editable per-prospect draft. (An Auto Email step sends automatically with no editable draft; to personalize an auto step you'd need the `{{customN}}` variable route instead — see "Alternative" at the end.)

## STEP 2 — Create or resolve the prospect

Always **dedupe first**: `GET prospects?filter[emails]=<email>`. If they exist, reuse that prospect `id` and skip the rest of this step. Make sure the prospect has an **email address attached** — an email step can't send without one. If the user gave only a name/company, resolve identity with `match_person` first so you create a clean, correct record.

**If they don't exist, how you create them depends on the tenant** — see `sep-cadence-enrollment` for the full rule:

- **CRM connected (`crm.enabled` is true) → go through the CRM.** Push the person with `crm_write(entity_type="prospect", records=[…])`, then wait for the tenant's CRM→Outreach mirror to create the prospect, then re-run the dedupe lookup above to get the prospect `id`. This respects the tenant's CRM field mapping and ownership routing; a direct create bypasses both and can duplicate the record the mirror is about to create anyway.
- **No CRM connected → `POST prospects` directly.** With no mirror to fight, this is the only path and it's the correct one.

Don't guess which case you're in — read `crm.enabled` from `get_tenant_settings()`.

## STEP 3 — Enroll the prospect

`POST sequenceStates` with relationships `prospect`, `sequence`, and a sendable `mailbox` (from Step 0.5). The response starts as `state: "pending"` — that's normal at creation.

## STEP 4 — Wait for activation

Poll `GET sequenceStates/<id>` until `state` becomes `active` and `activeAt` is set. On activation, `activeStepMailings` and `activeStepTasks` populate. If it stays `pending`, it's a Step-0 gate (schedule window, inactive sequence, mailbox) — diagnose and tell the user. There's no error on the state when it's just waiting (`errorReason`/`pauseReason` are null) — absence of an error does not mean it will activate; the window/mailbox is the usual cause.

## STEP 5 — Find the draft

`GET mailings?filter[prospect][id]=<id>` (the active-step mailing also appears under the sequenceState's `activeStepMailings`). The manual-email draft has `mailingType: "sequence"` and `state: "drafted"`. Grab its `id`. No draft yet → return to Step 4.

## STEP 6 — Compose the email

Read **`references/email-playbook.md`** and compose from these four sources:

1. **The prospect** — title, persona/seniority, tech footprint, recent activity/intent. From the prospect record + `ai_prospecting` talking points + `ask_onfire`/`query_intent_signals`.
2. **Their company** — 10-K themes, hiring momentum, growth/adoption trends, events, competitor/tech footprint. From `account_research` + `ask_onfire`.
3. **The tenant's ICP** — from `get_tenant_settings.account_research`: `golden_persona`, `competitors`, `technologies`, `organization` personas, `buying_committee_queries`, and derived use cases. Frame the value prop and competitive angle around *this tenant's* ICP, not generic copy.
4. **User input + conversation context** — the angle/product to pitch, tone, constraints, anything established earlier in the chat.

Hold the line on the researched essentials (full detail in the playbook): ~50–120 words, short paragraphs; subject under ~50 chars and personalized; open with a **specific, signal-based hook** (not a self-intro) that the subject line echoes; **multi-point personalization** tied to a real business signal; **one** soft, binary CTA ("Worth a quick call?"); link-light; keep the unsubscribe footer. **Ground every claim in real Onfire data — never invent signals, numbers, or facts.** If the data is thin, write a leaner email rather than fabricating specificity.

## STEP 7 — Stage the email on the draft

`PATCH mailings/<id>` setting `subject` and `bodyHtml` (and `bodyText` if you like). This **overwrites** the placeholder — there is only ever one email on the step; the placeholder is the same draft's starting content, not a separate message. Leave `state` as `drafted`. The email is now sitting on the manual-email **task** in Outreach, unsent.

## STEP 8 — Ask: auto-send, or self-send?

This is required. **Never send without explicit user confirmation.**

> "It's staged on the manual-email task, ready to go. Want me to send it now, or leave it for you to review and send yourself in Outreach?"

- **They want to send themselves** → done. It lives on their Tasks tab; they hit Send.
- **They explicitly say send** → `PATCH mailings/<id>` with `state: "scheduled"` (a past/now `scheduledAt` sends immediately). Then optionally `GET mailings/<id>` to confirm it moves `scheduled → delivering → delivered`. Sending is attributed to the sequence step — tracked, threaded, counts toward sequence metrics.

---

## Many prospects

Same flow, looped, with a few additions:

- **Resolve/dedupe in batch.** Use `match_person` (batches up to 100) for any rows lacking clean identity, and dedupe each against `GET prospects?filter[emails]=` before creating.
- **Throttling is real.** Sequences cap "Max adds per user every 24 hours" (default 50). Large lists will queue; tell the user up front.
- **Compose per prospect.** Each email is grounded in *that* prospect's and company's Onfire signals — the whole point. Don't reuse one body across the list (that's the auto-template anti-pattern).
- **Pace the activation polling.** Each prospect activates independently; collect their draft `id`s as they appear.
- **Batch the send decision.** Offer one clear choice for the set: "send all N now", "stage all for your review", or a per-prospect pass. Honor the same no-send-without-confirmation rule for the whole batch.
- Consider staging everything first, then presenting a short digest (prospect → subject line) so the user can approve the batch in one look.

---

## Hard rules (the things that bite)

- **Confirm `sep.type == "outreach"` every session.** Another provider means another skill (`sep-cadence-enrollment`).
- **`sep_read`/`sep_write` take no `integration_id`** — don't invent the argument.
- **Prefer CRM-first for creating people** when a CRM is connected (see STEP 2).
- **Never prefix `api/v2/`** in `relative_url`.
- **The email step must be a Manual Email step**, and the **draft must already exist** before you PATCH it.
- **Pending ≠ broken.** It's almost always the delivery-schedule window, an inactive sequence, or a non-sendable mailbox. Diagnose those, don't retry blindly.
- **Sending requires the mailbox's *send* toggle**, not its *sync* toggle.
- **Never auto-send.** Stage, then ask. Only `state: "scheduled"` on an explicit yes.
- **Ground the copy in real Onfire data.** No invented signals, metrics, or claims.
- **The placeholder template is disposable.** Overwriting the draft replaces it; nothing extra goes out.

## Alternative: fully-automated Auto Email steps (no manual draft)

If the user wants the sequence to **send automatically** with no per-prospect human task, a Manual Email step is the wrong tool — there's no draft to edit at send time. Instead use an **Auto Email** step whose template maps to prospect custom variables (e.g. subject `{{custom1}}`, body `{{custom2}}`), and write the composed copy into the prospect's `custom1`/`custom2` fields **before** the step fires. Give each auto-email step its own custom-field pair so distinct steps render distinct copy. This trades editability for hands-off sending. Default to the Manual Email path unless the user explicitly wants fully-automated sends.
