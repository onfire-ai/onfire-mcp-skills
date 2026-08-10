---
name: airgap-opportunity
description: Find and report air-gap demand signal — accounts, people and evidence about air-gapped, isolated, disconnected, cross-domain and classified environments. Use whenever someone asks about air gap, air-gapped, isolated or disconnected networks, data diodes, cross domain solutions, SCIF/SIPR/JWICS/classified networks, offline or DDIL deployment, or asks "who is working on air-gap", "air-gap opportunity", "air-gap accounts", "air-gap signals", "air-gap volume", or wants an air-gap prospect list or report. Anchored on the curated `Air-Gapped Environment` and `Cross Domain / Data Diode` insights, with `search_community_messages` and `query_intent_signals` for verbatim evidence.
---

# airgap-opportunity

Finds accounts, people and evidence around **air-gapped, isolated and disconnected environments** and returns them as a prospect list or a report.

Built for tenants selling into isolated networks — ZTNA, secure remote access, privileged access, cross-domain and OT security. The commercial premise: isolation alone is no longer treated as a control. OT-visibility vendors have largely won the "see inside the network" argument; the open question in these conversations is *who gets in and what they can reach*. This skill finds the people asking it.

---

## The matching rule — read this first

**Accuracy beats coverage.** A short, certain list is the deliverable. A long, noisy one is a failure.

Matching is a three-stage gate. All three apply, in order:

```
STAGE 1  MUST   — Group A (the environment itself). At least one term. Non-negotiable.
                  AND
STAGE 2  SHOULD — at least one term from Groups B–F (OR between all of them).
                  AND NOT
STAGE 3  NOISE  — none of the exclusion patterns.
```

Never return a match on Groups B–F alone. "SCADA", "zero trust", a ZTNA product name or "Kubernetes" without a Group A term is **not** an air-gap signal — it is generic security or infrastructure chatter and must be dropped.

---

## Group A — the environment itself (MANDATORY)

At least one of these must be present.

```
air gap · air-gapped · airgapped · airgap · air-gapped network · air gapped environment
isolated network · network isolation · physically isolated · physical isolation · standalone network
disconnected environment · disconnected network · disconnected cluster · disconnected install
offline deployment · offline install · offline registry · offline mirror
data diode · unidirectional gateway · unidirectional security gateway · one-way transfer
cross domain solution · cross-domain guard · CDS
sneakernet · removable media transfer
SCIF · classified network · SIPR · NIPR · JWICS · IL5 · IL6
DDIL · denied degraded intermittent limited
sovereign cloud · on-prem repatriation
```

**Precision note:** the bare phrase "air gap" has physical-engineering homonyms (transformer cores, HVAC, PC case airflow, construction). The compound terms — data diode, cross domain solution, disconnected cluster, offline registry — are effectively fully precise. When the user wants maximum certainty, restrict Group A to the compound terms only.

---

## Groups B–F — context (OR between all of them)

At least one term from anywhere in B–F. These never stand alone; they qualify a Group A hit and tell you which play it belongs to.

### B · OT, ICS and critical infrastructure
```
OT security · operational technology · IT/OT convergence · IT/OT DMZ · ICS · industrial control system
SCADA · DCS · PLC · HMI · RTU · data historian · Modbus · DNP3 · OPC UA · Profinet · EtherNet/IP
Purdue model · Purdue Level 3.5 · ISA-95 · zones and conduits
IEC 62443 · NERC CIP · NIS2 · Cyber Resilience Act · CMMC · FedRAMP High
safety instrumented system · critical infrastructure · cyber-physical systems · IIoT
```

### C · The access capability
```
secure remote access · privileged remote access · vendor remote access · third-party access
jump host · jump server · bastion host · privileged access workstation · just-in-time access
network segmentation · microsegmentation · zero trust · ZTNA · software-defined perimeter · SDP
least privilege · defense in depth · SASE · MFA · conditional access
```

### D · ZTNA / secure-access products
```
Zscaler Private Access · Zscaler ZPA · Zscaler Internet Access
CrowdStrike Falcon Private Access · Netskope Private Access · Netskope NPA
Palo Alto Prisma Access · Prisma SASE · Cisco Duo Beyond · Cisco Secure Access · Cisco AnyConnect · Cisco ISE
Fortinet ZTNA · FortiClient · FortiGate · Cloudflare Access · Cloudflare Zero Trust · Cloudflare One
Tailscale · Twingate · Teleport · StrongDM · Perimeter 81 · Check Point Harmony SASE
Cato Networks · Versa Networks · Zero Networks · OpenZiti · Banyan Security · Axis Security
GoodAccess · NordLayer · Cloudbrink · Knocknoc · Border0 · OpenVPN
```

### E · OT remote access, cross-domain, PAM, OT visibility, identity
```
OT remote access:  Cyolo · Xage Security · Dispel · Claroty xDome · Claroty Secure Remote Access
                   TXOne Networks · TXOne SafePort · BlackBear ICS · Siemens SINEC · Honeywell SRA
Cross-domain:      Owl Cyber Defense · Owl data diode · Waterfall Security · Waterfall HERA
                   Fox-IT DataDiode · Forcepoint CDS · Garrison · OPSWAT · MetaDefender · MetaDefender Kiosk
PAM:               CyberArk · BeyondTrust · BeyondTrust EPM · Delinea · Delinea Secret Server · Thycotic
                   HashiCorp Boundary · HashiCorp Vault · Apache Guacamole · Wallix · Senhasegura
OT visibility:     Claroty · Nozomi Networks (Guardian/Vantage/Arc) · Dragos · Armis · Forescout
                   Tenable OT · Indegy · Microsoft Defender for IoT · Cisco Cyber Vision
Identity:          Okta · Ping Identity · Microsoft Entra ID · Azure AD · OneLogin · ID.me
                   SailPoint · Saviynt · Active Directory · PKI · YubiKey · smart card / CAC
```

### F · Platforms where the air-gap problem surfaces
```
Kubernetes · Red Hat OpenShift · Rancher · Harvester · VMware Tanzu · Zarf · Harbor · Helm
Argo CD · Flux · Docker registry · JFrog Artifactory · Sonatype Nexus · Red Hat Satellite
Ansible · Terraform · Elastic · Splunk · Wazuh · Tanium · IBM QRadar · Cortex XSOAR
```

Group F matters operationally — getting Kubernetes, OpenShift, Rancher, Harbor or Artifactory into a disconnected environment is one of the most repeated complaints in this space, and it is the moment a platform team goes looking for an access answer.

---

## Stage 3 — noise exclusions (MUST NOT match)

### Physical-world homonyms
Drop matches where "air gap" refers to physical engineering rather than networks:
```
air gap under / beneath / between the · slot · GPU · cooler · heatsink · woofer · speaker
HVAC · insulation · window · drywall · transformer core · PCB trace · capacitor · case fan · airflow
```

### Vendors and competitors — drop the person, not just the message
Never present someone employed by a vendor in this category as a prospect. Build the exclusion list from the tenant's own competitor set via `get_tenant_settings` (`account_research.competitors`), and extend it with the vendors named in Groups D and E.

### Marketing and non-buyer content
Drop booth promotion, event marketing, product broadcast and tutorial content. Tells: `booth #`, `swing by`, `come see`, `join us`, `register`, `webinar`, `exhibiting`, `Day N of my journey`, heavy hashtag stacking, third-person product copy.

**Keep** first-person problem statements: "we have", "we are running", "our environment", "I'm working on", "I need", "how do I", "has anyone tried", "?".

---

## Retrieval — two paths, use both

### Path 1 · Curated insights (preferred, highest precision)

Two curated insights encode Group A. Use these first — they are deduped and far more precise than text matching.

| Insight value | Kind | Covers |
|---|---|---|
| `Air-Gapped Environment` | technology | air gap, air-gapped, airgap environment, disconnected environment/cluster, offline install/deployment/registry/mirror, physical isolation, physically isolated, standalone network, sneakernet, DDIL |
| `Cross Domain / Data Diode` | technology | cross domain solution, data diode |

Confirm with `resolve_insights(["air-gapped environment","cross domain solution"])`, then query with `ask_onfire`:

```json
{
  "entity": "company",
  "insight_filters": [{"kind": "technology", "value": ["Air-Gapped Environment", "Cross Domain / Data Diode"]}],
  "select": ["name", "website", "industry", "size_band", "location_country"],
  "limit": 50
}
```

For people use `entity: "contact"` with the same filter, selecting `full_name, job_title, current_company_name, linkedin_url`. Pass both values as a **list inside one filter** to OR them; use separate `insight_filters` entries only when both must be true.

Always call `describe_onfire_schema(["contact","company"])` before authoring the QueryIR — field names are specific (`current_company_name`, not `company_name`).

Narrow firmographically with `entity-company-search` / `entity-people-search`, and size accounts with `get_company_headcount`.

### Path 2 · Raw evidence (verbatim quotes and freshest signal)

Curated insights give the account list; messages give the quote a rep can open with.

- `search_community_messages` — semantic. Pass 1–3 natural-language phrasings of the same intent, e.g. `["deploying software in an air-gapped or disconnected environment", "securing OT/ICS networks isolated from the internet", "remote access into segmented industrial or classified networks"]`. Ask the user for a time window before searching. Rows hit by 2–3 phrasings are the strongest.
- `query_intent_signals` — structured non-message events (job changes, job posts, event attendance) with `keyword_match` set to Group A terms.
- `detect_warm_intros` — a path in once an account is chosen.

---

## Scoring — rank by play, not by volume

Assign each signal to the highest-priority play it qualifies for:

1. **Access into the isolation** — Group A + (`remote access`, `vendor access`, `third-party access`, `jump host/box/server`, `bastion`, `ssh key`, `privileged access`, `proxy through`, `who can access`). The exact product surface. Highest priority.
2. **OT / classified operator** — Group A + (`SCADA`, `OT security`, `industrial control`, `PLC`, `classified`, `SIPR`, `SCIF`, `Purdue`). Compliance budget, regulated buyer.
3. **Cross-domain / diode** — Group A compound terms. Defence and critical infrastructure only, effectively no false positives.
4. **Platform / deployment pain** — Group A + Group F. Highest volume, lowest individual intent; best for community presence rather than outbound.

Boost within a play for: **2+ people at the same account**, **new in seat under 12 months**, **repeat threads from the same person**, **an incumbent named with dissatisfaction**, **a message under 90 days old**.

---

## Output

Ask which the user wants if unclear. Default to the prospect list.

### A · Prospect list / CSV

Columns, in order:

```
name,website,industry,employees,headquarters,linkedin_url,long_summary,
intent_holder_linkedin_url,date,source_type,source_link,message_text,
contact_name,job_title,location,last_update_date
```

Field rules:
- `name` … `linkedin_url` — the **account**. `linkedin_url` is the company page, `https://www.linkedin.com/company/{slug}`.
- `long_summary` — 1–3 sentences: the person's problem in their own terms, then why the tenant's product answers it. This is what the rep reads. Write it per row; never leave it blank.
- `intent_holder_linkedin_url` — the person, `https://www.linkedin.com/in/{slug}`.
- `date`, `last_update_date` — `Month D, YYYY, HH:MM AM` (full month name, no zero-padded day).
- `source_type` — `Slack`, `Discord`, `Reddit`, `Linkedin`, `Twitter`, `StackOverflow`, `Discourse`, `Company Change`, `Linkedin Job Post`, `Event Attendee`.
- `source_link` — the permalink returned with the message.
- `message_text` — verbatim, newlines collapsed to spaces.

### B · Report
Branded A4 HTML, optionally rendered to PDF. Structure that works: headline account and people counts with a growth curve → account breakdown (size descending, region, industry) → CRM coverage if a CRM is connected → keyword vocabulary → evidence cards → renewals. Keep evidence to roughly 10 of the sharpest signals rather than everything found.

When rendering to PDF, remember JavaScript charts do not execute in most HTML-to-PDF engines — build charts as HTML/CSS bars or inline SVG.

### C · Renewals
Use the tender / renewal-radar entity via `ask_onfire` for public-sector contracts with renewal dates and named incumbents. Filter to the tenant's product surface — zero trust, ZTNA, micro-segmentation, secure and privileged remote access, IAM/ICAM, cross-domain, classified network. **Exclude generic SCADA construction, plant maintenance and hardware refresh** — they carry the vocabulary but buy nothing in this category.

### D · CRM coverage (when a CRM is connected)
Match accounts to the tenant CRM on resolved company identity and web domain, and report matched versus net-new whitespace at **account level only**. Some CRM instances expose no Account relationship on Opportunity — where that is the case, do not attempt pipeline status; say so rather than inferring it.

---

## Presenting results

The reader is a GTM user, not an engineer. Lead with the people and what they said. Never surface internal mechanics — similarity scores, thresholds, corroboration counts, or the platform a message came from.

---

## Verification before delivering

1. **Every row has a Group A term.** Spot-check five at random. If any qualifies only on Groups B–F, the gate leaked.
2. **No vendor or competitor employees** presented as prospects.
3. **Attribution is correct.** Confirm the person on each evidence card is the actual message sender, not a same-name match. This is a real and easy error to make.
4. **Links resolve.** Person, company and source permalinks all well-formed.
5. **Counts trace to a query.** Never state a volume that was not returned by a tool call.
6. State the precision caveat: bare "air gap" carries physical-engineering homonyms, so a share of raw matches are non-IT; compound terms are effectively fully precise.
