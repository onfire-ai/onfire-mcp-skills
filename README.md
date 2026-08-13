# onfire-mcp-skills

Claude Agent Skills for the [Onfire](https://onfire.ai) MCP — a B2B go-to-market data
lake and CRM tooling layer. The skills route a question to the right tool and enforce
the playbook around it: consent gates on paid operations, tenant identity from OAuth,
and a house style for the customer-facing reports.

Installed as a Claude Code plugin. When someone enables it, **these instructions are
followed by their agent** — see [SECURITY.md](SECURITY.md) before contributing.

## What's here

24 skills:

| Group | Skills |
|---|---|
| Identity resolution | `match-person`, `match-company`, `deanonymize-emails` |
| Prospecting & contact data | `ai-prospecting`, `contact-data-enrichment` |
| Entity search | `entity-people-search`, `entity-company-search` |
| Signal layers | `airgap-opportunity`, `hiring-signals`, `event-attendance-signals`, `github-repo-signals`, `employee-footprint`, `company-growth-trends`, `title-movement`, `office-segmentation` |
| Community | `community-message-search`, `community-messages-sentiment`, `community-join-signals` |
| Reports | `account-research`, `competitor-report` |
| Sequences & CRM writes | `sep-cadence-enrollment`, `outreach-sequence-email-composer`, `gong-create-and-push-to-flow` |
| Recurring | `weekly-territory-plan` (the 5x5) |

Each skill is a directory under `skills/` with a `SKILL.md`, plus `references/` for
detail the agent loads on demand and `assets/` for templates and scripts.

## Working on this repo

Install the hooks once per clone — they are not automatic:

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

Run the checks CI runs:

```bash
python3 scripts/check_skill_policy.py
```

```bash
python3 -m venv .venv && .venv/bin/pip install "openpyxl==3.1.5" && .venv/bin/python -m unittest discover -s tests
```

`gitleaks` needs the binary on PATH (`brew install gitleaks`); CI runs it pinned in
Docker over the full history.

### Rules that are enforced, not suggested

- **No real personal data anywhere**, including examples. Gitleaks blocks emails, phones,
  SSNs, cards and LinkedIn profile URLs; names it cannot catch, so reviewers must. Write
  examples inside these ranges and they pass by construction — no config edit, no red
  build:

  | Kind | Use | Why it is safe |
  |---|---|---|
  | Email | `pat@example.com`, `x@anything.test`, `dev@foo.invalid` | RFC 2606 / 6761 reserved — IANA will not delegate them |
  | Phone | `+15551234567`, `+1 (555) 123-4567`, `555-0142` | 555 is never assigned as an area code, and no consumer line is issued in the 555 exchange |
  | LinkedIn | `linkedin.com/in/example-<anything>` | `example-` is the repo's synthetic-person prefix |
  | Names | `Jane Doe`, `John Doe`, `Northwind` | placeholder register |

  A value outside these ranges is treated as real PII, which is the right default for a
  public repo. If you genuinely need a new range, add it to `.gitleaks.toml` **and** add
  a vector to `scripts/check_pii_allowlist.py` — that test asserts both directions
  (fakes stay exempt, realistic values stay caught) so a widening can't open a hole
  quietly.
- **Generated files are self-contained.** No remote fonts, scripts, stylesheets or
  images in a report — they travel to people the author did not choose, and a remote
  fetch tells a third party who opened it and when.
- **Exported cells are inert.** Everything in a CSV or workbook came from a profile, a
  community message or a model draft; none of it is trusted enough to be a formula.
- **Dependencies are pinned and isolated.** A venv with an exact version, never a global
  install into the user's interpreter.
- **Tool identifiers are exact.** No resolving an MCP tool by scanning the ambient tool
  list: short names are guessable, so any other connected server can answer to one.
- **Logs carry shapes, not values.** Field names and a status, never a raw tool response.

`scripts/check_skill_policy.py` enforces the mechanical half of that list. Each rule
traces to a finding in a security, privacy and compliance review; if you have a genuine
counter-example (documentation showing the wrong way), mark the line `policy-ok: <why>`.

## Reporting a security or privacy problem

Email **security@onfire.ai**. Do not open a public issue. See
[SECURITY.md](SECURITY.md).

## License

Copyright (c) 2026 Onfire AI Ltd. All rights reserved — **not open source**. You may
read, evaluate and install these skills unmodified to use the Onfire MCP; redistribution,
modification and derivative works need written permission. See [LICENSE](LICENSE).
