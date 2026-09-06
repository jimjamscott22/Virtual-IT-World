# Phase 2a handoff

Written at the end of the session that landed Tasks 15, 16 and 17 —
every task in Phase 2a. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/game-dev-progress-review-i56yyx` |
| Pull request | [#10](https://github.com/jimjamscott22/Virtual-IT-World/pull/10), draft, green |
| Base | `main` — **merged in at `fa5bef0`**, which is PR #9's own implementation of Task 15. See the collision section below. |
| Tests | 624 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

## Health check done at the start of this session

Before writing anything, the Task 14 state was verified rather than assumed:
`main` green at 564 passing, pylint 10.00/10 on both targets, no `TODO`/
`FIXME`/`xfail` anywhere, branch identical to `main`. Three real findings:

1. **`AGENTS.md` had drifted badly.** It was still the long-form Task 3-era
   text while `CLAUDE.md` had been compressed and carried through Task 14 —
   so the convention below ("both files identical except the title line")
   was documented but not true, and a Codex session would have been briefed
   on a codebase eleven tasks out of date. `AGENTS.md` is now a byte-for-byte
   copy of `CLAUDE.md` below the title. The long per-task prose it carried
   is not lost: it is in git history and in the PRs, which is exactly where
   `CLAUDE.md` says that detail lives.
2. **`mail-cannot-send-or-receive.md` was an orphaned KB article** — shipped
   inert in Task 10, linked by no fault. Task 15 closes that: both new mail
   faults link it.
3. **Two latent defects, both found by driving the code live rather than by
   the suite.** Written up in `CLAUDE.md`'s deviation table and fixed here:
   `_read_mail_rules`'s fixed-width column collided with a realistic
   forwarding address, and `Ticket.accept_escalation` silently discarded
   tier-2's acceptance text — the only place any fault's
   `escalation_reason` is ever spoken.

## What landed this session

**Task 15** from the plan (line 1697) — **the two reference mail faults**:

- `src/vitsc/faults/catalog/mail.py` (new), registered via
  `catalog/__init__.py`:
  - `mail.mailbox_full` (`difficulty=2`): `apply()` pushes `used_mb` just
    over `quota_mb`; `is_present()` is `used_mb >= quota_mb`. Two canonical
    resolutions, `mail.set_quota` and `mail.archive`, neither of them "the"
    answer. Added to `session/ticket.py:WORK_STOPPING`.
  - `mail.external_forwarding_rule` (`difficulty=4`, escalate-correct):
    `apply()` adds an innocuously named `MailRule` forwarding outside
    `meridian.local` *and* sets `forwarding_smtp`. **Deviation from the
    plan:** `is_present()` covers both halves and `canonical_resolutions()`
    is `[]`, because no action clears `forwarding_smtp` — so a technician
    who deletes the visible rule finds the fault still present. Full
    reasoning in `CLAUDE.md`'s deviation table.
- `tests/test_faults_mail.py` (new): the plan's four tests plus eight more,
  the load-bearing one being
  `test_removing_the_rule_alone_does_not_clear_the_fault`.
- `tests/test_catalog.py`: both hardcoded roster tests extended;
  `test_exactly_two_faults_are_escalate_correct` renamed to `..._three_...`.
- `tests/test_end_to_end.py`: the `mail.mailbox_full` `HTTP_FIX` /
  `TARGET_FIELD` entries, pulled forward from Task 16 because the existing
  guard fails the moment the fault registers.

**Two out-of-plan fixes**, both surfaced by the new faults:

- `env/simulated.py:_read_mail_rules` now sizes its columns from the
  content instead of a fixed `:<28`. Regression test in
  `tests/test_simulated_env.py`.
- `Ticket.accept_escalation(text, at)` records tier-2's words;
  `AfterAction.tier2_note` carries them; `_afteraction.html` renders them.
  Tests in `tests/test_tier2.py` and `tests/test_web_escalate.py`. Before
  this, an accepted escalation — the correct disposition for three faults —
  showed the player nothing about *why* the ticket was not theirs.

**Verified live, not just green tests**, three ways: every `mail` command
driven directly against a real `SimulatedEnvironment` through the real
`MailConsole`; both faults worked end to end through `TestClient` (resolve
path, escalate path, and the wrong-disposition path, checking the grade and
verdict each time); and the real server (`uv run python -m vitsc`) started,
a ticket driven in off the simulated clock via `/events`, and `mail
get-mailbox` run through an actual `POST /ticket/{id}/tool`.

## Task 16 also landed

**End-to-end coverage for every new surface** — plan line 1791. Step 1's
`HTTP_FIX` entries came in with Task 15; this added Step 2's tests and then
some, all in `tests/test_end_to_end.py`:

- `test_a_cascade_can_be_worked_through_http` — three tickets sharing one
  `cascade_id`, one `print restart-spooler`, three clean closes, each report
  carrying the "was behind 3 tickets" note.
- `test_a_bounced_escalation_can_be_recovered_through_http` — escalate a
  fixable fault, get bounced on ownership, fix it, close it. Also asserts the
  bounce text passes `scrub()` against the fault's own leak terms.
- `test_a_mail_ticket_can_be_worked_through_http` and
  `test_an_escalate_correct_mail_ticket_is_accepted_through_http` — the mail
  slice's two faults have *opposite* correct dispositions, so one test cannot
  cover both. The second is also the only end-to-end proof that
  `escalation_reason` reaches the rendered report.
- `test_a_seeded_distractor_does_not_block_any_ticket` — a full pass with
  noise in the world, asserting `collateral_count == 0` (a distractor must
  never be blamed on the technician) and that every seeded distractor's note
  is named in the report.

`test_every_resolvable_fault_has_an_http_fix_mapped` was strengthened from
containment to set equality, so a stale entry fails too, and
`test_every_http_fix_names_a_real_command_and_target_field` was added for the
other way an entry can be wrong.

**Driven manually as well**, per the plan's Step 4 and convention 5. Two real
servers, no `TestClient`: the default app for a bounced escalation (tier-2
returns it, ticket goes back to `in_progress`, the nudge names nothing) and
an ordinary ticket closed "Resolved correctly" with three distractors seeded
and named as pre-existing in the report; and a second server built with a
cascade dealt, where the queue rendered one shared `C1` tag on three rows in
three different voices, a single `restart-spooler` cleared it, and all three
closed correctly with the cascade note.

## Task 17 also landed

**Documentation refresh** — plan line 1888, the last task in Phase 2a.

- **Step 1** (`CLAUDE.md`'s architecture section) was the real work. The layer
  diagram had never been updated past Phase 1: it listed six tools, no
  session layer, no persona layer, and no distractors. It now shows all eight
  tools, both catalogs feeding `World`, and the two layers that sit above
  `Environment`. New bullets for `vitsc.distractors` and `vitsc.kb`;
  `FaultBase`, cascades and the thirteen-fault domain breakdown folded into
  the faults bullet; `session/tier2.py` into the session bullet.
- The "enforced mechanically" line became a **table of the six guarantees
  that are proved by a test rather than trusted to a reviewer**, each naming
  the file that proves it. That is the most useful thing in the section for
  anyone deciding whether a change is safe.
- **Step 2** (the deviation table) needed nothing new — it has been extended
  per task rather than left to the end, which is how it stayed accurate.
- **Step 3** (the spec's §6 catalog table) is **not done, and is the one open
  item in Phase 2a.** See below.
- **Step 4**: `docs/superpowers/plans/2026-08-14-phase-2b-catalog.md` written
  as a skeleton — goal, seven inherited constraints, the fault-per-task
  shape, the domain table, three open questions to settle *before* Task 1
  (does the estate grow? does difficulty drive scheduling? does a session
  end?), and a Definition of Done.

### The one thing Task 17 could not do

Step 3 says to update the design spec's §6 catalog table. **The spec is not in
the working tree** — it and the whole Phase 1 plan were deleted in commit
`dbcd2bb` ("Delete the design specification…", authored by Jamie Scott,
2026-08-28), 4,604 lines across the two files.

That was a deliberate, titled commit by the repo owner, so restoring it is
not a call this session made unilaterally. Recover with:

```bash
git show dbcd2bb^:docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md
git show dbcd2bb^:docs/superpowers/plans/2026-08-07-phase-1-drill.md
```

If the spec comes back, §6 needs: the catalog table grown from "v1 catalog
(10 faults)" to the current thirteen, and the `Fault` protocol's four Phase
2a members added to its listing (`kb_articles`, `escalation_is_correct` /
`escalation_reason` / `escalation_evidence`, `reporters()`). If it stays
deleted, `CLAUDE.md` is the sole architectural record and the 2a plan's own
cross-references to the spec (its lines 11–12, and Task 17's file list) are
permanently dangling — worth a line in the 2b plan saying so.

## Phase 2a Definition of Done

Checked item by item against the plan's own list, not asserted:

| | Item | Status |
|---|---|---|
| 1 | `uv run pytest` green with LM Studio **not** running | ✅ 624 passed |
| 2 | `uv run pytest` green with LM Studio **running** | ⬜ **cannot be checked here** — no sandbox has had network to a local LM Studio. `docs/verifying-lmstudio.md` is the manual procedure; a green pipeline does not stand in for it |
| 3 | `VITSC_PERSONA=lmstudio` roleplays every ticket; stopping LM Studio mid-session shows the degraded banner | ⬜ same, manual |
| 4 | Thirteen faults conform across every placement, in all five domains | ✅ identity 4, printing 3, network 2, endpoint 2, mail 2 |
| 5 | Every distractor passes the non-interference harness | ✅ 99 passed |
| 6 | A cascade opens several tickets, one fix clears all, report names the shared cause | ✅ automated **and** played live |
| 7 | A fixable escalation bounces with a leak-free nudge; an escalate-correct one with evidence is accepted | ✅ automated and played live |
| 8 | No KB article names a fault id or `canonical_title`; every `kb_articles` link resolves | ✅ |
| 9 | `grep -r "from vitsc.faults" src/vitsc/tools/` empty; `test_architecture.py` green with `mail.py` and `kb.py` present | ✅ |
| 10 | No leak term in any system prompt | ✅ |
| 11 | A full ticket can be worked in the browser in all five domains | ✅ all five played through a real server over HTTP: `ad.account_locked`, `net.static_dns_misconfig`, `print.spooler_stopped`, `endpoint.disk_full`, `mail.mailbox_full` — each closed "Resolved correctly" |

**Phase 2a is complete except for items 2 and 3**, which are a manual check on
a machine with LM Studio running and cannot honestly be marked from here.
Do those, settle the spec question above, and this file can be deleted.

## Task 15 was implemented twice — read this before touching `mail.py`

While this branch was working Tasks 15–17, **PR #9 landed the same Task 15 on
`main` independently** (`fa5bef0`, merged 2026-09-06). Two sessions built the
same two faults from the same plan. `main` was merged into this branch and the
overlap resolved deliberately rather than by picking a side:

| File | Resolution |
| --- | --- |
| `faults/catalog/mail.py` | **PR #9's module kept as the base** — its naming, placements (`_mailbox_owners`, all users), symptom wording, and `quota_mb="999999"` all stand. Three changes applied on top, below. |
| `tests/test_faults_mail.py` | This branch's kept: it is a strict superset, containing all four of PR #9's tests plus eight more. |
| `tests/test_catalog.py` | Both sides made the *same* substantive change (same id sets, same escalate-correct roster). This branch's docstrings kept. |
| `tests/test_end_to_end.py` | Auto-merged; both added the same `HTTP_FIX`/`TARGET_FIELD` entries. |
| `CLAUDE.md` / `AGENTS.md` / `docs/handoff.md` | This branch's kept — they are current through Task 17 where PR #9's stop at 15 — with PR #9's unique content folded in (the `escalation_evidence` nuance, conventions 19–20 below). |

### The three changes applied on top of PR #9's `mail.py`

1. **`ExternalForwardingRule.is_present()` now gates on both halves.**
   PR #9's own open thread flagged this and judged it "not a correctness bug,
   since no invariant tracks `forwarding_smtp`". That reasoning is right about
   *invariants* and about *grading* — the fault is escalate-correct, so a
   technician who removes the rule and closes as resolved is marked wrong
   either way. But `is_present()` is documented in `faults/base.py` as "the
   single source of truth for both 'is it broken' and 'was it fixed'", and on
   `main` as merged it reports **fixed** on a mailbox that is still
   redirecting every message to an outside address. Reproduced directly:
   `mail.remove_rule` → `is_present()` False → `Get-Mailbox` still shows
   `ForwardingSmtpAddress: …@external-mail.example.com`.
   PR #9's thread proposed the other resolution — have `mail.remove_rule`
   clear `forwarding_smtp` too. That was rejected on purpose: it would make
   "delete the rule" a *complete* fix for a security incident, which is the
   opposite of what this fault exists to teach. **If you prefer that
   direction, this is the one change to revert.**
2. **`canonical_resolutions()` is now `[]`**, which follows from 1: with the
   gate covering `forwarding_smtp`, no sequence of existing actions clears
   the fault. Same encoding `endpoint.failing_disk` already uses, and
   `tests/test_catalog.py` already carries the branch for it.
3. **Both faults now set `kb_articles = ["mail-cannot-send-or-receive"]`**,
   which had shipped inert in Task 10 and was linked by no fault. Also
   `assert mailbox is not None` replaced with a raising helper — an `assert`
   vanishes under `python -O`, and this one guards the pass/fail gate.

Also: `diagnostic_path()` gained `mail.mailbox` alongside `mail.rules`, since
after change 1 the fault has two halves and `mail.rules` only shows one.

## Conventions this codebase expects

Things that are easy to get wrong and are not obvious from the code alone.

1. **Register instances, not classes.** `register_distractor(Thing())` /
   `register(Thing())` at the bottom of the module. A bare class fails at
   *collection* time with a missing `self`.
2. **Deviations from the plan get recorded.** `CLAUDE.md` and `AGENTS.md`
   both carry a "Where the code deliberately diverges from the plan" table.
   The two files are identical except their first-line title and tool name —
   check that this is still true before you finish, because it silently
   stopped being true between Tasks 3 and 14.
3. **Lint is two commands.** `uv run pylint src` keeps the strict set;
   `tests` relaxes four pytest idioms. Prefer fixing a finding, or
   suppressing it at its own line, over adding to the global disable list —
   a design-limit bump (`max-locals`, `max-args`, `max-attributes`) is one
   line in `[tool.pylint.design]` with a comment naming which change needed
   it, and the comment gets extended (not replaced) the next time it moves.
4. **`tests/conftest.py` clears `VITSC_*` for every test.** Do not remove it.
5. **Prove a new mechanism actually works, not just that pytest is green.**
   Both of this session's out-of-plan fixes were found this way and by no
   test. Drive it against a real `SimulatedEnvironment`, then through the
   real running app.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Adding faults changes the candidate pool
   too — Task 15 did, and the suite happened to stay green, but re-run it in
   full and read failures carefully rather than assuming either way.
7. **A `Ticket | None` → `list[Ticket]` return-type change breaks
   `is None`/`is not None` checks silently, not loudly** — a list is always
   "not None", so a `while x() is not None: pass` loop against the new
   signature never terminates. Prefer truthiness or an explicit `== []`.
8. **`ServiceState` (`world/models.py`) is a real `str, Enum`, not a bare
   string constant, and its values are mixed-case** (`"Running"`,
   `"Stopped"`). Compare against `ServiceState.RUNNING`, not an assumed
   all-caps form.
9. **A fault whose `reporters()` returns a list (a cascade fault) breaks any
   test that assumes `assigned_to` names the reporter.** Prefer
   `session/queue.py:resolved_reporters(world, fault, placement)`.
10. **`diagnostic_path()` and `canonical_resolutions()` receive only a
    `Placement`, never `World`.** A literal company-topology string
    (`MER-FS-01`, `PRT-ACC-01`) is an accepted fallback when no sentinel
    fits — not a new sentinel invented per fault.
11. **A message shown to the *technician* is not subject to leak-term
    scrubbing — only persona/user-facing text is.** The one exception: a
    *bounce* message for a fixable fault must stay generic across the whole
    catalog.
12. **The plan's own worked examples can contradict its prose description of
    an algorithm's step order, or a test's own naive assertion can be wrong
    even when transcribed faithfully.** Trust the behavioural requirement.
13. **A raw substring check for a leak term against a *whole rendered page*
    is unreliable — check the specific generated text instead**, via
    `persona/client.py:scrub()`.
14. **`| safe` in a template is not categorically forbidden — only for text
    that can trace back to a ticket, a persona, or a chat turn.** Check the
    data's provenance before copying either pattern. `AfterAction.tier2_note`
    is static catalog text but still autoescaped, because it arrives via a
    `ChatTurn`.
15. **A `World` field with no default (`mail: MailSystem`) makes every direct
    `World(...)` construction outside `world/seed.py` a build error until
    updated.** Grep for `World(` before adding a second required field.
16. **A sandboxed session's git safety classifier can block a *reset* of an
    already-merged branch back to `main`.** Cut a new branch name off `main`
    instead and move on.
17. **A `DispatchTool`'s error-message wording can leak the wrong vocabulary
    layer.** When a handler's args-dict key and the real cmdlet's flag name
    differ, decide deliberately which one an error message echoes, and check
    what any existing test already expects before picking.
18. **A tool's own `_tools.html`/registry "modify" instructions in the plan
    can be inert.** `_tools.html` iterates `all_tools()` and each tool's own
    `commands()` generically. Check whether a generic loop already covers a
    new tool before editing the template.
19. **Fixed-width column formatting in `env/simulated.py` is a landmine.**
    `f"{value:<28}"` does not truncate — a value wider than the field pushes
    the next column flush against it with no separating space, and nothing in
    the suite notices because test fixtures use short values. Several other
    renderers still use fixed widths (`_read_ad_user`, `_read_machine_state`,
    `_read_machine_services`, `_read_mail_queue`); they are fine today only
    because their values are short. Size from the content if you add one.
20. **`Fault.escalation_reason` reaches the player through exactly one
    string**, `tier2.py`'s acceptance text, and from there through
    `Ticket.chat` into `AfterAction.tier2_note`. Anything that drops a
    tier-2 chat turn silently deletes the entire teaching payload of an
    escalate-correct ticket, with no test failing.

21. **A hardcoded "complete" id-set test (`test_v1_catalog_is_complete`) and
    a hardcoded count test (`test_exactly_three_faults_are_escalate_correct`)
    both break the moment a task registers a new fault — before the task that
    "officially" owns updating them arrives.** Keep them current in the same
    task that adds the fault. (From PR #9's handoff; this branch hit the same
    thing independently.)
22. **`tests/test_end_to_end.py`'s `HTTP_FIX`/`TARGET_FIELD` tables must stay
    current in the task that registers a new escalate-incorrect fault**, not
    whichever later task's plan text happens to mention the file. The guard
    iterates `all_faults()` and fails immediately. (Also from PR #9.)
23. **Two sessions can be given the same task.** Task 15 was built twice, in
    parallel, from the same plan — see the collision section above. Before
    starting a task, check whether `main` has moved and whether an open PR
    already covers it.

## Open threads

Not blocking Task 16, but real.

- **Two of `CLAUDE.md`'s three context pointers were dangling.** The design
  spec and the Phase 1 plan were both deleted from the tree in commit
  `dbcd2bb`, but `CLAUDE.md` still listed them as if they existed — as does
  the Phase 2a plan, at its own lines 11–12 and in Task 17's file list.
  `CLAUDE.md` now says so and gives the `git show dbcd2bb^:...` recovery
  command; the plan is left alone, since editing a plan to match reality is
  Task 17's call, not a drive-by.
- **`remote clear-disk` with no `gb` silently succeeds and frees nothing.**
  `_do_machine_clear_disk` reads `float(a.args.get("gb", "0"))`, so a player
  who types `remote clear-disk host=MER-WS-001` gets `ok=True` and the
  cheerful message "MER-WS-001 now has 0.7 GB free of 256.0 GB" — a mutation
  logged against them that did nothing. `_do_mail_set_quota` handles the same
  situation the opposite way, rejecting a missing `quota_mb` outright.
  Found by mistyping the command against a real server during the Definition
  of Done pass. Not fixed here: Task 17 is a documentation task, and the fix
  touches a `mutating`/grading-adjacent path that deserves its own change.
  The fix is to treat a missing `gb` as a rejection (`ok=False`, no
  mutation), matching `set_quota`, and let `DispatchTool`'s existing
  "a rejected call never reached the environment" rule keep the grade honest.
- **PR #9's `forwarding_smtp` thread is resolved**, by the gate change above rather than by clearing the field. Reopen it if you prefer the other direction.
- **`ipconfig` rendering has no test coverage.** `_read_net_ipconfig` builds
  `ipconfig`-shaped output whose dotted-leader spacing deliberately mimics
  the real utility, and nothing asserts on it. Related to convention 19.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance. `docs/verifying-lmstudio.md`
  is the manual procedure; a green pipeline does **not** stand in for it.
- **Two ways still reach `Disposition.ESCALATED`**: the reviewed
  `/ticket/{id}/escalate` flow (Task 9), and the unreviewed "Escalated"
  option still sitting in the close-ticket dropdown. Now sharper than it was:
  the dropdown path skips `review_escalation` entirely, so it produces an
  after-action with no `tier2_note` and never tells the player why the ticket
  was not theirs — the very thing this session just fixed on the reviewed
  path. Whether the dropdown option should be removed is a real design
  question nothing in the plan resolves; flagging it rather than deciding it.
- **No CSS was added for `.chat-tier2`, `.tier2-bounce`, `.tier2-outcome`,
  `.tier2-note`, `.escalate-form`, `.ticket-actions`, `.kb-suggestions`,
  `.kb-page`, `.kb-article`, `.kb-results`, or `.kb-search`.** Matches
  existing precedent (`.warning`, `.ticket-cascade`, `.cascade-note` are also
  unstyled), but a future styling pass would want to pick these up.
- **`_kb.html` has no link back to it from `layout.html`/`index.html`.** The
  KB is reachable by typing `/kb` directly, or via the after-action's links.
- **`mail.mailbox`'s `TotalItemSize`/`ProhibitSendQuota` render as a plain
  `"51200.0 MB"`** rather than real Exchange's mixed-unit
  `"50 GB (53,687,091,200 bytes)"` style. Consistent with how this codebase
  already simplifies other cmdlet output.
- **No mail invariant exists.** Task 12 deliberately deferred one; with two
  mail faults now live, "a mailbox was deleted" or "quota set below usage"
  are the plausible candidates if a technician's collateral damage in the
  mail domain ever needs teeth.

## Resuming

```bash
git checkout claude/game-dev-progress-review-i56yyx
uv sync
uv run pytest          # expect 624 passed, 0 xfailed
```

Phase 2a's tasks are all complete. What is left is the Definition of Done's
items 2 and 3 (the LM Studio check, on a machine that has it) and the spec
question in the Task 17 section above. `CLAUDE.md` is the architectural brief
and is current; `docs/superpowers/plans/2026-08-14-phase-2b-catalog.md` is the
next plan, as a skeleton to fill in.
