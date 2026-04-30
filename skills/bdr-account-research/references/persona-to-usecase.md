# Persona → Use Case Mapping

Maps Phoenix prospect titles and AI reasoning signals to BDR use cases,
and defines buying committee priority tiers.

---

## Title keyword → primary use case

Use substring matching (case-insensitive) on `TITLE_NAME`:

### Network Sec
`network`, `infrastructure`, `SD-WAN`, `SASE`, `ZTNA`, `VPN`, `firewall`,
`connectivity`, `telecom`

### AI Sec
`AI`, `machine learning`, `ML`, `data science`, `GenAI`, `LLM`, `artificial intelligence`,
`model risk`, `AI risk`, `AI governance`

### Sec Ops
`SOC`, `security operations`, `threat`, `incident response`, `SIEM`, `detection`,
`forensics`, `threat intelligence`, `red team`, `blue team`, `purple team`

### CNAPP
`cloud security`, `cloud architect`, `DevSecOps`, `platform security`,
`container`, `Kubernetes`, `cloud engineer`, `SRE`, `DevOps`, `infrastructure security`

### Identity
`identity`, `IAM`, `access management`, `privileged`, `zero trust`

### Endpoint
`endpoint`, `EDR`, `device management`

---

## Tenant config persona → use case

Map from `config.account_research.buying_committee_queries` persona labels:

| Tenant persona label | Use case(s) |
|---------------------|-------------|
| `network_security_specialist` | Network Sec |
| `ztna_implementer` | Network Sec |
| `it_network` | Network Sec |
| `ai_security_specialist` | AI Sec |
| `soc_specialist` | Sec Ops |
| `secops` | Sec Ops |
| `cloud_security_specialist` | CNAPP |
| `kubernetes_security_specialist` | CNAPP |
| `cloud_governance_specialist` | CNAPP |
| `ciem_specialist` | CNAPP / Identity |
| `vulnerability_manager` | AppSec / Sec Ops |
| `endpoint_manager` | Endpoint |
| `vpn_specialist` | Network Sec |
| `threat_intelligence` | Sec Ops |
| `CISO`, `CIO` | All use cases (economic buyer) |

---

## AI reasoning signal → use case

Scan `ai_reasoning` field from Phoenix for these keyword patterns:

| Keywords in reasoning | Use case |
|----------------------|----------|
| `Kubernetes`, `Docker`, `container`, `OpenShift`, `Helm` | CNAPP |
| `Terraform`, `cloud-native`, `AWS`, `Azure`, `GCP`, `multi-cloud` | CNAPP |
| `CSPM`, `CWPP`, `CASB`, `DSPM`, `Prisma`, `Wiz`, `Aqua` | CNAPP |
| `SIEM`, `SOAR`, `XDR`, `NDR`, `threat detection`, `SOC` | Sec Ops |
| `Splunk`, `Microsoft Sentinel`, `QRadar`, `Exabeam` | Sec Ops |
| `IAM`, `Vault`, `access control`, `identity`, `ZTNA` | Network Sec / Identity |
| `AI`, `LLM`, `GenAI`, `model`, `Bedrock`, `Windsurf`, `MCP` | AI Sec |
| `DevSecOps`, `CI/CD`, `pipeline security`, `code security` | CNAPP / AppSec |
| `network`, `firewall`, `SD-WAN`, `MPLS`, `VPN` | Network Sec |

A prospect may map to multiple use cases. Show them in the section for their
**primary** use case (highest keyword count) and cross-reference in secondary sections.

---

## Buying committee priority tiers

### High — Economic buyers
- C-suite: CISO, CIO, CTO, CTRO, CEO, COO
- VP-level: VP Security, VP Engineering, VP Cloud, VP Infrastructure
- Directors with budget authority: Director Security, Director Cloud Security
- Distinguished Engineers / Fellows (technical authority + executive access)
- Named in 10-K as responsible for cybersecurity program

### Medium — Technical champions and influencers
- Senior Managers with platform/architecture scope
- Principal / Staff / Lead Engineers in security domains
- Architects: Enterprise Architect, Cloud Security Architect, Solutions Architect
- Program managers with security delivery scope

### Support — End users and technical validators
- Individual contributors: Engineers, Analysts, SREs
- Specialists: DevOps Engineers, Platform Engineers, Security Engineers
- Early-tenure roles (< 6 months in seat)

---

## Receptivity signals from Phoenix reasoning

The following patterns in `ai_reasoning` indicate higher outreach receptivity:

| Pattern | Implication |
|---------|------------|
| `golden window`, `X months in role` | New in role — more open to change |
| `attending [conference]` | Actively evaluating vendors |
| `warm`, `ecosystem alumni` | Prior relationship with vendor ecosystem |
| `recently promoted` | Expanded mandate, new budget cycle |
| `consolidating`, `eliminating inefficiencies` | Active cost/tool optimisation |
| `driving`, `leading` near technology initiative | Decision authority |

Surface the top 2–3 receptivity signals per prospect in their card.

---

## Signal holder → prospect matching

When a Metabase signal has an `intent_holder_linkedin_url`, attempt to match it
against Phoenix prospect `LINKEDIN_URL` values:

```
normalize(url) = url.lower().strip('/').replace('https://','').replace('www.','')
match = any(normalize(signal_url) in normalize(prospect_url) or vice versa)
```

If matched: merge the signal data and Phoenix prospect data into a single enriched
card, showing both the intent signal (source, date, summary) and the AI reasoning.

If not matched: show the signal holder as a standalone entry in the signals table
with whatever name/title is available from the signal record.
