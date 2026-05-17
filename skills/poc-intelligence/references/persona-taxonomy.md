# Persona Taxonomy & Title Normalization

## Normalization Rules

Apply in this order before any bucketing:

1. Lowercase everything
2. Strip trailing/leading whitespace
3. Remove punctuation except hyphens
4. Replace common abbreviations:
   - `vp` -> `vice president`
   - `svp` -> `senior vice president`
   - `evp` -> `executive vice president`
   - `cto` -> `chief technology officer`
   - `ciso` -> `chief information security officer`
   - `cio` -> `chief information officer`
   - `ceo` -> `chief executive officer`
   - `coo` -> `chief operating officer`
   - `cmo` -> `chief marketing officer`
   - `cro` -> `chief revenue officer`
   - `mgr` -> `manager`
   - `dir` -> `director`
   - `eng` -> `engineer`
   - `dev` -> `developer`
   - `arch` -> `architect`
   - `sr` -> `senior`
   - `jr` -> `junior`
5. Strip seniority prefixes when they appear before the core title:
   - `senior`, `sr.`, `principal`, `staff`, `lead`, `junior`, `jr.`, `associate`
   - BUT: `lead` is NOT stripped when it IS the core concept (e.g. "team lead")
6. Strip company-specific suffixes in parentheses: `director of sales (emea)` -> `director of sales`
7. Merge region variants: `director of sales - emea` and `director of sales` -> same bucket

---

## Core Title Groupings (for deduplication)

These variants all map to the same normalized title:

| Normalized Title | Raw Variants |
|---|---|
| VP Sales | VP of Sales, VP Sales, Vice President Sales, Vice President of Sales, Sales VP |
| VP Engineering | VP of Engineering, VP Engineering, Vice President Engineering |
| Director of Sales | Dir of Sales, Sales Director, Director Sales |
| Head of Sales | Head of Sales Development, Head Sales |
| Chief Revenue Officer | CRO, Chief Revenue Officer, SVP Revenue |
| Chief Technology Officer | CTO, Chief Technology Officer, VP Technology (when no CTO exists) |
| Engineering Manager | Engineering Mgr, Manager Engineering, Manager of Engineering |
| Sales Development Rep | SDR, BDR, Sales Development Representative, Business Development Representative |
| Account Executive | AE, Account Exec |
| Customer Success Manager | CSM, Customer Success Mgr |

---

## Persona Buckets

### Champion
Practitioners and users who benefit directly from the product. They advocate internally.
- Data Engineer, Data Scientist, Analytics Engineer
- Software Engineer, Backend Engineer, Platform Engineer
- Marketing Operations, Revenue Operations, Sales Operations
- Growth Manager, Product Manager
- Any IC-level role in the target department

### Economic Buyer
Budget holders and decision makers who approve purchase.
- C-suite: CEO, CTO, CRO, CMO, COO, CISO, CIO
- VP level and above with budget ownership
- Director with clear P&L responsibility
- General Manager, Managing Director

### Technical Evaluator
Evaluates technical fit, integration, security, and architecture.
- Solutions Architect, Enterprise Architect, Technical Architect
- IT Manager, IT Director
- Security Engineer, Security Analyst, InfoSec
- DevOps, Platform Engineer, Infrastructure Engineer
- Technical Lead (evaluating a platform)

### End User
Will use the product daily. High influence on adoption success.
- Any analyst or IC role in the target department
- SDR / BDR (for sales tools)
- Recruiter (for HR tools)
- Designer (for design tools)

### Blocker / Gatekeeper
Can slow or stop a deal. Needs to be managed, not sold to.
- Procurement, Vendor Management, Purchasing
- Legal, Compliance, Risk
- IT Security (when not also the Technical Evaluator)
- Finance (for budget approval cycles)

---

## Healthy Buying Committee Benchmark

For a typical mid-market B2B SaaS deal, a healthy CRM contact distribution looks like:

| Persona | Target % | Red Flag if below |
|---|---|---|
| Champion | 35-50% | < 20% |
| Economic Buyer | 15-25% | < 10% |
| Technical Evaluator | 15-20% | < 8% |
| End User | 10-20% | n/a |
| Blocker / Gatekeeper | < 10% | > 25% |

**Champion-led risk**: Champion > 60% AND Economic Buyer < 10%. Common cause of late-stage losses.
**Top-down risk**: Economic Buyer > 40% AND Champion < 20%. Common cause of poor adoption post-sale.
**No evaluator risk**: Technical Evaluator < 5%. Common cause of integration-related deal delays.
