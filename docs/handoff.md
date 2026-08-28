# Phase 2a handoff

Written at the end of the session that landed Task 6. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/distractor-catalog-session-seeding-yufnrd` |
| Pull request | [#5](https://github.com/jimjamscott22/Virtual-IT-World/pull/5) — **open, draft, not merged** |
| Base | `main` (Tasks 1–3 already merged via #4) |
| Tests | 494 passing, 2 xfailed (both expected — see below) |
| Lint | 10.00/10 on `src` and on `tests` |

The 2 xfails are deliberate and named `strict=True`: `tests/test_cascade.py`'s
two tests that call `get_fault("print.server_spooler_stopped")` will start
*failing the xfail* (i.e. XPASS, which `strict=True` turns into a real
failure) the moment Task 7 registers that fault — that's the signal to strip
the `@NO_CASCADE_FAULT_YET` marker off them, not a bug to chase.

## What landed this session

**Task 5** (cascade data model) — see the previous handoff's content, now
folded into `CLAUDE.md`/`AGENTS.md`'s Task 5 paragraph; PR #5 already carried
it.

**Task 6** from the plan (line 820) — **cascade-aware grading and
after-action**:

- `session/grading.py`: `duplicate_mutations(ticket, siblings=None) -> int`
  counts repeated identical mutating `(tool, command, args)` calls beyond
  their first use, folding in every other ticket in `siblings` (deduped by
  `id()`) so a technician re-running the same repair once per cascade ticket
  is counted the same as repeating it within one ticket. `Grade` gained a
  `duplicate_mutations` field; `grade_ticket()` gained an optional
  `siblings: list[Ticket] | None = None` parameter that feeds only that
  field — it is explicitly commented that `siblings` must never touch
  `correct`/`fault_cleared`/`disposition_correct`, since `is_present()`
  against the live world already covers every sibling, and branching pass/
  fail on cascade membership would be the fault-aware special-casing the
  core design principle forbids.
- `session/afteraction.py`: `build_after_action()` gained the matching
  `siblings` parameter and `AfterAction.cascade_note` (empty for a single
  ticket, otherwise `"One <fault> was behind N tickets — the fix was a
  single fix."`), plus a verdict suffix — `"You fixed this N times. One root
  cause needs one fix."` — appended only when the fault cleared and
  `duplicate_mutations > 0`.
- `session/store.py`: `cascade_id` added to the `closed_tickets` schema and
  `ClosedRecord`; `Store.init()` now also runs a `PRAGMA table_info` check
  and `ALTER TABLE ... ADD COLUMN` for a database created before this task,
  so an existing on-disk store still opens. `save_closed()`/`history()`
  updated to round-trip the new column.
- `web/routes/close.py`: resolves a closing ticket's siblings from
  `session.queue.tickets` by matching `cascade_id` (`None` when the ticket
  has no cascade) and passes them to both `grade_ticket()` and
  `build_after_action()`.
- `web/templates/_afteraction.html`: renders `report.cascade_note` when
  non-empty, autoescaped like every other report field.
- `tests/test_grading.py` and `tests/test_store.py` extended. Since
  `print.server_spooler_stopped` doesn't exist yet, the cascade-shaped tests
  build their own siblings with `ticket.model_copy(update={...})` rather
  than going through `queue.open_cascade()` — no xfail needed for Task 6's
  own tests, only for the two inherited from Task 5.
- Manually verified the full mechanism end-to-end (not just green tests)
  with a throwaway multi-reporter stub fault (registered, exercised,
  discarded, never committed): three cascade siblings each "fix" the same
  root cause independently; `duplicate_mutations` came back `2` (three fixes
  minus one), `cascade_note` named "3 tickets", and the verdict read
  `"Resolved correctly. You fixed this 3 times. One root cause needs one
  fix."` The first pass of that script had a bug of its own — the stub
  compared `machine.services["Spooler"]` against `"RUNNING"` (wrong case)
  instead of `vitsc.world.models.ServiceState.RUNNING` (value `"Running"`),
  so the fix never registered as clearing — worth remembering that
  `ServiceState` is a genuine enum with mixed-case values, not a bare string
  constant, the next time a fault or its test compares against it directly.

## Next: Task 7

**The reference cascade fault and queue grouping** — plan line 899. Adds
`print.server_spooler_stopped` to `catalog/printing.py`:

- `placements()`: machines with `assigned_to is None` that host at least one
  printer (`MER-PRT-01` today).
- `apply()`: stops the server's `Spooler` service and appends a matching
  event-log entry.
- `is_present()`: server's `Spooler` is not `RUNNING`.
- `reporters()`: every user whose assigned machine has a printer installed on
  that server, sorted for determinism — the first fault to actually return a
  list instead of `FaultBase`'s default `None`.
- `symptoms()`: jargon-free, identical in substance across reporters, with
  `scope` as the honest cascade tell ("a couple of people near me said the
  same").
- `canonical_resolutions()`: one path, `machine.restart_service` with
  `service=Spooler`.
- `leak_terms`: `["spool", "service", "server", "queue"]`.

Then `_queue.html` renders `ticket.cascade_id` as a small tag on each sibling
row — explicitly **not** merged/grouped rows, so the technician has to notice
the pattern themselves rather than have it pre-solved for them.

This is also the point where Task 5's and Task 6's `@NO_CASCADE_FAULT_YET`
xfails in `tests/test_cascade.py` flip from `xfail` to real assertions —
removing the marker is part of Task 7's own step list, not a separate
cleanup.

## Conventions this codebase expects

Things that are easy to get wrong and are not obvious from the code alone.

1. **Register instances, not classes.** `register_distractor(Thing())` /
   `register(Thing())` at the bottom of the module. A bare class fails at
   *collection* time with a missing `self`.
2. **Deviations from the plan get recorded.** `CLAUDE.md` and `AGENTS.md`
   both carry a "Where the code deliberately diverges from the plan" table.
   Both files are kept identical except their first-line title/tool-name.
3. **Lint is two commands.** `uv run pylint src` keeps the strict set;
   `tests` relaxes four pytest idioms. Prefer fixing a finding, or
   suppressing it at its own line, over adding to the global disable list —
   a design-limit bump (`max-locals`, `max-args`, `max-attributes`) is one
   line in `[tool.pylint.design]` with a comment naming which change needed
   it, and the comment gets extended (not replaced) the next time it moves.
4. **`tests/conftest.py` clears `VITSC_*` for every test.** Do not remove it.
5. **Prove a new mechanism actually works, not just that pytest is green.**
   Tasks 3/4/5 did this by breaking a distractor on purpose, or registering a
   real throwaway multi-reporter fault; this session did the same for
   grading — a script exercising `duplicate_mutations`/`cascade_note`/the
   verdict line together, end to end, against a live cascade, not just their
   unit tests in isolation. Whatever you're adding, find the equivalent
   "prove it actually does the thing" check before moving on.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this
   (fixed by changing `test_web_close.py`'s seed from 1 to 0); Task 5's and
   Task 6's changes did not touch `SessionQueue`'s RNG path at all — but
   re-run the full suite and read failures carefully rather than assuming
   either way whenever a scheduling-adjacent change lands.
7. **A `Ticket | None` → `list[Ticket]` return-type change breaks
   `is None`/`is not None` checks silently, not loudly** — a list is always
   "not None", so a `while x() is not None: pass` loop against the new
   signature never terminates. Search for exact-`None` comparisons against
   anything whose return type changes to a collection, and prefer truthiness
   (`while x(): pass`) or an explicit `== []` once you find them.
8. **`ServiceState` (`world/models.py`) is a real `str, Enum`, not a bare
   string constant, and its values are mixed-case** (`"Running"`,
   `"Stopped"`, not `"RUNNING"`/`"STOPPED"`). A fault or a test that compares
   a service state against an all-caps string literal will silently never
   match. Compare against `ServiceState.RUNNING` (etc.) or the exact stored
   casing, not an assumed all-caps form.

## Open threads

Not blocking Task 7, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance. `docs/verifying-lmstudio.md`
  is the manual procedure; a green pipeline does **not** stand in for it.
- **`web/routes/queue.py` and the templates don't yet show cascades as
  grouped.** Task 5/6 only changed the data model and the grading/report
  layer; the queue UI still renders three sibling tickets as three
  independent rows with no visible `cascade_id`. This is exactly what
  Task 7 Step 4 covers — a small tag per row, deliberately not merged.

## Resuming

```bash
git checkout claude/distractor-catalog-session-seeding-yufnrd
uv sync
uv run pytest          # expect 494 passed, 2 xfailed
```

Then read Task 7 in the plan (line 899) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
