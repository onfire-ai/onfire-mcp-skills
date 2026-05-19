# 10-K Extraction Patterns

How to extract the relevant sections from EDGAR `FULL_MARKDOWN` filings for each
part of the BDR report. The `FULL_MARKDOWN` column can be 500K–900K characters.
Never load it fully into a prompt — extract only what you need.

---

## General extraction approach

Use Python substring search on the raw markdown text:

```python
def extract_section(text, keyword, chars=4000):
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return None
    return text[idx:idx + chars]

def find_all(text, keyword, chars=2000):
    results = []
    start = 0
    while True:
        idx = text.lower().find(keyword.lower(), start)
        if idx == -1:
            break
        results.append(text[idx:idx + chars])
        start = idx + 1
    return results
```

Cap each extraction at 4,000 characters. If a section appears multiple times,
take the **last** occurrence (it is usually the actual section, not a table-of-contents ref).

---

## Priority 1 — Item 1C: Cybersecurity governance

Search keyword: `Item 1C. Cybersecurity`

Find all occurrences, take the **last** one (the full section, not the TOC).
Extract 8,000 characters from that position.

What to look for inside this section:

| Signal | Pattern |
|--------|---------|
| CISO credentials | `CISO`, `Chief Information Security Officer` + years/background |
| CTRO credentials | `CTRO`, `Chief Technology Risk Officer` + background |
| Governance body | `Risk Committee`, `Board of Directors` + cybersecurity |
| Response plan | `Enterprise Cyber Response Plan`, `ECRP`, `incident response` |
| Three lines of defense | `three lines of defense`, `first line`, `second line` |
| Table-top exercises | `table-top`, `tabletop` |
| Third-party risk | `third-party risk management` |
| Compliance frameworks | `NIST`, `ISO`, `SOC 2`, `FedRAMP`, `CIRCIA`, `OCC` |
| M&A integration | `integration of [company]`, `acquired`, `Transaction` |

Fortinet-relevant use case connections:
- Response plan + CIRCIA → **Sec Ops** (FortiSOAR + CIRCIA compliance)
- Third-party risk → **CNAPP** (DSPM, CASB for third-party SaaS)
- CISO/CTRO background → **buying committee** enrichment
- M&A integration → **CNAPP** + **Sec Ops** (expanded attack surface)

---

## Priority 2 — AI and GenAI risk factors

Search keyword: `generative AI`

Also search: `artificial intelligence`, `AI solutions`, `models and AI`, `third-party AI`

What to look for:

| Signal | Pattern |
|--------|---------|
| AI data leakage risk | `inadvertent`, `unauthorized disclosure`, `training sets`, `sensitive information` |
| AI governance gap | `manual`, `human error`, `data management` near `AI` |
| Regulatory AI risk | `OCC`, `SR 11-7`, `model risk`, `legal`, `regulatory` near `AI` |
| AI in production | `generative AI`, `LLM`, `foundation model`, `Eno`, `Chat Concierge` |

Fortinet-relevant use case connection: → **AI Sec** (FortiAI governance, API gateway protection)

---

## Priority 3 — Cloud infrastructure and architecture

Search keywords: `cloud infrastructure`, `Amazon Web Services`, `AWS`, `Azure`, `GCP`

Also search: `Kubernetes`, `microservices`, `data centers`, `hybrid`

What to look for:

| Signal | Pattern |
|--------|---------|
| Pure cloud | `100%`, `entirely`, `all-in on cloud`, `closed our last data center` |
| Hybrid | `combination of data centers and`, `on-premises` near cloud provider |
| Kubernetes | `Kubernetes`, `container`, `microservices` |
| Cloud provider | `Amazon Web Services`, `Microsoft Azure`, `Google Cloud` |
| Third-party SaaS | named SaaS vendors + `TSYS`, `FIS`, `Fidelity` |

Fortinet-relevant use case connection: → **CNAPP** (CSPM/CWPP for confirmed cloud environment)

---

## Priority 4 — M&A / acquisition integration

Search keyword: `integration of [acquired company name]`

Also search: `Transaction`, `acquisition`, `acquired`, `merger`

What to look for:

| Signal | Pattern |
|--------|---------|
| Active integration | `actively integrating`, `integration is underway`, `integration of [name]` |
| Security integration | `cybersecurity program`, `security controls` near `integration` |
| New tech estate | `data centers`, `third-party vendors`, `network`, `payment` |
| Risk from integration | `risks that may arise`, `integration risks`, `diversion` |

Fortinet-relevant use case connections:
- New data centers from acquisition → **CNAPP** (Prisma coverage gap for non-AWS estate)
- Integration security risk → **Sec Ops** (expanded SOC scope)
- New payment network → **Network Sec** (PCI DSS scope expansion)

---

## Priority 5 — Key technology disclosures

Search keywords: `AWS`, `Snowflake`, `Databricks`, `Okta`, `Kubernetes`, `Terraform`,
`Microsoft Entra`, `Microsoft 365`, `ServiceNow`

For each hit, capture 500 characters of context. Use these as **technology signals**
in the CNAPP and Sec Ops use case cards.

---

## Priority 6 — Financial context (for report header)

Search keywords: `Total net revenue`, `net revenue increased`, `employees`

Extract up to 500 characters each. Use for the stat grid in the report header.

Pattern examples:
- `Total net revenue increased X percent to $Y billion` → revenue
- `As of December 31, 20XX, [Company] had approximately X,XXX employees` → headcount

---

## What NOT to extract

- Executive compensation tables
- Audit committee reports
- Share repurchase programs
- Loan portfolio details
- Derivatives disclosures
- Any section > 3 levels nested in a table

---

## 10-K quote handling

When including a 10-K quote in the report:
- Keep it under 15 words — paraphrase everything else
- One quote per filing section maximum
- Always label with `Source: [Company] 10-K, [Section], [Filing Date]`
- Blockquote style in HTML: `border-left: 3px solid var(--color-border-secondary)`
- Never reproduce full paragraphs — summarise in your own words and cite
