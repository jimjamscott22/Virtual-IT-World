# Phase 2a handoff

Written at the end of the session that landed Task 7. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/distractor-catalog-session-seeding-yufnrd` |
| Pull request | [#5](https://github.com/jimjamscott22/Virtual-IT-World/pull/5) — **open, draft, not merged** |
| Base | `main` (Tasks 1–3 already merged via #4) |
| Tests | 502 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

There are no deliberate xfails left. Tasks 5 and 6 each shipped with two
tests marked `xfail(raises=KeyError, strict=True)` because they exercised
`print.server_spooler_stopped` before it existed; Task 7 (this session) added
that fault and stripped every one of those markers, so they now run as
ordinary passing assertions.

## What landed this session

**Task 6** (cascade-aware grading and after-action) — see the previous
handoff's content, now folded into `CLAUDE.md`/`AGENTS.md`'s Task 6
paragraph; PR #5 already carried it.

**Task 7** from the plan (line 899) — **the reference cascade fault and
queue grouping**:

- `faults/catalog/printing.py`: `ServerSpoolerStopped`
  (`print.server_spooler_stopped`) — placed on a print server
  (`assigned_to is None` and hosting at least one printer, via the new
  `_print_servers(world)` helper; `MER-PRT-01` today), not a workstation.
  It's the first fault to override `FaultBase.reporters()` with an actual
  list: every user whose assigned machine has a printer installed whose
  `host` is this server, sorted for determinism (six people in the seed
  data today). `diagnostic_path()` can't resolve a printer name from
  `World` — the method only ever receives a `Placement` — so its second
  query hardcodes a literal printer on that server
  (`_SERVER_DIAGNOSTIC_PRINTER = "PRT-ACC-01"`), the same pattern
  `net.static_dns_misconfig` already uses for `MER-FS-01`. `leak_terms`:
  `["spool", "service", "server", "queue"]`. `symptoms().scope` — "a couple
  of people near me said the same" — is the cascade tell, phrased the way a
  person would say it.
- `web/templates/_queue.html`: renders `ticket.cascade_id` as a small tag
  (`<span class="ticket-cascade">`) on each sibling row. Rows stay
  independent and unmerged **on purpose** — a merged row would hand the
  technician the pattern instead of letting them notice it.
- `tests/test_cascade.py`: the `@NO_CASCADE_FAULT_YET` markers on
  `test_siblings_share_a_cascade_id_and_a_placement` and
  `test_fixing_the_root_clears_every_sibling` are gone; two new tests
  (`test_server_spooler_reporters_are_users_of_that_server_s_printers`,
  `test_it_only_places_on_a_print_server`) cover the fault's own shape.
- `tests/test_web_queue.py`: `test_cascade_siblings_are_visibly_related_in_the_queue`
  forces a cascade via `queue.open_cascade()` (not random seeding — the
  fixture's default seed doesn't reliably deal this fault) and asserts the
  shared `"C1"` tag renders at least twice in `/`'s HTML.
- Two pre-existing tests broke and needed fixing, both because they assumed
  every fault resolves to a *single* reporter via `assigned_to`:
  - `tests/test_end_to_end.py:test_every_resolvable_fault_has_an_http_fix_mapped`
    needed a `HTTP_FIX` entry for the new fault id (same `(tool, command)`
    pair as `print.spooler_stopped`: `("print", "restart-spooler")` — the
    underlying action and command are identical, only the fault differs).
  - `tests/test_grading.py:test_every_fault_produces_a_report_with_a_bound_shortest_path`
    derived `sam` as `placement.key if kind == "user" else
    machines[...].assigned_to`, which is `None` for a print-server
    placement and raised `KeyError: None`. Now uses
    `session/queue.py:resolved_reporters(world, fault, placement)[0]` — the
    same resolution the scheduler itself uses, so it works for both the
    ordinary case and a cascade fault's own `reporters()`.
  - `tests/test_catalog.py:test_v1_catalog_is_complete` hardcodes the whole
    fault-id set; it now includes the new id, with a comment noting the
    name is historical (Phase 2a additions still belong in it) rather than
    a hard boundary at ten.
- Manually verified the whole thing end-to-end through the real rendered
  page (not just the unit tests): built a session, called
  `queue.open_cascade(get_fault("print.server_spooler_stopped"))`, hit `/`
  through `TestClient`, and confirmed three tickets with three distinct
  personas (Maria Alvarez, Bruno Ferreira, Sandra Whitfield), all tagged
  `C1`, all rendered as P1.

## Next: Task 8

**The simulated tier-2** — plan line 984. This is a bigger one: it adds a
`TicketState.AWAITING_TIER2`, `Ticket.escalate()`/`reopen()`/
`accept_escalation()`, a new `session/tier2.py` with `Tier2Response` and
`review_escalation()` (accepts a well-evidenced escalation of an
escalate-only fault, bounces a fixable one back with a `tier2` chat turn),
and `Grade.escalation_quality`. It also widens `ChatTurn.speaker` to
`Literal["tech", "user", "tier2"]` — any template that renders chat needs to
style the third speaker distinctly, since it is not the reporting user and
conflating them would mislead the player about who they're talking to.

The plan's own `tests/test_tier2.py` draft calls `queue.open_for(fault, at)`,
which doesn't exist on `SessionQueue` today (Task 5 named the equivalent
things `_open()` — private — and `open_cascade(fault)`, which resolves its
own placement rather than taking one). Reconcile that before copying the
plan's test verbatim: either add a small public `open_for(fault, at)` or
adapt the test to `open_cascade`/the existing surface, whichever keeps the
scheduler's bookkeeping in one place per the Task 5 design note.

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
   This session did it by driving the real rendered `/` page through
   `TestClient` after forcing a cascade open, rather than trusting the
   assertion-only test. Whatever you're adding, find the equivalent "prove
   it actually does the thing" check before moving on.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this;
   Tasks 5–7 did not touch the RNG path — but re-run the full suite and
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
   this way when Task 7 landed the first such fault (see above). Prefer
   `session/queue.py:resolved_reporters(world, fault, placement)` over
   hand-rolled `sam` derivation in any new or old test that needs "who gets
   the ticket" for an arbitrary fault.
10. **`diagnostic_path()` and `canonical_resolutions()` receive only a
    `Placement`, never `World`.** When a query needs a concrete value only
    `World` can supply and no existing sentinel (`PLACEHOLDER`,
    `PLACEHOLDER_MACHINE`, `PLACEHOLDER_GROUP`, `PLACEHOLDER_PRINTER`) fits,
    a literal company-topology string is an accepted fallback —
    `net.static_dns_misconfig` hardcodes `MER-FS-01`, and
    `print.server_spooler_stopped` now hardcodes `PRT-ACC-01` — not a new
    sentinel invented per fault.

## Open threads

Not blocking Task 8, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance. `docs/verifying-lmstudio.md`
  is the manual procedure; a green pipeline does **not** stand in for it.
- **The plan's Task 8 test fixture references a `SessionQueue` method that
  doesn't exist** (`open_for(fault, at)` — see "Next: Task 8" above). Worth
  deciding the API shape deliberately rather than papering over it, since
  Task 8's own tests will need whichever choice is made.

## Resuming

```bash
git checkout claude/distractor-catalog-session-seeding-yufnrd
uv sync
uv run pytest          # expect 502 passed, 0 xfailed
```

Then read Task 8 in the plan (line 984) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
