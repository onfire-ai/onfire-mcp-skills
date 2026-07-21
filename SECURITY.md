# Security Policy

This repository publishes **Claude Agent Skills**. When someone installs the
plugin, the skills' instructions are trusted and followed by their agent, and
any bundled hooks / MCP servers / scripts run in their session. Treat every
change as something that will execute on other people's machines.

## Reporting a vulnerability or data exposure

Do **not** open a public issue for a security problem or a suspected PII/secret
leak. Email **security@onfire.ai** with details and we will respond privately.

## What is automatically enforced

- **Local pre-commit/pre-push hook** (gitleaks) scans staged changes and full
  history for secrets and PII (emails, phones, SSNs, cards, LinkedIn URLs, and
  hidden/invisible Unicode). See `.gitleaks.toml` / `.pre-commit-config.yaml`.
  Install once per clone: `pre-commit install --hook-type pre-commit --hook-type pre-push`.
- **Branch protection on `main`**: PRs only, one non-author approval, code-owner
  review, admins included; only the `developers` team can merge.
- On the public repo, GitHub **secret scanning + push protection** provide a
  server-side gate that cannot be bypassed with `--no-verify`.

## Skill contribution review checklist

Automated scanning cannot catch everything (especially free-text names and
injected natural-language directives). Reviewers must manually confirm, for
every PR:

- [ ] **No secrets or PII** — no keys/tokens/passwords, and no real personal or
      customer data (names, work emails, phone numbers, LinkedIn profiles,
      CRM/record IDs) in `SKILL.md` or examples. Use synthetic placeholders.
- [ ] **No hidden Unicode** — no zero-width, bidirectional-override, or Unicode
      Tag characters used to smuggle invisible instructions.
- [ ] **No prompt injection** — no "ignore previous instructions", no directives
      telling the agent to read credentials, environment variables, `~/.ssh`,
      `/etc`, or files outside the working directory, and no data-exfiltration
      instructions (sending output to an external endpoint).
- [ ] **No new code-execution surface without sign-off** — new `hooks`, MCP
      servers (`.mcp.json`), or bundled scripts get explicit maintainer review.
      No dynamic code download/execution (e.g. piping a remote script into a
      shell).
- [ ] **No `allowed-tools` escalation** — broadening a skill's declared tools
      (especially shell execution) must be justified in the PR description.
- [ ] **Secrets by reference only** — skills name environment variables; they
      never hardcode credential values.

## For people installing these skills

- Review a skill before enabling it — read the `SKILL.md` and any scripts.
- You can disable skill shell execution in managed settings
  (`disableSkillShellExecution: true`) if you want a stricter posture.
