# Pre-delivery Checklist — Competitor Report

The agent must explicitly verify every item before presenting the file.
This is non-optional. The brief is client-grade; failures here are
expensive.

Run through the list in order. If any item fails, fix it before
proceeding.

---

## Structural integrity

- [ ] **Cover page has no `.act` class** (`<div class="page cover">`,
      not `<div class="page act">`)
- [ ] **Every other page has `class="page act"`** to force its own
      page break
- [ ] **Page numbers run sequentially** `02 / N` through `N / N`; cover
      has no footer
- [ ] **Page denominators all match** (every footer says `{i} / {N}`
      for the same `N`)
- [ ] **No orphaned section title mid-page** (verify by opening the
      PDF and scanning each transition)
- [ ] **WeasyPrint render succeeded** with no errors
- [ ] **No giant whitespace flood** (a sign that `.page` is fighting
      `@page` margins - check the CSS overrides)

---

## Content integrity

- [ ] **All quote text is verbatim** - no paraphrasing of any
      `message_text` field
- [ ] **Every quoted author has a LinkedIn handle attached**
- [ ] **Unresolved rows shown muted, not hidden** (`opacity: 0.65`
      on those rows)
- [ ] **No named accounts in summary stats or strategic-read callouts**
      - named accounts allowed only in the cover, the exhibit, and the
      evidence wall
- [ ] **No revenue estimates / dollar amounts** anywhere in the brief
- [ ] **No GTM recommendations or "you should do X" language** - the
      brief is analytical only

---

## Language and tone

- [ ] **No em dashes (`—`)** outside verbatim evidence quotes - always
      `-`
- [ ] **No specific channel names** (LinkedIn, Twitter, individual
      Slack community names) anywhere in customer-facing copy. Use
      "owned brand surfaces" and "external developer communities".
- [ ] **No internal tool names** (Snowflake, Phoenix, MCP, query_onfire,
      Onfire dataset IDs) in customer-facing copy. Use "market
      intelligence", "intent signals", "CRM records".
- [ ] **Action titles are full sentences**, not noun phrases. Every
      page's `<h2 class="action-title">` must have a subject + verb.
- [ ] **Every page closes with a `.sowhat` synthesis block** (or a
      similarly-shaped callout)

---

## Numeric conventions

- [ ] **Percentages used in opinion / sentiment cuts**, not raw counts.
      The headline "92% positive share" reads cleaner than "134 of 145
      opinionated".
- [ ] **Owned-vs-external sentiment infographic has NO numbers** -
      just visual balance and qualitative labels ("Skews
      overwhelmingly positive" / "Skews sharply negative")
- [ ] **Raw counts allowed** in stat-card heroes (e.g. "63 net-new
      accounts"), hire counts, and signal counts - but not in
      opinion / sentiment breakdowns

---

## Time-window discipline

- [ ] **Quarter window is strictly enforced** - every signal outside
      the window is excluded or explicitly flagged
- [ ] **No GitHub time-trend claims** - the data is snapshot-only.
      The Complication 2C action sub explicitly says so, and the
      Assumptions and Definitions block reiterates.
- [ ] **Acquisition window labelled** as `last 12 months ({rolling_12mo_start} - {q_end})`
- [ ] **Mid-month current column flagged with asterisk + footnote**
      in the monthly stacked bar (if the brief includes the current
      partial month)

---

## Vendor-trust events conditional

- [ ] **Trust-events page included if-and-only-if** 3+ distinct
      dimensions detected (vendor ethics + product quality +
      commercial trust + operational reliability + general
      trustworthiness)
- [ ] If included: **trust-event amplification is consistent** across
      the exec summary callout, finding #01, the Complication 3 page,
      and the evidence wall
- [ ] If omitted: **page 10 is removed** and pages 11-13 renumber to
      10-12; no dangling references to "vendor-trust events" anywhere
      in the brief

---

## Back-matter integrity

- [ ] **Section heading reads "Assumptions and definitions"** -
      NOT "Sources and methodology"
- [ ] **No record counts in the assumptions block** ("700 messages
      scored", "135 of 185 authors resolved" etc. - these belong in
      analysis sections, not the back matter)
- [ ] **Every term used in the brief has a definition entry** -
      reader should never wonder what "Net-new mentioner account" or
      "Owned brand surface" means

---

## Exhibit A integrity

- [ ] **Exhibit A is on the last page** (page 13, or page 12 if
      vendor-trust omitted)
- [ ] **Firmographic strip has all 6 cards** (HQ / Founded / Employees /
      Revenue band / Ownership / Last raise) - any missing data
      replaced with "Not disclosed" or "n/a", not blank
- [ ] **Bottom-line read at the end** ties the quarter's findings back
      to the baseline (so the brief reads as one argument across all
      13 pages, not two disconnected halves)

---

## File handling

- [ ] **HTML saved** to `outputs/{competitor_lc}-brief.html`
- [ ] **PDF rendered** to `outputs/{competitor_lc}-brief.pdf`
- [ ] **Both files presented** via `mcp__cowork__present_files`
- [ ] **One-sentence summary** in the final chat response (NOT a recap
      of the brief contents - the reader can read the brief)

---

## Final smell test

- [ ] **Read the action titles top-to-bottom** - they should form a
      coherent argument by themselves
- [ ] **Read the `.sowhat` blocks top-to-bottom** - they should
      reinforce the argument with cross-section connections
- [ ] **The brief tells one story**, not 13 isolated sections

If reading just the action titles + sowhats doesn't deliver the
brief's lead finding, the structure has drifted. Fix before delivery.
