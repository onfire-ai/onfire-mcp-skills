---
name: gong-create-and-push-to-flow
description: End-to-end workflow to create a prospect in the CRM (Salesforce), wait for it to sync into Gong, enroll it into a Gong Engage flow, and prefill the flow's manual email step with a personalized subject and body per prospect. Use whenever the user wants to "push someone to Gong", "add a prospect to a Gong flow", "create a lead and put them in a flow", "enroll X in the High Touch Outbound flow", "sequence this person in Gong", "write/prefill a custom email for the flow step", "restage prospects with custom emails", or any request that combines creating/finding a CRM record with getting them into a Gong flow and/or personalizing the email they'll receive. Handles the full chain: enrich contact → create Salesforce Lead/Contact → confirm the CRM→Gong sync → inspect the flow's steps for a manual email step → assign to the flow with per-prospect subject/body overrides. Reads and writes your tenant's CRM/Gong via the Onfire Integrations tools.
---

# Gong: Create and Push to Flow (with personalized email steps)

Take a person (a name, a LinkedIn URL, a prospecting result), make sure they exist in the CRM, wait for Gong to mirror them, enroll them into a **Gong Engage flow**, and — when the user wants personalized outreach — **prefill the flow's manual email step with a custom subject and body per prospect** so the rep opens a ready-to-send composer.

This skill is the orchestration layer over the Onfire Integrations tools. The Onfire engine owns the auth and API plumbing; this skill owns the sequence of steps, the Gong-specific path quirks, and the pre-flight checks that keep the flow assignment (and the content override) from silently failing.

## The shape of the workflow

```
Resolve tenant + integration ids (Salesforce crm.integration_id, Gong sep.integration_id)
   → Enrich the person (email + phone) if you don't have contact data
   → Create the prospect in Salesforce (Lead or Contact) — capture the CRM record Id
   → Wait for the CRM → Gong sync (Gong mirrors Salesforce; not instant)
   → Confirm the person is in Gong (data-privacy lookup by email)
   → Pick the target flow (GET /v2/flows)
   → Inspect the flow's steps (POST /v2/flows/steps) — find the manual email step; ALERT if none
   → Compose the personalized email per prospect; get user approval
   → Assign the prospect to the flow with per-prospect content overrides (POST /v2/flows/prospects/assign)
   → Verify: re-list assignments; have the user open the email to-do in Engage
```

**Key mental model for personalization:** email content overrides are applied **at assignment time, per flow instance, one prospect per assign call**. There is no API to edit the email of an instance that already exists — to change it you *restage*: unassign the instance, then re-assign with the new overrides (see RESTAGING below).

## Tools this skill orchestrates

| Purpose | Tool |
|---|---|
| Get tenant config + integration ids | `get_tenant_settings()` |
| Enrich email + phone | `contact_data_enrichment` (see the contact-data-enrichment skill) |
| Resolve a person → LinkedIn + title/company | `match_person` |
| **Read** your tenant's CRM / Gong | `onfire_integration_read(integration_id, relative_url, params)` |
| **Write** to your tenant's CRM / Gong (create record, assign flow) | `onfire_integration_write(integration_id, http_method, relative_url, json_body, params)` |

---

## STEP 0 — Pre-flight (read before promising anything)

1. **Resolve integration ids fresh, every session.** Call `get_tenant_settings()` and read `crm.integration_id` (Salesforce) and `sep.integration_id` (Gong). **Ids rotate** (e.g. after an integration reconnect) — never hard-code or reuse them across sessions; a write against a stale id is rejected.

2. **The CRM → Gong sync is not instant.** Gong does not accept a brand-new person directly — it builds its prospect list by mirroring the connected CRM (Salesforce). So the order is always **create in Salesforce first, then wait for sync, then assign the flow**. There is no API to force or read the sync cadence from tenant settings; it typically runs several times a day / at least daily. Don't promise a time — poll Gong for the person (Step 3) and only assign once they appear. Offer to schedule a re-check if they haven't synced yet.

---

## GONG PATH RULES — the #1 source of wasted calls

Unlike Outreach/Salesloft, **the engine does NOT auto-apply Gong's `/v2/` prefix.** Gong's API root is `https://api.gong.io/` with nothing appended.

- ✅ `relative_url = "v2/flows"` → hits `https://api.gong.io/v2/flows`
- ❌ `relative_url = "flows"` → hits `https://api.gong.io/flows` → **404 Not Found**

Always include `v2/` in the Gong `relative_url`.

---

## STEP 1 — Enrich + create the CRM record (Salesforce)

If you don't already have the person's email/phone, enrich first (`contact_data_enrichment`; ≤10 contacts = single call, no consent gate). You need at least a name and company; email/phone are nice-to-have but Gong keys off the **CRM record Id**, not the email.

Create a Salesforce **Lead** (required fields: `LastName`, `Company`):

```
onfire_integration_write(
  integration_id = <crm.integration_id>,
  http_method    = "POST",
  relative_url   = "sobjects/Lead",          # Salesforce root services/data/vXX.X/ is auto-applied — no v2/ here
  json_body = {
    "FirstName": "John",
    "LastName":  "Doe",
    "Company":   "Acme Corporation",
    "Title":     "Director of Vulnerability Management",
    "Email":     "john.doe@acme.com",
    "Phone":     "+15551234567"
  }
)
```

On success you get `{"id": "00QQH00000LqzbV2AR", "success": true}`. **Capture that `id`** — it's the `crmProspectId` Gong needs.

> Note the asymmetry: **Salesforce** paths are bare (`sobjects/Lead`, the engine adds `services/data/vXX.X/`), but **Gong** paths must carry `v2/`. Two different integrations, two different root behaviors.

---

## STEP 2 — Wait for the sync

Gong mirrors the Salesforce record on its own schedule. Don't assume it's there. Either:

- Ask the user to confirm they see the person in Gong, **or**
- Poll (Step 3) yourself, and if not present, offer to re-check later (a scheduled task works well: re-run Step 3, then Step 4 once found).

---

## STEP 3 — Confirm the person is in Gong

Use Gong's data-privacy lookup (a GET, keyed by email) to verify the mirror exists and grab the CRM linkage:

```
onfire_integration_read(
  integration_id = <sep.integration_id>,
  relative_url   = "v2/data-privacy/data-for-email-address",
  params         = {"emailAddress": "john.doe@acme.com"}
)
```

A synced person returns a `customerData[].objects[]` entry like:

```json
{ "objectType": "Lead", "externalId": "00QQH00000LqzbV2AR",
  "mirrorId": "{\"integrationId\":\"...\",\"crmObjectType\":\"LEAD\",\"crmId\":\"00QQH00000LqzbV2AR\"}" }
```

`externalId` / `crmId` == the Salesforce Id from Step 1. If `customerData` is empty, they haven't synced yet — do not attempt the assign.

(`emails`, `calls`, `meetings` will be empty for a brand-new lead — that's expected, not a problem.)

---

## STEP 4 — Pick the flow

List flows the owner can use. **The engine accepts `flowOwnerEmail`** as the query param (Gong's docs also call it `flowEmailOwner`; `flowOwnerEmail` is what worked in practice). Omitting it returns `400 flowOwnerEmail parameter is missing`.

```
onfire_integration_read(
  integration_id = <sep.integration_id>,
  relative_url   = "v2/flows",
  params         = {"flowOwnerEmail": "<owner@company.com>"}
)
```

Returns `flows[]` with `id`, `name`, `visibility`. Show the user the candidates and let them pick unless they already named one. Capture the flow `id` **as a string** (see the precision warning below).

---

## STEP 5 — Inspect the flow's steps and find the manual email step

**Do this BEFORE assigning whenever the user wants a personalized/custom email.** The content override targets a step **number**, so you must know which step is the email step — and whether one exists at all.

Endpoint: **`POST /v2/flows/steps`** (body: `flowIds`, up to 20 flow ids, as strings). Note: the Onfire read tool rejects Gong POSTs as "not read-shaped", so this read goes through `onfire_integration_write` (it's still a read — Gong just models it as POST):

```
onfire_integration_write(
  integration_id = <sep.integration_id>,
  http_method    = "POST",
  relative_url   = "v2/flows/steps",
  json_body = {"flowIds": ["1328474376461590521"]}
)
```

Real response shape (captured live):

```json
{ "flows": [{
    "id": "1328474376461590521", "name": "My Test Flow",
    "folderId": "439380271411523934", "visibility": "Company",
    "exclusive": true, "description": null,
    "steps": [{
      "id": "1186724529325049978",
      "stepOrder": 1,
      "action": "SEND_EMAIL",
      "subject": "Test",
      "body": "<div></div>",
      "isReply": false }] }] }
```

How to read it:

- **`stepOrder` is 1-based and maps directly to the `number` you'll send in the assign override.**
- A **manual email step** has `action: "SEND_EMAIL"`. That's the step whose `subject`/`body` you can override per prospect.
- The template `subject`/`body` on the step are just the defaults the composer opens with — a **blank body (`"<div></div>"`) is perfectly fine**; the override replaces it anyway.

### ⚠️ If the flow has NO manual email step — STOP and alert the user

If no step in `steps[]` has `action: "SEND_EMAIL"`, there is nothing to write the personalized email into. **Do not assign and pretend it worked.** Tell the user:

> "The flow *<name>* has no manual email step, so I can't prefill a custom email. Please add a 'Send email' step to the flow in Gong (Engage → Flows → edit the flow). The step's template can be completely blank — my override supplies the subject and body."

Then wait; re-run this step check after they've added it.

---

## STEP 6 — Compose the personalized emails and get approval

Ground each email in what you know: the prospect's title/company (from the CRM record or Onfire data), the user's stated angle/hook per person, and conversation context. One email per prospect — this is the whole point of the per-prospect assign call.

Show all drafts (subject + body) to the user and get an explicit go-ahead **before** any assign/unassign writes.

---

## STEP 7 — Assign the prospect to the flow (with content overrides)

Endpoint: **`POST /v2/flows/prospects/assign`**. This is the correct path — earlier-generation guesses like `/v2/flows/{flowId}/prospects` return `404 Not Found`.

All fields go in the **JSON body**, not the query string (putting them in `params` returns `400` with `flowId should be a valid Long` / `flowInstanceOwnerEmail: null is not a valid email address` / `crmProspectsIds is empty`).

**Plain assign (no custom email):** you can batch up to 100 prospects in one call:

```
onfire_integration_write(
  integration_id = <sep.integration_id>,
  http_method    = "POST",
  relative_url   = "v2/flows/prospects/assign",
  json_body = {
    "flowId": "6498280454937525788",              # STRING — see below
    "flowInstanceOwnerEmail": "owner@yourcompany.com",
    "crmProspectsIds": ["00QQH00000LqzbV2AR"]      # Salesforce record Id(s), up to 100
  }
)
```

**Personalized assign (custom email per prospect): ONE prospect per call**, because the `overrides` block applies to every prospect in the call. The exact, verified schema (from the live Gong API spec — field names matter, see the warning below):

```
onfire_integration_write(
  integration_id = <sep.integration_id>,
  http_method    = "POST",
  relative_url   = "v2/flows/prospects/assign",
  json_body = {
    "flowId": "1328474376461590521",               # STRING
    "flowInstanceOwnerEmail": "owner@yourcompany.com",
    "crmProspectsIds": ["00QQH00000Lm4Wr2AJ"],     # exactly one when personalizing
    "overrides": {
      "steps": [{
        "number": 1,                                # = stepOrder of the SEND_EMAIL step from STEP 5
        "subject": "OTel-native, index-free observability — no sampling",
        "body": "<div>Hi John,<br><br>…full HTML body…<br><br>Best,<br>Alex</div>"
      }]
    }
  }
)
```

The full `overrides` object (all optional, Beta Phase):

```json
"overrides": {
  "steps": [ { "number": <int, 1-based>, "subject": <string>, "body": <string, HTML> } ],
  "flowInstanceVariables": [ /* flow variable key/value updates, applied to the entire flow */ ],
  "coolOffOverride": <bool>   // assign even if the prospect is in cool-off
},
"flowInstanceDescription": <string>   // sibling of overrides, not inside it
```

### ⚠️ WRONG FIELD NAMES ARE SILENTLY IGNORED — this is the trap

Gong returns **HTTP 200 and assigns the prospect** even if your override block uses wrong field names — it just drops the unknown fields, and the composer opens with the flow's default template (empty/`Test`). There is **no error to catch**. Names that were tried and silently ignored: `flowInstanceContent`, `stepsContentOverride`, `stepNumber`, `bodyHtml`. The only accepted names are exactly: **`overrides` → `steps` → `number` / `subject` / `body`**. If the user reports the composer is empty after your assign, this is why — restage with the correct schema.

### ⚠️ Pass `flowId` as a STRING
Gong flow ids are 19-digit Longs (e.g. `6498280454937525788`) that exceed JavaScript's safe-integer range. If you pass it as a JSON **number** it gets rounded (→ `...526000`) and Gong returns `404 "Flow not found"`. Always quote it as a string so the exact value is preserved. Same care applies to any Gong id you round-trip.

Success looks like:

```json
{ "prospectsAssigned": [{
    "flowName": "High Touch Outbound Flow",
    "crmProspectId": "00QQH00000LqzbV2AR",
    "flowInstanceId": "4769935861624480845",
    "flowInstanceStatus": "Running" }],
  "prospectsNotAssigned": [] }
```

Report the `flowName`, `flowInstanceStatus`, and the linked CRM Id back to the user. Anything in `prospectsNotAssigned` needs follow-up (usually the person isn't synced into Gong yet — go back to Step 3).

---

## STEP 8 — Verify

1. **API-side:** re-run `POST v2/flows/prospects` (body: `{"crmProspectsIds": [...]}`; like `v2/flows/steps`, this POST-read must go through `onfire_integration_write`) and confirm each prospect has exactly one instance on the target flow with `flowInstanceStatus: "Running"`. Note: there is **no API to read back the override content** of an instance — a 200 on assign plus correct field names is your only API-side guarantee.
2. **UI-side (the real proof):** have the user open the prospect's **"Send email" to-do** — Engage → To-dos, or Engage → People → the person → To-dos tab → click the "Send email / Step 1" row. The composer must show the custom subject and body. **If they had a composer window open from before the restage, it shows stale cached content — close and re-open the to-do.**

---

## RESTAGING — replace the email of prospects already in a flow

Overrides only apply at assignment. To change the email of someone already in the flow:

```
1. Find their current flow instance ids:
   POST v2/flows/prospects   body: {"crmProspectsIds": ["00Q…", …]}
   → each entry has flowId, flowInstanceId, flowInstanceStatus
2. Unassign (batch OK, up to 100):
   POST v2/flows/prospects/unassign-flows-by-instance-id
   body: {"flowInstanceIds": ["4860310507072265577", …]}    # strings!
   → response lists unassignedFlowInstanceIds
3. Re-assign one prospect at a time with the overrides block (STEP 7).
   → each gets a NEW flowInstanceId, restarted at step 1
```

Warn the user before unassigning: restaging **kills the current instance's progress** — the new instance starts from step 1. (That's usually the point, but say it.) If the user only has flow instance ids and names (not CRM ids), resolve the CRM ids first: query Salesforce for the people by name/email, then match via `POST v2/flows/prospects`.

---

## Related Gong Engage endpoints (all under `v2/`, ids as strings)

| Purpose | Method + path |
|---|---|
| List flows | `GET v2/flows?flowOwnerEmail=…` |
| List flow folders | `GET v2/flows/folders?flowOwnerEmail=…` |
| Get flow details + steps (find the email step) | `POST v2/flows/steps` — body `{"flowIds": [...]}`, ≤20 |
| List flows already assigned to prospects | `POST v2/flows/prospects` — body `{"crmProspectsIds": [...]}` |
| Assign prospects to a flow (+ content overrides) | `POST v2/flows/prospects/assign` |
| Assign ignoring cool-off | `POST v2/flows/prospects/assign/cool-off-override` |
| Unassign by CRM prospect id | `POST v2/flows/prospects/unassign-flows-by-crm-id` |
| Unassign by flow instance id | `POST v2/flows/prospects/unassign-flows-by-instance-id` |

> **Tool routing quirk:** Gong's read-shaped POSTs (`v2/flows/steps`, `v2/flows/prospects`) are rejected by `onfire_integration_read` ("not a read-shaped request"). Send them through `onfire_integration_write` — they're still reads on Gong's side.

Bearer scopes (for reference): `api:flows:read` for the reads, `api:flows:write` for assign/unassign. The Onfire engine handles auth; you don't pass tokens.

## Common failure → cause

- `404 "Not Found"` on a Gong call → you dropped the `v2/` prefix, or used a wrong sub-resource path (e.g. `/v2/flows/{id}/prospects`). Use `/v2/flows/prospects/assign`.
- `404 "Flow not found"` on assign → `flowId` was sent as a number and got rounded. Send it as a string.
- `400 flowId should be a valid Long` / `crmProspectsIds is empty` → you put the fields in the query string; move them into `json_body`.
- `400 flowOwnerEmail parameter is missing` → add `flowOwnerEmail` to `params` on the flows list call.
- `prospectsNotAssigned` non-empty → the CRM record hasn't synced into Gong yet; re-run the Step 3 lookup and retry once it appears.
- Write rejected / id not found → you used a stale integration id. Re-fetch ids from `get_tenant_settings()`.
- Assign returns 200 but the composer opens with the flow's default/empty template → your override used wrong field names and Gong silently dropped them. Use exactly `overrides.steps[].number/subject/body`, then restage.
- `onfire_integration_read` rejects `POST v2/flows/prospects` or `POST v2/flows/steps` → expected; route those read-shaped POSTs through `onfire_integration_write`.
- User says the email looks stale/wrong right after a restage → they're looking at a composer window opened before the restage; have them close and re-open the to-do.

## What this skill does NOT do

- It doesn't **send** emails — the override prefills the composer of the manual email step; the rep (or the flow's automation) still owns the send.
- It doesn't edit the email of an existing flow instance in place — no such API. Changing content means restaging (unassign + re-assign with overrides).
- It doesn't score or rank the prospect — use `ai_prospecting` first if you need to decide *who* to push.
- It doesn't bypass the sync. If the person isn't in Gong yet, the answer is "wait / re-check", not a direct Gong contact create.
