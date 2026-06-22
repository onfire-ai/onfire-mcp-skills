---
name: community-message-search
description: Find people and companies by what they SAID in community/social messages (Slack, Discord, Reddit, StackOverflow, GitHub, etc.) using the `search_community_messages` tool — semantic vector search that returns the SENDERS of messages mentioning or discussing a topic, regardless of how they feel about it. Use for message-based discovery and prospecting — phrases like "find relevant people talking about my competitors", "who's discussing <topic>", "companies whose employees mentioned <topic>", "people raising <pain point>", "find prospects discussing <category>", "relevant chatter about <theme> for this account", "who's asking about <problem>". This is MENTION / discovery, NOT opinion — if the user wants positive/negative sentiment, complaints, or advocacy, use community-messages-sentiment instead; if they want who JOINED a named community, use community-join-signals; for non-message signals (job changes, events, job posts) use query_intent_signals.
---

# community-message-search

Semantic (vector) search over the Onfire community-message corpus via the
`search_community_messages` tool. You give 1–3 natural-language phrasings of
ONE intent; each is embedded and matched by cosine similarity; the tool
consolidates the runs and returns the **people who sent** the most relevant
messages (LinkedIn URL, name, the message text, community, and a `query_hits`
corroboration score). It is the message-as-signal **discovery** tool.

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
    threshold=0.75,                        # min cosine similarity [0,1]; default 0.75
    community_types=None,                  # e.g. ["Discord","Slack"] to restrict platforms
    since=None,                            # ISO date YYYY-MM-DD lower bound
    limit=50,                              # max results after consolidation (also per-query k)
)
```

### Compose THREE distinct phrasings (not one repeated)

The tool runs each phrasing separately and rewards messages that more than one
phrasing surfaces (`query_hits` 2–3 = strong corroboration). Give three
genuinely different angles on the same intent, composed from the user's ICP:

```python
# "people talking about my competitors" (a CNAPP vendor)
query=[
  "practitioners comparing or evaluating cloud/container security tools like <competitors>",
  "teams frustrated with or migrating off their current CNAPP",
  "questions asking which AppSec/CNAPP platform to choose",
]
```

Pull the competitor / keyword / persona terms from the tenant ICP first via
`get_tenant_settings` (`account_research`: competitors, hot keywords, personas),
then fold them into the phrasings. Never pass bare keywords — describe the intent
in natural language.

## Threshold handling — REQUIRED behavior

`threshold` is the minimum cosine similarity (default **0.75**). If the response
comes back with `needs_threshold_adjustment: true` (nothing cleared the bar),
**do not silently retry** — tell the user and ask whether to **lower** it
(e.g. 0.65 → more but looser matches) or refine the intent. Higher = fewer,
tighter; lower = more, looser.

## Reading the results

- Each row is a **sender**: `intent_holder_linkedin_url`, `name`,
  `message_text`, `community_name` / `community_type`, `date`, plus `query_hits`
  and `score`.
- **`query_hits` is the strength signal** — rows hit by 2–3 of your phrasings
  are the strongest corroborated matches. Lead with those.
- Results cap at `limit` (default 50). If the user wants more, call again with a
  higher `limit`.
- The corpus is **GLOBAL** (not company-partitioned). Relevance comes from your
  query; firmographic narrowing happens downstream (next section).

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
- **Treating it as tenant-scoped.** Global corpus; narrow firmographically
  downstream with the entity tools.
- **Silently lowering the threshold on an empty result.** Surface
  `needs_threshold_adjustment` and let the user choose.
