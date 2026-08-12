#!/usr/bin/env python3
"""Fail the build when a skill reintroduces a pattern we removed on purpose.

Every rule here corresponds to a finding in the 2026-08-10 security, privacy and
compliance audit. They are cheap greps, not analysis -- their job is to stop a
quiet regression six months from now, when the reason a line was written this
way has left the room. A rule that starts crying wolf is worse than no rule, so
each one is anchored as tightly as the pattern allows and carries the sentence a
contributor needs to fix it.

Escape hatch: put `policy-ok` on the offending line or the line directly above
it, with a reason. Documentation that deliberately shows the wrong way needs it.

    python3 scripts/check_skill_policy.py

Exit status is 0 when clean, 1 when any rule fires.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = "skills/weekly-territory-plan/assets/artifact_template.html"
BUILDER = "skills/weekly-territory-plan/assets/pg_plan_builder.py"

# (id, human message, compiled pattern, glob) -- a match anywhere is a failure.
FORBIDDEN = [
    (
        "global-pip-install",
        "Installing into the user's interpreter. Use a throwaway venv with a pinned\n"
        "     version instead: python3 -m venv .venv-x && .venv-x/bin/pip install \"pkg==1.2.3\"",
        r"--break-system-packages",
        "skills/**/*.md",
    ),
    (
        "remote-webfont",
        "Remote webfont. Generated reports travel to people the author did not pick;\n"
        "     a font link turns every open into a third-party request carrying their IP.\n"
        "     Use the --font-sans / --font-serif system stacks.",
        r"fonts\.(googleapis|gstatic)\.com",
        "skills/**/*.md",
    ),
    (
        "ambient-tool-discovery",
        "Resolving an MCP tool by scanning the ambient tool list. Short names are\n"
        "     guessable, so any other server in the workspace can answer to one. Use the\n"
        "     exact identifier the agent substituted into TOOLS, and fail closed.",
        r"listMcpTools",
        "skills/**/*.html",
    ),
    (
        "raw-payload-logging",
        "Logging a raw tool response. These payloads carry names, emails, phone numbers\n"
        "     and profile ids. Log fieldNames(x) and a status instead -- shapes, not values.",
        r"console\.\w+\([^)]*\b(raw|payload|payloads|consent|result)\s*:",
        "skills/**/*.html",
    ),
    (
        "unescaped-rich-field",
        "Interpolating an agent-authored markup field without escRich(). glance and\n"
        "     mail.b share a document with callMcpTool; they get the <b>/<br> allowlist.",
        r"\+\s*(account\.glance|person\.mail\.b)\b",
        TEMPLATE,
    ),
    (
        "internal-warehouse-path",
        "Internal warehouse identifier in a public repo. Describe the data, not the table.",
        r"\b(silver|gold)\.[a-z_]+\.[a-z_]+",
        "skills/**/*.md",
    ),
]

# (id, human message, compiled pattern, path) -- absence is a failure.
REQUIRED = [
    (
        "csp-present",
        f"{TEMPLATE} must keep its Content-Security-Policy meta tag: it is what stops\n"
        "     injected markup from loading a remote script or beaconing the board out.",
        r"Content-Security-Policy",
        TEMPLATE,
    ),
    (
        "rich-sanitizer-present",
        f"{TEMPLATE} must keep escRich() -- the <b>/<br> allowlist for the two fields\n"
        "     the data contract lets the agent author as markup.",
        r"function escRich\(",
        TEMPLATE,
    ),
    (
        "csv-formula-guard",
        f"{TEMPLATE} must keep the apostrophe guard in csvCell(): CSV has no type\n"
        "     system, so it is the only thing stopping =HYPERLINK(...) from running.",
        r"""if \(/\^=/\.test\(s\)""",
        TEMPLATE,
    ),
    (
        "xlsx-string-typing",
        f"{BUILDER} must keep data_type = \"s\" in _write_cell(): openpyxl types a\n"
        "     leading = as a live formula otherwise.",
        r'data_type = "s"',
        BUILDER,
    ),
]


def scan(glob: str):
    """Yield (path, lineno, line, prev_line) for every file the glob selects."""
    paths = sorted(ROOT.glob(glob)) if "*" in glob else [ROOT / glob]
    for path in paths:
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            yield path, index + 1, line, (lines[index - 1] if index else "")


def excused(line: str, previous: str) -> bool:
    return "policy-ok" in line or "policy-ok" in previous


def main() -> int:
    failures = []

    for rule_id, message, pattern, glob in FORBIDDEN:
        regex = re.compile(pattern)
        hits = [
            (path, lineno, line)
            for path, lineno, line, previous in scan(glob)
            if regex.search(line) and not excused(line, previous)
        ]
        if hits:
            failures.append((rule_id, message, hits))

    for rule_id, message, pattern, target in REQUIRED:
        path = ROOT / target
        if not path.is_file():
            failures.append((rule_id, f"{target} is missing.", []))
            continue
        if not re.search(pattern, path.read_text(encoding="utf-8")):
            failures.append((rule_id, message, []))

    if not failures:
        checked = len(FORBIDDEN) + len(REQUIRED)
        print(f"skill policy: {checked} rules, all clean")
        return 0

    print("skill policy: FAILED\n")
    for rule_id, message, hits in failures:
        print(f"  [{rule_id}] {message}")
        for path, lineno, line in hits:
            print(f"     {path.relative_to(ROOT)}:{lineno}: {line.strip()[:100]}")
        print()
    print("Each rule traces to a finding in the security/privacy audit. If a hit is a")
    print("deliberate counter-example, add `policy-ok: <reason>` on or above the line.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
