## What & why

<!-- Briefly describe the change and the motivation. -->

## Skill security checklist

Confirm each item (see `SECURITY.md` for detail). PRs that add or change skills,
the plugin manifest, hooks, MCP servers, or scripts require a `developers`
code-owner review.

- [ ] No secrets or PII — synthetic placeholders only (no real names, emails,
      phones, LinkedIn profiles, CRM/record IDs, keys, or tokens).
- [ ] No hidden/invisible Unicode (zero-width, bidi-override, Unicode Tags).
- [ ] No prompt-injection or data-exfiltration directives in `SKILL.md`/references
      (no "ignore previous", no reading credentials/env/`~/.ssh`/`/etc`, no
      sending output to external endpoints).
- [ ] No new `hooks` / `.mcp.json` / scripts without explicit maintainer sign-off;
      no dynamic remote code execution.
- [ ] No unjustified `allowed-tools` escalation (especially shell execution).
- [ ] Secrets referenced by env-var name only — never hardcoded.
