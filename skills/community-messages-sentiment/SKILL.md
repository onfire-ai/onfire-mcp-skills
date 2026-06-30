---
name: community-messages-sentiment
description: Run aspect-based SENTIMENT analysis over the Onfire community-messages corpus (Slack, Discord, Reddit, etc.) using the `community_messages_sentiment` tool. USE ONLY when the question has an explicit OPINION / FEELING angle — how a community feels about a product, vendor, or topic: positive vs negative, complaints, praise, advocacy, satisfaction, frustration. Trigger phrases: "sentiment about <X>", "what does the community think of <Y>", "positive/negative feedback on <Z>", "who's complaining about <product>", "find advocates for <topic>", "are people frustrated with <vendor>", "POC sentiment". Do NOT use this to merely FIND or discover people/messages that MENTION or discuss a topic with no opinion angle (e.g. "find relevant people talking about my competitors", "who's discussing <topic>", "companies whose employees mentioned <X>") — that is message discovery: use the community-message-search skill (the `search_community_messages` tool). Decision rule: if there is NO positive/negative angle, this is the WRONG skill. The tool scores LLM polarity per message and BILLS per returned message, so it first asks you how many messages to analyze; it returns a small inline summary plus a persisted CSV dataset of the scored on-topic messages — this skill enforces the post-call playbook so the dataset (not the inline numbers) becomes the deliverable.
---

# community_messages_sentiment

Semantic vector retrieval (the same ranker behind `community-message-search`) + Vertex (Gemini) per-message aspect scoring over the Onfire community-messages corpus. **Pure top-k**: `target_messages` is the number of most-relevant messages we retrieve, the number we LLM-score, and the cap on what we return and bill. Company enrichment via `silver.dataspring.dataspring_people_full` + `gold.entities.companies` resolves each sender's employer so you get a by-company breakdown in addition to the by-community one.

## Routing gate — answer this BEFORE using this skill

> **Does the request name an OPINION / FEELING** — positive/negative,
> complaint, praise, advocacy, satisfaction, frustration?

- **No** → this is the WRONG skill. If they want to FIND people/messages that
  merely MENTION or discuss a topic (e.g. *"relevant people talking about my
  competitors"*, *"who's discussing X"*, *"companies whose employees mentioned
  Y"*), use **`community-message-search`** (the `search_community_messages`
  tool). If they want who JOINED a community, use **`community-join-signals`**.
- **Yes** → continue here. This tool spends LLM time scoring polarity and bills
  per returned message; only pay that when the opinion angle is the point.

## When to use this

- "What does the Slack community feel about Nexagon?"
- "Find positive vs negative discussions of Codeshield in the last 90 days."
- "Who's complained about Cloudward POCs? Get me their LinkedIns."
- "Find advocates / detractors for vendor X across communities since March."
- "Which companies have the most employees complaining about <product>?"
- Any question that mixes a **topic** + a **date range** + an **opinion angle**.

Skip this for:

- **Plain mention/discovery with no opinion angle** ("find people talking about
  X", "who's discussing Y") — use **`community-message-search`**
  (`search_community_messages`); this tool would waste LLM time scoring opinion
  you didn't ask for.
- Sentiment toward a person rather than a product/topic — the people here are the **authors** of the messages, not the subjects.

## Two modes — pick one, then size it with the user

The tool has two retrieval modes (`mode`). Both LLM-score every candidate and
**bill per returned message** (1 credit each), so size the run with the user
first — framed as the **number of messages to analyze**, never as cost.

### `mode="top_k"` (default) — "about N opinion messages"

Returns the `target_messages` messages most relevant to the subject. Use for a
representative read or when the user names a count.

- `target_messages` is **required**. Call without it and the tool returns a
  `needs_input` envelope — **ASK the user**: *"How many community messages should
  I analyze — ~50 for a quick read or ~150–300 for a fuller picture?"* then
  resubmit with `target_messages=N`.
- Above 500 the tool returns `needs_confirmation`; confirm the volume, resubmit
  with `confirmed=true`.
- You may get **slightly fewer** than N (off-topic drops) — compare
  `total_returned` to `target_messages` and relay honestly.

### `mode="date_range"` — "ALL the sentiment in this window"

Scores **every** message mentioning the keywords in `[date_from, date_to]` — the
window is the scope, not a count. Use when the user wants exhaustive coverage:
*"everything said about X in Q1"*, a competitor brief, etc.

- The tool first COUNTS the window. Above the threshold it returns
  `needs_confirmation` with `matched_in_window` / `will_analyze` — **tell the user
  the volume** (*"~6,300 messages match this window — analyze them?"*), then
  resubmit with `confirmed=true`.
- Capped per run (`max_range_messages`, currently 10k). A window bigger than the
  cap is truncated to the most recent and flagged in `note` — narrow the dates
  for full coverage.
- `keyword_mode` ("all"=AND / "any"=OR) controls the lexical keyword match here
  (it's ignored in top_k).
- Relevance is enforced by the per-message LLM score (off-topic dropped), not a
  cosine floor, so `discarded_off_topic` can be higher than in top_k — tighten
  the keywords if it is.

## Pre-step: resolve company names via `match_company` before calling

**Always do this before passing `exclude_companies`.**

Exclusion drops senders whose resolved current employer (from `silver.dataspring.dataspring_people_full`, matched by company LinkedIn URL) is in your list. The only accepted key is the canonical company **LinkedIn URL** — the tool now **rejects a bare company name with an error** (it can't reliably match "Nexagon" to "Nexagon, Inc.").

**Rule: if the user supplies a company name (or domain) for exclusion, call `match_company` for each one first and use the returned LinkedIn URL.**

```python
# User says: "exclude Nexagon employees"
match_company("Nexagon")
# → { "linkedin_url": "linkedin.com/company/nexagon", "name": "Nexagon", ... }

# Then pass the LinkedIn URL to the tool:
community_messages_sentiment(
    ...,
    exclude_companies=["linkedin.com/company/nexagon"],
)
```

If `match_company` returns no result for a name, skip that entry and tell the user it couldn't be resolved. Passing a bare company name now raises a validation error — resolve it first.

If the user already provides a company LinkedIn URL (e.g. `"linkedin.com/company/nexagon"`), skip the `match_company` call for that entry.

## Input shape

**top_k (default)** — N most-relevant messages:
```python
community_messages_sentiment(
    keywords=["Nexagon"],                                        # 1-10 topic tokens; steer the relevance search
    sentiment_subject="Positive or negative experience with Nexagon",
    date_from="2026-02-20",                                       # ISO date, inclusive
    date_to="2026-05-20",                                         # ISO date, inclusive
    mode="top_k",                                                 # default
    target_messages=150,                                          # REQUIRED in top_k — scored AND returned ≤ this. ASK the user if unknown.
    concurrency=None,                                             # optional; defaults to server ceiling
    exclude_companies=["linkedin.com/company/nexagon"],          # resolved LinkedIn URLs only (bare names error)
)
```

**date_range** — every keyword-matching message in the window:
```python
community_messages_sentiment(
    keywords=["Nexagon"],                                        # the lexical match defining the candidate set
    sentiment_subject="Positive or negative experience with Nexagon",
    date_from="2026-01-01",
    date_to="2026-03-31",
    mode="date_range",                                            # scope = the whole window, not a count
    keyword_mode="all",                                           # "all"=AND / "any"=OR across keywords (date_range only)
    confirmed=True,                                               # set AFTER the user confirms the volume the count gate reported
    exclude_companies=["linkedin.com/company/nexagon"],
)                                                                 # target_messages is ignored in date_range
```

### How to phrase `sentiment_subject`

This is the **aspect** the LLM judges against AND the phrasing that drives candidate relevance — be specific, don't just pass the keyword.

| Bad | Good |
|---|---|
| `"Nexagon"` | `"Positive or negative experience with Nexagon's vulnerability data"` |
| `"POC"` | `"Trust and friction during Cloudward POCs"` |
| `"AI tools"` | `"Whether CodeQuill saves engineering time vs. CodeAssist"` |

The subject framing is what makes this aspect-based: "I love Slack but Nexagon's UI is terrible" gets correctly classified as **negative toward Nexagon**, not mixed-overall. It also steers retrieval, so a sharp subject yields more on-topic candidates and fewer drops.

## Output shape

```json
{
  "dataset": { "id": "ds_abc123...", "row_count": 142, "expires_at": "...", "schema": [...] },
  "mode": "top_k",                 // or "date_range"
  "target_messages": 150,          // top_k only; date_range carries "matched_in_window" instead
  "total_returned": 142,
  "total_scanned": 150,
  "discarded_off_topic": 8,
  "scoring_errors": 0,
  "sentiment_subject": "...",
  "keywords": [...],
  "date_range": { "from": "...", "to": "..." },
  "counts": {
    "positive": 47, "negative": 71, "neutral": 24,
    "irrelevant": 0, "error": 0
  },
  "unique_senders_with_linkedin": 128,
  "unique_companies_resolved": 64,
  "by_community": [
    { "community_type": "Slack", "community_name": "DevSecOps Community",
      "positive": 18, "negative": 29, "neutral": 9, "irrelevant": 0, "error": 0 },
    ...
  ],
  "by_company": [
    { "company_name": "Acme Corp", "company_linkedin_url": "linkedin.com/company/acme",
      "company_industry": "Computer Software", "company_size": "1001-5000",
      "positive": 4, "negative": 12, "neutral": 3, "irrelevant": 0, "error": 0 },
    ...up to 15
  ],
  "top_positive": [
    { "linkedin_url": "...", "sender_name": "...", "sender_job_title": "Staff Engineer",
      "company_name": "Acme Corp", "company_industry": "Computer Software",
      "community_type": "Slack", "community_name": "DevSecOps Community",
      "message_text": "...", "confidence": 0.92, "reason": "..." },
    ...up to 5
  ],
  "top_negative": [ ...up to 5 ],
  "note": "Returned 142 of the 150 requested — ...",   // present ONLY when fewer than requested
  "wall_clock_seconds": 18.4,
  "concurrency_used": 25
}
```

- `total_scanned` = messages actually LLM-scored (the top-k, ≤ `target_messages`).
- `total_returned` = on-topic messages kept, returned, and billed (`= row_count`).
- `discarded_off_topic` = scored candidates the model flagged `irrelevant` (mentioned the subject but carried no opinion) and dropped — **scored but NOT billed**.
- `scoring_errors` = candidates that could NOT be scored (a transient LLM error). Excluded and **NOT billed**. If scoring fails for *everything* and nothing survives, the tool returns an explicit `{"error": ...}` instead of a clean empty result — surface that as "scoring failed, please retry," never as "no sentiment found." `counts` shows `irrelevant`/`error` as 0 because neither is in the returned (billed) set; `discarded_off_topic` and `scoring_errors` are where they're reported.

### Dataset columns

The persisted CSV includes: `linkedin_url`, `sender_name`, `sender_job_title`, `company_linkedin_url`, `company_name`, `company_industry`, `company_size`, `company_country`, `community_type`, `community_name`, `message_timestamp`, `message_text`, `sentiment_subject`, `sentiment_value`, `confidence`, `reason`, `relevance_score`, `message_id`.

`relevance_score` is the semantic match score (0–1) of the message to the subject. Company fields are populated for senders whose LinkedIn URL matches a record in `silver.dataspring.dataspring_people_full`. Senders not found there have null company fields.

## The post-call playbook (READ THIS)

**The dataset is the deliverable. The inline JSON is a preview.**

After every successful call, do these four things in order:

1. **State the headline.** One sentence from `counts` + `by_community` + `by_company`, e.g. *"Sentiment toward Nexagon skewed negative — 71 negative vs 47 positive across 128 unique authors from 64 companies, heaviest in r/devops and the DevSecOps Slack; Acme Corp and Beta Inc employees are the most vocal critics."* If `total_returned` is less than `target_messages` (see `note`), **say so explicitly** ("only 142 relevant messages existed for this subject/window").

2. **Quote 1-2 exemplars from `top_positive` and `top_negative`** with the author's LinkedIn URL, job title, and company. These are sorted by confidence — they're the most defensible quotes you have.

3. **Offer the dataset as a file.** Call `download_dataset(dataset_id="<id>")` and surface the link as *"Full per-message breakdown (linkedin, company, sentiment, confidence, reason): \<link\>"*. Do not skip this.

4. **Mention the dataset_id and that follow-up questions are free.** *"The dataset (`ds_abc123`) is queryable for 7 days — ask me 'who said X', 'show me only Slack messages', or 'break it down by company industry'."*

## Follow-up questions: use `query_datasets`, do NOT re-run the tool

| User says | What to do |
|---|---|
| *"Show me everyone who said something negative"* | `query_datasets("SELECT linkedin_url, sender_name, company_name, message_text, reason FROM ds_... WHERE sentiment_value='negative' ORDER BY confidence DESC")` |
| *"Only the Slack messages"* | `query_datasets("SELECT * FROM ds_... WHERE community_type='Slack'")` |
| *"Who are the top complainers?"* | `query_datasets("SELECT linkedin_url, sender_name, company_name, COUNT(*) AS n FROM ds_... WHERE sentiment_value='negative' GROUP BY 1,2,3 ORDER BY n DESC LIMIT 25")` |
| *"Which industries complain most?"* | `query_datasets("SELECT company_industry, COUNT(*) AS n FROM ds_... WHERE sentiment_value='negative' GROUP BY 1 ORDER BY n DESC")` |
| *"Break down by company"* | The inline `by_company` already has this — don't re-query. |
| *"How does it skew by month?"* | `query_datasets("SELECT DATE_TRUNC('month', message_timestamp::date) AS m, sentiment_value, COUNT(*) FROM ds_... GROUP BY 1,2 ORDER BY 1")` |
| *"Which companies have the most negative senders?"* | `query_datasets("SELECT company_name, company_industry, company_size, SUM(CASE WHEN sentiment_value='negative' THEN 1 ELSE 0 END) AS neg FROM ds_... GROUP BY 1,2,3 ORDER BY neg DESC LIMIT 20")` |

The dataset holds only on-topic rows (`sentiment_value` ∈ positive/negative/neutral) — there are no `irrelevant`/`error` rows to filter out.

Only re-run `community_messages_sentiment` when the user genuinely changes the inputs — different keywords, wider date range, different sentiment subject, or a **larger `target_messages`** to analyze/return more. A bigger `target_messages` is a new (billed) call; tell the user explicitly.

## Reading the counts honestly

- `discarded_off_topic` is the count of scored candidates that mentioned the subject but didn't carry an opinion about it. A high ratio of `discarded_off_topic` to `total_scanned` means the subject/keywords were too broad — tighten them. These are NOT billed. (Candidates that *failed* scoring are counted separately in `scoring_errors`, also not billed.)
- `counts` is over the **returned** messages only (positive/negative/neutral); `irrelevant`/`error` show 0 there by design.
- `unique_senders_with_linkedin` is the people reach number — how many authors you can follow up with.
- `unique_companies_resolved` tells you how many employers are represented. A high ratio of resolved companies means the `by_company` breakdown is reliable; a low ratio means many senders weren't in dataspring.
- `total_returned < target_messages` means the relevant pool ran out — **say so** (don't imply we found exactly what was asked).

## Hard rules

- Always offer `download_dataset` after a successful call.
- When `total_returned < target_messages`, **lead with that** ("only N relevant messages existed for this subject/window") before quoting numbers.
- For drill-downs, use `query_datasets` — never re-run for slicing.
- Don't quote `message_text` as gospel — it's truncated to 500 chars. Tell the user if they want the full text of a specific message it isn't available.
- Company fields are null for senders not found in dataspring. Don't claim company-level insight for messages where `company_name` is null.

## Common pitfalls

- **Calling without asking how many.** `target_messages` is required; if you don't pass it the tool just asks you to get a count. Decide the volume with the user FIRST (frame as volume, not cost).
- **Stopping at the inline counts.** The user will ask follow-ups. Surface the dataset_id.
- **Re-running for "show me only negatives".** Wasteful. Use `query_datasets`.
- **Using a vague `sentiment_subject` like `"Nexagon"`.** The aspect framing is what makes this worth the LLM cost — and a sharper subject means fewer off-topic drops, so you hit your target.
- **Forgetting date math.** "Last 3 months" → convert before calling.
- **Treating `top_positive`/`top_negative` as exhaustive.** They are 5 exemplars sorted by confidence.
- **Ignoring null company fields.** `unique_companies_resolved` < `unique_senders_with_linkedin` means some senders weren't resolved — the by_company breakdown is a subset, not the full picture.
- **Passing a bare company name to `exclude_companies`.** This now raises a validation error. Always resolve via `match_company` first and pass the LinkedIn URL.

## Worked examples

### "What's the community saying about Nexagon lately?"

First, if they didn't say how many: *"How many messages should I analyze — ~100 for a quick read or ~250 for a fuller picture?"* Say they pick 200.

```python
community_messages_sentiment(
    keywords=["Nexagon"],
    sentiment_subject="Positive or negative experience with Nexagon",
    date_from="<today minus 90d>",
    date_to="<today>",
    target_messages=200,
    exclude_companies=["linkedin.com/company/nexagon"],  # resolved via match_company; strips insider voices
)
```

Then:
1. *"Across the last 3 months, sentiment toward Nexagon skewed negative — 71 negative vs 47 positive across 128 unique authors from 64 companies (192 of the 200 most-relevant messages were on-topic). Negative discussion concentrated in r/devops and the DevSecOps Slack; employees at Acme Corp and Beta Inc are the most vocal critics."*
2. Quote 1 positive + 1 negative exemplar with LinkedIn URL, job title, and company.
3. `download_dataset(dataset_id="...")` → surface link.
4. *"The dataset (`ds_...`) is queryable for 7 days — ask me 'which industries complain most', 'show me only the Slack threads', or anything else."*

### "Which companies have the most employees complaining about Cloudward POCs?"

```python
community_messages_sentiment(
    keywords=["Cloudward", "POC"],
    sentiment_subject="Friction or dissatisfaction during Cloudward POCs",
    date_from="<today minus 180d>",
    date_to="<today>",
    target_messages=150,
)
```

Then use `by_company` from the inline result to identify top negative companies, and drill with:
```sql
query_datasets("SELECT company_name, company_industry, linkedin_url, sender_name, message_text
                FROM ds_<id>
                WHERE sentiment_value='negative'
                ORDER BY company_name, confidence DESC")
```

### "How does sentiment compare for Nexagon vs Codeshield?"

Two **separate** calls (different keywords, different subject framing — split `target_messages` across them, e.g. 150 each), then narrate both headlines side by side and offer both download links.

## What this skill does NOT do

- It does not look up sentiment **about a specific person**. The authors are returned; the targets are the keywords.
- It does not query a CRM. Output is community messages, not pipeline/opportunity data.
- It does not produce a customer-facing PDF or HTML report — pair it with `docx` or `pdf` skills if needed.
- It does not enrich the returned LinkedIn URLs with emails/phones. Pipe `linkedin_url` values into `contact_data_enrichment` if the user asks to reach out.
