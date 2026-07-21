# Cold Email Playbook — composing the manual-email content

How to write the email this skill stages on the manual-email step. The rules below are distilled from current (2025–2026) cold-outbound reply-rate research; sources at the bottom. The non-negotiable Onfire rule sits on top of all of it.

## Rule zero: ground everything in real Onfire data

Every specific claim — a signal, a number, a technology, a hiring trend, a 10-K theme — must come from actual Onfire data for *this* prospect / company / tenant. Never invent specificity to make an email feel personalized. If the signals are thin, write a shorter, more general email rather than fabricating detail. Fabricated personalization is worse than none: it's the fastest way to lose trust and get marked as spam.

## The data → email mapping

Pull from four sources and let them shape distinct parts of the email:

| Source | Tools | Feeds |
|---|---|---|
| **The prospect** | prospect record, `ai_prospecting` talking points, `ask_onfire`/`query_intent_signals` | The hook, the persona-appropriate framing, the "why you" |
| **Their company** | `account_research` (10-K, footprint, intent, use cases), `ask_onfire` (hiring, growth, events) | The trigger/timeline, the "why now", credible specifics |
| **The tenant's ICP** | `get_tenant_settings.account_research` (`golden_persona`, `competitors`, `technologies`, `organization`, `buying_committee_queries`, derived use cases) | The value prop, the competitive angle, what to actually pitch |
| **User + conversation** | the chat | Product/angle, tone, constraints, prior context |

The best emails anchor the hook to a **real business signal** (leadership change, hiring momentum, a 10-K priority, an intent/footprint signal, event attendance) and connect it to the tenant's ICP value prop.

## Structure (target ~50–120 words)

1. **Subject** — under ~50 characters, ideally 1–5 words, personalized; it should reference the *same* thing as the opening line. Short subjects survive mobile (≈66% of opens are mobile).
2. **Opener (the hook)** — the first 2–3 seconds decide everything. Lead with *them* and a specific signal, not a self-introduction. **Timeline/trigger-based hooks beat problem-statement hooks** (~2.3× in the data). No "Hi, I'm X from Y."
3. **Body** — 1–2 short paragraphs. One value prop tied to the signal, with light proof (a peer pattern, a concrete outcome). Skimmable. Keep it about them.
4. **One CTA** — a single, soft, **binary** ask: "Worth a quick call?" / "Does this match where you're headed?" Interest-based CTAs beat hard meeting-asks on a first cold touch.
5. **Footer** — keep the unsubscribe link; keep the first email link-light otherwise.

## What moves reply rates (and what kills them)

- **Multi-point personalization** lifts replies dramatically (~142% in the cited research) vs. template blasts. Use more than one real signal where the data supports it.
- **Brevity wins.** Short emails feel easy to answer. 50–100 words is a good target band.
- **One question, not many.** Extra questions depress replies (adding questions can cut reply rate ~21%); a single clear ask outperforms a "moving target."
- **Keep the same CTA across the sequence** rather than escalating/softening every touch.
- **Follow-ups are reminders, not new pitches.** Winning sequences run ~3–7 calm touches.
- **Subject + opener must match.** A subject that promises one thing and an opener about another reads as bait.

## A reusable skeleton (fill from Onfire data)

```
Subject: <2–5 words, references the hook>

Hi <First>,

<Specific, signal-based hook tied to a real trigger at their company —
from Onfire data. One sentence.>

<One value prop framed to the tenant's ICP, with light proof. One–two
sentences. About them, not you.>

<One soft binary CTA — e.g. "Worth a 20-minute call to see how other
<peer-type> teams are handling this?">

Best,
<Sender / team>
```

## Quality bar before staging

- Would this make sense **only** to this prospect, or could it go to anyone? (It should be the former.)
- Is every specific claim backed by real Onfire data?
- Subject ≤ ~50 chars and matched to the opener?
- Exactly one ask, and is it soft/binary?
- Under ~120 words, skimmable, link-light, unsubscribe intact?

## Sources

- Reply.io — Write Cold Emails That Convert (2025 data): https://reply.io/write-better-cold-emails/
- Instantly — Cold Email Reply-Rate Benchmarks: https://instantly.ai/blog/cold-email-reply-rate-benchmarks/
- The Digital Bloom — Cold Outbound Reply-Rate Benchmarks 2025 (Hook × ICP): https://thedigitalbloom.com/learn/cold-outbound-reply-rate-benchmarks/
- Sparkle — Cold Email Outreach Best Practices (data-backed): https://sparkle.io/blog/cold-email-outreach-best-practices/
- Mailshake — Cold Email Subject Lines best practices: https://mailshake.com/blog/cold-email-subject-line-sales/
- Hunter — Cold Email Subject Lines: https://hunter.io/blog/cold-email-subject-line/
- Mixmax — Cold Email CTAs that get replies: https://www.mixmax.com/blog/cold-email-call-to-action-examples
- Woodpecker — How to write a cold email that works: https://woodpecker.co/blog/how-to-write-a-cold-email-that-actually-works-six-step-tutorial/
