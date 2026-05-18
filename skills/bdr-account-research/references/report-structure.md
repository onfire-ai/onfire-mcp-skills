# Report Structure — A4 HTML Template

Full layout specification for the BDR account research report.
This is a **customer-facing, print-ready A4 HTML file** — not a widget,
not a web dashboard.

The template is **tenant-agnostic**. Brand color, display name, and use
case palette flow in from the `bdr_account_research` envelope at render
time. Nothing in this file is hardcoded to a specific tenant.

---

## Core design principles

- **Onfire palette, used sparingly.** The report's visual identity is
  Onfire's, not the tenant's: navy (`--brand`) anchors the header bar,
  section eyebrows, score fills, and footer mark; purple (`--accent`)
  is reserved for one or two single-word highlights per page. Everywhere
  else is cool neutral. Tenant brand colors are NOT used as theme
  colors — only the tenant display name + logo appear as content inside
  the header bar.
- **A4 print layout.** 174mm body width, `@page` block set, all sizes
  in `pt`, every `.card` has `break-inside: avoid`.
- **Self-contained.** No external dependencies. No Google Fonts CDN.
  No external images. System fonts only. Logo as base64 data URI.
- **Background graphics preserved for PDF.** `print-color-adjust: exact`
  in `@media print` is non-optional — without it, every colored tint
  disappears on the printed page.
- **Customer-facing copy.** Zero mentions of internal tools (see
  "Forbidden internal tool names" below). Neutral abstractions only.
- **No em dashes.** Use a regular hyphen `-` everywhere. Em dash `—`
  is forbidden outside verbatim evidence quotes.
- **"Account Research"** — never "Account Brief".
- **LinkedIn-linked company name.** Header company name is always an
  `<a>` with a 1.5pt dotted underline.
- **Employee stat clarity.** Always explain headcount with a
  parenthetical breakdown when there's an acquisition or notable split.
- **Key contacts on new pages.** Each use-case contacts block carries
  `break-before: page`.
- **No break mid-card.** Every `.card` carries `break-inside: avoid`.
- **No buying committee or cold opens section.**
- **Footer is logo + company + label + date.** Nothing else; no
  sources line.
- **Signal messages quoted verbatim.** Never paraphrase `message_text`.

---

## Reading the runtime contract

Before rendering, pull these values from the envelope:

| Render value | Source | Fallback |
|---|---|---|
| Tenant display name | `tenant_config.brand.display_name` | `tenant_config.tenant_id`, title-cased |
| Tenant logo (base64) | `tenant_config.brand.logo_data_uri` | omit logo, use text wordmark only |
| Section order | `render_spec.section_order` | the order in this file |
| Use case palette | `render_spec.use_case_palette` | required — never invent |
| Page setup | `render_spec.page_setup` | the CSS block below |
| Hard rules | `render_spec.hard_rules` | the list below |

**The report is Onfire-branded, not tenant-branded.** The color palette,
header-bar background, eyebrows, and score fills come from the fixed
Onfire palette baked into the CSS below — they do not vary per tenant.
The tenant display name and (optional) tenant logo still appear in the
header bar / footer so the BDR reading the report sees their own org's
name, but they are content, not theme. Ignore any
`tenant_config.brand.primary` value if present; it's legacy and no
longer drives anything.

---

## Full CSS block

```css
/* Reset */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* Design tokens — Onfire palette (fixed) + cool neutrals + semantic intents.
   Brand color does NOT vary per tenant; the report's visual identity is
   Onfire's. */
:root {
  /* Onfire brand — fixed. Do not inject tenant colors here. */
  --brand:        #0A2540;        /* Onfire navy — header bar, primary text */
  --brand-dark:   #051628;        /* deepest navy — hover/active accents */
  --brand-mid:    #6B8FA8;        /* mid slate — quote borders, subdued fills */
  --brand-light:  #DCEFF5;        /* cyan-tint — soft section bands / hero fills */
  --accent:       #7C5CFF;        /* Onfire purple — single-word highlights, key callouts */
  --accent-light: #ECE7FF;        /* purple tint — accent fills, no-flood */

  /* Cool neutrals — shifted from the warm Helvetica palette to a slightly
     cyan-leaning off-white. Keeps the report from looking like a print
     mailer and matches the Onfire web aesthetic. */
  --bg:        #F4F8FA;
  --surface:   #FFFFFF;
  --border:    #E2E8EE;
  --border-md: #C5D0DA;
  --text:      #0A2540;
  --muted:     #4A5B6D;
  --faint:     #94A3B8;

  /* Semantic intents — used for Why-Now alerts, not for branding */
  --hi-bg:    #FBEAE9; --hi-text:    #8C1B15;  /* danger / red flag */
  --med-bg:   #FAEEDA; --med-text:   #7A4A0A;  /* warn / amber */
  --low-bg:   #EEF1F4; --low-text:   #4A5B6D;  /* neutral / context */
  --ok-bg:    #E2F2E7; --ok-text:    #1E5C32;  /* success / green */
  --info-bg:  #ECE7FF; --info-text:  #3D2C99;  /* info / Onfire purple */

  /* Use case palette — injected dynamically from render_spec.use_case_palette
     One block per use case tag the orchestrator returned. Do not invent. */
  /* Example shape:
     --uc-<tag>-bg, --uc-<tag>-text, --uc-<tag>-bar  */
}

/* Page — A4 */
@page { size: A4; margin: 16mm 18mm 18mm 18mm; }
html  { font-size: 10pt; }
body  {
  /* SYSTEM FONTS ONLY — no Google Fonts CDN (file:// blocks it) */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
               Helvetica, Arial, sans-serif;
  background: #fff; color: var(--text);
  line-height: 1.55; width: 174mm; margin: 0 auto; padding: 0 0 10mm;
  font-feature-settings: "ss01", "cv11";  /* harmless on unsupported fonts */
}

/* Force background colors to print in PDF — REQUIRED */
@media print {
  * { -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      color-adjust: exact !important; }
}

/* Header bar — full-bleed across the page on PDF, contained on screen.
   Defined in the stylesheet (not inline) so screen-media overrides can
   actually reach it; inline-style specificity used to defeat the screen
   override, which made the bar clip off the visible viewport in
   browser previews. */
.header-bar {
  background: var(--brand);
  color: #fff;
  display: flex; align-items: center; justify-content: space-between;
  padding: 9pt 18mm;
  margin: 0 -18mm 10pt;   /* bleed past the 174mm body column on PDF */
}
.header-bar .wm { display: flex; align-items: center; gap: 8pt; }
.header-bar .wm-logo {
  width: 26pt; height: 26pt; border-radius: 3pt;
  background: #fff; padding: 2pt;
}
.header-bar .wm-name {
  font-size: 11pt; font-weight: 700; color: #fff; letter-spacing: -.01em;
}
.header-bar .wm-sub {
  font-size: 7.5pt; color: rgba(255,255,255,.78);
  margin-top: 1pt; letter-spacing: .02em;
}
.header-bar .meta {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 7pt; color: rgba(255,255,255,.7);
  text-align: right; line-height: 1.5;
}

/* Screen preview */
@media screen {
  html { background: #E2E8EE; font-size: 11px; }
  body { box-shadow: 0 2px 28px rgba(0,0,0,.15);
         padding: 0 0 20mm; margin: 20px auto; }
  /* On screen the body is centred in a viewport that's often narrower
     than the printable A4 width, so the PDF edge-bleed trick clips off
     the visible area. Contain the bar inside the body box instead. */
  .header-bar { margin: 0 0 10pt; padding-left: 12pt; padding-right: 12pt; }
}

/* Typography */
p      { font-size: 9pt; line-height: 1.65; margin-bottom: 3pt; }
p:last-child { margin-bottom: 0; }
strong { font-weight: 600; color: var(--text); }
a      { color: var(--brand); text-decoration: none; }
em     { font-style: italic; }

/* Section header — eyebrow + title + subtitle pattern */
.section-head { margin: 14pt 0 8pt; break-after: avoid; }
.section-eye  { font-size: 6.5pt; font-weight: 700; letter-spacing: .14em;
                text-transform: uppercase; color: var(--brand);
                margin-bottom: 2pt; }
.section-title { font-size: 13pt; font-weight: 700; letter-spacing: -.01em;
                 color: var(--text); margin-bottom: 2pt; }
.section-sub   { font-size: 8pt; color: var(--muted); line-height: 1.55; }

/* Hairline section divider used between major blocks */
hr.divider { border: none; border-top: .4pt solid var(--border-md);
             margin: 10pt 0 6pt; }

/* Labels, tags */
.lbl { display: block; font-size: 6.5pt; font-weight: 700; letter-spacing: .12em;
       text-transform: uppercase; color: var(--muted); margin-bottom: 4pt; }
.tag { display: inline-flex; align-items: center; font-size: 7pt; font-weight: 600;
       padding: 1.5pt 7pt; border-radius: 100pt; white-space: nowrap;
       line-height: 1.5; letter-spacing: .02em; }

/* Cards */
.card { background: var(--surface); border: .5pt solid var(--border);
        border-radius: 6pt; padding: 10pt 12pt; margin-bottom: 7pt;
        break-inside: avoid; }
.card-accent  { border-left: 2.5pt solid var(--brand);
                border-radius: 0 6pt 6pt 0; }
.card-brand-top { border-top: 2pt solid var(--brand); }

/* Layout helpers */
.two   { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; margin-bottom: 8pt; }
.three { display: grid; grid-template-columns: repeat(3,1fr); gap: 8pt; margin-bottom: 8pt; }
.sig   { font-size: 8.5pt; margin-bottom: 3pt; line-height: 1.5; }
.tp    { font-size: 8.5pt; margin-bottom: 5pt; line-height: 1.6; }

/* Alert block — used for Why-Now severity tinting */
.alert { border-radius: 4pt; padding: 7pt 9pt; margin-bottom: 6pt;
         font-size: 8.5pt; line-height: 1.55; break-inside: avoid;
         display: flex; gap: 8pt; align-items: flex-start; }
.alert:last-child { margin-bottom: 0; }
.alert .a-num { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                font-size: 9pt; font-weight: 700; flex-shrink: 0; min-width: 12pt; }
.alert.hi  { background: var(--hi-bg);  color: var(--hi-text);  }
.alert.med { background: var(--med-bg); color: var(--med-text); }
.alert.low { background: var(--low-bg); color: var(--low-text); }
.alert.ok  { background: var(--ok-bg);  color: var(--ok-text);  }
.alert.info{ background: var(--info-bg);color: var(--info-text);}
.alert strong { color: inherit; font-weight: 700; }

/* Quote block — for verbatim talking-point excerpts (10-K filings,
   LinkedIn profiles, public talks, press releases — anything cited in
   the solution-fit "Talking points" block) */
.quote { background: var(--bg); border-left: 2.5pt solid var(--brand-mid);
         border-radius: 0 4pt 4pt 0; padding: 6pt 9pt; margin: 7pt 0;
         break-inside: avoid; }
.quote p   { font-size: 8pt; color: var(--muted); font-style: italic;
             margin: 0; line-height: 1.65; }
.quote .src { font-size: 6.5pt; color: var(--faint); margin-top: 3pt;
              font-style: normal; font-weight: 600; letter-spacing: .04em;
              text-transform: uppercase; }

/* Evidence block — verbatim message_text / LinkedIn profile excerpts */
.evidence { margin-top: 5pt; background: var(--bg);
            border-left: 1.5pt solid var(--border-md);
            border-radius: 0 3pt 3pt 0; padding: 4pt 8pt; break-inside: avoid; }
.evidence-lbl { font-size: 6pt; font-weight: 700; letter-spacing: .08em;
                text-transform: uppercase; color: var(--faint); margin-bottom: 2pt; }
.evidence p { font-size: 7.5pt !important; line-height: 1.55 !important;
              color: var(--muted) !important; margin-bottom: 0 !important;
              font-style: italic; }

/* Prospect / signal rows */
.pr, .signal-row {
  display: flex; align-items: flex-start; gap: 8pt; padding: 7pt 0;
  border-bottom: .4pt solid var(--border); break-inside: avoid;
}
.pr:last-child, .signal-row:last-child { border-bottom: none; }
.av { width: 22pt; height: 22pt; border-radius: 50%; display: flex;
      align-items: center; justify-content: center;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 7pt; font-weight: 700; flex-shrink: 0; }
.signal-name  { font-size: 9pt; font-weight: 600; color: var(--text);
                text-decoration: none; }
.signal-title { font-size: 7.5pt; color: var(--muted); margin-bottom: 2pt; }
.signal-body  { font-size: 8pt; line-height: 1.55; }

/* Stat grid */
.stat-grid { display: grid; grid-template-columns: repeat(6,1fr);
             gap: 5pt; margin-bottom: 9pt; }
.stat { position: relative; background: var(--bg); border-radius: 4pt;
        padding: 6pt 7pt 7pt; overflow: hidden; }
.stat::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0;
               height: 1.5pt; background: var(--brand); }
.stat-val { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11pt; font-weight: 600; color: var(--text);
            margin-bottom: 1pt; line-height: 1.2; }
.stat-lbl { font-size: 6.5pt; color: var(--muted); line-height: 1.35;
            letter-spacing: .02em; }

/* Score bar */
.score-track { width: 50pt; height: 4pt; background: var(--bg);
               border-radius: 2pt; overflow: hidden;
               border: .3pt solid var(--border); }
.score-fill  { height: 100%; border-radius: 2pt; }
.score-num   { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
               font-size: 8.5pt; font-weight: 600; }

/* Why-Now numbered rows — alternate to .alert when an unstyled list reads better */
.why-row { display: flex; gap: 9pt; align-items: flex-start;
           margin-bottom: 8pt; break-inside: avoid; }
.why-num { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
           font-size: 10pt; color: var(--brand);
           font-weight: 700; flex-shrink: 0; min-width: 14pt; margin-top: 1pt; }

/* Page break rule */
.contacts-page-break { break-before: page; page-break-before: always; }
```

### Onfire palette reference

The brand tokens are hard-coded — no per-tenant injection. When in doubt,
use these values verbatim:

| Token | Hex | Role |
|---|---|---|
| `--brand`        | `#0A2540` | Onfire navy. Header bar bg, section eyebrows, primary text. |
| `--brand-dark`   | `#051628` | Deepest navy. Hover-equivalents, ultra-dark accents. |
| `--brand-mid`    | `#6B8FA8` | Mid slate. Quote-block left border, subdued dividers. |
| `--brand-light`  | `#DCEFF5` | Cyan-tinted off-white. Hero bands, soft section fills (use sparingly). |
| `--accent`       | `#7C5CFF` | Onfire purple. Single-word highlights, key callouts (≤2 uses per page). |
| `--accent-light` | `#ECE7FF` | Purple tint. Accent fills behind a highlighted noun. |

The purple accent is the differentiator — use it like the Onfire
marketing pages do ("Life's too short for **bad data**"): one or two
times per page on the noun that matters, never as block fills, never
on body copy. If the page has three accent uses you've made it look
loud; pull one back to navy.

Do not ship CSS color functions (`color-mix`, `hsl(from ...)`) — print
rendering of those is inconsistent across PDF engines.

---

## Section 1: Header bar

Onfire-navy bar across the full page width on PDF (contained inside the
body column on screen — the `.header-bar` CSS handles both contexts).
The tenant logo and display name still appear inside the bar so the
BDR's own org is identified, but the bar's color is fixed (Onfire
navy), not tenant-driven.

```html
<div class="header-bar">
  <div class="wm">
    <!-- Tenant logo (optional, only if tenant_config.brand.logo_data_uri present).
         The bar's background is Onfire navy, not the tenant's brand color. -->
    <img class="wm-logo" src="[BASE64_DATA_URI]" alt="[Tenant Display Name]">
    <div>
      <div class="wm-name">[Tenant Display Name]</div>
      <div class="wm-sub">Account Research - [Company Name]</div>
    </div>
  </div>
  <div class="meta">
    [Month Year]<br>Confidential
  </div>
</div>
```

**Do not** add inline `style="..."` to `.header-bar` overriding margin /
padding / background. The screen-media override needs the stylesheet
rule to win; inline styles defeat it and re-introduce the left-clip bug
in browser previews.

---

## Section 2: Company header card

```html
<div class="card card-brand-top">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
    flex-wrap:wrap;gap:6pt;margin-bottom:9pt">
    <div>
      <!-- ALWAYS a LinkedIn link with dotted underline -->
      <div style="font-size:15pt;font-weight:700;letter-spacing:-.02em;margin-bottom:2pt">
        <a href="[COMPANY_LINKEDIN_URL]"
          style="color:inherit;text-decoration:none;border-bottom:1.5pt dotted var(--faint)"
          target="_blank">[Company Name] ↗</a>
      </div>
      <div style="font-size:8pt;color:var(--muted)">
        [Exchange:Ticker] - [Industry] - [HQ]
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:3pt;align-items:flex-end">
      <!-- 2-3 top tags, neutral palette -->
    </div>
  </div>
  <div class="stat-grid">
    <div class="stat">
      <div class="stat-val">$X.XB</div>
      <div class="stat-lbl">FY[year] revenue</div>
    </div>
    <!-- ALWAYS include parenthetical breakdown on headcount when relevant -->
    <div class="stat">
      <div class="stat-val">~100K</div>
      <div class="stat-lbl">Total employees (Company A 55K + Acquired Co 45K, post-acquisition)</div>
    </div>
    <!-- 4 more stats -->
  </div>
  <p style="font-size:9pt;line-height:1.65">
    [2-3 sentence overview. No internal tool names. No marketing copy.]
  </p>
</div>
```

---

## Section 3: Why this account - why now

Every Why-Now point carries an inline source-and-date citation in the
bold strong tag. No exceptions. The reader should be able to point to
the document / event / profile / signal a claim came from, and in what
timeframe, without clicking out.

You may render Why-Now in either of two visual styles. Pick one per
report and use it consistently:

### Style A: Numbered prose rows (default)

Clean, scannable, restrained. Best when claims are similar in severity.

```html
<div class="card card-accent">
  <div class="section-head" style="margin-top:0">
    <div class="section-eye">Why this account, why now</div>
    <div class="section-title">[Headline framing the macro pattern]</div>
  </div>

  <div class="why-row">
    <span class="why-num">01</span>
    <p><strong>[Bold claim] ([source], [date or date range]).</strong>
      [Body prose that names the specific person / document / event evidence.]
      [Tie to the brand's talk track or solution.]</p>
  </div>

  <!-- 3 to 5 more numbered points, same source-and-date stamp -->
</div>
```

### Style B: Severity-tinted alert stack

Use when claims vary in severity (e.g. an active competitive displacement
risk vs. a routine renewal cycle). Color carries meaning — apply
deliberately, not for decoration.

```html
<div class="card card-accent">
  <div class="section-head" style="margin-top:0">
    <div class="section-eye">Why this account, why now</div>
    <div class="section-title">[Headline]</div>
  </div>

  <div class="alert hi">
    <span class="a-num">01</span>
    <div><strong>[Hot signal] ([source], [date]).</strong> [Body…]</div>
  </div>
  <div class="alert med">
    <span class="a-num">02</span>
    <div><strong>[Active build-out] ([source], [date]).</strong> [Body…]</div>
  </div>
  <div class="alert info">
    <span class="a-num">03</span>
    <div><strong>[Strategic context] ([10-K, date]).</strong> [Body…]</div>
  </div>
</div>
```

**Severity mapping:**
- `hi` — competitive displacement, active churn risk, hot intent signal in
  the last 90 days, current vendor-pain post.
- `med` — visible build-out / hiring / event participation in the last 12
  months indicating buying intent.
- `low` — background context that supports the play but isn't time-sensitive.
- `ok` — alumni / champion-at-account signal, expansion opportunity.
- `info` — public-filing or strategic-direction context (10-K, earnings).

### Acceptable inline-citation formats

| Source type | Inline format examples |
|-------------|------------------------|
| 10-K / annual filing | `([Company] 10-K, March 2, 2026)` · `(annual filing, [Month Year])` |
| LinkedIn profile (current role) | `(LinkedIn profile evidence, current role)` · `(LinkedIn profile, in seat since [Month Year])` |
| LinkedIn company-change record | `(company-change records, [Month Year])` |
| Conference / event | `(RSA Conference 2026, April 2026)` · `(KubeCon NA 2025, November 2025)` |
| Community Slack / Discord | `(SPIFFE community Slack, June 2025)` |
| LinkedIn post / digital signal | `(LinkedIn post, [Date])` |

### Required citation structure per point

1. **Bold title carries the source-and-date stamp** — either as a
   parenthetical at the end of the bold or inside the bold itself if the
   source IS the headline (`<strong>...spoke at RSA Conference 2026...</strong>`).
2. **Body prose names the specific person, document, or event** — not a
   generic "annual filing" or "a current employee."
3. **No date-less claims.** If a claim has no date, do not include it
   as a Why-Now point. Demote it into a use-case card or drop it.
4. **Date precision matches the source.** 10-K → exact filing date.
   LinkedIn profile → "in seat since [Month Year]". Slack message → exact
   post date. Event → "[Event Name] [Year]" with month if known.
5. **Multi-source points cite all sources** semicolon-separated:
   `(KubeCon NA 2025, November 2025; SPIFFE community Slack, June 2025)`.
6. **Never cite internal tool names.** See "Forbidden internal tool names".

---

## Section 4: Confirmed technology deployment - LinkedIn profiles

Placed immediately after Why-Now, before signals. This is the strongest
evidence section — real people at the account who list the tenant's
products or competitors in their own LinkedIn job descriptions.

```html
<div class="section-head">
  <div class="section-eye">Confirmed technology deployment</div>
  <div class="section-title">[Company] - LinkedIn profile evidence</div>
  <div class="section-sub">
    Current employees listing the brand's products or competitor products
    directly in their LinkedIn job descriptions.
  </div>
</div>

<div class="card card-accent">
  <!-- One .pr row per person, 3 max -->
  <div class="pr">
    <div class="av" style="background:var(--uc-[tag]-bg);color:var(--uc-[tag]-text)">
      [Initials]
    </div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:6pt;flex-wrap:wrap;margin-bottom:2pt">
        <a href="[LINKEDIN_URL]" style="font-size:9pt;font-weight:600;
          color:var(--text);text-decoration:none">[Full Name]</a>
        <!-- Confirmation tag — what the profile proves -->
        <span class="tag" style="background:var(--hi-bg);color:var(--hi-text)">
          [Product confirmed / Competitor in-seat / etc.]
        </span>
        <span class="tag" style="background:var(--uc-[tag]-bg);color:var(--uc-[tag]-text)">
          [Job Title]
        </span>
      </div>
      <div style="font-size:7.5pt;color:var(--muted);margin-bottom:3pt">
        [Job Title] - [Company] - [Location]
      </div>
      <p style="font-size:8pt;line-height:1.5">
        [1 sentence explaining what this profile confirms and why it matters]
      </p>
      <div class="evidence">
        <div class="evidence-lbl">Source - LinkedIn profile - current role</div>
        <p>&ldquo;[Exact text from JOB_SUMMARY or HEADLINE]&rdquo;</p>
      </div>
    </div>
  </div>
</div>
```

**Picking the 3 best profiles:**
- Direct product name mention beats general category mention.
- Currently employed beats former employee (check `JOB_START_DATE` recency).
- Senior Engineer / Architect / Manager beats junior titles.

### Profile-validation rule - employee vs contractor

Before citing a LinkedIn profile as evidence of internal product
deployment OR as an internal champion, validate the relationship.
Reject any profile whose HEADLINE or SUMMARY uses any of:

- "supporting [Fortune 100 / a financial / etc.] client"
- "consulting for"
- "contracted to"
- "managed services for"
- "augmenting [Company]'s team"
- any wording other than direct employment at the target

Even if the dataset maps the person's `JOB_COMPANY_LINKEDIN_URL` to the
target account, the headline language is the source of truth on
employment relationship. Contractors at managed-services firms commonly
get mapped to client account URLs in third-party data — this is a known
data-mapping artifact, not a citation reason.

Rejection workflow:
1. Drop the profile entirely from Why-Now and Confirmed Technology
   Deployment sections.
2. Drop the profile from Key Contacts.
3. If the technical evidence is unique and lost when the profile is
   dropped, find a second profile that is a direct employee, OR demote
   the claim to general industry context.

Never frame a contractor as an "internal champion" or "in seat".

---

## Section 5: Intent signals

```html
<div class="section-head">
  <div class="section-eye">Intent signals</div>
  <div class="section-title">Last 12 months</div>
  <div class="section-sub">
    Verified public-facing signals showing the account's teams engaging
    on relevant topics.
  </div>
</div>

<div class="card card-accent">
  <div style="display:flex;align-items:center;justify-content:flex-end;
    margin-bottom:6pt;gap:4pt;flex-wrap:wrap">
    <span class="tag" style="background:var(--uc-[tag]-bg);color:var(--uc-[tag]-text)">
      [N] signals detected
    </span>
    <span class="tag" style="background:var(--ok-bg);color:var(--ok-text)">
      All verified
    </span>
  </div>

  <div class="signal-row">
    <div class="av" style="background:var(--uc-[tag]-bg);color:var(--uc-[tag]-text)">
      [Initials]
    </div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:5pt;flex-wrap:wrap;margin-bottom:2pt">
        <a href="[linkedin_url]" class="signal-name">[Full Name]</a>
        <span class="tag" style="background:var(--info-bg);color:var(--info-text)">
          [Neutral source tag]
        </span>
        <span style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
          font-size:7pt;color:var(--faint)">[Date]</span>
      </div>
      <div class="signal-title">[Title] - [Company] - [Location]</div>
      <p class="signal-body">
        [Your own analysis of why this signal is relevant — NOT the AI summary]
      </p>
      <div class="evidence">
        <div class="evidence-lbl">Source - [source_name / source_type] - [Date]</div>
        <p>&ldquo;[Exact message_text from the database]&rdquo;</p>
      </div>
    </div>
  </div>
</div>
```

### Source tag substitution

| Raw `source_name` / `source_type` | Display tag |
|---|---|
| RSA Conference | "RSA Conference [Year]" |
| KubeCon, CloudNativeCon | "[Conference] [Year]" |
| NVIDIA GTC | "NVIDIA GTC [Year]" |
| Slack | "Professional community" |
| Discord | "Community engagement" |
| LinkedIn | "Digital intent signal" |
| Reddit | "Professional community" |
| GitHub | "Developer community signal" |
| Company Change | "Company change - [New Company]" |
| Promotion | "Promotion - [New Title]" |
| Event Attendee (generic) | "[Event Name] - attendee" |

### Evidence block rule (CRITICAL - all signal types)

- Always quote `message_text` **verbatim**. Trim with leading or
  trailing `…` only. Never paraphrase, summarize, translate, fix typos,
  reflow whitespace, or alter characters inside the quoted span. The
  quoted text must be a contiguous substring of `message_text`
  byte-for-byte.
- **Never substitute `short_summary` or any other column.** This
  includes Event Attendee, Company Change, and Promotion signals.
- If `message_text` is empty, skip the evidence block. Do not invent
  one and do not substitute another field.

### When there are no signals, omit the section

If the intent_signals query returns zero verified signals AND no other
source produces relevant content, OMIT the entire Intent Signals
section. Skip the section header, skip the empty card, go directly to
the next section divider.

Never render negative-state copy like "No verified intent signals on
file" or "Recommend revisiting after the next quarterly signal
refresh." The Confirmed Technology Deployment section, the company
header, the 10-K quotes in use-case cards, and the Why-Now bullets
together carry the substance when intent signals are absent.

**Prerequisite — actually run the query.** Only omit the section after
`intent_signals` has been actually executed for the correct
`account_website` AND returned zero rows. Never omit on assumption.

---

## Section 6: Solution fit divider + use case cards

Section 6 begins with a hairline divider and section head, then renders
one use case card per entry in `tenant_config.derived_use_cases`, in
the order provided (highest evidence first). Each card is followed by
its own Key Contacts card on a new page.

The set of use cases is **dynamic**. Do not assume a fixed list. If the
orchestrator returns three use cases, render three. If it returns six,
render six. Tag colors come from `render_spec.use_case_palette` keyed
by the use case `tag` — never invent a color.

The section header collapses to a single eyebrow line that combines the
fixed label with the active brand and target account, so the divider
reads as a self-contained heading without a separate title/subtitle pair.

```html
<hr class="divider">

<div class="section-head">
  <div class="section-eye">Solution fit - [Tenant Display Name] use cases at [Account Display Name]</div>
</div>

<!-- One per derived_use_case -->
<div class="card">
  <div style="display:flex;align-items:center;justify-content:space-between;
    margin-bottom:8pt;flex-wrap:wrap;gap:4pt">
    <div style="display:flex;align-items:center;gap:6pt">
      <span class="tag" style="background:var(--uc-[tag]-bg);color:var(--uc-[tag]-text)">
        [Use Case Label]
      </span>
      <span style="font-size:7.5pt;color:var(--muted)">[Supporting note]</span>
    </div>
    <div style="display:flex;align-items:center;gap:5pt">
      <div class="score-track">
        <div class="score-fill"
          style="width:[score*10]%;background:var(--uc-[tag]-bar)"></div>
      </div>
      <span class="score-num" style="color:var(--uc-[tag]-text)">[score] / 10</span>
    </div>
  </div>
  <div class="two">
    <div>
      <span class="lbl">Account signals</span>
      <!-- Cite as "annual filing", "market intelligence", "[Event Year]",
           LinkedIn profile (in-seat date), hiring-pattern data, etc. -->
    </div>
    <div>
      <span class="lbl">[Tenant Display Name] solution alignment</span>
      <!-- Brand-side talking points, drawn from
           tenant_config.derived_use_cases[].evidence. The label is
           rendered uppercase by the .lbl class; spell the tenant name
           the way it appears in tenant_config (e.g. "JFrog solution
           alignment" -> "JFROG SOLUTION ALIGNMENT"). -->
    </div>
  </div>
  <span class="lbl">Talking points</span>
  <div class="quote">
    <p>&ldquo;[Short verbatim quote, under ~20 words]&rdquo;</p>
    <p class="src">[Attribution - see source-citation guidance below]</p>
  </div>
</div>

<!-- KEY CONTACTS - ALWAYS new page, color-coded label by use case tag -->
<div class="card contacts-page-break">
  <span class="lbl" style="color:var(--uc-[tag]-text);
    border-bottom:.5pt solid var(--uc-[tag]-bg);padding-bottom:4pt;margin-bottom:8pt">
    Key contacts - [Use Case Label]
  </span>
  <!-- .pr rows for each contact -->
</div>
```

### Talking-points source citation

The verbatim quote in the `Talking points` block does **not** have to be
a 10-K excerpt. Any first-party, verifiable source the orchestrator
surfaced (or that the agent quoted directly from a referenced artifact)
is acceptable. Cite the source in the `.src` line with enough detail
that a reader can find it again. Examples:

| Source type | `.src` line |
|---|---|
| Annual filing (10-K) | `[Company] Annual Report (10-K) - [Section] - [Filing Date]` |
| LinkedIn profile (current role / summary) | `[Person Name] ([Role at Account]) - LinkedIn profile - current role` |
| Public talk / conference | `[Person Name] - [Conference Name] [Year]` |
| Press release / blog | `[Company] - [Headline] - [Publication Date]` |
| Job posting | `[Company] - [Job Title] posting - [Date observed]` |

Never invent an attribution. If the quote can't be sourced to a
verifiable artifact, drop the talking-points block for that card rather
than guess.

### If a use case has no signal at the account

Render a short card that frames it as a follow-on to stronger use cases.
Honest framing ("a follow-on, not an opener") is acceptable. Do not
fabricate signal evidence.

### Key contacts card content

Each contact card must surface the fields the `ai_prospecting_field_glossary`
contract's `how_to_use` guidance calls out:

- warm-intro tier label + connector name + shared company (when present)
- composite score with its breakdown
- top three personas from `CURRENT_PERSONAS`
- `PAST_COMPANIES_USED_CLIENT_TECH` when non-empty
- career-momentum signals
- `ai_reasoning` bullets, verbatim
- one opener from `product_talking_points`, verbatim

Never silently drop these fields — consistency across contact cards
matters more than card density.

---

## Section 7: Footer

No sources line. Logo (if available) + company name + label + date.

```html
<div style="margin-top:10pt;padding-top:6pt;border-top:.5pt solid var(--brand-mid);
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4pt">
  <div style="display:flex;align-items:center;gap:5pt">
    <!-- Logo optional -->
    <img src="[BASE64_DATA_URI]" alt="[Brand]"
      style="width:14pt;height:14pt;border-radius:2pt">
    <span style="font-size:7.5pt;font-weight:700;color:var(--brand)">
      [Brand display name]
    </span>
  </div>
  <p style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:6.5pt;color:var(--faint)">
    [Company Name] - Account Research - [Month Year]
  </p>
</div>
```

---

## Quick reference: forbidden vs correct

| Never write | Write instead |
|---|---|
| `—` (em dash) | `-` (hyphen) |
| "Metabase signals" | "Intent signals" |
| "Slack signal" | "Professional community" |
| "Discord signal" | "Community engagement" |
| "Phoenix prospects" | "Key contacts" |
| "Snowflake 10-K" | "Annual filing" |
| "Tenant config match" | "Solution alignment" |
| "Account Brief" | "Account Research" |
| Bare headcount number | Headcount with parenthetical breakdown when relevant |
| Company name plain text | `<a href="[linkedin]">` with dotted underline |
| AI summary of message | Verbatim `message_text` from the dataset |
| Buying committee section | Removed — do not include |
| Cold opens section | Removed — do not include |
| Footer sources line | Removed — footer is name + label + date |
| Google Fonts CDN `<link>` | System font stack only |
| Background colors not printing | `@media print { * { print-color-adjust: exact !important } }` |
| Hardcoded brand color literal | `var(--brand)` / `var(--accent)` from the fixed Onfire palette |
| Tenant brand color in CSS | Tenant brand never colors the report; only the display name + logo appear as content |
| Invented use case tag color | The exact entry from `render_spec.use_case_palette` |

---

## Forbidden internal tool names

Never name an internal product or pipeline tool in the customer-facing
report under any circumstance. These get replaced with neutral
abstractions:

| Internal name | Customer-facing label |
|---|---|
| Phoenix | "Identified prospects" / "verified key contacts" |
| Phoenix prospect data | "LinkedIn profile evidence" (when source is profile data) OR "buyer signals data" |
| AI prospecting | "Buyer signals" |
| Metabase | "Intent signals" |
| Snowflake (as source) | "Annual filing" / "10-K" (cite the doc) |
| MCP, Onfire, OnFire | (never appears in report text) |

Acceptable abstractions in customer-facing prose:
- "annual filing" / "10-K"
- "LinkedIn profile evidence"
- "company-change records"
- "intent signals"
- "industry research"
- "market intelligence"
- "[Conference Name] [Year]" (real events, e.g. "RSA Conference 2026")
- "[Community channel] community Slack / Discord"

Snowflake CAN appear as a CUSTOMER product (e.g. "Snowflake Cortex AI is
in production at the account"). It cannot appear as the SOURCE of the
report data. Same rule for any vendor: if they sell it and the account
uses it, mention freely. If we use it to research, never mention.

Final grep before delivery:

```
grep -iE 'phoenix|metabase|mcp|onfire' report.html
```

Zero matches required.
