# PDF Generation

How to produce a downloadable PDF from the account research report HTML.

---

## Approach: HTML → PDF via weasyprint

Generate the PDF from an HTML string that mirrors the widget layout, using print-friendly
typography. Save to `/mnt/user-data/outputs/`.

```python
import subprocess
import sys

# Install if needed (run once)
subprocess.run([sys.executable, "-m", "pip", "install", "weasyprint", "--break-system-packages", "-q"], check=True)

from weasyprint import HTML, CSS
import os

def generate_report_pdf(html_content: str, company: str, tenant: str) -> str:
    """Generate PDF from HTML report content. Returns output file path."""
    output_dir = "/mnt/user-data/outputs"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"account-research-{company.replace('.', '-')}-{tenant}.pdf"
    output_path = os.path.join(output_dir, filename)

    # Wrap HTML in a print-ready document with base styles
    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 20mm 15mm; size: A4; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
  }}
  .sec {{
    background: #fff;
    border: 0.5pt solid #e0e0e0;
    border-radius: 8pt;
    padding: 12pt 14pt;
    margin-bottom: 10pt;
    page-break-inside: avoid;
  }}
  .lbl {{
    font-size: 8pt;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #666;
    margin: 0 0 5pt;
  }}
  .tag {{
    font-size: 8pt;
    padding: 1pt 6pt;
    border-radius: 4pt;
    font-weight: 600;
  }}
  .sig, .tp {{ font-size: 10pt; margin: 0 0 4pt; line-height: 1.5; }}
  .quote {{
    background: #f5f5f5;
    border-left: 3pt solid #ccc;
    padding: 8pt 10pt;
    margin: 6pt 0;
  }}
  .quote p {{ font-size: 9pt; color: #555; margin: 0; font-style: italic; }}
  .two {{ display: table; width: 100%; }}
  .two > div {{ display: table-cell; width: 50%; vertical-align: top; padding-right: 10pt; }}
  .stat-grid {{ display: table; width: 100%; }}
  .stat {{ display: inline-block; width: 18%; margin-right: 2%; background: #f5f5f5; padding: 8pt; border-radius: 6pt; margin-bottom: 6pt; }}
  .stat-val {{ font-size: 14pt; font-weight: 600; margin: 0 0 2pt; }}
  .stat-lbl {{ font-size: 8pt; color: #666; margin: 0; }}
  a {{ color: #185FA5; text-decoration: none; }}
  h1 {{ font-size: 16pt; font-weight: 600; margin: 0 0 3pt; }}
  .pr {{ padding: 8pt 0; border-bottom: 0.5pt solid #e0e0e0; }}
  .pr:last-child {{ border-bottom: none; }}
  @media print {{
    .sec {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
{html_content}
</body>
</html>"""

    HTML(string=full_html).write_pdf(
        output_path,
        stylesheets=[CSS(string="@page { margin: 20mm 15mm; }")]
    )

    return output_path
```

---

## HTML content to pass to the PDF generator

Extract the **inner HTML** of your widget (everything inside the outer `<div>`) and pass
it to `generate_report_pdf`. Strip any `<style>` tags that use CSS variables
(weasyprint doesn't resolve them) — the print stylesheet above handles styling.

Convert CSS variable colors to their hex equivalents for the PDF:
- `var(--color-text-primary)` → `#1a1a1a`
- `var(--color-text-secondary)` → `#666666`
- `var(--color-background-primary)` → `#ffffff`
- `var(--color-background-secondary)` → `#f5f5f5`
- `var(--color-border-tertiary)` → `#e0e0e0`

---

## Fallback: pdfkit

If weasyprint fails (e.g. missing system libraries):

```python
subprocess.run([sys.executable, "-m", "pip", "install", "pdfkit", "--break-system-packages", "-q"])
import pdfkit
pdfkit.from_string(full_html, output_path, options={"page-size": "A4", "margin-top": "20mm"})
```

pdfkit requires `wkhtmltopdf` to be installed. Check with:
```bash
which wkhtmltopdf
```

---

## Final step

After generating the PDF, call `present_files([output_path])` to make it downloadable.
Tell the user: "[Company] BDR report saved as PDF."
