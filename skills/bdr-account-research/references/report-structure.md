# Report Structure — A4 HTML Template

Full layout specification for the BDR account research report.
This is a **customer-facing, print-ready A4 HTML file** - not a widget.

---

## Core design principles

- **Fortinet branded** — red header bar, Fortinet red color palette throughout
- **A4 print layout** — 174mm content width, all sizes in `pt`, `@page` CSS set
- **Self-contained** — no external dependencies. No Google Fonts CDN. No external images.
  System fonts only. Logo as base64 data URI.
- **Customer-facing** — zero mentions of internal tools. Use "market intelligence",
  "intent signals", "annual filing", "industry research".
- **No em dashes** — use a regular hyphen `-` everywhere. Never use `—`
- **"Account Research"** — never "Account Brief"
- **LinkedIn links** — company name in header is an `<a>` link with dotted underline
- **Employee stat clarity** — always explain headcount with a breakdown
- **Key contacts on new pages** — each use case contacts block starts with `break-before: page`
- **No break mid-card** — every `.card` has `break-inside: avoid`
- **No buying committee or cold opens** — these sections are removed
- **No footer sources line** — footer is: [logo] · [Company] · Account Research · [Month Year]
- **Signal messages quoted verbatim** — never paraphrase `message_text`
- **Background graphics preserved for PDF** — `print-color-adjust: exact` in `@media print`

---

## Full CSS block

```css
/* Reset */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* Fortinet brand tokens */
:root {
  --ftn-red:        #D9261C;
  --ftn-red-dark:   #A8190F;
  --ftn-red-light:  #FBEAE9;
  --ftn-red-mid:    #F4C0BD;
  --bg:       #F6F5F2;
  --surface:  #FFFFFF;
  --border:   #E0DDD6;
  --border-md:#C9C6BE;
  --text:     #1A1816;
  --muted:    #68655E;
  --faint:    #AEABA5;
  --netsec-bg:#E6F1FB; --netsec-text:#155496; --netsec-bar:#2E74C8;
  --secops-bg:#E1F5EE; --secops-text:#0D6350; --secops-bar:#199068;
  --cnapp-bg: #EAF3DE; --cnapp-text: #3B6D11; --cnapp-bar: #5C8F1E;
  --aisec-bg: #EEEDFE; --aisec-text: #4840A8; --aisec-bar: #7269CC;
  --hi-bg:    #FBEAE9; --hi-text:    #8C1B15;
  --med-bg:   #F9EDDA; --med-text:   #7A4A0A;
  --low-bg:   #EEECE6; --low-text:   #565350;
}

/* Page — A4 */
@page { size: A4; margin: 16mm 18mm 18mm 18mm; }
html  { font-size: 10pt; }
body  {
  /* SYSTEM FONTS ONLY — no Google Fonts CDN (blocked in file:// context) */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: #fff; color: var(--text);
  line-height: 1.55; width: 174mm; margin: 0 auto; padding: 0 0 10mm;
}

/* Force background colors to print in PDF — REQUIRED */
@media print {
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}

/* Screen preview */
@media screen {
  html { background: #C9C6BE; font-size: 11px; }
  body { box-shadow: 0 2px 28px rgba(0,0,0,.15); padding: 0 0 20mm; margin: 20px auto; }
  .header-bar { margin: 0; }
}

/* Typography */
p    { font-size: 9pt; line-height: 1.65; margin-bottom: 3pt; }
p:last-child { margin-bottom: 0; }
strong { font-weight: 600; }
a    { color: var(--netsec-text); text-decoration: none; }

/* Labels, tags */
.lbl { display: block; font-size: 7pt; font-weight: 600; letter-spacing: .08em;
       text-transform: uppercase; color: var(--muted); margin-bottom: 4pt; }
.tag { display: inline-block; font-size: 7.5pt; font-weight: 500;
       padding: 1.5pt 6pt; border-radius: 3pt; white-space: nowrap; line-height: 1.5; }

/* Cards */
.card { background: var(--surface); border: .5pt solid var(--border);
        border-radius: 6pt; padding: 9pt 11pt; margin-bottom: 7pt; break-inside: avoid; }
.card-accent  { border-left: 2.5pt solid var(--ftn-red); border-radius: 0 6pt 6pt 0; }
.card-red-top { border-top: 2pt solid var(--ftn-red); }

/* Layout helpers */
.two  { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; margin-bottom: 8pt; }
.sig  { font-size: 8.5pt; margin-bottom: 3pt; line-height: 1.5; }
.tp   { font-size: 8.5pt; margin-bottom: 5pt; line-height: 1.6; }

/* Quote block */
.quote { background: var(--ftn-red-light); border-left: 2.5pt solid var(--ftn-red-mid);
         border-radius: 0 4pt 4pt 0; padding: 6pt 8pt; margin: 7pt 0; }
.quote p { font-size: 7.5pt; color: var(--muted); font-style: italic; margin: 0; line-height: 1.65; }
.quote .src { font-size: 6.5pt; color: var(--faint); margin-top: 3pt; font-style: normal; font-weight: 500; }

/* Evidence block (real message_text / LinkedIn profile quotes) */
.evidence { margin-top: 5pt; background: #F6F5F2; border-left: 1.5pt solid #C9C6BE;
            border-radius: 0 3pt 3pt 0; padding: 4pt 7pt; }
.evidence-lbl { font-size: 6pt; font-weight: 700; letter-spacing: .08em;
                text-transform: uppercase; color: #AEABA5; margin-bottom: 2pt; }
.evidence p { font-size: 7.5pt !important; line-height: 1.55 !important;
              color: #68655E !important; margin-bottom: 0 !important; font-style: italic; }

/* Prospect / signal rows */
.pr { display: flex; align-items: flex-start; gap: 7pt; padding: 6pt 0;
      border-bottom: .4pt solid var(--border); break-inside: avoid; }
.pr:last-child { border-bottom: none; }
.signal-row { display: flex; align-items: flex-start; gap: 7pt; padding: 7pt 0;
              border-bottom: .4pt solid var(--border); break-inside: avoid; }
.signal-row:last-child { border-bottom: none; }
.av { width: 22pt; height: 22pt; border-radius: 50%; display: flex; align-items: center;
      justify-content: center; font-family: monospace; font-size: 7pt; font-weight: 600; flex-shrink: 0; }
.signal-name  { font-size: 9pt; font-weight: 600; color: var(--text); text-decoration: none; }
.signal-title { font-size: 7.5pt; color: var(--muted); margin-bottom: 2pt; }
.signal-body  { font-size: 8pt; line-height: 1.55; }

/* Stats */
.stat-grid { display: grid; grid-template-columns: repeat(6,1fr); gap: 5pt; margin-bottom: 9pt; }
.stat { background: var(--bg); border-radius: 4pt; padding: 5pt 6pt; }
.stat-val { font-family: monospace; font-size: 11pt; font-weight: 500;
            color: var(--ftn-red); margin-bottom: 1pt; line-height: 1.2; }
.stat-lbl { font-size: 6.5pt; color: var(--muted); line-height: 1.3; }

/* Score bar */
.score-track { width: 50pt; height: 3.5pt; background: var(--bg); border-radius: 2pt;
               overflow: hidden; border: .3pt solid var(--border); }
.score-fill  { height: 100%; border-radius: 2pt; }
.score-num   { font-family: monospace; font-size: 8.5pt; font-weight: 500; }

/* Why-now rows */
.why-row { display: flex; gap: 8pt; align-items: flex-start; margin-bottom: 7pt; break-inside: avoid; }
.why-num { font-family: monospace; font-size: 10pt; color: var(--ftn-red);
           font-weight: 600; flex-shrink: 0; min-width: 14pt; margin-top: 1pt; }

/* Section title */
.section-title { font-size: 7pt; font-weight: 700; letter-spacing: .1em;
                 text-transform: uppercase; color: var(--ftn-red);
                 margin: 10pt 0 7pt; display: flex; align-items: center; gap: 6pt; break-after: avoid; }
.section-title::after { content: ""; flex: 1; height: .5pt; background: var(--ftn-red-mid); }

/* Page break rules */
.contacts-page-break { break-before: page; }
hr.divider { border: none; border-top: .4pt solid var(--border); margin: 6pt 0 8pt; }
```

---

## Section 1: Red header bar

Embed the Fortinet logo as base64. Generate with:
```bash
base64 fortinet_logo.jpeg | tr -d '\n'
# Then prefix: data:image/jpeg;base64,<output>
```

```html
<div class="header-bar" style="background:#D9261C;margin:0 -18mm;padding:7pt 18mm;
  display:flex;align-items:center;justify-content:space-between;margin-bottom:10pt">
  <div style="display:flex;align-items:center;gap:8pt">
    <img src="[BASE64_DATA_URI]" alt="Fortinet" style="width:26pt;height:26pt;border-radius:3pt">
    <div>
      <div style="font-size:11pt;font-weight:600;color:#fff">Fortinet</div>
      <div style="font-size:7.5pt;color:rgba(255,255,255,.75);margin-top:1pt">
        Account Research - [Company Name]
      </div>
    </div>
  </div>
  <div style="font-family:monospace;font-size:7pt;color:rgba(255,255,255,.65);
    text-align:right;line-height:1.5">[Month Year]<br>Confidential</div>
</div>
```

---

## Section 2: Company header card

```html
<div class="card card-red-top">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
    flex-wrap:wrap;gap:6pt;margin-bottom:9pt">
    <div>
      <!-- ALWAYS a LinkedIn link with dotted underline -->
      <div style="font-size:15pt;font-weight:600;letter-spacing:-.02em;margin-bottom:2pt">
        <a href="[COMPANY_LINKEDIN_URL]"
          style="color:inherit;text-decoration:none;border-bottom:1.5pt dotted #AEABA5"
          target="_blank">[Company Name] ↗</a>
      </div>
      <div style="font-size:8pt;color:var(--muted)">[Exchange:Ticker] - [Industry] - [HQ]</div>
    </div>
    <div style="display:flex;flex-direction:column;gap:3pt;align-items:flex-end">
      <!-- 2-3 top tags -->
    </div>
  </div>
  <div class="stat-grid">
    <div class="stat"><div class="stat-val">$X.XB</div><div class="stat-lbl">FY[year] revenue</div></div>
    <!-- ALWAYS include breakdown in employee label -->
    <div class="stat"><div class="stat-val">~100K</div>
      <div class="stat-lbl">Total employees (Company A 55K + Acquired Co 45K, post-acquisition)</div></div>
    <!-- 4 more stats -->
  </div>
  <p style="font-size:9pt;line-height:1.65">[2-3 sentence overview. No internal tool names.]</p>
</div>
```

---

## Section 3: Why this account - why now

**Every point must cite its source inline in the first sentence.** No separate evidence
blocks — the source and date are woven into the opening sentence naturally.

**Format pattern:**
`[Bold title.] [Source with date] [verb: confirms/discloses/shows/states] [the claim]. [BDR relevance.]`

**Source reference by origin:**

| Origin | Inline citation format |
|--------|----------------------|
| SEC 10-K | `[Company]'s annual filing (10-K, [Date])` |
| LinkedIn post | `[Person/Role] posted on LinkedIn ([Month Year])` |
| LinkedIn company change | `LinkedIn company change notification ([Month Year])` |
| LinkedIn promotion | `LinkedIn promotion notification ([Month Year])` |
| Fortinet Discord/Slack | `A [Company] [role] posted in the Fortinet community [platform] ([Date])` |
| Public event | `[Person/Company] at [Event Name] [Year]` |
| Press release | `[Company] press release ([Month Year])` |
| EU/gov regulation | `[Regulation] ([Official reference, date] - enforcement [date])` |
| Phoenix results | `AI prospecting results ([Month Year]) identified...` |

**Correct examples:**
- `Capital One's annual filing (10-K, Feb 19, 2026) explicitly discloses that employee AI tools risk PII leakage...`
- `A Siemens security engineer posted in the Fortinet community Discord (Mar 17, 2026): "How do you guys like FortiPAM?" — confirming an active evaluation.`
- `LinkedIn company change notification (Dec 2025) shows George G. moved from AMS to PMI as Senior IT Service Manager.`

**Wrong:**
- `Market intelligence shows...` — too vague
- `Sources confirm...` — no source named
- Adding a separate evidence block below the point — inline only

```html
<div class="card card-accent">
  <span class="lbl">Why this account - why now</span>
  <div class="why-row">
    <span class="why-num">01</span>
    <p><strong>Bold title.</strong> [Source with date] confirms/discloses [claim].
      [Supporting context and BDR relevance.]</p>
  </div>
  <!-- repeat 02-05 — each point MUST have inline source in first sentence -->
</div>
```

---

## Section 4: Confirmed technology deployment — LinkedIn profiles

Placed **immediately after "Why Now"**, before signals. This is the strongest evidence
section — real people at the account who list the tenant's products or competitors in
their own LinkedIn job descriptions.

```html
<div class="section-title">Confirmed technology deployment - LinkedIn profiles - [Company]</div>
<div class="card card-accent">
  <span class="lbl" style="margin-bottom:6pt">
    Current employees listing [tenant] or competitor products directly in their LinkedIn
    job descriptions
  </span>

  <!-- One .pr row per person, 3 max -->
  <div class="pr">
    <div class="av" style="background:[uc-bg];color:[uc-text]">[Initials]</div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:7pt;flex-wrap:wrap;margin-bottom:2pt">
        <a href="[LINKEDIN_URL]" style="font-size:9pt;font-weight:600;
          color:var(--text);text-decoration:none">[Full Name]</a>
        <!-- Confirmation tag — what the profile proves -->
        <span class="tag" style="background:var(--hi-bg);color:var(--hi-text)">
          [FortiGate confirmed / Palo Alto in-seat / etc.]
        </span>
        <span class="tag" style="background:[uc-bg];color:[uc-text]">[Job Title]</span>
      </div>
      <div style="font-size:7.5pt;color:var(--muted);margin-bottom:3pt">
        [Job Title] - [Company] - [Location]
      </div>
      <p style="font-size:8pt;line-height:1.5">
        [1 sentence explaining what this profile confirms and why it matters]
      </p>
      <!-- Evidence block with VERBATIM quote from their LinkedIn profile -->
      <div class="evidence">
        <div class="evidence-lbl">Source - LinkedIn profile - current role</div>
        <p>&ldquo;[Exact text from JOB_SUMMARY or HEADLINE that mentions the product]&rdquo;</p>
      </div>
    </div>
  </div>
</div>
```

**Picking the 3 best profiles:**
- Direct product name mention beats general category mention
  - STRONG: "Managed Fortinet firewalls, including FortiGate models"
  - WEAK: "experience with various security tools"
- Currently employed beats former employee (check JOB_START_DATE recency)
- Sr. Engineer / Architect / Manager beats junior titles
- For competitor evidence: prefer "Palo Alto confirmed in-seat" + model numbers

---

## Section 5: Intent signals

```html
<div class="card card-accent">
  <div style="display:flex;align-items:center;justify-content:space-between;
    margin-bottom:8pt;flex-wrap:wrap;gap:4pt">
    <!-- Label: "Intent signals" only - NEVER "Metabase signals" -->
    <span class="lbl" style="margin-bottom:0">Intent signals - [Date range]</span>
    <div style="display:flex;gap:4pt">
      <span class="tag" style="background:[uc-bg];color:[uc-text]">[N] signals detected</span>
      <span class="tag" style="background:var(--hi-bg);color:var(--hi-text)">All verified</span>
    </div>
  </div>

  <!-- Signal row -->
  <div class="signal-row">
    <div class="av" style="background:[uc-bg];color:[uc-text]">[Initials]</div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:5pt;flex-wrap:wrap;margin-bottom:2pt">
        <a href="[linkedin_url]" class="signal-name">[Full Name]</a>
        <!-- Source tag - see source substitution table -->
        <span class="tag" style="...">[Neutral source tag]</span>
        <span style="font-family:monospace;font-size:7pt;color:var(--faint)">[Date]</span>
      </div>
      <div class="signal-title">[Title] - [Company] - [Location]</div>
      <p class="signal-body">[Your own analysis of why this signal is relevant — NOT the AI summary]</p>
      <!-- Evidence block: VERBATIM message_text (if non-empty) -->
      <div class="evidence">
        <div class="evidence-lbl">Source - [source_name / source_type] - [Date]</div>
        <p>&ldquo;[Exact message_text from the database]&rdquo;</p>
      </div>
    </div>
  </div>
</div>
```

**Source tag substitution:**

| Raw `source_name` / `source_type` | Display tag |
|-----------------------------------|-------------|
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

**Evidence block rule (CRITICAL — applies to all signal types):**
- The evidence block always quotes `message_text` **verbatim**. Trim with leading
  or trailing `…` only; never paraphrase, summarize, translate, fix typos, reflow
  whitespace, or alter the characters inside the quoted span. The quoted text
  must be a contiguous substring of `message_text` byte-for-byte.
- **Never substitute `short_summary` or any other column** — including for
  `Event Attendee`, `Company Change`, or `Promotion` signals.
- `message_text` is empty — skip the evidence block. Do not invent one and do
  not substitute another field.

---

## Section 6: Use case cards

```html
<!-- Use case card -->
<div class="card">
  <div style="display:flex;align-items:center;justify-content:space-between;
    margin-bottom:8pt;flex-wrap:wrap;gap:4pt">
    <div style="display:flex;align-items:center;gap:6pt">
      <span class="tag" style="background:[uc-bg];color:[uc-text]">[Use Case]</span>
      <span style="font-size:7.5pt;color:var(--muted)">[Supporting note]</span>
    </div>
    <div style="display:flex;align-items:center;gap:5pt">
      <!-- Score bar: fill width = score * 10% -->
      <div class="score-track">
        <div class="score-fill" style="width:[score*10]%;background:[uc-bar]"></div>
      </div>
      <span class="score-num" style="color:[uc-text]">[score] / 10</span>
    </div>
  </div>
  <div class="two">
    <div>
      <span class="lbl">Account signals</span>
      <!-- Cite as "annual filing", "market intelligence", "[Event Year]" -->
    </div>
    <div>
      <!-- Label: "Fortinet solution alignment" — NOT "Tenant config match" -->
      <span class="lbl">Fortinet solution alignment</span>
    </div>
  </div>
  <span class="lbl">Talking points</span>
  <!-- 10-K quote block (under 15 words verbatim) -->
  <div class="quote">
    <p>"[Short verbatim quote from filing]"</p>
    <p class="src">[Company] Annual Report (10-K) - [Section] - [Filing Date]</p>
  </div>
</div>

<!-- KEY CONTACTS — ALWAYS new page, color-coded label -->
<div class="card contacts-page-break">
  <span class="lbl" style="color:[uc-text];border-bottom:.5pt solid [uc-bg];
    padding-bottom:4pt;margin-bottom:8pt">Key contacts - [Use Case]</span>
  <!-- .pr rows -->
</div>
```

---

## Section 7: Footer

No sources line. Just: logo + company name + label + date.

```html
<div style="margin-top:10pt;padding-top:6pt;border-top:.5pt solid #F4C0BD;
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4pt">
  <div style="display:flex;align-items:center;gap:5pt">
    <img src="[BASE64_DATA_URI]" alt="Fortinet" style="width:14pt;height:14pt;border-radius:2pt">
    <span style="font-size:7.5pt;font-weight:600;color:#D9261C">Fortinet</span>
  </div>
  <p style="font-family:monospace;font-size:6.5pt;color:var(--faint)">
    [Company Name] - Account Research - [Month Year]
  </p>
  <!-- NO sources line -->
</div>
```

---

## Quick reference: forbidden vs correct

| Never write | Write instead |
|-------------|---------------|
| `—` (em dash) | `-` (hyphen) |
| "Metabase signals" | "Intent signals" |
| "Slack signal" | "Professional community" |
| "Discord signal" | "Community engagement" |
| "Phoenix prospects" | "Key contacts" |
| "Snowflake 10-K" | "Annual filing" |
| "Tenant config match" | "Fortinet solution alignment" |
| "Account Brief" | "Account Research" |
| `~100K Employees post-Discover` | `~100K Total employees (Co A 55K + Co B 45K, post-acquisition)` |
| Company name plain text | `<a href="[linkedin]">` with dotted underline |
| AI summary of message | Verbatim `message_text` from database |
| Buying committee section | Removed — do not include |
| Cold opens section | Removed — do not include |
| Footer sources line | Removed — footer is name + label + date only |
| "Market intelligence shows..." in Why Now | `[Source] ([Date]) confirms/discloses...` inline in first sentence |
| Why Now point with no source | Remove the point or find a real source — never use vague attribution |
| Background colors not printing | `@media print { * { print-color-adjust: exact !important } }` |
