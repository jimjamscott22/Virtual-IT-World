# Phase 2b handoff

Written after Phase 2b's groundwork PR (#11) and its Task 1 (`8cf1804`,
`ad.cached_credentials_expired`), both merged to `main`. Records *situational*
state (what's landed, what's next, what's open) — architecture lives in
`CLAUDE.md`/`AGENTS.md`, and per-task detail lives in
`docs/superpowers/plans/2026-08-14-phase-2b-catalog.md`. Delete or rewrite this
file once Phase 2b's Definition of Done is met.

## Where things stand

| | |
| --- | --- |
| Branch | `main` |
| Latest commit | `8cf1804` — "feat(faults): add identity domain's cached-credentials fault (2b Task 1)" |
| Tests | 942 passed, 0 failed (verified live: `uv run pytest`) |
| Lint | 10.00/10 on `src` (verified live: `uv run pylint src`) |
| Faults registered | 14 — identity 5, network 2, printing 3, endpoint 2, mail 2 |

Phase 2a (Tasks 1–17) is fully complete and merged. Phase 2b's groundwork
(estate growth, fixed shift, difficulty-driven scheduling) is done, and its
Task 1 is the first fault added under that groundwork.

## What landed most recently

**Phase 2b groundwork** (`0a9d387`, PR [#11](https://github.com/jimjamscott22/Virtual-IT-World/pull/11)) settled the three questions the 2b plan
required before any fault-adding task:

- **The estate grew to 20 users / 10 workstations** (from 12/6), append-only
  so every existing row stayed byte-identical. Half the org now shares a
  terminal, which keeps a machine-placed fault from being a user-placed fault
  under another name.
- **A fixed eight-hour simulated shift** (`session/shift.py`, `/shift`):
  arrivals stop at 17:00, open tickets stay workable, and the end-of-shift
  report sums the store's own rows (except `unresolved`, which has to come
  from the live queue).
- **Difficulty now drives how often a fault is dealt**, not placement count.
  `choose_fault_and_placement()` picks the fault first (weighted 5/4/3/2/1 by
  `difficulty`), then a placement uniformly. Before this change the catalog's
  only cascade (one placement) was drawn 20x less often than a mail fault
  (twenty placements) for no reason anyone chose.

**Phase 2b Task 1** (`8cf1804`) — `ad.cached_credentials_expired`:

- Models a workstation whose cached domain sign-in has gone stale after an
  extended absence from the network: the user reaches their desktop fine,
  but mapped drives, printers, and mail all fail because the machine's live
  channel to the domain controller (`"Netlogon"` in `machine.services`) is
  down. Gated and cleared exactly like `print.spooler_stopped` — a
  `ServiceState.STOPPED` entry, cleared by `machine.restart_service`.
- Deliberately the cheapest possible 2b task: no new query/action kind, no
  new `World` field, no new tool surface — it reuses `machine.services` /
  `machine.restart_service`, already reachable via `remote services`,
  `ps Get-Service`, `ps Restart-Service`.
- The differential against the other four identity faults: `ad get-user` on
  the affected sam comes back completely clean (not locked, not expired, not
  disabled), because the account itself is never touched. The technician has
  to notice the account checks out and look at the machine instead.
- Adds `src/vitsc/data/kb/identity-signed-in-but-cut-off.md` (the existing
  identity KB article is about not being able to sign in at all, which
  doesn't fit this symptom).
- `tests/test_catalog.py` (`test_v1_catalog_is_complete`) and
  `tests/test_end_to_end.py` (`HTTP_FIX`/`TARGET_FIELD`) updated in the same
  commit, per conventions 21–22 below.

## What's next

Continuing down `docs/superpowers/plans/2026-08-14-phase-2b-catalog.md`'s
task list toward its **30+ fault target** (currently 14; roughly 16 more
needed, spread so no domain stays below five). The plan's domain table names
candidates per domain — network's duplicate-static-IP cascade and printing's
stuck-queue fault (which needs a new print-queue-clear action kind) are
flagged as the two that need new plumbing rather than reusing existing
query/action kinds, so they're more expensive tasks than Task 1 was.

Before starting the next task, re-verify `main`'s state rather than trusting
this file — a past session (see conventions 6 and 23 below) already hit two
sessions being handed the same task, and a change to `SessionQueue`'s RNG
consumption can silently shift which fault a fixed `seed=N` deals across the
whole suite.

## Phase 2b Definition of Done

Copied from the plan, not yet checked item by item this session:

- [ ] 30+ faults registered, conforming across every placement, in all five
      domains, none below five. **Currently 14** (identity 5, network 2,
      printing 3, endpoint 2, mail 2).
- [ ] At least two cascade faults in different domains, and at least four
      escalate-correct faults, no two escalate-correct for the same reason.
      **Currently:** one cascade (`print.server_spooler_stopped`), three
      escalate-correct faults.
- [ ] Every fault links at least one KB article; every article linked by at
      least one fault (no orphans either direction).
- [ ] Distractor count scaled to the catalog (currently 5, sized for the old
      13–14-fault catalog).
- [ ] Mail invariants land, with a fault that trips them when fixed wrongly.
      **Not started** — Task 12 (Phase 2a) deliberately deferred this.
- [ ] The escalation-disposition inconsistency (see Open threads) resolved
      one way or the other, deliberately.
- [ ] Every fault's `difficulty` chosen as a frequency decision, not just a
      hardness one.
- [ ] A full eight-hour shift workable end to end; `/shift` reads correctly
      for a good shift and a bad one.
- [ ] `uv run pytest` green with nothing on localhost; `uv run pylint src`
      and `tests` at 10.00/10. **✅ true right now** (942 passed, 10.00/10).
- [ ] A full ticket worked in the browser in all five domains, and a player
      working twenty consecutive tickets cannot predict the cause from the
      opening line.

## Still-open items carried over from Phase 2a

These were open at the end of Phase 2a and remain open — nothing in Phase 2b
so far has touched them:

- **The LM Studio path is still unverified.** No environment used so far has
  had network access to a local LM Studio instance.
  `docs/verifying-lmstudio.md` is the manual procedure; a green pipeline does
  **not** stand in for it.
- **The deleted design spec.** `docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`
  and the Phase 1 plan were deleted from the tree in commit `dbcd2bb`
  (deliberate, titled, by the repo owner). Recoverable with:
  ```bash
  git show dbcd2bb^:docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md
  git show dbcd2bb^:docs/superpowers/plans/2026-08-07-phase-1-drill.md
  ```
  If it stays deleted, `CLAUDE.md`/`AGENTS.md` remain the sole architectural
  record, and the 2a plan's own cross-references to the spec (lines 11–12,
  and Task 17's file list) stay permanently dangling.
- **`remote clear-disk` with no `gb` silently succeeds and frees nothing.**
  `_do_machine_clear_disk` reads `float(a.args.get("gb", "0"))`, logging a
  mutation that did nothing. `_do_mail_set_quota` handles the analogous case
  the opposite way (rejects outright). Fix: treat a missing `gb` as a
  rejection, matching `set_quota`.
- **Two ways still reach `Disposition.ESCALATED`**: the reviewed
  `/ticket/{id}/escalate` flow, and the unreviewed "Escalated" option still
  sitting in the close-ticket dropdown, which skips `review_escalation`
  entirely and produces an after-action with no `tier2_note`. Whether the
  dropdown option should be removed is a real design question, called out in
  the Phase 2b DoD above but not yet decided.
- **No CSS for tier-2/KB/cascade elements** (`.chat-tier2`, `.tier2-bounce`,
  `.tier2-outcome`, `.tier2-note`, `.escalate-form`, `.ticket-actions`,
  `.kb-suggestions`, `.kb-page`, `.kb-article`, `.kb-results`, `.kb-search`).
  Matches existing unstyled precedent (`.warning`, `.ticket-cascade`,
  `.cascade-note`).
- **`_kb.html` has no link back to it from `layout.html`/`index.html`.**
  Reachable only via `/kb` directly or the after-action's links.
- **`mail.mailbox`'s size fields render as a plain `"51200.0 MB"`** rather
  than real Exchange's mixed-unit style. Consistent with how this codebase
  already simplifies other cmdlet output.
- **No mail invariant exists** — also listed in the Phase 2b DoD above.

## Conventions this codebase expects

Carried forward from the Phase 2a handoff; still accurate and still easy to
get wrong. The full numbered list (25 items) lives in git history for this
file (see the commit that replaced this doc) and is summarized in `CLAUDE.md`
where it overlaps architecture. The ones most likely to bite the next 2b
fault task:

1. **Register instances, not classes** — `register(Thing())` at the bottom
   of the module.
2. **`CLAUDE.md` and `AGENTS.md` must stay byte-identical below the title
   line.** Check this before finishing a task; it silently drifted once
   already (Tasks 3–14).
3. **A hardcoded "complete" id-set test and escalate-correct count test both
   break the moment a task registers a new fault.** Update them in the same
   commit, not a later "documentation" task.
4. **`tests/test_end_to_end.py`'s `HTTP_FIX`/`TARGET_FIELD` tables must stay
   current in the task that registers a new escalate-incorrect fault** — the
   guard iterates `all_faults()` and fails immediately otherwise.
5. **`Fault.difficulty` decides how often a fault is dealt, not just how hard
   it is.** Choose it with frequency in mind (`DIFFICULTY_WEIGHTS` in
   `session/queue.py`).
6. **A fault whose `reporters()` returns a list (a cascade) breaks any test
   that assumes `assigned_to` names the reporter** — prefer
   `session/queue.py:resolved_reporters(world, fault, placement)`.
7. **`diagnostic_path()` and `canonical_resolutions()` receive only a
   `Placement`, never `World`** — use the sentinel constants in
   `faults/base.py`, or a literal topology string as a fallback.
8. **Prove a new mechanism works against a real `SimulatedEnvironment` and
   the real running app, not just green pytest.** Two out-of-plan defects in
   Phase 2a were found exactly this way.

## Resuming

```bash
git checkout main
git pull
uv sync
uv run pytest          # expect 942 passed
uv run pylint src      # expect 10.00/10
```

Next step is Phase 2b Task 2 — pick the next candidate from the domain table
in `docs/superpowers/plans/2026-08-14-phase-2b-catalog.md` (Task 1's own
section names the printing stuck-queue fault and network's duplicate-IP
cascade as the two that need new plumbing; anything else in the table is
closer to Task 1's shape). Write the task's own section into that plan before
starting, per its own "Shape of the work" convention.
