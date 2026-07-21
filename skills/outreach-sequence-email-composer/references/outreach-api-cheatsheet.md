# Outreach API cheat-sheet (via Onfire Integrations)

All calls go through the Onfire Integrations tools, which resolve credentials and route to Outreach. **The engine already applies the `api/v2/` root** — `relative_url` must be the bare path (`prospects`, not `api/v2/prospects`).

- **Reads (any tenant):** `onfire_integration_read(integration_id, relative_url, params?, http_method="GET")`
- **Writes:** `onfire_integration_write(integration_id, http_method, relative_url, json_body)`
- Bodies are **JSON:API**: `{"data": {"type": "...", "id": ..., "attributes": {...}, "relationships": {...}}}`.
- Get `integration_id` from `get_tenant_settings(...).sep.integration_id`. **Re-fetch each session — ids rotate.**

## Get the integration id + ICP

```
get_tenant_settings()
  → sep.integration_id, sep.type ("outreach")
  → account_research.{golden_persona, competitors, technologies,
      organization, buying_committee_queries, display_names_mapping}  # ICP
```

## Mailboxes — pick a sendable one

```
GET mailboxes?page[limit]=25
```
Choose where `attributes.sendState == "ENABLED"` and `attributes.sendDisabled == false`. `syncState`/syncing is irrelevant to sending. Note the `email` — that's the visible `from`.

## Sequences

List:
```
GET sequences?sort=-updatedAt&page[limit]=25
```
Key attributes: `name`, `enabled` (must be true to activate prospects), `sequenceType` ("interval" | "date"), `sequenceStepCount`. Relationships include `sequenceSteps`, `schedule`, `ruleset`.

Create (day-interval so prospects auto-activate on add):
```
POST sequences
{"data": {"type": "sequence",
  "attributes": {"name": "<name>", "sequenceType": "interval",
                 "shareType": "shared"},
  "relationships": {
    "schedule": {"data": {"type": "schedule", "id": <scheduleId>}},
    "ruleset":  {"data": {"type": "ruleset",  "id": <rulesetId>}}}}}
```
Then **Activate** it (UI toggle, or set `attributes.enabled` true if permitted). A new sequence is inactive until activated.

## Sequence steps

Read steps of a sequence:
```
GET sequenceSteps?filter[sequence][id]=<seqId>&sort=order
```
`stepType` values seen: `manual_email`, `auto_email`, `task` (generic), `call`, `linkedin`. The composer targets `manual_email`.

Create a Manual Email step (fires immediately):
```
POST sequenceSteps
{"data": {"type": "sequenceStep",
  "attributes": {"stepType": "manual_email", "order": 1, "interval": 0},
  "relationships": {"sequence": {"data": {"type":"sequence","id":<seqId>}}}}}
```

## Template for the step (placeholder shell)

A manual-email step needs a template. Create one with throwaway content, then link it.
```
POST templates
{"data": {"type": "template",
  "attributes": {"subject": "draft",
                 "bodyHtml": "<div>placeholder</div>"}}}

POST sequenceTemplates
{"data": {"type": "sequenceTemplate",
  "relationships": {
    "sequenceStep": {"data": {"type":"sequenceStep","id":<stepId>}},
    "template":     {"data": {"type":"template","id":<templateId>}}}}}
```
Reading templates needs `templates.read`/`templates.all` and `sequenceTemplates.read`/`.all`. A passthrough template can instead map to custom vars (subject `{{custom1}}`, body `{{custom2}}`) — that's the Auto Email route, not the manual one.

## Prospect — dedupe, then create

Dedupe by email:
```
GET prospects?filter[emails]=<email>
```
Create (verify attribute shape against the live schema; attach an email address):
```
POST prospects
{"data": {"type": "prospect",
  "attributes": {"firstName": "<f>", "lastName": "<l>",
                 "company": "<co>", "title": "<title>",
                 "emails": ["<email>"]}}}
```
If the email isn't attached on create, add it via `POST emailAddresses` related to the prospect. An email step can't send without an email address. Useful prospect fields: `custom1..custom150` (for the Auto Email variable route).

## Enroll — sequenceState

```
POST sequenceStates
{"data": {"type": "sequenceState",
  "relationships": {
    "prospect": {"data": {"type":"prospect","id":<prospectId>}},
    "sequence": {"data": {"type":"sequence","id":<seqId>}},
    "mailbox":  {"data": {"type":"mailbox","id":<mailboxId>}}}}}
```
Response `state` starts `pending`. Poll:
```
GET sequenceStates/<id>
```
Activated when `state == "active"` and `activeAt` is set; `activeStepMailings` / `activeStepTasks` then populate. Stuck `pending` with null `errorReason` = schedule window / inactive sequence / non-sendable mailbox (not an error).

## Find + stage the draft

```
GET mailings?filter[prospect][id]=<prospectId>
```
The manual-email draft has `mailingType == "sequence"`, `state == "drafted"`, and links to the `sequenceStep`, `sequenceState`, and `task`. Stage the composed email (overwrites the placeholder):
```
PATCH mailings/<mailingId>
{"data": {"type": "mailing", "id": <mailingId>,
  "attributes": {
    "subject": "<composed subject>",
    "bodyHtml": "<composed html>",
    "bodyText": "<composed text>"}}}
```
Keep the unsubscribe `<div class="outreach-signature outreach-unsubscribe">…%unsubscribe_url%…</div>` in `bodyHtml`.

## Send (only on explicit user confirmation)

```
PATCH mailings/<mailingId>
{"data": {"type": "mailing", "id": <mailingId>,
  "attributes": {"state": "scheduled"}}}
```
A `scheduledAt` already in the past sends immediately. Mailing state then progresses `scheduled → delivering → delivered`. Confirm with `GET mailings/<id>`. **Do not send without an explicit yes.**

## Tasks (the manual-email task)

```
GET tasks?filter[prospect][id]=<prospectId>
```
The manual-email task links to the same `mailing`. It appears in the user's Tasks tab when self-sending.

## Common 403s

`unauthorizedOauthScope` names the missing scope. The flow needs: `prospects.read/write`, `sequences.read/write`, `sequenceSteps.read/write`, `sequenceStates.read/write`, `sequenceTemplates.all`, `templates.all`, `mailboxes.read`, `mailings.read/write`, `tasks.read/write`, `emailAddresses.read/write`. `schedules.read` is often missing — diagnose schedule issues from the UI. Adding scopes requires reconnecting the integration, which rotates the `integration_id`.
