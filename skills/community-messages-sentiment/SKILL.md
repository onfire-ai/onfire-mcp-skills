---
name: community-messages-sentiment
description: Run aspect-based sentiment analysis over the Onfire community-messages corpus (Slack, Discord, Reddit, etc.) using the `community_messages_sentiment` tool. Use whenever the user asks how a community feels about a product, vendor, or topic — phrases like "sentiment about X", "what does the community think of Y", "positive/negative feedback on Z", "POC sentiment", "buzz around <vendor>", "who's complained about <product>", "find advocates for <topic>", or any question that combines a keyword/topic with a date range and an opinion angle. The tool returns a small inline summary plus a persisted CSV dataset of every scored message — this skill enforces the post-call playbook so the dataset (not the inline numbers) becomes the deliverable.
---

# community_messages_sentiment

Snowflake-backed retrieval + Vertex (Gemini) per-message aspect scoring over the Onfire community-messages corpus. The tool already does the heavy lifting; this skill tells you how to use the result so the user actually gets value out of it.

## When to use this

- "What does the Slack community feel about Sonatype?"
- "Find positive vs negative discussions of Snyk in the last 90 days."
- "Who's complained about Wiz POCs? Get me their LinkedIns."
- "Pull buzz around vendor X across communities since March."
- Any question that mixes a **keyword or topic** + a **date range** + an **opinion angle**.

Skip this for:

- Pure keyword search with no sentiment angle — use Snowflake directly via `septer_query` / `connect_query` / `query_datasets` (this tool spends LLM time you don't need).
- Sentiment toward a person rather than a product/topic — there's no LinkedIn-of-target lookup; the people here are the **authors** of the messages, not the subjects.

## Input shape

```python
community_messages_sentiment(
    keywords=["Sonatype"],                              # 1-10 tokens, whole-word, case-insensitive
    sentiment_subject="Positive or negative experience with Sonatype",
    date_from="2026-02-20",                             # ISO date
    date_to="2026-05-20",
    keyword_mode="all",                                 # "all" (AND) or "any" (OR). Default "all".
    max_messages=500,                                   # default 500, hard cap 5000
    concurrency=None,                                   # optional; defaults to server ceiling (1000)
)
```

### How to phrase `sentiment_subject`

This is the **aspect** the LLM judges against. Be specific — don't just pass the keyword.

| Bad | Good |
|---|---|
| `"Sonatype"` | `"Positive or negative experience with Sonatype's vulnerability data"` |
| `"POC"` | `"Trust and friction during Wiz POCs"` |
| `"AI tools"` | `"Whether Cursor saves engineering time vs. Copilot"` |

The subject framing is what makes this aspect-based: "I love Slack but Sonatype's UI is terrible" gets correctly classified as **negative toward Sonatype**, not mixed-overall.

## Output shape

```json
{
  "dataset": { "id": "ds_abc123...", "row_count": 500, "expires_at": "...", "schema": [...] },
  "total_matched": 2412,
  "total_scored": 500,
  "truncated_to_limit": true,
  "sentiment_subject": "...",
  "keywords": [...],
  "keyword_mode": "all",
  "date_range": { "from": "...", "to": "..." },
  "counts": {
    "positive": 142, "negative": 188, "neutral": 81,
    "irrelevant": 86, "error": 3
  },
  "unique_senders_with_linkedin": 263,
  "by_community": [
    { "community_type": "Slack", "community_name": "DevSecOps Community",
      "positive": 47, "negative": 71, "neutral": 22, "irrelevant": 18, "error": 1 },
    ...
  ],
  "top_positive": [ { "linkedin_url": "...", "message_text": "...", "confidence": 0.92, "reason": "..." }, ...up to 5 ],
  "top_negative": [ ...up to 5 ],
  "wall_clock_seconds": 22.4,
  "concurrency_used": 1000
}
```

## The post-call playbook (READ THIS)

**The dataset is the deliverable. The inline JSON is a preview.**

After every successful call, do these four things in order:

1. **State the headline.** One sentence built from `counts` and `by_community`, e.g. *"Sentiment toward Sonatype skewed negative — 188 negative vs 142 positive across 263 unique authors, concentrated in r/devops and the DevSecOps Slack."* If `truncated_to_limit` is true, **say so explicitly**: *"based on the latest 500 of 2,412 matching messages."*

2. **Quote 1-2 exemplars from `top_positive` and `top_negative`** with the author's LinkedIn URL. These are sorted by confidence — they're the most defensible quotes you have. Never paraphrase silently; the LinkedIn URL is part of the evidence.

3. **Offer the dataset as a file.** Call `download_dataset(dataset_id="<id>")` and surface the resulting link to the user as *"Full per-message breakdown (linkedin, community, sentiment, confidence, reason): \<link\>"*. Do not skip this — most of the value is in the per-row detail, not the counts.

4. **Mention the dataset_id and that follow-up questions are free.** *"The dataset (`ds_abc123`) is queryable for 7 days — ask me 'who said X', 'show me only the Slack messages', or 'group by sender' and I'll slice it without re-running."*

## Follow-up questions: use `query_datasets`, do NOT re-run the tool

Almost every follow-up the user asks is answerable from the dataset that's already in S3. Re-calling `community_messages_sentiment` is expensive and wasteful. Examples:

| User says | What to do |
|---|---|
| *"Show me everyone who said something negative"* | `query_datasets("SELECT linkedin_url, sender_name, community_name, message_text, reason FROM ds_... WHERE sentiment_value='negative' ORDER BY confidence DESC")` |
| *"Only the Slack messages"* | `query_datasets("SELECT * FROM ds_... WHERE community_type='Slack'")` |
| *"Who are the top complainers?"* | `query_datasets("SELECT linkedin_url, sender_name, COUNT(*) AS n FROM ds_... WHERE sentiment_value='negative' GROUP BY 1,2 ORDER BY n DESC LIMIT 25")` |
| *"How does it break down by community?"* | The inline `by_community` already has this — don't re-query. |
| *"How does it skew by month?"* | `query_datasets("SELECT DATE_TRUNC('month', message_timestamp::date) AS m, sentiment_value, COUNT(*) FROM ds_... GROUP BY 1,2 ORDER BY 1")` |

Only re-run `community_messages_sentiment` when the user genuinely changes the inputs — different keywords, a wider date range, a different sentiment subject. Sampling more messages (raising `max_messages`) does require a new call; tell the user that explicitly so they can decide.

## Reading the counts honestly

- `irrelevant` ≠ noise to hide. It's messages where the keyword matched but **no sentiment about the subject** was expressed (e.g. "POC" matched a different POC, or someone linked Sonatype's homepage without commenting). Report it: *"...86 messages mentioned Sonatype but didn't actually express an opinion about it."* Don't fold irrelevant into neutral.
- `error` rows are Vertex failures (rate limit, malformed response). If `error` is more than ~5% of total, mention it as a caveat.
- `unique_senders_with_linkedin` is the actionable headline number — it's how many real people you can reach out to. Surface it.
- `total_matched > total_scored` means you sampled. **Always disclose the sample.** The user makes different decisions on 500-of-2412 than on 500-of-500.

## Hard rules

- Always offer `download_dataset` after a successful call. The user shouldn't have to ask.
- When `truncated_to_limit` is true, **lead with the sampling caveat** before quoting numbers.
- For drill-downs, use `query_datasets` against the existing `dataset_id` — never re-run for slicing.
- Don't quote the `message_text` field as gospel — it's truncated to 500 chars in the dataset. If the user wants full text, query the source row by `message_id` in Snowflake (`silver.community_messages.int_messages_with_linkedin`).
- Don't conflate "the keyword appeared" with "the community has an opinion." That's exactly what `irrelevant` exists to separate.
- The LinkedIn URLs in the dataset are the **message authors**, not the topic. If the user asks "who at Sonatype is being talked about", that's a different question — say so.

## Common pitfalls

- **Stopping at the inline counts.** The user will ask follow-ups. If you didn't surface the dataset_id or download link, you've shifted that cost back onto a second tool call.
- **Re-running for "show me only negatives".** Wasteful. Use `query_datasets`.
- **Using a vague `sentiment_subject` like `"Sonatype"`.** That measures whether messages are positive or negative *in general*, not toward Sonatype. The aspect framing is what makes this tool worth the LLM cost.
- **Forgetting the date math.** "Last 3 months" against today's date — convert before calling. The tool won't infer it.
- **Treating `top_positive`/`top_negative` as exhaustive.** They are 5 exemplars sorted by confidence. The rest of the evidence is in the dataset.

## Worked examples

### "What's the community saying about Sonatype lately?"

```python
community_messages_sentiment(
    keywords=["Sonatype"],
    sentiment_subject="Positive or negative experience with Sonatype",
    date_from="<today minus 90d>",
    date_to="<today>",
)
```

Then:
1. *"Across the last 3 months, sentiment toward Sonatype skewed negative — 188 negative vs 142 positive across 263 unique authors, based on the latest 500 of 2,412 matching messages. Negative discussion concentrated in r/devops and the DevSecOps Slack."*
2. Quote 1 positive + 1 negative exemplar with linkedin URLs.
3. `download_dataset(dataset_id="...")` → surface link.
4. *"The dataset (`ds_...`) is queryable for 7 days — ask me 'who complained the most', 'show me only the Slack threads', or anything else."*

### "Filter to only the people who said something negative about Snyk's UI"

User had a prior `community_messages_sentiment` run on `["Snyk"]` with subject "Snyk's UI quality". Don't re-run. Do:

```sql
query_datasets("SELECT linkedin_url, sender_name, community_name, message_text, reason
                FROM ds_<prior_id>
                WHERE sentiment_value='negative'
                ORDER BY confidence DESC")
```

### "How does sentiment compare for Sonatype vs Snyk?"

Two **separate** calls (different keywords, different subject framing), then narrate both headlines side by side and offer both download links. Do not try to mix subjects in a single call — the aspect framing is per-call.

## What this skill does NOT do

- It does not look up sentiment **about a specific person**. The authors are returned; the targets are the keywords.
- It does not query a CRM. Output is community messages, not pipeline/opportunity data.
- It does not produce a customer-facing PDF or HTML report — pair it with a doc-skill (e.g. `docx` or `pdf`) if the user wants a polished deliverable.
- It does not enrich the returned LinkedIn URLs with emails/phones. Pipe `linkedin_url` values into `contact_data_enrichment` if the user asks to reach out.
