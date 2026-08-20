#!/usr/bin/env python3
"""Test that .gitleaks.toml's PII allowlist exempts fakes and still catches real PII.

The allowlist is a security control with a usability failure mode in both
directions. Too narrow and every contributor writing an example gets a red
build for no reason they can infer -- that is what happened with `+14155551234`.
Too wide and a real prospect's email slips into a public repo silently. A regex
that does the first is annoying; a regex that does the second is the leak this
repo scans for. Neither is visible by reading the pattern, so it gets vectors.

WHY THE MUST-BE-CAUGHT VECTORS ARE ASSEMBLED FROM FRAGMENTS
-----------------------------------------------------------
These vectors have to be things the allowlist does NOT exempt -- otherwise they
prove nothing. "Not exempt" is the space where real personal data lives, so the
first version of this file reached for realistic-looking values: a named
executive at a real corporate domain, two real LinkedIn profiles, a phone
number in an assignable range. Then, because the repo scan flagged them, the
file was added to the scanner's own exclusion list.

That is the failure this repo exists to prevent, committed inside the test for
it. Public repo, real identifiers, hidden from the control by the control's own
config.

So every must-be-caught vector is now built from two properties instead:

  1. It MATCHES the rule shape -- otherwise the test is vacuous.
  2. It CANNOT belong to anybody, by construction, not by looking unlikely:
       - phones use area codes and exchanges starting with 0 or 1, which NANP
         permanently forbids. No such number can be dialled, ever.
       - domains end in a TLD that does not exist and is not applied for, or in
         .invalid, which RFC 6761 guarantees will never resolve.
       - handles use the placeholder register (Jane Doe / John Doe / Northwind).

And they are assembled at runtime from fragments, so no matchable literal
appears in this source file. That is what lets the file be scanned like every
other file, with no exclusion. If you add a vector, keep both properties: build
it from pieces, and make it structurally impossible rather than merely obscure.

    python3 scripts/check_pii_allowlist.py --write-fixtures /tmp/pii-fixtures
    gitleaks dir --config .gitleaks.toml --report-format json \\
        --report-path /tmp/pii-fixtures/report.json --exit-code 0 \\
        /tmp/pii-fixtures
    python3 scripts/check_pii_allowlist.py --verify /tmp/pii-fixtures/report.json

`--exit-code 0` matters: this scan is SUPPOSED to find the must-be-catch
vectors, so a nonzero exit is the expected outcome, not a failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Fragments. Kept apart so this file contains no string a PII rule can match.
# ---------------------------------------------------------------------------
_AT = "@"
_PLUS_ONE = "+" + "1"
# TLDs that cannot host a mailbox: .invalid is reserved unresolvable by RFC 6761,
# and the other is not a delegated TLD and is not in any application round.
_DEAD_TLDS = ("invalid", "nx" + "tld")
# NANP forbids 0 and 1 as the leading digit of both the area code and the
# exchange, so every number built from these is permanently undialable.
_DEAD_AREA = ("000", "111")
_DEAD_EXCH = ("000", "100")


_LI_PREFIX = "linkedin" + ".com/in/"


def _mail(local: str, *labels: str) -> str:
    return local + _AT + ".".join(labels)


def _handle(name: str) -> str:
    return _LI_PREFIX + name


def _e164(area: str, exch: str, last: str) -> str:
    return _PLUS_ONE + area + exch + last


def _dashed(area: str, exch: str, last: str) -> str:
    return f"{area}-{exch}-{last}"


# Values a contributor might plausibly write in an example. Every one MUST be
# exempt -- if any of these fails CI, the allowlist is too narrow and the next
# person to write a skill example is blocked with no way to know why. These are
# safe as literals precisely because the allowlist exempts them.
FAKES = [
    # 555 area code, and 555 exchange in a real area code (both conventions)
    "+15551234567",
    "+14155551234",
    "+1 (555) 555-1234",
    "+1-555-0100",
    "555-0142",
    "(555) 123-4567",
    # RFC 2606 / 6761 reserved, as the final label
    "pat@example.com",
    "sam@subdomain.example.org",
    "dev@widgets.example",
    "qa@anything.test",
    "x@foo.invalid",
    # repo conventions
    "linkedin.com/in/example-person-7",
    "linkedin.com/in/example-person-100",
    "linkedin.com/in/example-buyer",
    "linkedin.com/in/example-cto-acme",
    "linkedin.com/in/johndoe",
    "onfire-ai@onfire.ai",
]


def must_be_caught() -> list[tuple[str, str]]:
    """(vector, what it proves). Assembled, never literal. Nobody's data."""
    dead, nxtld = _DEAD_TLDS
    return [
        # Basic detection: a phone-shaped and mail-shaped value outside every
        # exempt range still gets reported.
        (_e164(_DEAD_AREA[0], _DEAD_EXCH[0], "0000"),
         "E.164 outside the 555 space is still detected"),
        (_dashed(_DEAD_AREA[1], _DEAD_EXCH[1], "1000"),
         "formatted phone outside the 555 space is still detected"),
        (_mail("jane.doe", "northwind", nxtld),
         "ordinary address at a non-reserved domain is still detected"),
        # Boundary: "example" as a PREFIX of a longer label must not inherit the
        # example.com exemption.
        (_mail("j.doe", "examplecorp", nxtld),
         "examplecorp is not example.<tld>"),
        # Boundary: the reserved name must be the LAST label. An unanchored \b
        # let it match as a subdomain, which exempted real addresses.
        (_mail("j.doe", "test", "northwind", nxtld),
         "a reserved word as a SUBDOMAIN must not exempt the domain"),
        (_mail("j.doe", "localhost", "northwind", nxtld),
         "localhost as a subdomain must not exempt the domain"),
        (_mail("j.doe", "example", "northwind", nxtld),
         "example as a subdomain must not exempt the domain"),
        # Boundary: our own domain is exempt; a neighbouring TLD is not.
        (_mail("someone", "onfire", nxtld),
         "onfire.<other tld> is not onfire.ai"),
        # Boundary: "example-" is the LinkedIn convention; a longer word is not.
        (_handle("examplary-person"),
         "examplary- is not example-"),
        (_handle("northwind-buyer"),
         "an ordinary handle is still detected"),
        # .invalid is exempt as a final label, so this pairs with the subdomain
        # cases above: same reserved word, wrong position.
        (_mail("j.doe", dead, "northwind", nxtld),
         "invalid as a subdomain must not exempt the domain"),
    ]


def write_fixtures(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "fakes.txt").write_text(
        "Synthetic placeholders. None of these may be reported.\n"
        + "\n".join(FAKES) + "\n",
        encoding="utf-8",
    )
    caught = must_be_caught()
    (target / "reals.txt").write_text(
        "Outside every exempt range. Every one of these must be reported.\n"
        + "\n".join(v for v, _ in caught) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(FAKES)} exempt and {len(caught)} must-catch vectors to {target}")


def verify(report: Path) -> int:
    if not report.is_file():
        print(f"FAIL: no gitleaks report at {report}. Did the scan step run?")
        return 1

    text = report.read_text(encoding="utf-8").strip()
    findings = json.loads(text) if text else []

    reported: dict[str, set[str]] = {"fakes.txt": set(), "reals.txt": set()}
    for finding in findings:
        name = Path(finding.get("File", "")).name
        if name in reported:
            reported[name].add(finding.get("Match", "").strip())

    def hit(value: str, bucket: str) -> bool:
        """A vector counts as reported if any finding's match overlaps it.

        Containment in both directions: gitleaks reports the matched span, which
        for a formatted phone can be a substring of the vector.
        """
        return any(m and (m in value or value in m) for m in reported[bucket])

    false_positives = [v for v in FAKES if hit(v, "fakes.txt")]
    missed = [(v, why) for v, why in must_be_caught() if not hit(v, "reals.txt")]

    if not false_positives and not missed:
        print(f"PII allowlist: {len(FAKES)} exempt as intended, "
              f"{len(must_be_caught())} caught as intended — correct")
        return 0

    print("PII allowlist: FAILED\n")
    if false_positives:
        print("  Too NARROW — these synthetic placeholders were reported as real PII.")
        print("  A contributor writing one of these gets a red build for no reason:")
        for v in false_positives:
            print(f"     {v}")
        print("  Fix: widen the matching range in .gitleaks.toml [allowlist].\n")
    if missed:
        print("  Too WIDE — these were NOT reported. Each one is a leak path: real")
        print("  PII of this shape would reach a public repo unnoticed.")
        for v, why in missed:
            print(f"     {v}\n        should prove: {why}")
        print("  Fix: tighten the range that swallowed them. Do not delete the vector.\n")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-fixtures", metavar="DIR",
                       help="write the test vectors to DIR for gitleaks to scan")
    group.add_argument("--verify", metavar="REPORT",
                       help="check a gitleaks JSON report against the expectations")
    args = parser.parse_args()

    if args.write_fixtures:
        write_fixtures(Path(args.write_fixtures))
        return 0
    return verify(Path(args.verify))


if __name__ == "__main__":
    sys.exit(main())
