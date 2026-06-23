---
name: community-message-search
description: Find people and companies by what they SAID in community/social messages (Slack, Discord, Reddit, StackOverflow, GitHub, etc.) using the `search_community_messages` tool — semantic vector search that returns the SENDERS of messages mentioning or discussing a topic, regardless of how they feel about it. Use for message-based discovery and prospecting — phrases like "find relevant people talking about my competitors", "who's discussing <topic>", "companies whose employees mentioned <topic>", "people raising <pain point>", "find prospects discussing <category>", "relevant chatter about <theme> for this account", "who's asking about <problem>". This is MENTION / discovery, NOT opinion — if the user wants positive/negative sentiment, complaints, or advocacy, use community-messages-sentiment instead; if they want who JOINED a named community, use community-join-signals; for non-message signals (job changes, events, job posts) use query_intent_signals.
---

# community-message-search

Semantic (vector) search over Onfire's community-message data via the
`search_community_messages` tool. You give 1–3 natural-language phrasings of
ONE intent; the tool searches and returns the **people who sent** the most
relevant messages — their LinkedIn URL, name, what they said, and when. It is
the message-as-signal **discovery** tool.

Each row also carries internal signals (a corroboration count, a similarity
score, and the community the message came from). Those are for **your reasoning
only** — never put them in front of the client. See *Presenting results to the
client* below.

## Route here vs. the neighbors — DECIDE THIS FIRST

Answer one question before picking a tool:

> **Is the user asking about an OPINION / FEELING** — positive, negative,
> complaints, praise, advocacy, satisfaction, frustration?

- **Yes → `community-messages-sentiment`** (it scores polarity per message). Stop.
- **No — they want to FIND people/companies that MENTIONED or DISCUSSED
  something → THIS skill.**
- They want **who JOINED a named community** (membership, not messages) →
  `community-join-signals`.
- They want **non-message** signals (job changes, promotions, events, job
  posts) → `query_intent_signals`.

Word cues that land HERE: "talking about", "mentioned", "discussing",
"raising", "asking about", "relevant people/prospects", "chatter". Word cues
that mean the **sentiment** skill instead: "complaining", "love/hate",
"frustrated", "advocates", "positive/negative", "sentiment", "how they feel".

A request like *"get me relevant people that are talking about my competitors"*
has **no opinion angle** — it is discovery → **this skill**, not sentiment.

## When to use this

- "Find relevant people talking about my competitors."
- "Companies whose employees mentioned <topic> in community messages."
- "Who's discussing <category / pain point> lately?"
- "Find prospects raising <problem> we solve."
- "Relevant community chatter for this account / ICP."

## Input shape

```python
search_community_messages(
    query=[                                # 1–3 phrasings of the SAME intent
        "...angle 1...",
        "...angle 2...",
        "...angle 3...",
    ],
    threshold=0.6,                         # min cosine similarity [0,1]; default 0.6
    community_types=None,                  # e.g. ["Discord","Slack"] to restrict platforms
    since=None,                            # ISO date YYYY-MM-DD lower bound; ASK the user for a window if unspecified
    limit=50,                              # max results after consolidation (also per-query k)
)
```

### Compose the queries that get vectorized — REQUIRED

Each string in `query` is embedded verbatim and matched by *meaning*, so match
quality IS the quality of that text. Write each phrasing as a full, natural-
language description of the buying intent — a sentence a real person would say or
post — **not** a bare keyword or a lone vendor list.

Give 1–3 genuinely different angles on the SAME intent (the tool rewards messages
that more than one phrasing surfaces — `query_hits` 2–3 = strong corroboration).
Each phrasing should:
- describe a **situation or question** (evaluating, comparing, migrating off,
  frustrated with, asking which…), not just nouns strung together;
- weave in concrete ICP terms — competitor names, pain points, personas — which
  you pull from `get_tenant_settings` (`account_research`: competitors, hot
  keywords, personas) **first**;
- stay grounded in what the user actually asked for.

```python
# "people talking about my competitors" (a CNAPP vendor)
query=[
  "practitioners comparing or evaluating cloud/container security tools like <competitors>",
  "teams frustrated with or migrating off their current CNAPP",
  "questions asking which AppSec/CNAPP platform to choose",
]
```

Never pass bare keywords or a lone vendor list — describe the intent in natural
language, or the vector match degrades.

## Time window — REQUIRED: ask before searching

`since` (ISO `YYYY-MM-DD`) bounds how far back to look. If the user did NOT give a
clear time window, **ASK before calling the tool** — don't silently search all of
history. e.g. *"How far back should I look — the last 3 months, the last year, or
all time?"* Translate their answer into `since` (omit it only for an explicit
"all time" / no limit). Skip the question only when the user already stated a
window ("in the last quarter", "since January", "this year").

## Threshold handling — REQUIRED behavior

`threshold` is the minimum similarity (default **0.6**) — internally, how tight
a match has to be. Think of it as how wide you cast the net: higher = fewer,
tighter matches; lower = more, looser ones.

If the response comes back with `needs_threshold_adjustment: true` (nothing
cleared the bar), **do not silently retry**. Tell the client in plain language —
*"I didn't find a strong match for that. Want me to widen the search, or should
we sharpen what we're looking for?"* — and let them choose. Never expose the
numeric threshold (0.75, 0.65, …) or the word "threshold" to the client; it is
an internal dial, not something a GTM user should have to reason about.

## Reading the results (internal)

- Each row is a **sender**: `intent_holder_linkedin_url`, `name`,
  `message_text`, `date`, plus internal-only `query_hits`, `score`, and
  `community_name` / `community_type`.
- **`query_hits` is the strength signal** — rows hit by 2–3 of your phrasings
  are the strongest corroborated matches. Use it to **order** what you show
  (best first); do not show the number itself.
- Every returned sender is already resolved to a real person: the tool only
  returns senders it could match to a member profile **that has a LinkedIn
  URL**, and `name` is their real name when known (falling back to the handle).
  So `intent_holder_linkedin_url` is always populated — there are no "anonymous
  handle" rows to explain away.
- Results cap at `limit` (default 50). If the client wants more, call again with
  a higher `limit`.
- The data is **GLOBAL** (not company-partitioned). Relevance comes from your
  query; firmographic narrowing happens downstream (next section).

## Presenting results to the client

The client is a GTM / sales person, not an engineer. Translate every result
into plain business language. **Lead with the people and what they're saying.**

**Always show, per person:**
- The person's **name** (or their handle if that's all we have).
- Their **LinkedIn URL** (`intent_holder_linkedin_url`) — always present, since
  the tool only returns senders it could resolve to a profile. Show it as a
  clickable link.
- **What they said** — a short, readable paraphrase or the message itself.
- The **date** of the message (`date`), formatted readably (e.g. "Mar 2026").

A clean default table:

| Person | LinkedIn | What they're saying | Date |
| --- | --- | --- | --- |
| Jane Doe | linkedin.com/in/janedoe | Evaluating SAST tools to replace Snyk | Mar 2026 |

**Never show the client:**
- The **community / platform** a message came from (e.g. "r/devops", "Reddit",
  "Discord", "Slack", a channel or subreddit name) — or any breakdown of where
  results came from ("~77% Reddit"). Drop it entirely.
- The **`query_hits` / "Hits" column**, the similarity **score**, the
  **threshold** (0.75 / 0.66 / …), or counts framed as corpus sizes.
- Internal vocabulary: "corpus", "embedding", "cosine", "vector", "threshold",
  "tightness", "corroborated by N of my search angles", result counts as
  "sizes". Speak in terms of *people*, *what they're saying*, and *when*.

If nothing comes back (`needs_threshold_adjustment: true` — either nothing
matched, or no sender resolved to a contactable profile), say so plainly and
offer to widen the search. Never expose the threshold number or frame the reason
in technical terms.

## Building a prospect list (combine with the entity tools)

The corpus has no firmographic filter, so do it in two steps:

1. `search_community_messages(...)` → the senders who mentioned the topic.
2. Filter/enrich those people or their companies with `entity-people-search`
   (`contact`), `entity-company-search` (`company`), or `get_company_headcount`.

> *"Companies whose employees mentioned AI security → UK companies with 60+ code
> contributors and ≤1500 employees":* run the search for AI-security chatter,
> collect the sender companies, then use `entity-company-search` to keep UK
> companies with `github_contributors ≥ 60` and `headcount ≤ 1500`.

## Billing

`search_community_messages` bills **1 credit per consolidated row returned**
(not per internal sub-query). `limit` is the cap — raise it deliberately when
the user asks for more.

## Common pitfalls

- **Routing a sentiment question here.** Any positive/negative/complaint/advocacy
  angle → `community-messages-sentiment`. This tool does not score opinion.
- **One phrasing instead of three.** You lose the corroboration ranking.
- **Bare keywords.** Describe the intent; the match is semantic.
- **Treating it as tenant-scoped.** Global data; narrow firmographically
  downstream with the entity tools.
- **Silently lowering the threshold on an empty result.** Surface
  `needs_threshold_adjustment` and let the client choose — in plain language.
- **Leaking internal mechanics to the client.** No threshold/score/`query_hits`/
  "Hits" column, no "corpus"/"embedding"/"vector" talk, no result counts as
  "sizes". See *Presenting results to the client*.
- **Naming the community / platform.** Never show "r/devops", "Reddit",
  "Discord", a channel/subreddit, or a where-it-came-from breakdown.
- **Hiding the date or LinkedIn URL.** Both go in the client output whenever
  available.
