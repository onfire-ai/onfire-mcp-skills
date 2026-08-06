# Deliverables

Every run produces three things, side by side. The artifact is where the rep works, the
standalone file is what they can forward, and the workbook is what they work the list
from. Deliver all three, every run.

| Deliverable | Purpose | Lifecycle |
|---|---|---|
| The artifact | the live working surface | one per rep, same id, updated in place |
| A standalone HTML file | shareable, forwardable | rewritten each run |
| A plan workbook (`.xlsx`) | the week's working list | **one file, appended** each run |

---

## 1. The artifact

See `artifact-template.md`. Create on setup, update on every run under
`state.artifact_id`, verify it rendered.

## 2. The standalone HTML file

An artifact cannot be exported or handed to a teammate, so the same rendered markup is
also written to a file at `state.report_path`.

- Rendered in **customer-facing mode** — it will be read by people who are not the rep.
- Both guard shims at the top of the script, with a neutral message.
- **Fully self-contained**: no external fonts, no external images, no external scripts.
  Any image is a data URI. System font stack only.
- Present it alongside the workbook so the rep always has the current pair.

## 3. The plan workbook

A styled `.xlsx` at `state.plan_workbook_path`, with a new week block appended beneath
the previous ones. **One file for the rep's whole history** — never a new file per week.

### Layout

One block per run, stacked top to bottom:

```
<BANNER>                                     <- plan_format.banner, cream
WEEK <n>  (week of YYYY-MM-DD)               <- accent fill
<ACCOUNT NAME, UPPER CASE>                   <- dark fill, one per account
CONTACT: | TITLE: | EMAIL ADDRESS: | PHONE NUMBER: | LINKEDIN: |
Touchpoint 1..5 | Completed? | Meeting Booked? | Notes
<one row per person>
                                             <- thin separator, then the next account
```

Thirteen columns. The touchpoint columns carry a dropdown seeded from
`plan_format.touchpoints`. The LinkedIn cell is a live hyperlink. `Completed?` and
`Meeting Booked?` are left empty — they belong to the rep. `Notes` carries the one-line
why-now, with the warm-intro sentence appended when there is one.

### Rules

- **Append, never recreate.** Open the existing workbook and add the new block. Create
  the file only when it does not exist.
- **Idempotent.** Re-running the same week must not produce a duplicate block. The
  builder checks for the week label before appending — a rep who runs it twice on a
  Monday should not get two identical weeks.
- **Never pad to a target count.** Three people at an account means three rows. No
  placeholder filler rows. This is the same rule as the resolver and the people layer,
  and the builder enforces it rather than trusting the caller.
- **Email and phone stay empty** unless the rep explicitly enriched that person. The
  workbook is not a place where contact data quietly appears.
- Deliver the file every run, so the rep always has the current version.

### Building it

`assets/pg_plan_builder.py` maintains the workbook. It needs `openpyxl`:

```bash
pip install openpyxl --break-system-packages
```

```python
from pg_plan_builder import add_week

add_week(
    path="Territory_Plan_<rep-slug>.xlsx",
    week_label="WEEK 2  (week of 2026-07-20)",
    accounts=[
        {"name": "Northwind", "contacts": [
            {"name": "Jane Doe", "title": "Director, Platform",
             "email": "", "phone": "",
             "linkedin": "https://linkedin.com/in/example-person-04",
             "notes": "Authored the account's why-now message, 12 Jul 2026",
             "warm": "Introduced by Jane Roe, shared 18 months at Continental Bank"},
        ]},
    ],
    touchpoints=["Personalized Email", "Event Invite", "Partner Engagement",
                 "Marketing Content", "Sequence Cadence"],
    banner="TERRITORY PLAN",
)
```

`accounts` is a list of `{name, contacts[]}`. Each contact takes `name`, `title`,
`email`, `phone`, `linkedin`, `notes`, and optionally `warm`. Leave `email` and `phone`
as empty strings. Pass `touchpoints` and `banner` from `plan_format` rather than
relying on the defaults, so a tenant's own vocabulary reaches the file.

### Why a workbook and not a Sheet

Worth recording, because it looks like an odd choice until you check the tooling.

The Drive connector can **create** files but cannot **edit** them. It has no cell
write, no append, no `batchUpdate`, no formatting, and no data validation. So a Google
Sheet cannot receive a new week block: each run would have to create a whole new file,
which loses the rep's edits and their history, and is exactly what "one file, appended"
exists to prevent. Styling and the touchpoint dropdowns are not expressible either.

A local `.xlsx` edited in place is currently the only way to meet the requirement. If a
Sheets connector with cell-write appears, this deliverable should move there — the
layout above is what it would need to reproduce. **Do not silently spawn a new sheet
per week as a workaround**; say what is not possible instead.

---

## Presenting

Present the standalone HTML and the workbook together at the end of every run, and tell
the rep what changed: how many accounts and people are new this week, how many warm
paths were found, and — when the count came in under the target — that it did, and why.

An honest short week is more useful than a padded full one, and saying so is what keeps
the ceiling from being read as a quota.
