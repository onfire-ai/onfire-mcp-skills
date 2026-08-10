---
name: sep-cadence-enrollment
description: The gateway for ALL work against a connected sales engagement platform (SEP) — Outreach, Salesloft, Gong Engage, Reply.io. Use whenever the user names one of those platforms or uses their vocabulary — "add them to a cadence", "sequence these prospects", "push this person to Outreach", "enroll in Salesloft", "put them in my flow", "sync this lead to the SEP", "what cadences do we have", "is she already in a sequence", "start outreach on these accounts", "push my prospecting results into a cadence". Owns provider discovery (never guess Outreach vs Salesloft), the CRM-first law (write to the CRM, validate the write landed, then create the SEP copy — never the reverse), the engine-enforced CRM-proof gate and its CRM_UPLOAD_REQUIRED refusal, the exact-email rule that keeps the CRM→SEP hydration sync from creating duplicates, and the per-provider enrollment recipe. Routes to sibling skills for email composition (outreach-sequence-email-composer) and Gong flow personalization (gong-create-and-push-to-flow).
---

# SEP Cadence Enrollment

Everything that touches the tenant's connected sales engagement platform starts here. This skill owns the three things that break every SEP workflow in production:

1. **Which provider is connected** — Outreach, Salesloft, Gong and Reply.io use different resource names, different body shapes, and different API roots. Guessing is the #1 cause of wasted calls.
2. **The order of operations** — the CRM write comes first and must be *validated* before you create anyone in the SEP. The engine enforces this; see [THE LAW](#the-law-crm-first-validated-then-the-sep-copy).
3. **The exact-email rule** — the SEP copy you create must carry the *same email* as the CRM record, or the tenant's hydration sync will later create a duplicate alongside it. See [Why the email must match exactly](#why-the-email-must-match-exactly).

## Route first

| The user wants | Go to |
|---|---|
| Enroll someone in a cadence / sequence / flow | **this skill**, all the way through |
| Enroll **and** have the agent write the per-prospect email (Outreach manual-email steps) | this skill for STEPS 1–5, then `outreach-sequence-email-composer` |
| Enroll into a **Gong Engage flow** with per-prospect subject/body overrides | this skill for STEPS 1–4, then `gong-create-and-push-to-flow` |
| Decide **who** to enroll | `ai-prospecting` / `onfire-prospecting` first, then come back |
| Emails/phones before pushing to the CRM | `contact-data-enrichment` first |
| Just read the SEP (list cadences, check enrollment, look up a person) | STEP 1 + the [read recipes](#read-recipes-by-provider); skip the write path |

## Tools

| Purpose | Tool |
|---|---|
| Discover the connected provider + CRM | `get_tenant_settings()` → `settings.sep.type`, `settings.crm.enabled` |
| Create/update people in the CRM | `crm_write(entity_type, records)` → `crm_write_status(job_id)` → `crm_write_results(job_id)` |
| Read the SEP (people, cadences, users, enrollment state) | `sep_read(relative_url, http_method="GET", params=…)` |
| Write to the SEP (create the copy, then enroll) | `sep_write(http_method, relative_url, json_body=…)` |
| Resolve identity before pushing | `match_person`, `match_company` |
| Emails + phones | `contact_data_enrichment` |

Neither `sep_read` nor `sep_write` takes an `integration_id` — the engine resolves the tenant's SEP internally. `crm_write` likewise resolves the CRM internally. Do not invent an id argument.

`sep_write` is **deny-by-default**: a tenant without the grant gets a refusal, not a silent no-op. If it's refused, say so plainly and stop — do not fall back to some other write path.

---

## THE LAW: CRM first, validated, then the SEP copy

**When a CRM is connected, a person reaches the SEP only after a `crm_write` for that person has been confirmed successful.** You do not wait for the tenant's CRM→SEP sync to mirror them. You create the SEP copy yourself, immediately after validation.

This is not a convention you have to remember — **the engine enforces it**. `sep_write` refuses a prospect-create unless a *CRM proof row* exists for that person.

### How the proof gate works

`crm_write_results(job_id)` mints one proof row in `mcp_control.sep_prospect_crm_proof` for every prospect record that came back `succeeded` on a `completed` job. A `sep_write` prospect-create then atomically **consumes** one matching row. No matching row → the call is refused with:

```json
{"status": "error", "error_code": "CRM_UPLOAD_REQUIRED", "error": "..."}
```

The proof is matched on **`linkedin_url`** (Outreach, Salesloft, Reply.io) or **`crm_id`** (Gong). **Email is deliberately not stored** in the proof table — it sits on the hard-PII boundary of the CRM export-results payload and never reaches the MCP. That has a consequence you must internalize:

> **Two different fields do two different jobs.** `linkedin_url` is what *unlocks the gate*. `email` is what *prevents the duplicate later*. A SEP create body needs **both**. A body carrying only an email is refused (`CRM_UPLOAD_REQUIRED`) — the gate fails closed when it finds no matchable identifier.

### Why the order still matters

The gate exists because writing to the SEP first breaks three things:

- **You'd bypass the tenant's field mapping.** `crm_write` respects the tenant's configured CRM field mapping, including the `Owner = Export Person` mapping that keeps the Onfire integration user from becoming the record owner. A SEP-first create honors none of it, and the CRM record that follows is owned by the wrong user.
- **You'd have no CRM lineage for routing.** Ownership is assigned CRM-side (LeanData or equivalent) after the record is created. A SEP person with no CRM counterpart has nothing for that routing to land on.
- **You'd create the duplicate the hydration sync is about to create.** The tenant's CRM→SEP sync still fires on its own schedule. It dedupes on email. Match the email and it hydrates the person you created; get it wrong and you get two.

### The flow

```
Resolve provider + CRM               (STEP 1 — get_tenant_settings)
   → Push the person into the CRM     (STEP 2 — crm_write)
   → Validate the push landed         (STEP 3 — crm_write_status → crm_write_results)   ← mints the proof
   → Create the SEP copy              (STEP 4 — sep_write, if not already there)        ← consumes the proof
   → Pick the cadence                 (STEP 5 — sep_read)
   → Enroll                           (STEP 6 — sep_write)
   → Verify + report                  (STEP 7)
```

**No waiting anywhere in that chain.** STEP 3 is a poll to a terminal job status, not a poll for an external sync.

If the person is **already in the SEP** (the user points at an existing prospect, or STEP 4's lookup finds them), skip the create and go straight to STEP 5. The law governs *creation*, not enrollment of people who already exist.

### The one exception: no CRM connected

If `settings.crm.enabled` is false there is no field mapping to bypass, no routing to fight, and no hydration sync to collide with. A direct SEP create is then the only path in, and it is the correct one — **and the gate does not fire at all**, so no proof is needed. Check `crm.enabled` before deciding; don't infer it from whether the person happens to exist.

| | People enter via | Proof required | Enrollment |
|---|---|---|---|
| `crm.enabled == true` | `crm_write` → validate → SEP create (STEPS 2–4) | **yes** | STEPS 5–7 |
| `crm.enabled == false` | direct SEP create — Outreach `POST prospects`, Salesloft `POST people`, Reply.io `POST contacts` | no | STEPS 5–7 |

### Gong is different in two ways

1. **Gong has no SEP copy to create.** It builds its prospect list entirely from the connected CRM and accepts no direct creates. STEP 4 is a no-op on Gong. No CRM means no Gong enrollment at all — say that rather than attempting a create that cannot succeed.
2. **On Gong the proof is consumed at enrollment.** The gated path is `v2/flows/prospects/assign` — the *assign* call — matched on the `crm_id` values in `crmProspectsIds`. So on Gong, STEP 6 is the call that needs the proof, and STEP 3's validation is what makes it possible.

Gong also still depends on its own CRM sync for the record to be *assignable*: the proof gate lets your call through, but Gong itself returns the record in `prospectsNotAssigned` if it hasn't ingested that CRM record yet. That is a Gong-side wait, not ours — report it and offer a re-check.

---

## STEP 1 — Provider discovery (every conversation, before any URL)

```
get_tenant_settings()
```

Read `settings.sep.type` and `settings.crm.enabled`. **Never** infer the provider from the user's wording — "cadence" is ordinary English, not a Salesloft signal, and plenty of Outreach users say it.

| `sep.type` | Concept name | API root the engine already applies | `relative_url` you write |
|---|---|---|---|
| `outreach` | sequence | `api/v2/` | `prospects`, `sequences`, `sequenceStates`, `users`, `mailboxes` |
| `salesloft` | cadence | `v2/` | `people`, `cadences`, `cadence_memberships`, `users` |
| `gong` | flow | *(none — root is the bare host)* | `v2/flows`, `v2/flows/prospects/assign` |
| `replyio` | sequence | `v3/` | `contacts`, `sequences` |

**Gong is the exception: it keeps its `v2/` prefix; everyone else drops theirs.** `"flows"` on Gong 404s; `"v2/people"` on Salesloft 404s.

If `settings.sep` is absent, the caller has no Onfire Integrations tool granted, or no SEP is connected. Say that and stop.

If `settings.crm.enabled` is false, take [the no-CRM exception](#the-one-exception-no-crm-connected): create directly in the SEP (except on Gong, which can't), then run STEPS 5–7.

---

## STEP 2 — Push the person into the CRM

```
crm_write(
  entity_type = "prospect",
  records = [{
    "name": "John Doe",
    "email": "john.doe@acme.com",
    "job_title": "Director of Vulnerability Management",
    "company_name": "Acme Corporation",
    "company_website": "acme.com",
    "linkedin_url": "https://www.linkedin.com/in/johndoe",
    "company_linkedin_url": "https://www.linkedin.com/company/acme",
    "phones": ["+15551234567"]
  }]
)
```

Notes that matter here:

- **`linkedin_url` is now load-bearing, not optional.** It is the proof-match key. A prospect that lands in the CRM without one mints **no proof row**, and you will not be able to create them in the SEP at all. If you're missing LinkedIn URLs, resolve them with `match_person` *before* this call.
- **`email` is the join key for the hydration sync.** Record it exactly as you send it — you need the identical string in STEP 4. If you're missing emails, run `contact_data_enrichment` first (or pass `contact_data_enrich=True`).
- **Keep prospects and accounts in separate jobs.** Proof minting checks the entity type of the job's **first record** only, so a job that leads with an account record mints nothing for the prospects behind it. One `crm_write` per entity type.
- **Do not set the owner yourself.** The tenant's field mapping already maps owner to the exporting person, and the CRM's routing has the final word. Trying to force it fights both.
- Confirm the record list with the user before calling — these are live CRM writes.

---

## STEP 3 — Validate the push landed

This step replaces the old wait-for-sync. It is a poll on **our own job**, which is fast and deterministic.

```
crm_write_status(job_id)     → poll until "completed" or "failed"
crm_write_results(job_id)    → per-record outcome + the queryable dataset
```

`crm_write_status` takes roughly 3s for one record, 5–7s for a handful, longer for large batches.

**You must call `crm_write_results`.** This is the single most important behavioral rule in this skill. Polling `crm_write_status` to `completed` is *not* enough — the proof rows are minted inside `crm_write_results`. Skip it and every downstream `sep_write` prospect-create fails with `CRM_UPLOAD_REQUIRED`, with nothing in the CRM to explain why.

Validation means, per record, all of:

| Condition | Where you read it |
|---|---|
| Job reached `completed` (not `failed`) | `crm_write_status` / the `status` in results |
| The record's `status` is `succeeded` | the results dataset, per row |
| The record carries a `linkedin_url` (or `crm_id` for Gong) | the results dataset, per row |

The results dataset has one row per submitted record with `source_index`, `entity_type`, `status` (`succeeded`/`failed`/`skipped`/`unknown`), `name`, `linkedin_url`, `crm_id`, `operation` (`create`/`update`), and a resolved `error` object on failures.

**Partition on these columns and carry only the `succeeded` rows forward.** Rows that came back `failed` or `skipped` have no proof and cannot enter the SEP — report them with their error rather than retrying the SEP write against them.

Capture `crm_id` per row here as well: it's the Gong enrollment key in STEP 6, and it's what you cite when the user asks what landed in Salesforce.

> Proof minting is best-effort by design — if it fails internally, `crm_write_results` still returns your dataset successfully and logs a warning. So a clean CRM result followed by `CRM_UPLOAD_REQUIRED` is a real (if rare) combination. See [Common failure → cause](#common-failure--cause).

---

## STEP 4 — Create the SEP copy

### First: check whether they're already there

The user may be pointing at someone who already exists in the SEP, and the tenant's hydration sync may have brought them in on a previous cycle. Look them up by email before creating anything:

```
outreach   → sep_read("prospects", params={"filter[emails]": "john.doe@acme.com"})
salesloft  → sep_read("people",    params={"email_addresses": "john.doe@acme.com"})
gong       → sep_read("v2/data-privacy/data-for-email-address",
                      params={"emailAddress": "john.doe@acme.com"})
replyio    → sep_read("contacts",  params={"email": "john.doe@acme.com"})
```

**Found → skip the create entirely** and go to STEP 5 with the id you just read. Creating on top of an existing person is exactly the duplicate this skill exists to prevent. (The unconsumed proof row simply stays unconsumed; it is harmless and carries no expiry.)

Capture the id from the response: Outreach `data[0].id` (prospect id), Salesloft `data[0].id` (person id), Reply.io the contact id, Gong `customerData[].objects[].externalId` (the CRM record id).

**Not found → create the copy.** These bodies carry both required fields: the **email** that must match the CRM record exactly, and the **`linkedin_url`** the proof gate matches on.

### Outreach

```
sep_write(
  http_method  = "POST",
  relative_url = "prospects",
  json_body = {"data": {"type": "prospect", "attributes": {
    "emails":     ["john.doe@acme.com"],
    "linkedinUrl": "https://www.linkedin.com/in/johndoe",
    "firstName":  "John",
    "lastName":   "Doe",
    "title":      "Director of Vulnerability Management",
    "company":    "Acme Corporation"
  }}}
)
```

The gate reads `data.attributes.linkedinUrl` (it also accepts `linkedin_url`).

### Salesloft

```
sep_write(
  http_method  = "POST",
  relative_url = "people",
  json_body = {
    "email_address": "john.doe@acme.com",
    "linkedin_url":  "https://www.linkedin.com/in/johndoe",
    "first_name":    "John",
    "last_name":     "Doe",
    "title":         "Director of Vulnerability Management",
    "company_name":  "Acme Corporation"
  }
)
```

The gate reads `linkedin_url` (it also accepts `linkedinUrl`).

### Reply.io

```
sep_write(
  http_method  = "POST",
  relative_url = "contacts",
  json_body = {
    "email":     "john.doe@acme.com",
    "linkedin":  "https://www.linkedin.com/in/johndoe",
    "firstName": "John",
    "lastName":  "Doe",
    "company":   "Acme Corporation"
  }
)
```

The gate reads `linkedin` (it also accepts `linkedin_url`).

### Gong

**No create.** Skip to STEP 5. Gong's prospect list comes from the CRM only, and its proof is consumed by the assign call in STEP 6.

### If the create is refused

`CRM_UPLOAD_REQUIRED` means the gate found no unconsumed proof row matching the identifiers in your body. Work the causes in this order:

1. **Did you call `crm_write_results`?** Most common cause by a wide margin.
2. **Is the `linkedin_url` in your SEP body byte-identical to the one in the CRM results row?** The match is exact — a trailing slash, `http` vs `https`, or a `www.` difference is a miss.
3. **Did that record come back `succeeded`?** `failed` and `skipped` rows mint nothing.
4. **Does your body carry a LinkedIn URL at all?** An email-only body always fails closed.
5. **Was the proof already consumed** by an earlier create for the same person? Then they're already in the SEP — go look (see above) rather than re-uploading.

Do **not** work around a refusal by dropping to a different write path or by re-sending without the identifier. Fix the cause or report it.

### Retry semantics after a failed create

If the create passes the gate but the SEP itself rejects it:

- **4xx** → the proof is **refunded automatically** (returned to unconsumed). Fix the body and retry the same `sep_write`. No new CRM upload needed.
- **5xx or transport error** → the proof stays **consumed**. A retry will hit `CRM_UPLOAD_REQUIRED`. Before re-uploading to the CRM, **read the SEP to check whether the create actually landed** — a 5xx often means it did. Only re-run `crm_write` + `crm_write_results` if it genuinely isn't there.

---

## STEP 5 — Pick the cadence

```
outreach   → sep_read("sequences", params={"sort": "-updatedAt"})
salesloft  → sep_read("cadences",  params={"per_page": "100"})
gong       → sep_read("v2/flows",  params={"flowOwnerEmail": "<rep@company.com>"})
replyio    → sep_read("sequences")
```

Show the candidates with their names and enabled/active state, and let the user pick unless they already named one. **Re-read the list at enrollment time rather than trusting a cadence id from earlier in the conversation** — cadences get renamed, archived, and disabled, and a stale id enrolls into nothing or into the wrong thing. If the user named a cadence by name, confirm the id you resolved it to before writing.

Gong flow ids are 19-digit values that exceed JavaScript's safe-integer range — **always carry them as strings**, or they round and 404.

---

## STEP 6 — Enroll

One enrollment write per person. These bodies are the ones the platform actually accepts.

**Attribution is set here, explicitly.** A person you created in STEP 4 is owned SEP-side by the integration's token holder, not by the CRM's routing — so the rep the cadence runs under is whatever you pass in `user_id` / the mailbox relationship / `flowInstanceOwnerEmail`. Resolve the intended rep and pass them. Never leave it to chance and never assume an inherited owner.

### Salesloft

```
sep_write(
  http_method  = "POST",
  relative_url = "cadence_memberships",
  json_body = {
    "person_id":  "<person id from STEP 4>",
    "cadence_id": "<cadence id from STEP 5>",
    "user_id":    "<Salesloft user id — see below>"
  }
)
```

`user_id` is the rep the cadence is attributed to. Resolve it from their email first:

```
sep_read("users", params={"search": "rep@company.com"})
```

Salesloft's `/users` endpoint **ignores an `email[]` filter and returns the whole workspace** — `search` is the only filter that narrows server-side, and it free-text matches name *and* email. So filter the results client-side for an exact case-insensitive email match before using the id. If no user matches, omit `user_id` entirely; Salesloft then attributes the enrollment to the integration's token holder. Say which rep it landed under either way.

### Outreach

```
sep_write(
  http_method  = "POST",
  relative_url = "sequenceStates",
  json_body = {"data": {"type": "sequenceState", "relationships": {
    "prospect": {"data": {"type": "prospect", "id": <prospect id, int>}},
    "sequence": {"data": {"type": "sequence", "id": <sequence id, int>}},
    "mailbox":  {"data": {"type": "mailbox",  "id": <mailbox id, int>}}
  }}}
)
```

Outreach ids here are **integers**, not strings, and the mailbox is **required**. Resolve it:

```
sep_read("users", params={"filter[email]": "rep@company.com"})   → user id
sep_read("mailboxes", params={"filter[user][id]": "<user id>"})  → pick the mailbox
```

Pick a mailbox with `sendState == "ENABLED"` and `sendDisabled == false`. Sending and syncing are independent toggles — the *send* toggle is the one that gates outbound; a disabled *sync* toggle only affects reply tracking.

A `201` returns the sequenceState with `state: "pending"` — that is **normal at creation**, not a failure. It becomes `active` once the sequence's delivery-schedule window opens. If it stays pending, the cause is almost always one of: the sequence is not activated, the delivery schedule's window is closed right now, or the mailbox can't send. Diagnose those three; don't retry the write.

### Gong Engage

Gong enrollment is an **assign against the CRM record id**, not a SEP-side person id — and it is the call the proof gate checks on Gong:

```
sep_write(
  http_method  = "POST",
  relative_url = "v2/flows/prospects/assign",
  json_body = {
    "flowId": "<flow id as a STRING>",
    "crmProspectsIds": ["<crm_id from crm_write_results>"],
    "flowInstanceOwnerEmail": "rep@company.com"
  }
)
```

The `crm_id` values must be the ones from your validated `crm_write_results` rows — those are what the proof was minted on. Up to 100 CRM ids per call when you're not personalizing; note that each id consumes its own proof row.

For **per-prospect subject/body overrides, hand off to `gong-create-and-push-to-flow`** — the override schema is exact, wrong field names are silently accepted and dropped, and that skill documents the whole trap.

### Reply.io

```
sep_write(
  http_method  = "POST",
  relative_url = "sequences/<sequence id>/contact-links/bulk",
  json_body = {"contactIds": [<contact id, int>]}
)
```

Reply.io rejects an already-enrolled contact with a generic error indistinguishable from a blocked sequence, so **check first**: `sep_read("contacts/<contact id>/sequences")` and skip the write if the target sequence is already there.

---

## STEP 7 — Verify and report

Confirm the enrollment landed, then report in business terms.

```
outreach   → sep_read("sequenceStates/<id>")                  → state, activeAt
salesloft  → sep_read("cadence_memberships", params={"person_id": "<id>"})
gong       → sep_write("POST", "v2/flows/prospects", json_body={"crmProspectsIds": ["<id>"]})
replyio    → sep_read("contacts/<contact id>/sequences")
```

(Gong models two of its reads as POSTs; `sep_read` rejects those as not read-shaped, so they route through `sep_write`. They're still reads, and they are not prospect-creates, so the proof gate doesn't touch them.)

Report per person: **created/matched in the CRM → created in <provider> (or already there) → enrolled in <cadence name> under <rep>**. Name anyone who didn't make it and why (CRM write failed, no LinkedIn URL so no proof, no email, already enrolled, Gong hasn't ingested the CRM record yet).

**Already-enrolled is a success, not a failure.** Salesloft returns 409/422 for it, Reply.io a generic error, Outreach a validation error. Report it as "already in that cadence" and move on.

---

## Why the email must match exactly

The tenant's CRM→SEP hydration sync **does not go away** because you created the SEP copy yourself. It still runs on the CRM's own schedule, and when it reaches the record you just pushed it will do one of two things:

- **The emails match** → it hydrates the person already in the SEP. Fields get enriched, CRM lineage attaches, ownership routing lands. One person. This is the outcome you want.
- **The emails differ** → it has no way to recognize your copy and creates a second person. Now the cadence is running on one record while the CRM lineage sits on the other.

So the email you send in STEP 4 must be **byte-identical** to the email you sent to `crm_write` in STEP 2 — same string, no case normalization, no alias substitution, no picking a different address off the same person because it looked tidier. Carry the exact string through; don't re-derive it.

Two related facts worth knowing:

- **The proof gate cannot help you here.** It never sees email (PII boundary), so a mismatched email passes the gate happily and produces a duplicate days later. This one is on you, not the engine.
- **Free-mail domains** (gmail / hotmail / yahoo / outlook / icloud) are commonly excluded from the tenant's hydration rule. Those people won't be hydrated at all — which is fine, your SEP copy stands on its own, but say so rather than implying CRM lineage they'll never get.

If you find a duplicate that already exists, don't paper over it with a third record. Report it, name both records, and let the user decide the merge.

---

## Read recipes by provider

For read-only asks ("what cadences do we have", "is she already in a sequence", "who's in this cadence"), skip STEPS 2–4 entirely — run STEP 1, then:

| Ask | Outreach | Salesloft |
|---|---|---|
| List cadences | `sequences` | `cadences` |
| Find a person | `prospects` + `filter[emails]` | `people` + `email_addresses` |
| Their enrollments | `sequenceStates` + `filter[prospect][id]` | `cadence_memberships` + `person_id` |
| Find a rep | `users` + `filter[email]` | `users` + `search` (then match client-side) |

`sep_read` is read-only by construction — write-shaped requests sent to it are redirected, not executed. It never touches the proof gate.

---

## Many people at once

- **One `crm_write` call** for the whole batch (up to 10,000 records / 25 MB) — not one per person. Prospects only; keep accounts in a separate job.
- **One `crm_write_results` call** for that job. It mints every proof row in the batch in one shot.
- **Partition on the results dataset** — `succeeded` + has `linkedin_url` goes forward; everything else gets reported with its error. Don't send failed rows into the SEP.
- **One existence-check pass** over the batch before creating, then create only the people who aren't there.
- **Creates and enrollments are one write per person** on Salesloft, Outreach and Reply.io. Gong batches up to 100 per assign when there are no per-prospect overrides — and consumes one proof row per id.
- **Cadences cap adds per user per 24 hours** (Outreach defaults to 50). Warn the user before a large list, and expect the overflow to queue.

## User-facing language

Present every operation as the Onfire engine working with their sales engagement platform. In user-visible text: **no REST paths, no API versions, no HTTP methods, no vendor endpoint names, no proof-table mechanics.** Say "added John to the Enterprise Outbound cadence under Sarah", not "POST cadence_memberships returned 201". When the gate refuses, say "that person hasn't been confirmed in the CRM yet — I'll push them there first", not "CRM_UPLOAD_REQUIRED, no unconsumed proof row".

## Hard rules

- **CRM first, validated, then the SEP copy.** Never create a person in the SEP before `crm_write_results` confirms `succeeded` for them. (No CRM → direct create is correct; Gong never creates at all.)
- **Always call `crm_write_results`.** `crm_write_status` reaching `completed` is not validation and mints no proof.
- **Send `linkedin_url` on every CRM record and on every SEP create.** No LinkedIn URL means no proof, which means no SEP create, ever.
- **Send the identical email** to the SEP that you sent to the CRM. This is what stops the hydration sync from duplicating the person.
- **Check whether the person already exists** in the SEP before creating them.
- **Never work around `CRM_UPLOAD_REQUIRED`.** Fix the cause or report it. There is no alternate write path.
- **Discover the provider before writing any URL.** Never infer it from the user's vocabulary.
- **Never repeat the API root** in `relative_url` — except Gong, which keeps its `v2/`.
- **Confirm live writes with the user** before calling `crm_write` or `sep_write`, and name the exact people and the exact cadence.
- **Re-resolve the cadence id at enrollment time.** Don't trust one from earlier in the conversation.
- **Set attribution explicitly at enrollment.** Don't rely on an inherited owner.
- **Never mix prospects and accounts** in one `crm_write` job when SEP creates will follow.
- **Gong ids are strings.** Outreach relationship ids are integers. Getting this wrong 404s.
- **`pending` is not broken** on Outreach — it's the delivery-schedule window.
- **Already-enrolled is a success.** Don't retry it, don't report it as an error.

## Common failure → cause

| Symptom | Cause |
|---|---|
| `CRM_UPLOAD_REQUIRED` on a SEP create | Work the [refusal checklist](#if-the-create-is-refused). Ranked by frequency: you skipped `crm_write_results`; the `linkedin_url` doesn't match byte-for-byte; the record came back `failed`/`skipped`; your body has an email but no LinkedIn URL; the proof was already consumed. |
| `CRM_UPLOAD_REQUIRED` right after a clean `crm_write_results` | Either the record had no `linkedin_url`/`crm_id` (nothing to mint on), the job led with an account record so nothing was minted, or the best-effort mint failed internally and logged a warning. Re-check the results row, then re-run `crm_write` for that person. |
| `CRM_UPLOAD_REQUIRED` on a SEP-only tenant | Shouldn't happen — the gate only fires when a CRM is connected. Re-read `settings.crm.enabled`; you may be on a different tenant than you think. |
| Duplicate person in the SEP a few days later | The email you sent to the SEP didn't match the CRM record's email, so the hydration sync created a second one. See [Why the email must match exactly](#why-the-email-must-match-exactly). |
| SEP create returned 4xx, retry also refused | The 4xx should have refunded the proof. If the retry is refused, the identifier in the retry body differs from the original — compare them character by character. |
| SEP create returned 5xx, retry refused with `CRM_UPLOAD_REQUIRED` | Expected: 5xx does not refund. Read the SEP first — the create often landed. Only re-upload to the CRM if it truly didn't. |
| `404 routeNotFound` on any SEP call | You used another provider's resource name, or repeated the API root (or dropped Gong's `v2/`). Re-read STEP 1. |
| Cadence lands under the wrong rep | `user_id` / mailbox / `flowInstanceOwnerEmail` resolved to the wrong person. Attribution is explicit now — re-resolve the rep. |
| Salesloft user lookup returns the whole workspace | Expected — `email[]` is ignored. Use `search` and filter client-side. |
| Outreach sequenceState stuck at `pending` | Sequence not activated, delivery-schedule window closed, or the mailbox can't send. Not a retry. |
| Outreach `422` on enroll | Missing mailbox relationship, or ids passed as strings instead of integers. |
| Gong `404 Flow not found` | `flowId` was sent as a number and rounded. Send it as a string. |
| Gong `prospectsNotAssigned` non-empty | Gong hasn't ingested that CRM record yet. This is a Gong-side sync, not something the proof gate covers. Report it and offer a re-check. |
| `sep_write` refused outright (not `CRM_UPLOAD_REQUIRED`) | The tenant doesn't have the write grant. Report it; there is no fallback path. |
