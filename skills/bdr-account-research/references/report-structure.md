# Report Structure & HTML Widget Template

Full layout specification for the BDR account research report widget.

---

## Design principles

- Follow the claude.ai design system (CSS variables, flat surfaces, no gradients)
- Use sentence case everywhere — never ALL CAPS or Title Case
- LinkedIn URLs must be `<a href="...">` links
- 10-K quotes use a left-border blockquote; never reproduce > 15 words verbatim
- Fit score bars: filled `div` inside a 90px × 5px container
- Avatars: 32×32px circles with initials, colored per use case
- All source attribution: small 10px label with `letter-spacing: 0.05em`

---

## CSS base

```css
.sec { background: var(--color-background-primary); border: .5px solid var(--color-border-tertiary); border-radius: var(--border-radius-lg); padding: 1.25rem; margin-bottom: 1rem; }
.lbl { font-size: 11px; font-weight: 500; letter-spacing: .08em; text-transform: uppercase; color: var(--color-text-secondary); margin: 0 0 6px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: var(--border-radius-md); font-weight: 500; white-space: nowrap; }
.sig { font-size: 13px; color: var(--color-text-primary); margin: 0 0 4px; line-height: 1.55; }
.tp  { font-size: 13px; color: var(--color-text-primary); margin: 0 0 6px; line-height: 1.65; }
.pr  { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: .5px solid var(--color-border-tertiary); }
.pr:last-child { border-bottom: none; }
.av  { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 500; flex-shrink: 0; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.quote { background: var(--color-background-secondary); border-left: 3px solid var(--color-border-secondary); border-radius: 0 var(--border-radius-md) var(--border-radius-md) 0; padding: 10px 12px; margin: 8px 0; }
.quote p { font-size: 12px; color: var(--color-text-secondary); line-height: 1.6; margin: 0; font-style: italic; }
.src { font-size: 10px; color: var(--color-text-secondary); margin: 4px 0 0; font-style: normal; font-weight: 500; letter-spacing: .05em; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; margin-bottom: 16px; }
.stat { background: var(--color-background-secondary); border-radius: var(--border-radius-md); padding: 10px 12px; }
.stat-val { font-size: 18px; font-weight: 500; color: var(--color-text-primary); margin: 0 0 2px; line-height: 1.2; }
.stat-lbl { font-size: 11px; color: var(--color-text-secondary); margin: 0; line-height: 1.3; }
@media(max-width:500px) { .two { grid-template-columns: 1fr; } .stat-grid { grid-template-columns: 1fr 1fr; } }
```

---

## Section 1: Report header

```html
<!-- Red dot + source label -->
<div class="sec">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
    <div style="width:7px;height:7px;border-radius:50%;background:#E24B4A;flex-shrink:0"></div>
    <span class="lbl" style="margin:0">BDR Intelligence · [data source badges]</span>
    <!-- Data source badges: show only sources that contributed data -->
    <!-- Snowflake: background:#E6F1FB;color:#185FA5 -->
    <!-- Metabase: background:#FCEBEB;color:#A32D2D -->
    <!-- Phoenix: background:#EAF3DE;color:#3B6D11 -->
    <!-- Missing source: background:#F1EFE8;color:#5F5E5A with "N/A" suffix -->
  </div>

  <!-- Company name + top use case + notable tags -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:14px">
    <div>
      <p style="font-size:20px;font-weight:500;margin:0 0 3px">[Company Name]</p>
      <p style="font-size:13px;color:var(--color-text-secondary);margin:0">[Exchange:Ticker] · [Industry] · [HQ] · 10-K [Filing Date]</p>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <!-- Top use case tag, notable finding tags (max 3) -->
    </div>
  </div>

  <!-- Stat grid: revenue, employees, signals count, prospects scored, notable metric -->
  <div class="stat-grid">...</div>

  <!-- 2–3 sentence company overview -->
  <p style="font-size:14px;line-height:1.7;margin:0">...</p>
</div>
```

---

## Section 2: Why now

```html
<div class="sec" style="border-left:3px solid #E24B4A;border-radius:0 var(--border-radius-lg) var(--border-radius-lg) 0">
  <p class="lbl" style="margin-bottom:10px">Why this account — why now · [sources cited]</p>
  <!-- 3–5 numbered points, each with a bold title and 2–3 sentence explanation -->
  <!-- Each point ends with a source badge or inline citation -->
  <div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:8px">
    <span style="font-size:14px;color:#E24B4A;font-weight:500;flex-shrink:0;min-width:18px">01</span>
    <p class="tp" style="margin:0"><strong style="font-weight:500">Bold title.</strong> Explanation text...</p>
  </div>
  <!-- repeat for 02, 03, etc -->
</div>
```

---

## Section 3: Live signals

```html
<div class="sec" style="border-left:3px solid #E24B4A;border-radius:0 var(--border-radius-lg) var(--border-radius-lg) 0">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
    <p class="lbl" style="margin:0">Live signals · Metabase · [tenant_id] · [company_website]</p>
    <div style="display:flex;gap:5px">
      <span class="tag" style="background:#EAF3DE;color:#3B6D11">[N] signals returned</span>
      <span class="tag" style="background:#FCEBEB;color:#A32D2D">All [signal_type]</span>
    </div>
  </div>

  <!-- One row per signal holder (merge if same person has multiple signals) -->
  <div style="display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:.5px solid var(--color-border-tertiary)">
    <div class="av" style="background:[uc-color-bg];color:[uc-color-text]">[initials]</div>
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:2px">
        <a href="[linkedin_url]" style="font-size:13px;font-weight:500;color:var(--color-text-primary);text-decoration:none">[Full Name]</a>
        <span class="tag" style="background:#FCEBEB;color:#A32D2D">Priority</span>
        <span class="tag" style="background:#FAEEDA;color:#854F0B">[source · date]</span>
      </div>
      <p style="font-size:12px;color:var(--color-text-secondary);margin:0 0 3px">[Title] · [Location]</p>
      <p style="font-size:12px;color:var(--color-text-primary);margin:0;line-height:1.5">[short_summary or long_summary]</p>
      <!-- If matched to Phoenix prospect, show ai_reasoning snippet here -->
    </div>
  </div>
</div>
```

If no signals: show a single row with "No live signals found for [tenant_id] at [company_website]."

---

## Section 4: Use case cards (one per derived use case)

```html
<div class="sec">
  <!-- Header: use case badge + prospect count note + fit score bar -->
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:6px">
    <div style="display:flex;align-items:center;gap:8px">
      <span class="tag" style="background:[uc-bg];color:[uc-text]">[Use Case Name]</span>
      <span style="font-size:12px;color:var(--color-text-secondary)">[supporting note]</span>
    </div>
    <div style="display:flex;align-items:center;gap:8px">
      <div style="width:90px;height:5px;background:var(--color-background-secondary);border-radius:4px;overflow:hidden">
        <div style="width:[score*10]%;height:100%;background:[uc-bar];border-radius:4px"></div>
      </div>
      <span style="font-size:13px;font-weight:500;color:var(--color-text-primary)">[score]/10</span>
    </div>
  </div>

  <!-- Two-column: account signals (left) + tenant config match (right) -->
  <div class="two">
    <div>
      <p class="lbl">Account signals</p>
      <!-- 3–5 bullet signals from Metabase + 10-K -->
    </div>
    <div>
      <p class="lbl">Fortinet tenant config match</p>
      <!-- Technologies ✓, Personas ✓, Competitors confirmed/likely -->
    </div>
  </div>

  <!-- Talking points: 2–3, each grounded in a specific data source -->
  <p class="lbl">Talking points</p>
  <!-- If 10-K quote available: show blockquote, then add talking point referencing it -->

  <!-- Top prospects for this use case -->
  <p class="lbl" style="margin-top:12px">Top prospects</p>
  <!-- prospect rows (see signal row template above, same structure) -->
</div>
```

---

## Section 5: Buying committee table

```html
<div class="sec" style="margin-bottom:0">
  <p class="lbl" style="margin-bottom:10px">Buying committee</p>
  <!-- One row per person, priority badge on right -->
  <!-- Priority colors: high=#FCEBEB/#A32D2D, medium=#FAEEDA/#854F0B, support=#F1EFE8/#5F5E5A -->
  <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:.5px solid var(--color-border-tertiary)">
    <div>
      <p style="font-size:13px;font-weight:500;margin:0">[Name or Role]</p>
      <p style="font-size:11px;color:var(--color-text-secondary);margin:0">[Title] · [data source]</p>
    </div>
    <span class="tag" style="background:[priority-bg];color:[priority-text]">[priority]</span>
  </div>
</div>
```

---

## Section 6: Approach + cold opens

```html
<!-- 2-column: approach narrative (left) + cold open scripts (right) -->
<div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px">
  <div class="sec" style="margin-bottom:0">
    <p class="lbl" style="margin-bottom:8px">Recommended sequence</p>
    <p style="font-size:13px;line-height:1.7;margin:0">...</p>
  </div>
  <div style="display:flex;flex-direction:column;gap:10px">
    <!-- Cold open 1: most senior buyer -->
    <div class="sec" style="margin-bottom:0;background:var(--color-background-secondary)">
      <p class="lbl" style="margin-bottom:5px">Cold open · [Buyer Name/Role]</p>
      <p style="font-size:13px;line-height:1.6;margin:0;font-style:italic">"..."</p>
    </div>
    <!-- Cold open 2: top technical champion -->
    <div class="sec" style="margin-bottom:0;background:var(--color-background-secondary)">
      <p class="lbl" style="margin-bottom:5px">Cold open · [Champion Name/Role]</p>
      <p style="font-size:13px;line-height:1.6;margin:0;font-style:italic">"..."</p>
    </div>
  </div>
</div>
```

---

## Missing data states

When a section has no data from a source, show a muted inline note rather than hiding
the section entirely:

```html
<p style="font-size:13px;color:var(--color-text-secondary);line-height:1.6;margin:0">
  No [Snowflake 10-K / Metabase signals / Phoenix prospects] found for this account.
  [Brief note on what would appear here if data were available.]
</p>
```
