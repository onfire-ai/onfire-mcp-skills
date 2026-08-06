# The state file, dedup, and where "done" lives

The promise this skill makes is that **nothing already worked comes back**. That
promise is kept by one file, and by being strict about which store owns what.

---

## Three tiers, and why

| Tier | Store | Holds | Rule |
|---|---|---|---|
| **1 — source of truth** | the state file, one per rep | every account and person surfaced per week, the suppression list, worked and dismissed flags, week history, last run | Read **before** generating. Written **after** delivering. Anything that must survive a rebuild lives here. |
| **2 — write-ahead buffer** | `window.storage` | this session's clicks: removed a person, dismissed a signal, marked something worked, revealed a contact or checked one and found nothing, view preferences | Written the moment the rep clicks, so the artifact survives a mid-week reload. **Drained into the state file at the start of the next run.** |
| **3 — banned** | `localStorage`, `sessionStorage` | nothing, ever | They fail inside artifacts. No exceptions, including view preferences — use `window.storage` for those too. |

The reason tier 2 exists at all: a dismissal that lives only in the browser
disappears when the schedule regenerates the board on Monday, so the rep dismisses
the same item every week. The reason tier 1 is authoritative: the scheduled run
rebuilds from the state file, not from browser storage, so anything the state file
does not know about **will** come back.

Draining is therefore not an optimisation. Skip it and the core promise breaks.

---

## Shape

Markdown, so a rep can read and hand-edit it. One file per rep at
`state.state_file_path`.

```markdown
# Territory plan state — <rep_owner>
last_run: 2026-07-20
weeks: 3

## Accounts surfaced
| week_of | account | domain | linkedin_slug | fit | tier | status | top_signal |
|---|---|---|---|---|---|---|---|
| 2026-07-20 | Northwind | northwind.example.com | northwind | 84 | ACT NOW | Working | Open platform roles, 12 Jul 2026 |

## People surfaced
| week_of | account | full_name | title | persona | linkedin_url | warm | why_now | status |
|---|---|---|---|---|---|---|---|---|
| 2026-07-20 | Northwind | Jane Doe | Director, Platform | PLATFORM | linkedin.com/in/example-person-04 | yes | Authored the account's why-now message, 12 Jul 2026 | Sequenced |

## Suppressed — never surface again
| linkedin_url_or_domain | kind | reason | added |
|---|---|---|---|
| linkedin.com/in/example-person-09 | person | rep removed, not relevant | 2026-07-13 |
| oldco.example.com | account | rep removed, out of patch | 2026-07-06 |

## Dismissed signals
| signal_key | account | reason | added |
|---|---|---|---|
| intent:2026-07-06:northwind:platform-cost | Northwind | handled | 2026-07-13 |

## Setup log
| asked | question_id | offered | answer | was_default |
|---|---|---|---|---|
| 2026-07-06 | A1_territory | — | Bay Area; Pacific Northwest | no |
| 2026-07-06 | B3_size_band | — | 500-5000 | no |
| 2026-07-06 | F13_cadence | Mon 07:00 / other | Mon 07:00 | yes |
| 2026-07-06 | F14_contact_offer | keep / skip | keep | yes |

## Config changes
| changed | field | before | after |
|---|---|---|---|
| 2026-07-20 | plan_shape.fit_floor | 70 | 75 |
```

Notes on the columns that matter:

- **`status` belongs to the rep.** Surfaced, Working, Sequenced, Replied, Meeting,
  Won, Dropped. The skill writes `Surfaced` on first append and **never overwrites a
  status the rep has changed**. Append only.
- **`email` and `phone` are deliberately absent.** They are not stored here at all.
  They exist transiently in the artifact after a rep clicks, and in the workbook only
  if the rep enriched that person. Persisting them would turn a dedup ledger into a
  contact database.
- **`warm` is a boolean, not a tier.** The connector sentence lives in the artifact and
  the workbook. Tier words never appear anywhere.

---

## The setup log, and what it is for

*Setup log* records one row per interview question actually asked: when, which question,
the options offered where it was a pick-list, the answer, and whether that answer was
the offered default. *Config changes* records every later edit — before and after.

The point is to find questions that are not earning their place. A question every rep
answers with the default is not gathering information, it is spending the rep's patience;
a field reps change three days later was asked at the wrong time or phrased badly. Both
are visible in these two tables and invisible without them.

**Append only, and never re-ask to fill a gap.** If a question was skipped, the row is
simply absent. Re-asking to complete the log would be optimising the instrument at the
rep's expense, which is the exact failure the log exists to catch.

**The honest limitation:** these files are per rep, so nothing here aggregates on its
own. "Every rep answers question 9 the same way" is not a query this skill can run —
it needs a collection point across reps that does not exist yet. What this gives you is
the record; the analysis is still manual, and worth doing before adding another question
rather than after.

Nothing in either table is contact data, and neither is customer-facing.

---

## Dedup keys and normalisation

Matching on a raw URL fails constantly. The same profile arrives as
`https://www.linkedin.com/in/example-person-04/`, as
`linkedin.com/in/example-person-04`, and as that same path carrying a tracking query
string. Normalise before comparing, both when writing and when reading.

**Normalise a LinkedIn URL:** lowercase, strip the scheme, strip a leading `www.`,
strip any query string or fragment, strip a trailing slash. Compare the result.

**Normalise a domain:** lowercase, strip the scheme, strip a leading `www.`, strip any
path.

| Entity | Primary key | Secondary key |
|---|---|---|
| Account | normalised `linkedin_slug` | normalised `domain` |
| Person | normalised `linkedin_url` | — |

A person with no LinkedIn URL cannot be deduped reliably and should not be surfaced
as a named contact; use a labelled TBD seat instead.

**Accounts match on either key.** A company that appeared last week under its domain
and this week under its slug is the same company, and surfacing it again would be a
visible failure.

---

## Building the exclusion sets

At the start of every run, after draining the buffer:

- `worked_accounts` — every normalised slug **and** domain in *Accounts surfaced*,
  plus every account-kind row in *Suppressed*.
- `worked_contacts` — every normalised URL in *People surfaced*, plus every
  person-kind row in *Suppressed*.
- `dismissed_signals` — every `signal_key` in *Dismissed signals*.

Apply `worked_accounts` in the resolver's hard-gate stage, before any billed pull —
excluding a candidate is free, scoring one is not. Apply `worked_contacts` in the
people layer before assembling the committee.

**Suppression is stronger than surfacing.** A row the rep explicitly removed must never
return, even if it would score highly. That distinction is why suppression is its own
section rather than a status value.

---

## Draining the buffer

Before generating anything:

1. Read the buffered deltas from `window.storage`, key `plan-buffer`. Each entry is
   `{ kind, payload }`.
2. Apply each by kind, per the table below.
3. Write the state file.
4. Clear the drained buffer keys.
5. **Only now** build the exclusion sets.

| `kind` | Payload | What the drain does |
|---|---|---|
| `removed_person` | `account`, `person` | Append to *Suppressed*, kind `person`. |
| `replaced` | `account`, `removed`, `added` | Append `removed` to *Suppressed*; the added person enters *People surfaced* through the normal Step 9 append. |
| `revealed` | `account`, `person` | Nothing. Contact values are deliberately not persisted here. |
| `reveal_miss` | `account`, `person` | Nothing persisted, but **do not re-offer that person as a fresh reveal candidate in the same week's follow-up.** A miss is a checked person, not an unchecked one. |

**`revealed` and `reveal_miss` are separate kinds on purpose.** One `revealed` kind for
both outcomes cannot tell "we pulled this person and got a real email" from "we pulled
this person and got nothing", which is exactly the distinction needed to avoid paying
twice for the same empty answer.

Both kinds are written by the per-person reveal *and* by the artifact's per-account bulk
reveal, one entry per person either way — the bulk path is a batched call, not a
different outcome, so it records no differently.

If the buffer is unreadable, say so and continue with the state file alone. Do not
fail the run — but do not silently pretend the clicks never happened either, because
the rep will notice a dismissed item returning.

---

## The exported tracker view, and its real limitation

The rep-facing tracker in Drive is a **rendered view** of this file, not the source of
truth. It is a readable, sectioned sheet with a new block appended per run.

The connector constraint is worth stating plainly rather than working around
silently: **the Drive connector can create files but cannot edit cells.** There is no
append, no `batchUpdate`, no formatting, no data validation. So each run reads the
existing view, adds this run's rows, and writes the file back — and any new file id
must be reported so config stays current.

Two rules follow:

- **Never spawn a new tracker per week.** If rewriting is not possible, say so and
  keep the state file authoritative rather than quietly creating a second file.
- **Do not treat the exported sheet as the dedup source.** If a rep edits it, those
  edits are advisory; the state file is what the next run reads. A Drive connector
  with cell-write would let these converge, and that is a genuine prerequisite for
  richer per-account restriction handling.
