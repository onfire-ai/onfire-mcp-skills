# Changelog

Versions match `.claude-plugin/plugin.json`, which is what the marketplace serves.
This file starts at 0.5.1; earlier versions predate it.

## 0.5.1 — 2026-08-12

Security and privacy hardening. Closes every code-level finding from a customer's
static security, privacy and compliance review of `2338e01`.

### Fixed

- **Weekly territory plan artifact.** `glance` and `mail.b` were the only fields
  reaching the page unrendered. The data contract already limited them to `<b>` and
  `<br>`; nothing enforced it, and the agent authors them from CRM notes and community
  messages. Added `escRich()` — escape everything, re-admit those two tags only.
- **Artifact CSP.** Added a Content-Security-Policy meta. Blocks remotely loaded
  scripts and image beacons. Deliberately no `default-src`, so the cowork bridge's
  host-defined transport keeps working.
- **MCP tool resolution.** `resolveTool` no longer scans the ambient tool list for a
  name ending in the expected short name. Short names are guessable, so any other
  connected server could register `<anything>__contact_data_enrichment` and receive a
  rep's prospect list. Exact substituted identifier only; fails closed.
- **Spreadsheet formula injection.** `csvCell` neutralises formula introducers, scoped
  so revealed phone numbers are not disfigured. The workbook builder forces
  `data_type = "s"` — openpyxl otherwise types a leading `=` as a live formula.
- **Workbook hyperlinks.** LinkedIn cells accept `http(s)` only; anything carrying its
  own scheme renders as plain text.
- **Workbook paths.** `add_week` rejects a non-`.xlsx` or non-file path instead of
  silently appending a rep's week to an unrelated workbook.
- **Diagnostic logging.** Three sites logged raw tool responses — emails, phones,
  profile ids — into the browser console. They now log field names and a status.
- **Dependency installs.** Three skills installed unpinned packages into the user's
  interpreter with the system-package override. Now a throwaway venv at an exact
  version (`openpyxl==3.1.5`, `weasyprint==69.0`).
- **Competitor report fonts.** Remote Google Fonts removed; every recipient who opened
  a brief was disclosing that to a third party. System stacks via `--font-sans` /
  `--font-serif`.
- **Public-repo hygiene.** Internal warehouse identifiers removed from a skill doc.
- **PII scanner false positives.** The gitleaks allowlist worked by enumerating the fake
  values already in the tree, so it failed the next author by construction: `+14155551234`
  was rejected while `+15551234567` passed, for no reason a contributor could infer. It
  now exempts *reserved ranges* instead of specific strings — RFC 2606/6761 domains, the
  555 phone space, `example-` LinkedIn handles. Same detection, no guesswork. A failure
  now also prints the conventions instead of a bare list of redacted fingerprints.

### Added

- `.github/workflows/security.yml` — gitleaks over full history, skill-policy checks,
  and the workbook tests, on every PR and every push to `main`. The gitleaks rules and
  pre-commit config already existed but ran nowhere: the hooks are opt-in per clone and
  `--no-verify` walks past them.
- `scripts/check_skill_policy.py` — 10 rules, one per pattern this release removed,
  with a `policy-ok` escape hatch for docs that show the wrong way on purpose.
- `scripts/check_pii_allowlist.py` — 28 vectors asserting the gitleaks allowlist in both
  directions: synthetic placeholders stay exempt, out-of-range values stay caught. Runs
  in CI before the repo scan, because an untested allowlist makes the scan meaningless
  either way. The boundary vectors are the point — a reserved word as a *subdomain* must
  not exempt the real domain under it, and `examplary-` is not `example-`. Every
  must-be-caught vector is assembled at runtime from NANP-invalid number ranges and
  non-existent TLDs, so the file contains no matchable literal, belongs to nobody, and
  needs no exclusion from the scanner.
- `tests/test_pg_plan_builder.py` — 13 tests asserting the property (zero formula
  elements in a saved workbook) rather than the implementation.
- `LICENSE` — proprietary, with an explicit grant to install and use. The repo was
  public with no grant at all.
- `README.md`, and `SECURITY.md` updated to describe the CI gate.
