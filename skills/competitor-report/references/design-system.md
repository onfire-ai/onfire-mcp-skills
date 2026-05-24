# Design System — Competitor Report

The brief is a **13-page A4 PDF**, rendered from HTML via WeasyPrint.
The design idiom is consulting-firm: serif headings, sans-serif body,
restrained palette, lots of whitespace, action titles in the McKinsey
style.

This file documents the design tokens, the page scaffold, and the
per-section layouts.

---

## Design tokens

```css
:root {
  /* Ink scale */
  --ink:    #0B1F33;   /* primary text */
  --ink-2:  #3A4D63;   /* secondary text */
  --ink-3:  #6B7E94;   /* tertiary / muted text */

  /* Surface scale */
  --line:   #E5EAF0;
  --line-2: #CFD7E1;
  --soft:   #F7F9FC;
  --paper:  #FFFFFF;

  /* Semantic colors */
  --pos:        #1F7A4A;   /* positive / green */
  --pos-soft:   #EEF6F0;
  --neg:        #B22A1F;   /* negative / red */
  --neg-soft:   #FBEFED;
  --warn:       #C8853D;
  --warn-soft:  #FDF6EE;
  --neutral:    #94A3B8;   /* neutrals in stacked bars */
  --accent-1:   #5A8FA8;   /* second accent (IT services blue) */
  --accent-2:   #806B91;   /* third accent (media purple) */
}
```

---

## Typography

Two font families, both loaded from Google Fonts:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+Pro:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
```

| Use | Family | Weight |
|---|---|---|
| Body text, captions, labels | Inter | 400 / 500 / 600 |
| Page eyebrows, micro-labels (all-caps) | Inter | 600-700 + `letter-spacing: 0.08em` |
| `.action-title` (the McKinsey title) | Source Serif Pro | 700 |
| Hero numbers (`.num.serif`) | Source Serif Pro | 700 |

Default body sizing: **9pt** line-height **1.5**. Action titles are
**16-18pt**. Hero numbers are **24-32pt**.

---

## Page scaffold

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{Competitor} - Competitor Intelligence Brief</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+Pro:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    /* Reset */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    /* @page rule for WeasyPrint */
    @page {
      size: A4;
      margin: 18mm;
    }

    /* Body */
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 9pt;
      line-height: 1.5;
      color: var(--ink);
      background: var(--paper);
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    /* Page block */
    .page {
      position: relative;
      padding: 0;
    }
    @media print {
      .page {
        width: auto !important;
        min-height: auto !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        page-break-after: auto;
        page-break-before: auto;
        page-break-inside: auto;
      }
      .page.act { page-break-before: always; }
    }

    /* Running head + foot */
    .running-head {
      display: flex;
      justify-content: space-between;
      font-size: 7pt;
      color: var(--ink-3);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      font-weight: 600;
      border-bottom: 0.5pt solid var(--line);
      padding-bottom: 4pt;
      margin-bottom: 14pt;
    }
    .running-head .mark { color: var(--ink); display: flex; align-items: center; gap: 4pt; }
    .running-head .dot { display: inline-block; width: 5pt; height: 5pt; border-radius: 50%; background: var(--ink); }
    .running-foot {
      position: absolute;
      bottom: 8mm;
      left: 18mm;
      right: 18mm;
      display: flex;
      justify-content: space-between;
      font-size: 7pt;
      color: var(--ink-3);
      border-top: 0.5pt solid var(--line);
      padding-top: 4pt;
    }
    .running-foot .pn { font-feature-settings: 'tnum'; }
    @media print {
      .running-head, .running-foot { display: none !important; }
    }

    /* Eyebrows + titles */
    .eyebrow {
      font-size: 7pt;
      color: var(--ink);
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 6pt;
    }
    .action-title {
      font-family: 'Source Serif Pro', Georgia, serif;
      font-size: 17pt;
      font-weight: 700;
      color: var(--ink);
      line-height: 1.25;
      margin-bottom: 10pt;
    }
    .action-sub {
      font-size: 9pt;
      color: var(--ink-2);
      line-height: 1.55;
      max-width: 165mm;
    }

    /* Stats */
    .stat .lbl {
      font-size: 7pt;
      color: var(--ink-3);
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .stat .num {
      font-family: 'Source Serif Pro', Georgia, serif;
      font-size: 24pt;
      font-weight: 700;
      color: var(--ink);
      line-height: 1;
      margin-top: 4pt;
    }
    .stat .num.pos { color: var(--pos); }
    .stat .num.neg { color: var(--neg); }
    .stat .sub {
      font-size: 7.5pt;
      color: var(--ink-2);
      margin-top: 6pt;
      line-height: 1.5;
    }

    /* Cards */
    .card {
      border: 0.5pt solid var(--line);
      border-radius: 3pt;
      padding: 10pt 12pt;
      background: var(--paper);
    }
    .card.soft {
      background: var(--soft);
      border-color: var(--line);
    }

    /* Grids */
    .grid { display: grid; gap: 5mm; }
    .grid.cols-2 { grid-template-columns: 1fr 1fr; }
    .grid.cols-3 { grid-template-columns: 1fr 1fr 1fr; }
    .grid.cols-6 { grid-template-columns: repeat(6, 1fr); }

    /* Exhibit titles */
    .exh-title {
      font-size: 8.5pt;
      font-weight: 600;
      color: var(--ink);
      margin-bottom: 4pt;
    }
    .exh-sub {
      font-size: 7.5pt;
      color: var(--ink-3);
      line-height: 1.5;
    }

    /* Tables */
    .tbl-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 8pt; }
    thead th {
      text-align: left;
      font-weight: 600;
      color: var(--ink-3);
      font-size: 7pt;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-bottom: 0.5pt solid var(--line-2);
      padding: 4pt 6pt;
    }
    tbody td {
      border-bottom: 0.5pt solid var(--line);
      padding: 4pt 6pt;
      color: var(--ink-2);
      vertical-align: top;
    }

    /* Callouts */
    .callout {
      padding: 10pt 14pt;
      border-radius: 3pt;
      background: var(--soft);
      border: 0.5pt solid var(--line);
    }
    .callout.neg {
      background: var(--neg-soft);
      border-color: var(--neg);
    }

    /* Sowhat (synthesis blocks) */
    .sowhat {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 8pt;
      padding: 10pt 14pt;
      background: var(--warn-soft);
      border: 0.5pt solid var(--warn);
      border-radius: 3pt;
      font-size: 8.5pt;
      line-height: 1.55;
      color: var(--ink-2);
    }
    .sowhat::before {
      content: '➤';
      font-size: 11pt;
      color: var(--warn);
      line-height: 1;
    }

    /* Evidence quote rows */
    .ev {
      padding: 8pt 12pt;
      border-radius: 3pt;
      margin-bottom: 6pt;
    }
    .ev.pos { background: var(--pos-soft); border-left: 2pt solid var(--pos); }
    .ev.neg { background: var(--neg-soft); border-left: 2pt solid var(--neg); }
    .ev .body { font-size: 8pt; color: var(--ink); line-height: 1.55; display: block; margin-bottom: 4pt; font-style: italic; }
    .ev .meta { font-size: 7pt; color: var(--ink-3); }
    .ev .lnk { color: var(--ink-3); }

    /* Pills */
    .pill {
      display: inline-block;
      font-size: 6.5pt;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 1pt 5pt;
      border-radius: 2pt;
      vertical-align: middle;
    }
    .pill.pos { background: var(--pos-soft); color: var(--pos); }
    .pill.neg { background: var(--neg-soft); color: var(--neg); }
    .pill.warn { background: var(--warn-soft); color: var(--warn); }
    .pill.line { background: var(--soft); color: var(--ink-3); border: 0.5pt solid var(--line-2); }

    /* Dividers */
    .divider { height: 0; border-bottom: 0.5pt solid var(--line); }
  </style>
</head>
<body>
  <!-- 13 pages here -->
</body>
</html>
```

---

## Per-section layouts

### Page 1 - Cover

- No `running-foot` (the cover has no page number)
- Big serif competitor name
- "Competitor Intelligence Brief" eyebrow
- "Prepared for {tenant}" line
- Date + quarter label
- One-line "Q-window: {q_start} - {q_end}" footnote

### Page 2 - Executive summary (`.act`)

If 3+ vendor-trust dimensions detected, this page **opens with a red
callout** containing 3 cards (one per trust-event), then drops into the
three hero stats and the five numbered findings.

If fewer than 3 trust dimensions, no red callout - go straight to the
hero stats.

- Action title: pyramid-principle one-sentence lead with the
  highest-priority finding
- 3-card vendor-trust callout (if conditional pass)
- 3-card hero stat row: e.g. "Q headcount %", "External sentiment
  ratio", "Open Q-posted roles"
- 5-item numbered findings list, finding #01 = the lead finding from
  the action title

### Pages 3 + 4 - Complication 1A (`.act` each)

**Page 3 - by seniority:**

- 3-card hero row: OUT count / IN count / Net title delta
- 2-column ledger: Leadership (VP / Director / Manager+) | Department (IC)
  - Each row: direction arrow (▼ OUT / ▲ IN) + month + title + one-line note

**Page 4 - by movement type:**

- 3-card "Movement type" row:
  - **Paired swaps** (neutral, soft) - old → new in same function
  - **Departed-no-backfill** (amber, warn) - Q+1 hiring watch
  - **Net-new functions** (green, pos) - strategic bets
- 3-card "Strategic threads" row - the synthesis (e.g.
  "Public-sector GTM broadened", "Top-layer AI build", etc.)
- Sowhat callout - bottom-line synthesis

### Page 5 - Complication 1B (`.act`)

- Headcount % bar chart (12 months) on the left
- Q-hire continent breakdown on the right
- Sowhat - hiring tilt synthesis

### Page 6 - Complication 1C (`.act`)

- Open job postings, grouped by hiring manager
- Show: title, hiring manager name + LinkedIn handle, location,
  posting date
- Sowhat - what the open roles say about Q+1 priorities

### Page 7 - Complication 2A (`.act`)

The customer-acquisition motion page. Conventions learned from Sonatype:

- 3 hero cards:
  - Net-new accounts (12 months)
  - Q net-new alone
  - Enterprise wins count (1,000+ FTE) - no named accounts here
- **Monthly stacked bar SVG** (~700x260 viewBox):
  - 12 columns, one per month
  - 5 industry stacks: Software / IT services / Public+Healthcare+Cyber+Financial / Media / Other
  - Total label at top of each column
  - Q-window bracketed with "Q{N} 20YY - {N} NEW" caption
  - Mid-month current column flagged with asterisk + footnote
- 2-card row below: size breakdown + region breakdown (with bars + %)
- Sowhat - banks-are-existing-base vs software-is-the-acquisition synthesis

### Page 8 - Complication 2B (`.act`)

The sentiment split page. Conventions:

- 3 hero stats: owned-channel positive share, external positive share,
  negative concentration (qualitative, e.g. "Java / Maven")
- 2-column card: "By author's continent" + "By author's employer size"
  - Each row: label + percentage triple on top, **full-width tall bar**
    below (height 10-11pt active, 9pt muted)
  - Color legend in card header (Positive / Neutral / Negative swatches)
  - Unresolved row at bottom, muted via `opacity: 0.65`
- 2-card "Where the volume sits, by community" infographic:
  - Owned brand surfaces card (green) - "Skews overwhelmingly positive"
  - External developer communities card (red) - "Skews sharply negative"
  - Single horizontal positive-vs-negative bar each, NO numbers
- Negative-concentration callout
- Sowhat - owned-noisy vs external-loud-negative synthesis

### Page 9 - Complication 2C (`.act`)

GitHub footprint snapshot. Conventions:

- 3 stat cards: events tracked / countries / federal+enterprise engagers
- 2-column: top countries bar + notable engagers table
- Sowhat - footprint shape, NEVER a trend claim
- Methodology caveat embedded in `.action-sub`: "the date field is
  collection-date, not event-date, so this is a footprint snapshot
  not a time series"

### Page 10 - Complication 3 (`.act`) - CONDITIONAL

Only included if 3+ vendor-trust dimensions detected. Three-card layout
where each card explains one trust dimension:

- "Each one targets a different trust dimension"
- "Two are amplified by external voices"
- "External validation"

### Page 11 - Evidence wall (`.act`)

Verbatim quotes only. Layout:

- Eyebrow "Q evidence - the voices saying it"
- For each trust event (if applicable):
  - Mini-eyebrow with event name
  - `.ev.neg` block with the verbatim quote (italics) + author LinkedIn
- "For balance - the strongest positive voices" section
  - `.ev.pos` blocks - 2-3 verbatim positive quotes

### Page 12 - Assumptions and definitions (`.act`)

- Heading: "Assumptions and definitions" (NOT "Sources and
  methodology")
- 12-15 definitional bullets - what each term in the brief means
- Subsection: "What this brief does not cover"
- Subsection: "Refresh cadence"

See `references/analysis-patterns.md` for the canonical bullet list.

### Page 13 - Exhibit A · Company reference card (`.act`)

- Eyebrow "Exhibit A - Company reference card"
- Action title: short positioning sentence
- 6-card firmographic strip: HQ / Founded / Employees / Revenue band /
  Ownership / Last raise
- 2-column:
  - Left: product lineup table + "Who they sell to" paragraph
  - Right: "How they position" + "Public signals" + "Reference timeline"
- Sowhat - bottom-line read tying the quarter back to the baseline

---

## SVG patterns

### Stacked bar (monthly acquisition)

`viewBox="0 0 700 260"`, 12 columns, ~52px column pitch starting at
x=60, bar width 36, gap 16. Y axis 0 to max (typically 9 for the
12-month rollup). Each column from bottom up:

1. `<rect>` for Software stack (green `#1F7A4A`)
2. `<rect>` stacked above for IT services (`#5A8FA8`)
3. `<rect>` stacked above for Regulated bucket (`#C8853D`)
4. `<rect>` stacked above for Media (`#806B91`)
5. `<rect>` stacked above for Other (`#94A3B8`)
6. `<text>` total above the stack
7. `<text>` month label below the baseline

Q-window: add a horizontal `<line>` at y=246 spanning the in-quarter
columns, with a `<text>` "Q{N} 20YY - {N} NEW" centered above it.

### Horizontal bar with full width

For sentiment rows and acquisition size/region:

```html
<div style="margin-bottom: 10pt">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3pt">
    <span style="font-size:8.5pt;font-weight:600;color:var(--ink)">{label}</span>
    <span style="font-size:7.5pt;color:var(--ink-2);font-feature-settings:'tnum'">{pct1}% / {pct2}% / {pct3}%</span>
  </div>
  <div style="display:flex;height:11pt;border-radius:2pt;overflow:hidden">
    <div style="background:#1F7A4A;width:{pos_pct}%"></div>
    <div style="background:#94A3B8;width:{neu_pct}%"></div>
    <div style="background:#B22A1F;width:{neg_pct}%"></div>
  </div>
</div>
```

Avoid the 3-column-grid layout (label | bar | number). The bar gets
squeezed and reads as a sliver. Always stack vertically: label+number
on top, full-width bar below.

---

## Forbidden patterns

- **No em dashes** (`—`) outside verbatim quotes. Always `-`.
- **No internal tool names** (Snowflake, Phoenix, MCP, query_onfire,
  Onfire dataset IDs) in customer-facing copy. Use "market intelligence",
  "intent signals", "CRM records".
- **No specific channel names** (LinkedIn, Twitter, individual Slack
  community names) - use "owned brand surfaces" and "external developer
  communities".
- **No GitHub time-trend claims** - the data is snapshot-only.
- **No revenue estimates or dollar amounts** anywhere in the brief.
- **No GTM recommendations** - analytical only.
- **No named accounts in summary stats or strategic-read callouts** -
  named accounts allowed only in the cover, the exhibit, and the
  evidence wall.
- **No raw counts in opinion / sentiment cuts** - use percentages.

---

## Asset naming

Outputs are saved as:
- `{competitor_lc}-brief.html`
- `{competitor_lc}-brief.pdf`

E.g. `sonatype-brief.html`, `snyk-brief.html`.

Save first to the cowork outputs folder, then present via
`mcp__cowork__present_files`.
