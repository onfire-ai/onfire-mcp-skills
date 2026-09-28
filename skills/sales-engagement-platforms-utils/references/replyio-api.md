# Reply.io — read/query reference

`settings.sep.type == "replyio"`.

This reference is drawn from Reply.io's published spec rather than from heavy use, so treat
it as the less verified of the four. If a live response disagrees with anything here, trust
the response and the vendor docs.

**Docs:**
- <https://apidocs.reply.io/> — documentation portal
- <https://docs.reply.io/api-reference/> — resource reference
- <https://docs.reply.io/api-reference/bundled.yaml> — **the OpenAPI spec, fetchable as
  text.** Prefer this; the portals render in JavaScript and return nothing to a fetch.
- <https://docs.reply.io/llms.txt> — documentation index

---

Always rely on the provider's current official documentation where it is available.
The notes below are fixes we have found to work in practice, for when you hit
something the docs do not explain.

---

## Path form

Write bare resource names — `sequences`, `contacts`. Never prefix `v3/`.

Reply.io's base URL is `https://api.reply.io` and every documented path carries `/v3`, which
is the prefix already applied for you.

---

## Resources

| concept | write | spec path |
|---|---|---|
| sequences | `sequences`, `sequences/<id>` | `/v3/sequences` |
| contacts | `contacts`, `contacts/<id>` | `/v3/contacts` |
| a contact enrolled in a sequence | `sequence-contacts` | `/v3/sequence-contacts` |
| a sequence's steps | `sequences/<sequence_id>/steps` | `/v3/sequences/{sequence_id}/steps` |

The `Sequence` object carries its schedule and the email and LinkedIn accounts it sends
from. `Sequence Contact` carries current step, status, opt-out flag, and call and meeting
status.

---

## Paging — `top` / `skip`

Reply.io uses none of the other providers' conventions:

| param | meaning |
|---|---|
| `top` | maximum items to return |
| `skip` | items to skip |

```
sales_engagement_read(relative_url="sequences", params={"top": "50", "skip": "0"})
```

Rate limits are **100 requests/minute and 3,000/hour** — the tightest of the four. Page in
large `top` chunks rather than many small ones.

---

## Person lookup and enrollment

Lookup by email uses a **scalar** `email` parameter — one address per call.

Enrollment and contact creation are owned by `sep-cadence-enrollment`; the shapes are
`POST sequences/<sequence id>/contact-links/bulk` with `{"contactIds": [<int>, ...]}`, and a
**flat** contact body (`email`, `firstName`, `linkedin`, …) rather than a JSON:API envelope.

Reply.io also exposes `webhooks` for outbound events — replies, opens, clicks, bounces, and
LinkedIn events.

---

## Starting from scratch on a Reply.io tenant

1. `get_tenant_settings` — confirm `settings.sep.type == "replyio"`.
2. `sales_engagement_read(relative_url="sequences", params={"top": "5"})` — the cheapest
   probe. It confirms the path form and shows you the real response envelope.
3. Read the paging shape off that response before walking a collection.
