# Phase 2a handoff

Written at the end of the session that landed Task 15. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/game-dev-progress-review-i56yyx` |
| Base | `main` (Tasks 1–14 all merged; the branch was cut clean off it) |
| Tests | 618 passing, 0 xfailed |
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

## Next: Task 16

**End-to-end coverage for every new surface** — plan line 1791. The
`HTTP_FIX` half of its Step 1 is already done (above), so what remains is
Step 2's four new tests in `tests/test_end_to_end.py`:

- `test_a_cascade_can_be_worked_through_http` — three tickets, one
  `print restart-spooler`, all three grade cleared.
- `test_a_bounced_escalation_can_be_recovered_through_http` — escalate
  `ad.account_locked`, get bounced, fix it, close it.
- `test_a_mail_ticket_can_be_worked_through_http`.
- `test_a_seeded_distractor_does_not_block_any_ticket`.

Note the plan's snippet for the first uses `session.queue.open_cascade(...)`
and the second asserts `state.value == "in_progress"` — both APIs exist as
written. Then Task 17 (documentation refresh) closes Phase 2a; much of its
Steps 1–2 is already done, since `CLAUDE.md` has been kept current per task
rather than left to the end.

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

## Open threads

Not blocking Task 16, but real.

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
uv run pytest          # expect 618 passed, 0 xfailed
```

Then read Task 16 in the plan (line 1791) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
