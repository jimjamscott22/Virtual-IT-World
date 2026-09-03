# Phase 2a handoff

Written at the end of the session that landed Task 13. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/task-13-mail-env` |
| Pull request | not yet opened this session |
| Base | `main` (Tasks 1–12 merged via [#7](https://github.com/jimjamscott22/Virtual-IT-World/pull/7)) |
| Tests | 556 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

This branch is a fresh cut off `main`, not a continuation of
`claude/next-task-plan-y1g5ti` (which PR #7 merged and retired). A prior
session's attempt to force-reset that old branch name to `main` was blocked
by the sandbox's safety classifier as a destructive git op — `git checkout -B
<name> origin/main` plus a force-with-lease push both got refused, even
though the branch's own commits were already fully merged. The workaround:
cut a new, differently-named branch (`claude/task-13-mail-env`) straight off
`origin/main` instead of trying to force-reuse the old name. If a future
session hits the same block, don't fight the classifier — just pick a new
branch name.

## What landed this session

**Task 13** from the plan (line 1546) — **mail query and action kinds**:

- `src/vitsc/env/simulated.py` gains three read handlers and four action
  handlers, dispatched the same `getattr(self, f"_read_{kind}")`/
  `_do_{kind}` way as every other query/action kind (dots become
  underscores):
  - `_read_mail_mailbox`: `Get-Mailbox`-shaped output —
    `PrimarySmtpAddress`, `TotalItemSize`, `ProhibitSendQuota`,
    `ForwardingSmtpAddress`, `LitigationHoldEnabled`. Unknown sam → clean
    `ok=False`.
  - `_read_mail_rules`: a `Get-InboxRule`-style table (`Name`/`ForwardTo`/
    `DeleteMessage` columns), or `"No inbox rules configured."` when the
    mailbox has none. Unknown sam → clean `ok=False`.
  - `_read_mail_queue`: transport state + queue depth, but only for
    `world.mail.server` itself — any other target is `NOT_FOUND`, the same
    "the query names a specific real thing" discipline `printer.state` and
    `machine.state` already use.
  - `_do_mail_set_quota`: parses `quota_mb` as a float (invalid input → a
    clean `-ProhibitSendQuota must be a number.` failure, mirroring
    `machine.clear_disk`'s `-Gb` validation), then sets it directly.
  - `_do_mail_archive`: reduces `used_mb` to `ARCHIVE_TARGET_FRACTION`
    (10%) of the mailbox's *current* quota — never a remembered
    pre-archive value. This isn't a style choice: `SimulatedEnvironment`
    is constructed *after* `apply()`, so nothing cached at `__init__`
    could reflect a pre-fault value even if the code tried — the same
    gotcha `CLAUDE.md` already documents for `machine.renew_dhcp`
    (`dhcp_reserved_ip` existing as a fault-immune field for exactly this
    reason).
  - `_do_mail_remove_rule`: fails cleanly (`ok=False`) when the named rule
    doesn't exist, rather than silently no-op'ing or raising.
  - `_do_mail_restart_transport`: only accepts `world.mail.server` as a
    target (a `Restart-Service`-shaped "service not found" message
    otherwise), then sets `transport_state = RUNNING` and `queue_depth = 0`.
- `tests/test_simulated_env.py`: the plan's six tests, plus five more
  covering the reads (`mail.rules`/`mail.queue`) the plan's test block
  didn't exercise directly, and the not-found path for every new kind
  (`mail.rules` on an unknown user, `mail.queue`/`mail.restart_transport`
  on a non-mail-server target, `mail.remove_rule` on a nonexistent rule
  name) — the plan's own six tests only covered the happy paths plus one
  not-found case (`mail.mailbox`), and every other existing kind in this
  file has a matching not-found test, so these fill a real gap rather than
  padding coverage.
- Verified live, not just green tests: a `uv run python3 -c "..."` script
  drove every new read and action against a real `SimulatedEnvironment`
  built from `load_world()`, printing the actual rendered PowerShell/Exchange-
  style text for each (mailbox dump, empty vs. populated rule table, queue
  status, quota change, archive, rule removal, transport restart) and
  confirming every not-found path returns `ok=False` rather than raising.
- Nothing consumes these kinds yet — Task 14 (the mail console tool) is
  what exposes them to the player; `mail-cannot-send-or-receive.md`
  (shipped inert in Task 10's KB) still links to no fault until the mail
  fault catalog after that.

## Next: Task 14

**The mail console tool** — plan line 1634. Consumes Task 13's kinds.
`tools/mail.py`: `MailConsole` (`name = "mail"`), a `DispatchTool` subclass
mapping `get-mailbox`/`get-rules`/`get-queue` to the three read kinds and
`set-quota`/`archive`/`remove-rule`/`restart-transport` to the four action
kinds — the `TARGET_PARAM` is `"sam"` for the mailbox/rule commands but the
mail server hostname for `get-queue`/`restart-transport`, so check whether
`DispatchTool`'s single `TARGET_PARAM` class attribute is enough or whether
`target_key()` needs overriding per-command (`printing.py`'s
`PrintManagement` is worth checking first — it also has host-vs-printer
target ambiguity). Register in `tools/registry.py` (bringing the roster to
eight); extend `tests/test_web_tools.py::test_tool_pane_lists_every_tool`
with `"mail"`. Test file: `tests/test_tools_mail.py` (the plan's two tests
plus the usual not-found/missing-arg coverage this session added a habit of
writing for Task 13).

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
   This session did it with a standalone script exercising every new query/
   action kind directly against `SimulatedEnvironment` and printing the
   actual rendered output, not just asserting a substring is present.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this;
   Tasks 5–13 did not touch the RNG path — but re-run the full suite and
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
   `"Stopped"`, not `"RUNNING"`/`"STOPPED"`). Compare against
   `ServiceState.RUNNING` (etc.), not an assumed all-caps form.
9. **A fault whose `reporters()` returns a list (a cascade fault) breaks any
   test that assumes `assigned_to` names the reporter.** Prefer
   `session/queue.py:resolved_reporters(world, fault, placement)` over
   hand-rolled `sam` derivation.
10. **`diagnostic_path()` and `canonical_resolutions()` receive only a
    `Placement`, never `World`.** A literal company-topology string
    (`MER-FS-01`, `PRT-ACC-01`) is an accepted fallback when no sentinel
    fits — not a new sentinel invented per fault.
11. **A message shown to the *technician* is not subject to leak-term
    scrubbing — only persona/user-facing text is.** The one exception: a
    *bounce* message for a fixable fault must stay generic across the whole
    catalog, since naming that fault's own diagnostic vocabulary there hands
    over the answer instead of a nudge.
12. **The plan's own worked examples can contradict its prose description
    of an algorithm's step order, or a test's own naive assertion can be
    wrong even when transcribed faithfully.** `tier2.py`'s ownership-first
    ordering (Task 8) and Task 10's `scrub()`-based leak check are both
    cases of trusting the actual behavioral requirement over a plan's
    literal prose or literal draft test code.
13. **A raw substring check for a leak term against a *whole rendered page*
    is unreliable — check the specific generated text instead.** Use
    `persona/client.py:scrub()` against the generated text (a chat turn, a
    persona reply), not `in page_html`.
14. **`| safe` in a template is not categorically forbidden — only for text
    that can trace back to a ticket, a persona, or a chat turn.**
    `AfterAction.kb_suggestions` is `| safe` because every string in it is
    built from static local content that never touches user or model input.
    Check the data's provenance before copying either pattern.
15. **A `World` field with no default (`mail: MailSystem`) makes every direct
    `World(...)` construction outside `world/seed.py` a build error until
    updated.** Still only one constructor (`load_world()`) as of this
    session — grep for `World(` before adding a second required field.
16. **A sandboxed session's git safety classifier can block a *reset* of an
    already-merged branch back to `main` (`checkout -B` + force-push), even
    when the reset is genuinely non-destructive** (the discarded commits are
    already in `main`'s history). Don't spend cycles arguing with it or
    trying alternate destructive incantations — cut a new branch name off
    `main` instead and move on.

## Open threads

Not blocking Task 14, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance. `docs/verifying-lmstudio.md`
  is the manual procedure; a green pipeline does **not** stand in for it.
- **Two ways now reach `Disposition.ESCALATED`**: the reviewed
  `/ticket/{id}/escalate` flow (Task 9), and the unreviewed "Escalated"
  option still sitting in the close-ticket dropdown (pre-existing, untouched).
  Whether the dropdown option should eventually be removed now that a
  reviewed path exists is a real design question nothing in the plan
  resolves; flagging it rather than deciding it unilaterally.
- **No CSS was added for `.chat-tier2`, `.tier2-bounce`, `.tier2-outcome`,
  `.escalate-form`, `.ticket-actions`, `.kb-suggestions`, `.kb-page`,
  `.kb-article`, `.kb-results`, or `.kb-search`.** This matches existing
  precedent (`.warning`, `.ticket-cascade`, `.cascade-note` are also
  unstyled), but if a future task does a styling pass, these are exactly the
  classes it would want to pick up.
- **`_kb.html` has no link back to it from `layout.html`/`index.html`.** The
  KB is reachable by typing `/kb` directly, or via the `<a href="/kb/{id}">`
  links the after-action report renders — there is no persistent nav link
  from the main queue page.
- **`mail.mailbox`'s `TotalItemSize`/`ProhibitSendQuota` render as a plain
  `"51200.0 MB"` rather than real Exchange's mixed-unit
  `"50 GB (53,687,091,200 bytes)"` style.** Consistent with how this
  codebase already simplifies other cmdlet output (e.g. `ipconfig`'s
  simplified subnet handling) rather than chasing full fidelity; flagging in
  case a future polish pass wants to match real `Get-Mailbox` formatting
  more closely.

## Resuming

```bash
git checkout main   # Tasks 1-13 are all here once this session's PR merges
uv sync
uv run pytest          # expect 556 passed, 0 xfailed
```

Then read Task 14 in the plan (line 1634) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
