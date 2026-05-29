---
name: community-messages-sentiment
description: Run aspect-based sentiment analysis over the Onfire community-messages corpus (Slack, Discord, Reddit, etc.) using the `community_messages_sentiment` tool. Use whenever the user asks how a community feels about a product, vendor, or topic — phrases like "sentiment about X", "what does the community think of Y", "positive/negative feedback on Z", "POC sentiment", "buzz around <vendor>", "who's complained about <product>", "find advocates for <topic>", or any question that combines a keyword/topic with a date range and an opinion angle. The tool returns a small inline summary plus a persisted CSV dataset of every scored message — this skill enforces the post-call playbook so the dataset (not the inline numbers) becomes the deliverable.
---

# community_messages_sentiment

Snowflake-backed retrieval + Vertex (Gemini) per-message aspect scoring over the Onfire community-messages corpus. Company enrichment via `silver.dataspring.dataspring_people_full` + `gold.entities.companies` resolves each sender's employer so you get a by-company breakdown in addition to the by-community one.

## When to use this

- "What does the Slack community feel about Nexagon?"
- "Find positive vs negative discussions of Codeshield in the last 90 days."
- "Who's complained about Cloudward POCs? Get me their LinkedIns."
- "Pull buzz around vendor X across communities since March."
- "Which companies have the most employees complaining about <product>?"
- Any question that mixes a **keyword or topic** + a **date range** + an **opinion angle**.

Skip this for:

- Pure keyword search with no sentiment angle — use Snowflake directly via `septer_query` / `connect_query` / `query_datasets` (this tool spends LLM time you don't need).
- Sentiment toward a person rather than a product/topic — the people here are the **authors** of the messages, not the subjects.

## Pre-step: resolve company names via `match_company` before calling

**Always do this before passing `exclude_companies`.**

The exclusion filter joins against `silver.dataspring.dataspring_people_full` using `JOB_COMPANY_LINKEDIN_URL`. Name-based matching is unreliable (dataspring may store "Nexagon, Inc." while you pass "Nexagon"). The only safe key is the canonical company LinkedIn URL.

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

If `match_company` returns no result for a name, skip that entry and tell the user it couldn't be resolved. Never pass a bare company name as a fallback — it will silently fail to exclude anyone.

If the user already provides a company LinkedIn URL (e.g. `"linkedin.com/company/nexagon"`), skip the `match_company` call for that entry.

## Input shape

```python
community_messages_sentiment(
    keywords=["Nexagon"],                                        # 1-10 tokens, whole-word, case-insensitive
    sentiment_subject="Positive or negative experience with Nexagon",
    date_from="2026-02-20",                                       # ISO date
    date_to="2026-05-20",
    keyword_mode="all",                                           # "all" (AND) or "any" (OR). Default "all".
    max_messages=500,                                             # default 500, hard cap 5000
    concurrency=None,                                             # optional; defaults to server ceiling (1000)
    exclude_companies=["linkedin.com/company/nexagon"],          # resolved LinkedIn URLs only
)
```

### How to phrase `sentiment_subject`

This is the **aspect** the LLM judges against. Be specific — don't just pass the keyword.

| Bad | Good |
|---|---|
| `"Nexagon"` | `"Positive or negative experience with Nexagon's vulnerability data"` |
| `"POC"` | `"Trust and friction during Cloudward POCs"` |
| `"AI tools"` | `"Whether CodeQuill saves engineering time vs. CodeAssist"` |

The subject framing is what makes this aspect-based: "I love Slack but Nexagon's UI is terrible" gets correctly classified as **negative toward Nexagon**, not mixed-overall.

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
  "unique_companies_resolved": 87,
  "by_community": [
    { "community_type": "Slack", "community_name": "DevSecOps Community",
      "positive": 47, "negative": 71, "neutral": 22, "irrelevant": 18, "error": 1 },
    ...
  ],
  "by_company": [
    { "company_name": "Acme Corp", "company_linkedin_url": "linkedin.com/company/acme",
      "company_industry": "Computer Software", "company_size": "1001-5000",
      "positive": 12, "negative": 31, "neutral": 8, "irrelevant": 4, "error": 0 },
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
  "wall_clock_seconds": 22.4,
  "concurrency_used": 1000
}
```

### Dataset columns

The persisted CSV includes: `linkedin_url`, `sender_name`, `sender_job_title`, `company_linkedin_url`, `company_name`, `company_industry`, `company_size`, `company_country`, `community_type`, `community_name`, `message_timestamp`, `message_text`, `sentiment_subject`, `sentiment_value`, `confidence`, `reason`, `message_id`.

Company fields are populated for senders whose LinkedIn URL matches a record in `silver.dataspring.dataspring_people_full`. Senders not found there have null company fields.

## The post-call playbook (READ THIS)

**The dataset is the deliverable. The inline JSON is a preview.**

After every successful call, do these four things in order:

1. **State the headline.** One sentence from `counts` + `by_community` + `by_company`, e.g. *"Sentiment toward Nexagon skewed negative — 188 negative vs 142 positive across 263 unique authors from 87 companies, heaviest in r/devops and the DevSecOps Slack; Acme Corp and Beta Inc employees are the most vocal critics."* If `truncated_to_limit` is true, **say so explicitly**.

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

Only re-run `community_messages_sentiment` when the user genuinely changes the inputs — different keywords, wider date range, different sentiment subject. Sampling more messages (raising `max_messages`) does require a new call; tell the user explicitly.

## Reading the counts honestly

- `irrelevant` ≠ noise to hide. Report it: *"...86 messages mentioned Nexagon but didn't express an opinion about it."*
- `error` rows are Vertex failures. If > ~5% of total, mention it as a caveat.
- `unique_senders_with_linkedin` is the people reach number — how many authors you can follow up with.
- `unique_companies_resolved` tells you how many employers are represented. A high ratio of resolved companies means the `by_company` breakdown is reliable; a low ratio means many senders weren't in dataspring.
- `total_matched > total_scored` means you sampled. **Always disclose the sample.**

## Hard rules

- Always offer `download_dataset` after a successful call.
- When `truncated_to_limit` is true, **lead with the sampling caveat** before quoting numbers.
- For drill-downs, use `query_datasets` — never re-run for slicing.
- Don't quote `message_text` as gospel — it's truncated to 500 chars. Tell the user if they want the full text of a specific message it isn't available.
- Company fields are null for senders not found in dataspring. Don't claim company-level insight for messages where `company_name` is null.

## Common pitfalls

- **Stopping at the inline counts.** The user will ask follow-ups. Surface the dataset_id.
- **Re-running for "show me only negatives".** Wasteful. Use `query_datasets`.
- **Using a vague `sentiment_subject` like `"Nexagon"`.** The aspect framing is what makes this worth the LLM cost.
- **Forgetting date math.** "Last 3 months" → convert before calling.
- **Treating `top_positive`/`top_negative` as exhaustive.** They are 5 exemplars sorted by confidence.
- **Ignoring null company fields.** `unique_companies_resolved` < `unique_senders_with_linkedin` means some senders weren't resolved — the by_company breakdown is a subset, not the full picture.
- **Passing a bare company name to `exclude_companies`.** Name matching against dataspring is unreliable. Always resolve via `match_company` first and pass the LinkedIn URL. Passing a name will silently exclude nobody.

## Worked examples

### "What's the community saying about Nexagon lately?"

```python
community_messages_sentiment(
    keywords=["Nexagon"],
    sentiment_subject="Positive or negative experience with Nexagon",
    date_from="<today minus 90d>",
    date_to="<today>",
    exclude_companies=["Nexagon", "nexagon.com"],  # strip insider voices
)
```

Then:
1. *"Across the last 3 months, sentiment toward Nexagon skewed negative — 188 negative vs 142 positive across 263 unique authors from 87 companies, based on the latest 500 of 2,412 matching messages. Negative discussion concentrated in r/devops and the DevSecOps Slack; employees at Acme Corp (31 negative) and Beta Inc (22 negative) are the most vocal critics."*
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
    keyword_mode="all",
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

Two **separate** calls (different keywords, different subject framing), then narrate both headlines side by side and offer both download links.

## What this skill does NOT do

- It does not look up sentiment **about a specific person**. The authors are returned; the targets are the keywords.
- It does not query a CRM. Output is community messages, not pipeline/opportunity data.
- It does not produce a customer-facing PDF or HTML report — pair it with `docx` or `pdf` skills if needed.
- It does not enrich the returned LinkedIn URLs with emails/phones. Pipe `linkedin_url` values into `contact_data_enrichment` if the user asks to reach out.
