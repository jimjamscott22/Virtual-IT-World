# Phase 2a handoff

Written at the end of the session that landed Task 8. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/distractor-catalog-session-seeding-yufnrd` |
| Pull request | [#5](https://github.com/jimjamscott22/Virtual-IT-World/pull/5) — **open, draft, not merged** |
| Base | `main` (Tasks 1–3 already merged via #4) |
| Tests | 514 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

## What landed this session

**Task 7** (the reference cascade fault) — see the previous handoff's
content, now folded into `CLAUDE.md`/`AGENTS.md`'s Task 7 paragraph; PR #5
already carried it.

**Task 8** from the plan (line 984) — **the simulated tier-2**:

- `session/ticket.py`: `TicketState.AWAITING_TIER2`;
  `Ticket.escalation_note`/`tier2_bounces`; `escalate(note, at)` (moves to
  `AWAITING_TIER2`, raises if already closed — does **not** close the
  ticket, unlike a normal disposition); `reopen(text)` (appends a `tier2`
  `ChatTurn`, increments `tier2_bounces`, back to `IN_PROGRESS`, clears
  `disposition`); `accept_escalation(at)` (thin wrapper over
  `close(Disposition.ESCALATED, at)`).
- `persona/models.py`: `ChatTurn.speaker` widened to
  `Literal["tech", "user", "tier2"]`. Nothing renders it yet — the
  templates are Task 9's job.
- `session/tier2.py` (new): `Tier2Response(accepted, text)` and
  `review_escalation(ticket, fault, world)`. Judges **ownership before
  evidence** — see the deviation-table row below for why the order
  differs from the plan's own stated sequence. A fixable fault
  (`escalation_is_correct = False`) is bounced unconditionally with a
  deliberately generic "within your scope" message that never names the
  fault's own diagnostic query (any AD-specific wording risks colliding
  with that fault's `leak_terms`). A fault that belongs to tier-2 but
  whose note names no concrete evidence (the placement target, or the
  bound target of any `escalation_evidence`/`diagnostic_path` query) is
  bounced with a "what did you find" message. Otherwise it's accepted,
  quoting `fault.escalation_reason` back to the technician — a system
  message to the technician, not persona output, so leak-term scrubbing
  doesn't apply to it.
- `faults/catalog/identity.py` / `endpoint.py`: populated
  `escalation_reason` on the two escalate-correct faults
  (`ad.offboarded_reactivation`, `endpoint.failing_disk`) — previously
  `FaultBase`'s empty-string default.
- `session/grading.py`: `Grade.escalation_quality`
  (`"none"`/`"accepted"`/`"bounced"`, derived from `ticket.disposition`
  and `ticket.tier2_bounces`). Deliberately never touches `correct` — a
  ticket bounced and then correctly fixed anyway still grades correct;
  only the after-action (Task 9) is where the wrong escalation itself
  gets said.
- `session/queue.py`: `SessionQueue.open_for(fault, at)` — opens a ticket
  for a named fault at a named placement directly, bypassing the
  scheduler. `open_cascade(fault)` is now a one-line call to it with the
  fault's first placement, removing the duplicated bookkeeping the two
  methods used to carry separately.
- `tests/test_tier2.py` (new): the plan's eight tests plus one more
  (`test_a_fixable_fault_is_bounced_even_with_a_well_evidenced_note`,
  proving ownership really is checked first and not just coincidentally
  passing) and a `pytest.raises`-based rewrite of the closed-ticket
  escalation check. `tests/test_grading.py` gained three tests for
  `escalation_quality`, including one that reproduces the "bounced then
  fixed is still correct" guarantee directly.
- One lint fix needed: `Ticket.reopen()`'s `self.chat.append(...)` tripped
  the same pydantic-`default_factory` false positive `tools/base.py`'s
  `ToolLog.record` already carries a documented `# pylint:
  disable=no-member` for — same fix, same comment shape.
- Manually verified both paths end to end against the real fault catalog
  (not just the unit tests): a fixable fault escalated with a vague note,
  bounced, then fixed directly by the technician
  (`escalation_quality="bounced"`, `grade.correct=True`); and an
  escalate-only fault escalated with a well-evidenced note, accepted by
  tier-2 (`escalation_quality="accepted"`, `grade.correct=True`).

## Next: Task 9

**The tier-2 web flow** — plan line 1141. Wires Task 8's mechanism into the
app: `GET`/`POST /ticket/{id}/escalate`, a note form, rendering `_tier2.html`
on a bounce and the shared after-action tail on an accept (factor that tail
— grade, build after-action, `store.save_closed`, render `_afteraction.html`
— into one helper shared with `close.py` rather than duplicating it). Also:

- Register the new router in `web/app.py`.
- Add an "Escalate" control to `_ticket.html` beside Close, and style
  `tier2` chat turns distinctly in `_chat.html` — this is where Task 8's
  now-unrendered third `ChatTurn.speaker` actually gets a template.
- `afteraction.py` gains a `tier2: str` field and a verdict-chain addition:
  a bounced-then-fixed ticket should read something like "You tried to
  hand this off; it was yours. You did fix it after."
- Guard `TicketState.CLOSED` with a 409 on the escalate route, matching
  `close_ticket`'s existing behavior.

The plan's own draft test for this task (`test_a_bounced_escalation_...`,
`test_an_accepted_escalation_...`) calls `session.queue.open_for(...)`
directly against a fault fetched via `get_fault(...)` at module scope in the
test body — that import (`from vitsc.faults.registry import get_fault`) is
missing from the plan's own listed imports for `tests/test_web_escalate.py`;
add it when transcribing.

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
   This session did it with a standalone script exercising both the bounce
   path and the accept path against the real catalog end to end. Whatever
   you're adding, find the equivalent "prove it actually does the thing"
   check before moving on.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this;
   Tasks 5–8 did not touch the RNG path — but re-run the full suite and
   read failures carefully rather than assuming either way whenever a
   scheduling-adjacent change lands.
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
9. **A fault whose `reporters()` returns a list (a cascade fault) breaks any
   test that assumes `assigned_to` names the reporter.** Two tests broke
   this way when Task 7 landed the first such fault. Prefer
   `session/queue.py:resolved_reporters(world, fault, placement)` over
   hand-rolled `sam` derivation in any new or old test that needs "who gets
   the ticket" for an arbitrary fault.
10. **`diagnostic_path()` and `canonical_resolutions()` receive only a
    `Placement`, never `World`.** When a query needs a concrete value only
    `World` can supply and no existing sentinel (`PLACEHOLDER`,
    `PLACEHOLDER_MACHINE`, `PLACEHOLDER_GROUP`, `PLACEHOLDER_PRINTER`) fits,
    a literal company-topology string is an accepted fallback —
    `net.static_dns_misconfig` hardcodes `MER-FS-01`, and
    `print.server_spooler_stopped` hardcodes `PRT-ACC-01` — not a new
    sentinel invented per fault.
11. **A message shown to the *technician* (tier-2's accept/bounce text, an
    after-action verdict) is not subject to leak-term scrubbing — only
    persona/user-facing text is.** But a *bounce* message for a fixable
    fault is the one technician-facing exception: naming the fault's own
    diagnostic vocabulary there hands over the answer instead of a nudge,
    so keep that one message generic across the whole catalog rather than
    fault-specific.
12. **The plan's own worked examples can contradict its prose description
    of an algorithm's step order.** `session/tier2.py:review_escalation`'s
    docstring order was reordered to match what the plan's own test cases
    actually required — see the deviation table. When a plan's prose and
    its example code disagree, trust the examples (they're testable) and
    record the discrepancy rather than silently picking one.

## Open threads

Not blocking Task 9, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance. `docs/verifying-lmstudio.md`
  is the manual procedure; a green pipeline does **not** stand in for it.
- **`Ticket.escalate()`'s `at` parameter is unused.** It exists for
  signature symmetry with `close(disposition, at)`, since Task 9's route
  will call it as `ticket.escalate(note, at=world.clock)` alongside other
  `at`-taking calls. Nothing stores it (there's no `escalated_at` field).
  If a future task wants escalation timing, that's where it would go.

## Resuming

```bash
git checkout claude/distractor-catalog-session-seeding-yufnrd
uv sync
uv run pytest          # expect 514 passed, 0 xfailed
```

Then read Task 9 in the plan (line 1141) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
