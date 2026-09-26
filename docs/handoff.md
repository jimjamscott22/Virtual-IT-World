# Phase 2b handoff

Written at the end of the session that landed Phase 2b's catalog: the eighteen
faults that took the drill from thirteen to thirty-one, plus the KB, distractor,
invariant and escalation work the plan listed alongside them.

Delete this file when Phase 2b is closed out. It records *situational* state —
branch, PR, what is half-done, what is worth knowing once and not twice.
Architecture lives in `CLAUDE.md`, which is current.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/game-dev-progress-review-i56yyx` |
| Base | `main` at `27276e8` (Phase 2b groundwork) |
| Tests | 1632 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |
| Catalog | 31 faults — identity 7, network 6, printing 6, endpoint 6, mail 6 |

## What landed

One commit of machinery, five commits of faults, then the supporting work. Read
the commit messages: each one states what it changed and, where a test had to
change shape, why the test was wrong rather than the code.

**The machinery, first and on its own** (`9858414`). Most 2b faults could not be
expressed against the Phase 2a world. `ServiceState.DISABLED`, nested groups,
`Machine.proxy_server` / `last_domain_sync` / `clock_offset_minutes` /
`processes`, `Printer.jobs`, `Mailbox.delegates`,
`MailSystem.autodiscover_host` / `distribution_lists`, `Network.netmask`, six
new reads, sixteen new actions, and the routing model in `_reachable()`.

**The faults**, one commit per domain:

- identity `4113425` — `ad.cached_credentials_stale`,
  `ad.nested_group_membership`, `ad.upn_mismatch` (the fourth escalate-correct
  reason: nobody in IT knows the right answer).
- network `9107f88` — `net.wrong_subnet_mask`, `net.gateway_misconfigured`,
  `net.stale_proxy`, `net.duplicate_static_ip` (cascade). Four distinct
  observable signatures; the table is in that commit message and is the thing to
  preserve if `_reachable()` is ever touched.
- printing `29625df` — `print.printer_offline`, `print.stuck_job` (cascade),
  `print.driver_after_model_swap` (cascade).
- endpoint `666bc63` — `endpoint.corrupt_profile`,
  `endpoint.service_disabled`, `endpoint.time_skew`,
  `endpoint.runaway_process`.
- mail `d96969d` — `mail.transport_stalled` (cascade), `mail.stale_delegate`,
  `mail.autodiscover_broken`, `mail.ownerless_distribution_list`.

**The rest of the plan's list**: KB grown to fourteen articles with no orphans
either way and distractors to eleven (`1cacf73`); the mail invariants and the
single escalation path (`86dc208`); the store's session scoping (`dbfb405`).

## Four bugs found by driving the app, not by the suite

Convention 5 earned its place again. None of these was caught by pytest, and
three of them were in code this session had just written.

1. **`forgive()` silently dropped both new `Baseline` fields.** It rebuilds the
   model naming each field, so a field added and forgotten there defaults to
   empty on every arrival: the invariant never fires in a real session while its
   own unit tests pass. Guarded now by
   `test_forgiving_nothing_leaves_every_baseline_field_intact`. **This is the
   single most important thing in this file** — it generalises to any future
   `Baseline` field.
2. **`mail.remove_mailbox` made an unreachable raise reachable**, turning a bad
   grade into a 500. A missing mailbox now reads as the fault still present.
3. **The shift summary counted previous shifts.** `~/.vitsc/sessions.sqlite3`
   outlives the process, so four tickets closed reported seven. No timestamp
   could have separated the runs — the simulated clock restarts at 09:00 every
   session — so rows carry a `session_id`.
4. **A raw-substring assertion against rendered HTML passed vacuously** for any
   fault title containing an apostrophe, in two separate test files. The
   negative half was the dangerous one: it was a *leak* check.

## Phase 2b Definition of Done

Checked item by item against the plan's own list.

| | Item | Status |
|---|---|---|
| 1 | 30+ faults, conforming across every placement, all five domains, none below five | ✅ 31, none below six |
| 2 | Two cascades in different domains; four escalate-correct, no two for the same reason | ✅ five cascades in three domains; four reasons — authorisation, hardware, acting-destroys-evidence, nobody-knows-the-value |
| 3 | Every fault links an article; every article is linked | ✅ proved by `test_no_orphans_in_either_direction` |
| 4 | Distractor count scaled to the catalog, all passing the harness | ✅ eleven, ratio-guarded |
| 5 | Mail invariants land, with a fault that trips them when fixed wrongly | ✅ both trippable through HTTP on `mail.mailbox_full` |
| 6 | The escalation-disposition inconsistency resolved deliberately | ✅ one reviewed path; the dropdown option is gone and the route refuses it |
| 7 | Every fault's `difficulty` chosen as a frequency decision | ✅ 5/13/10/3 across 1–4; ~68% of dealt tickets are routine, asserted |
| 8 | A full eight-hour shift workable end to end; `/shift` reads correctly for a good shift and a bad one | ✅ driven on a real server; a deliberately mixed shift reads "2 of 3 closed correctly" |
| 9 | `uv run pytest` green with nothing on localhost; pylint 10.00/10 on both targets | ✅ |
| 10 | A full ticket workable in the browser in all five domains, and twenty consecutive tickets unpredictable | ✅ automated for all 31 (`test_every_fault_in_the_catalog_can_be_closed_correctly`); a cascade and a `net.stale_proxy` ticket also worked by hand on a real server |
| — | LM Studio: suite green with it running, and `VITSC_PERSONA=lmstudio` roleplaying every ticket | ⬜ **inherited from Phase 2a and still unverified.** No sandbox has had network to a local LM Studio. `docs/verifying-lmstudio.md` is the manual procedure; a green pipeline does not stand in for it |

## Open threads

- **The LM Studio path has never run.** The one item above that cannot be ticked
  from here. Everything else in Phase 2a's and 2b's Definitions of Done is done.
- **The design spec is still deleted** (commit `dbcd2bb`), so `CLAUDE.md` remains
  the sole architectural record and the 2a plan's cross-references to the spec
  (its lines 11–12, Task 17's file list) still dangle. Recover with
  `git show dbcd2bb^:docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`.
  If it comes back, §6's catalog table needs to go from ten faults to
  thirty-one and the `Fault` protocol listing needs the 2a members.
- **`is_present()` predicates overlap in three places, deliberately.**
  `print.wrong_driver` and `print.driver_after_model_swap` both mean "a
  workstation has the wrong driver for this printer";
  `share.group_membership_removed` and `ad.nested_group_membership` both mean
  "this person is not effectively in the group the share requires". That is
  honest — the gate is world state, and the world really is broken both ways —
  and the scheduler skips a fault that is already present, so no ticket is dealt
  twice for one cause. But it means a *second* fault can read as present while
  the first is active, and if a future feature ever asks "which fault is this
  world in", it will need a tie-break that does not exist today.
- **`mail.transport_stalled` and `mail.autodiscover_broken` share a placement**
  (`MER-MB-01`). Fine today; worth knowing if placement-holding ever becomes
  keyed on the placement alone rather than on fault + placement.
- **No CSS for any class added since Phase 2a** — `.chat-tier2`, `.tier2-*`,
  `.escalate-form`, `.ticket-actions`, `.kb-*`, and now nothing new beyond them.
  Matches existing precedent; a styling pass would want the lot.
- **`_kb.html` still has no link from `layout.html`/`index.html`.** Reachable by
  typing `/kb` or through the after-action's links.
- **Cross-session history is now available but unused.** `Store.history()` and
  `domain_stats()` take `all_sessions=True`. A career-to-date view is the
  obvious next thing to want and nothing builds it.
- **`ipconfig` rendering still has no test coverage**, and it now has more to get
  wrong: `_effective_mask`/`_effective_gateway` feed it. Related to convention 19.

## Conventions this codebase expects

Phase 2a's list (1–25) still holds; it is in this file's history at `27276e8` and
every item remains true. What Phase 2b adds:

26. **A new `Baseline` field must be added in three places, not two.**
    `capture_baseline`, `check_invariants`, *and* `session/queue.py:forgive`. The
    third is the one that gets forgotten, and forgetting it is silent.
27. **A raw-substring assertion against rendered HTML is unreliable in both
    directions.** An apostrophe becomes an entity, so a positive check fails and
    a negative check passes vacuously. Compare `markupsafe.escape(...)`, or
    — better, for a string you own — write the string without a possessive.
28. **An action that lets a technician destroy something makes previously
    unreachable code reachable.** `mail.remove_mailbox` turned a documented
    "cannot happen" raise into a 500 on close. When adding a destructive action,
    grep for what assumes the thing exists.
29. **`difficulty` shifts the *aggregate* mix, not just one fault's frequency.**
    `test_the_catalog_deals_mostly_routine_tickets` is the test a badly-chosen
    difficulty fails; it is about the catalog, not the scheduler.
30. **A distractor with no placements fails nothing.** Its conformance cases
    vanish from the parametrized file instead. Same for any parametrized harness
    keyed on a `placements()` call — an empty list is zero tests, not a failure.
31. **A fault placed on anything without an `assigned_to` must declare its own
    `reporters()`** — a server, a distribution list, a group. `resolved_reporters`
    returns `[]` otherwise and the ticket goes to nobody, which surfaces as a
    `KeyError`/`IndexError` well away from the fault that caused it.
32. **`HTTP_FIX` maps a fault to an ordered *list* of steps.** A repair needing
    two world changes needs two entries, or `resolve_via_http` posts half the fix
    and the ticket grades as closed-but-unfixed.

## Resuming

```bash
git checkout claude/game-dev-progress-review-i56yyx
uv sync
uv run pytest          # expect 1632 passed, 0 xfailed
uv run python -m vitsc # then work a shift; the drill is the point
```

Phase 2b's catalog is complete. The next plan has not been written. The obvious
candidates, in the order they would pay off:

1. **Verify the LM Studio path.** It is the last unticked item in two phases and
   needs nothing but a machine with the model running.
2. **A styling pass**, since the drill is now content-complete and looks it.
3. **Career-to-date progress** across sessions, which the store can already
   answer and nothing asks.
