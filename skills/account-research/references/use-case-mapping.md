# Use Case Mapping

Maps technology/competitor signals from tenant config → use case buckets,
and provides rules for detecting which use cases a tenant has excluded.

---

## Standard use case buckets

These are the canonical use cases. A tenant may support any subset of them.

| Use Case | ID | Badge color |
|----------|----|-------------|
| Network Sec | `network_sec` | Blue `#E6F1FB / #185FA5` |
| AI Sec | `ai_sec` | Purple `#EEEDFE / #534AB7` |
| Sec Ops | `sec_ops` | Teal `#E1F5EE / #0F6E56` |
| CNAPP | `cnapp` | Green `#EAF3DE / #3B6D11` |
| AppSec | `appsec` | Amber `#FAEEDA / #854F0B` |
| Identity | `identity` | Coral `#FAECE7 / #993C1D` |
| Endpoint | `endpoint` | Gray `#F1EFE8 / #5F5E5A` |

---

## Technology keyword → use case

Scan `config.account_research.queries_sections.technologies` for these keywords
(case-insensitive substring match):

### Network Sec
`NGFW`, `Firewall`, `SD-WAN`, `SASE`, `ZTNA`, `MPLS`, `VPN`, `Secure Access`,
`network segmentation`, `Firewalls Insight`

### AI Sec
`OpenAI`, `AWS Bedrock`, `ProtectAI`, `LAKERA`, `Prompt Security`, `HiddenLayer`,
`Enkrypt AI`, `Robust Intelligence`, `AI Security`, `LLM`, `GenAI`

### Sec Ops
`SIEM`, `SOAR`, `XDR`, `NDR`, `EDR`, `CTEM`, `threat detection`, `SOC`, `Splunk`,
`Microsoft Sentinel`, `IBM Qradar`, `Exabeam`, `Vectra`, `Darktrace`, `Tines`

### CNAPP
`CNAPP`, `CSPM`, `CWPP`, `CASB`, `Container Security`, `DSPM`, `Kubernetes`,
`Prisma Cloud`, `Wiz`, `Orca Security`, `Aqua Security`, `Sysdig`, `Lacework`

### AppSec
`Snyk`, `Veracode`, `Checkmarx`, `DAST`, `SAST`, `AppSec`, `SCA`, `RASP`,
`application security`, `code scanning`

### Identity
`Okta`, `Microsoft Entra ID`, `Microsoft Active Directory`, `CIEM`, `IAM`,
`Privileged Access`, `identity`

### Endpoint
`EDR`, `CrowdStrike`, `SentinelOne`, `endpoint`, `EPP`, `MDR`

---

## Competitor keyword → use case

Scan `config.account_research.queries_sections.competitors` for these keywords:

| Competitor keyword | Use case(s) |
|-------------------|-------------|
| Palo Alto Prisma Access, Zscaler, CATO Networks | Network Sec |
| Palo Alto Networks Firewall, Checkpoint Firewall, Cisco, SonicWall | Network Sec |
| Cloudflare, Akamai, F5 | Network Sec |
| ProtectAI, LAKERA, Prompt Security, HiddenLayer | AI Sec |
| Robust Intelligence, Enkrypt AI, Microsoft Copilot | AI Sec |
| CrowdStrike, SentinelOne, Microsoft Defender | Sec Ops / Endpoint |
| Splunk, Microsoft Sentinel, IBM QRadar, Exabeam | Sec Ops |
| Vectra, Darktrace, Tines | Sec Ops |
| Wiz, Orca Security, Aqua Security, Sysdig, Lacework | CNAPP |
| Prisma Cloud | CNAPP |
| Snyk | AppSec |

---

## Detecting excluded use cases

A use case is **excluded** (do not report on it) if:

1. **No technology keyword** from that use case appears in `queries_sections.technologies`, AND
2. **No competitor keyword** from that use case appears in `queries_sections.competitors`

Additionally, if the tenant config includes an explicit `excluded_use_cases` array, exclude
those regardless of keyword presence.

### Special rule: AppSec

AppSec is excluded for a tenant if **none** of these appear in their tech or competitor lists:
`Snyk`, `Veracode`, `Checkmarx`, `DAST`, `SAST`, `AppSec`, `SCA`, `code scanning`.

Even if you detect AppSec-adjacent signals at the account (e.g. GitHub Actions, CI/CD),
do not surface AppSec as a use case if the tenant has excluded it.

---

## Fit score formula

For each use case that passes the inclusion test:

```
fit_score = (
  (signal_count * 2)           # Metabase signals mapped to this use case
  + (prospect_count * 1.5)     # Phoenix prospects mapped to this use case
  + (keyword_density * 3)      # 10-K keyword matches for this use case (capped at 3)
  + (competitor_present * 2)   # Known competitor in-seat at account
)
```

Normalise to 1–10 range. If no 10-K data: weight keyword_density as 0.
If no Phoenix data: weight prospect_count as 0.
Always show fit_score with one decimal place.

---

## Use case color assignments for HTML widget

```css
/* Network Sec */
--uc-network-bg: #E6F1FB; --uc-network-text: #185FA5; --uc-network-bar: #378ADD;

/* AI Sec */
--uc-ai-bg: #EEEDFE; --uc-ai-text: #534AB7; --uc-ai-bar: #7F77DD;

/* Sec Ops */
--uc-secops-bg: #E1F5EE; --uc-secops-text: #0F6E56; --uc-secops-bar: #1D9E75;

/* CNAPP */
--uc-cnapp-bg: #EAF3DE; --uc-cnapp-text: #3B6D11; --uc-cnapp-bar: #639922;

/* AppSec */
--uc-appsec-bg: #FAEEDA; --uc-appsec-text: #854F0B; --uc-appsec-bar: #EF9F27;

/* Identity */
--uc-identity-bg: #FAECE7; --uc-identity-text: #993C1D; --uc-identity-bar: #D85A30;

/* Endpoint */
--uc-endpoint-bg: #F1EFE8; --uc-endpoint-text: #5F5E5A; --uc-endpoint-bar: #888780;
```
