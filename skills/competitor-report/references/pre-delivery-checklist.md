# Pre-delivery Checklist — Competitor Report

The agent must explicitly verify every item before presenting the file.
This is non-optional. The brief is client-grade; failures here are
expensive.

Run through the list in order. If any item fails, fix it before
proceeding.

---

## Self-validation pass (triple-check before anything else)

**The single highest-frequency defect class is the brief contradicting
itself.** Catch it here.

- [ ] **Every bar group sums to its stated total.** Compute by hand.
      Page 2 footprint = live HC. Page 5 Joiner bars = external-hires
      hero. Page 5 Leaver bars = real-departures hero. Page 6 columns
      sum to page-5 heroes. Page 7 by-X each sum to captured postings.
      Page 8 monthly cohort sums to N. Page 9 sentiment rows sum to
      EXACTLY 100% (no 99 / 101). Page 10 country bars sum to engager-
      rows headline.
- [ ] **Every "X%" claim recomputed against the actual data on the
      same page.** Do the division. Do not transcribe.
- [ ] **Page 5 Net headcount hero = chart endpoints.** `end_HC −
      start_HC` from the chart, not the movement math.
- [ ] **Same number cited on multiple pages is identical everywhere.**
      Live headcount appears on page 2, page 5 chart, and page 14
      Exhibit A — all three say the same number. The 49 / 7 / Net
      triple is consistent between page 2 stat sub and page 5 heroes.
      The 87 / 6 / 81 triple is consistent across page 2 hero, page 2
      finding, and page 8 hero.
- [ ] **Cross-page references point to the right page.** Every "see
      page N" / "on page N" / "evidence wall on page N" is verified
      after every conditional-page insertion or removal.
- [ ] **Roles and geo claims in narrative match the underlying data.**
      No "sales role attended" when no attendee is in sales. No "US
      east-coast" when one attendee is in Colorado. No "cited in 4+
      postings" when the postings table contains zero matches.
- [ ] **Page count fit.** Rendered PDF physical page count == logical
      section count. If not, at least one section overflows. Use the
      WeasyPrint footer-duplicate diagnostic to identify overflowing
      sections; trim until physical == logical.
- [ ] **Final scan as a skeptical outsider.** Read every action title
      top-to-bottom, then every sowhat. If anything reads odd, fix it
      before delivery.

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
- [ ] **No evidence-wall quote is from the target competitor account.**
      Scan every `.ev.neg` and `.ev.pos` on the evidence-wall page
      (page 12 in the default layout; one less if vendor-trust is
      omitted; one less if event-attendance is also omitted) — reject
      any quote whose speaker's current employer is the competitor.
- [ ] **No evidence-wall quote is from the prepared-for tenant.** Same
      scan - reject any whose speaker works for the tenant. Analytical
      mentions of either company on other pages are permitted; the
      rule is scoped to verbatim quotes on the evidence wall.
- [ ] **No mention of the prepared-for tenant anywhere in customer-
      facing copy.** Grep the assembled HTML for the tenant's brand
      name; the only allowed occurrence is the cover line when
      `brand_cover: true` was set, otherwise nowhere. When a tenant CEO
      or employee surfaces in events, use a category descriptor ("a
      category-incumbent CEO").
- [ ] **Unresolved rows shown muted, not hidden** (`opacity: 0.65`
      on those rows) - unless caller set `hide_unresolved: true`
- [ ] **No named accounts in summary stats or strategic-read callouts**
      - named accounts allowed only in the cover, the exhibit, the
      evidence wall, and the joiner / leaver detail cards on
      Complication 1B
- [ ] **No revenue estimates / dollar amounts** anywhere in the brief
- [ ] **No GTM recommendations or "you should do X" language** - the
      brief is analytical only
- [ ] **Departed-no-backfill detail table** on page 4 is present
      whenever Phase 2.1 detected any departed-no-backfill events. For
      each departed title it answers: (a) does any current employee
      hold the function under a different title (via Phase 1.13a
      SUMMARY scan, not just title-keyword), (b) is there an open
      posting (via `ds_open_jobs_active`), (c) is the function lapsed?
      Default to characterising as "parallel hold" unless both 13a and
      13b return empty.

---

## Language and tone

- [ ] **No em dashes (`—`)** outside verbatim evidence quotes - always
      `-`
- [ ] **No specific channel names** (LinkedIn, Twitter, individual
      Slack community names) anywhere in customer-facing copy. Use
      "owned brand surfaces" and "external developer communities".
- [ ] **No internal tool names** (Snowflake, Phoenix, MCP, ask_onfire,
      QueryIR, entity names, Onfire dataset IDs) in customer-facing copy.
      Use "market intelligence", "intent signals", "CRM records".
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

- [ ] **Window is strictly enforced** - every signal outside the
      `window_start` / `window_end` range is excluded or explicitly
      flagged.
- [ ] **Window mode is consistent everywhere.** Page footers, running
      headers, action titles, the Assumptions block, the cover and the
      sowhats all reflect the chosen mode (`Q1 2026` if quarter mode,
      `12-month view` / `12 months ending Mar 2026` if 12_month mode).
      No leftover `Q1` references when running in 12-month mode.
- [ ] **No GitHub time-trend claims** - the data is snapshot-only.
      The Complication 2C action sub explicitly says so, and the
      Assumptions and Definitions block reiterates.
- [ ] **Acquisition window labelled** as `last 12 months ({rolling_12mo_start} - {q_end})`
      regardless of brief window mode - the acquisition motion is
      always 12-month trailing
- [ ] **Mid-month current column flagged with asterisk + footnote**
      in the monthly stacked bar (if the brief includes the current
      partial month)
- [ ] **`INSIGHT_VALUE` casing checked.** If Query 07 returns zero
      rows, verify the competitor's canonical capitalisation in
      `ONFIRE.INSIGHTS_2_EVIDENCES` (e.g. `PackMint` not
      `Packmint`) before concluding "no acquisition motion data".
      Use `ILIKE`, not exact-match equality.

---

## Vendor-trust events conditional

- [ ] **Trust-events page included if-and-only-if** 3+ distinct
      dimensions detected (vendor ethics + product quality +
      commercial trust + operational reliability + general
      trustworthiness)
- [ ] If included: **trust-event amplification is consistent** across
      the exec summary callout, finding #01, the Complication 3 page,
      and the evidence wall
- [ ] If omitted: **the vendor-trust page is removed** and all
      downstream pages renumber down by 1. Every cross-reference of
      the form "see page N" / "evidence wall on page N" must be
      audited and corrected. No dangling references to "vendor-trust
      events" anywhere in the brief.

---

## Complication 1B split conditional (page 5b)

- [ ] **1B-split page included if-and-only-if** all three thresholds
      hit: ≥ 15 joiner stints AND ≥ 4 distinct title_role functions
      represented AND ≥ 3 internal promotions detected. Otherwise the
      function-bars and promotion-grouping content folds back into
      page 5.
- [ ] If included: **page numbering bumps** for every page from "Open
      job postings" onward; brief renders 14 pages.
- [ ] **Function bar rows have explicit % triples** (joiners, leavers,
      net) and the only-flat function carries a `FLAT` pill.
- [ ] **Internal promotions grouped by destination function**, not by
      month / cluster.

---

## People-movement reconciliation

- [ ] **Pages 3 and 5 source the same dataset** (`ds_employees`
      returned by `get_company_headcount`); each page's action-sub
      states the unit (title strings on page 3, person-stints on
      pages 5/5b) so the reader does not try to reconcile manually.
- [ ] **Page 5 Net headcount card = snapshot delta from the chart.**
      The Net hero card MUST equal `last_month_HC − first_month_HC`
      shown in the chart on the same page, NOT `external_hires −
      real_departures`. If movement math and snapshot delta diverge by
      more than ±3, surface the gap in the action title ("the N-person
      gap reflects LinkedIn-profile lag") rather than hiding it.
- [ ] **Page 5 Joiners card region/seniority/function bars sum to the
      external-hires hero number.** No internal-promotion stints in
      those bars. The card carries a small grey subtitle stating "{N}
      external hires only. Internal promotions sit on page 6."
- [ ] **Page 5 Leavers card bars sum to the real-departures hero
      number.** No internal-promotion artifact stints in those bars.
- [ ] **Page 6 department chart columns reconcile:** the external
      column sums to the page-5 external-hires hero, the promotions
      column sums to the promotions card total below, the departures
      column sums to the page-5 real-departures hero.
- [ ] **Promotions detection** used the same-person same-stint pairing
      (b.start_date >= a.end_date for the same `person_linkedin_url`).
      Don't double-count promotions in both joiner and leaver hero
      stats - they belong in their own bucket.

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

- [ ] **Exhibit A is the second-to-last page**, with Assumptions as
      the last page. The brief closes on the definitional appendix,
      not the firmographic card. Exact page numbers shift when
      conditional pages (event-attendance, vendor-trust, 1B-split) are
      included or omitted — the rule is the relative order, not a
      fixed page number.
- [ ] **Headcount in Exhibit A matches the live snapshot used
      everywhere else** (single number, no "~150 / 140-person offsite"
      mixing). The Employees card says exactly the same number that
      appears on page 2 Geographic footprint, page 5 chart endpoint,
      and any action-title headcount mention.
- [ ] **Exhibit A sowhat carries no unsupported claims.** If the
      sowhat says "cited explicitly in N postings", page 7's postings
      table must contain those citations. If it doesn't, trim the
      parenthetical instead of leaving an overclaim.
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
- [ ] **The brief tells one story**, not N isolated sections

If reading just the action titles + sowhats doesn't deliver the
brief's lead finding, the structure has drifted. Fix before delivery.
