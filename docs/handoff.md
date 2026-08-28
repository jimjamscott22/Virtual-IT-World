# Phase 2a handoff

Written at the end of the session that landed Task 5. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/distractor-catalog-session-seeding-yufnrd` |
| Pull request | [#5](https://github.com/jimjamscott22/Virtual-IT-World/pull/5) — **open, draft, not merged** |
| Base | `main` (Tasks 1–3 already merged via #4) |
| Tests | 483 passing, 2 xfailed (both expected — see below) |
| Lint | 10.00/10 on `src` and on `tests` |

The 2 xfails are deliberate and named `strict=True`: `tests/test_cascade.py`'s
two tests that call `get_fault("print.server_spooler_stopped")` will start
*failing the xfail* (i.e. XPASS, which `strict=True` turns into a real
failure) the moment Task 7 registers that fault — that's the signal to strip
the `@NO_CASCADE_FAULT_YET` marker off them, not a bug to chase.

## What landed this session

**Task 4** (distractor catalog and session seeding) — see the previous
handoff's content, now folded into `CLAUDE.md`/`AGENTS.md`'s Task 4
paragraph; PR #5 already carried it.

**Task 5** from the plan (line 652) — **cascade data model: reporters,
sibling tickets, plural arrivals**:

- `faults/base.py`: `FaultBase` (defaults for `kb_articles`,
  `escalation_reason`, `escalation_evidence`, `reporters()` → `None`). All ten
  catalog classes across `identity.py`/`network.py`/`printing.py`/`endpoint.py`
  now inherit it — no other change to any of them; `tests/test_catalog.py`
  stayed green throughout.
- `session/ticket.py`: `Ticket.cascade_id: str | None = None`;
  `priority_for(fault, user, reporters=1)` — P1 at `reporters >= 3` (in
  addition to the existing `WORK_STOPPING` check), P2 above 1.
- `session/queue.py`: `resolved_reporters(world, fault, at)` (the fault's own
  `reporters()` when it returns a list, else the single `reporter_sam`,
  dropping anyone missing from `world.org.users`); `_candidates()` now
  filters on that being non-empty. `open_ticket()` returns `list[Ticket]`
  (was `Ticket | None`) — one call applies the fault once and mints one
  ticket per `rng.sample`d reporter, capped by `CASCADE_MAX = 3` and by room
  left under `MAX_ACTIVE`; a candidate that wouldn't fully fit is skipped
  rather than partially dealt. `open_one()` is the single-ticket convenience
  every existing caller now uses; `open_cascade(fault)` opens a named fault's
  cascade directly for tests, bypassing the scheduler. `tick()` extends its
  arrivals list instead of appending one ticket at a time. A private `_open()`
  holds the actual bookkeeping (apply, forgive, sample, mint) shared by both
  `open_ticket()` and `open_cascade()`.
- `tests/test_cascade.py` (new): the plan's six tests. Two are `xfail` until
  Task 7 exists (see above); the other four pass now.
- Updated every `open_ticket()` caller across `tests/` (found via
  `grep -rn open_ticket tests/ src/`) to `open_one()` where a single `Ticket`
  was expected, and fixed the two `is None`/`is not None` checks in
  `tests/test_queue.py` that would otherwise be always-true against a list
  return (`test_damage_survives_every_remaining_arrival`'s
  `while queue.open_ticket() is not None` was an infinite loop against the
  new return type — caught because the suite hung, not because a test failed).
- `tests/test_ticket.py`: added two direct unit tests for the reporters
  argument to `priority_for` (P1 at 3+, P2 above 1), since no fault yet
  triggers that path through the scheduler end to end.
- `pyproject.toml`: `max-attributes` 8 → 9 (`SessionQueue` gained
  `_next_cascade_id`), same "raise a little rather than disable" convention
  as Task 4's bump.
- Manually verified the mechanism with a throwaway multi-reporter stub fault
  (registered, exercised, discarded — never committed): confirmed the
  cascade caps at `CASCADE_MAX` even with more declared reporters, shares one
  `cascade_id`, grades every sibling P1, gives each a distinct persona, and
  correctly caps to whatever room is left when the queue is nearly full.

Unlike Task 4, this refactor did **not** shift any test's dealt fault by
seed — `rng.sample()` is called even for the single-reporter case, which
could have, but the existing seed-pinned tests (`test_web_close.py`'s
`seed=0`, `test_end_to_end.py`'s `range(8)`) came through unaffected. Worth
re-checking with the same "manually verify the actual pytest run, don't
assume a mechanical refactor is seed-neutral" scrutiny if Task 6 or 7 touches
`SessionQueue`'s RNG consumption again.

## Next: Task 6

**Cascade-aware grading and after-action** — plan line 820. Adds
`Grade.duplicate_mutations` and an optional `siblings` parameter to
`grade_ticket()` (report-only — it must not change pass/fail logic, since
`is_present()` against the live world already covers siblings; the plan is
explicit that special-casing cascades in the gate is exactly what the core
design principle forbids), `AfterAction.cascade_note`, and a `cascade_id`
column on `session/store.py`'s schema (via `ALTER TABLE ... ADD COLUMN`
guarded by a `PRAGMA table_info` check, so an existing on-disk database
survives).

Task 6's own tests in the plan reference `print.server_spooler_stopped`
directly, same as Task 5's — expect the same two-test xfail pattern (or
write them that way from the start) until Task 7 lands.

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
   Task 3/4 did this by breaking a distractor on purpose; this session did it
   by registering a real throwaway multi-reporter fault and exercising
   `open_cascade()`/room-capping against it directly, since no real fault
   exercises the cascade path yet. Whatever you're adding, find the
   equivalent "prove it actually does the thing" check before moving on.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this
   (fixed by changing `test_web_close.py`'s seed from 1 to 0); Task 5's
   `rng.sample()` call did not, but re-run the full suite and read failures
   carefully rather than assuming either way — a scheduling change is exactly
   the kind of thing that breaks a seed-pinned assertion in a file the change
   itself never touched.
7. **A `Ticket | None` → `list[Ticket]` return-type change breaks
   `is None`/`is not None` checks silently, not loudly** — a list is always
   "not None", so a `while x() is not None: pass` loop against the new
   signature never terminates. Search for exact-`None` comparisons against
   anything whose return type changes to a collection, and prefer truthiness
   (`while x(): pass`) or an explicit `== []` once you find them.

## Open threads

Not blocking Task 6, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance. `docs/verifying-lmstudio.md`
  is the manual procedure; a green pipeline does **not** stand in for it.
- **`web/routes/queue.py` and the templates don't yet show cascades as
  grouped.** Task 5 only changed the data model (`cascade_id` exists, siblings
  share one), not the queue UI — three sibling tickets currently render as
  three independent rows. Plan line 899 (Task 7) mentions "queue grouping" in
  its title but the plan text for it wasn't read closely this session; check
  whether it's UI grouping or something else before assuming Task 7 covers it.

## Resuming

```bash
git checkout claude/distractor-catalog-session-seeding-yufnrd
uv sync
uv run pytest          # expect 483 passed, 2 xfailed
```

Then read Task 6 in the plan (line 820) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
