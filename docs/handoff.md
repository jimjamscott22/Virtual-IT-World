# Phase 2a handoff

Written at the end of the session that landed Task 14. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/task-13-mail-env` |
| Pull request | [#8](https://github.com/jimjamscott22/Virtual-IT-World/pull/8), merged, now covers Tasks 13–14 (see below) |
| Base | `main` (Tasks 1–12 merged via [#7](https://github.com/jimjamscott22/Virtual-IT-World/pull/7)) |
| Tests | 564 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

PR #8 was opened after Task 13 alone; Task 14 was stacked onto the same
branch/PR rather than split into a second one, continuing the precedent set
when Task 12 was stacked onto PR #7. Update the PR title/description to
cover both tasks before merging.

## What landed this session

**Task 14** from the plan (line 1634) — **the mail console tool**:

- `src/vitsc/tools/mail.py` (new): `MailConsole`, a `DispatchTool` subclass
  (`TARGET_PARAM = "sam"`) mapping `get-mailbox`/`get-rules`/`get-queue` to
  Task 13's read kinds and `set-quota`/`archive`/`remove-rule`/
  `restart-transport` to its action kinds. `target_key()` is overridden so
  `get-queue`/`restart-transport` read `args["host"]` instead of
  `args["sam"]` — the same host-vs-primary-target pattern
  `printing.py:PrintManagement` already uses for `restart-spooler`'s
  `from`.
- `src/vitsc/tools/registry.py`: `MailConsole()` registered, bringing the
  tool roster to eight. `tests/test_tools_rest.py::test_all_seven_tools_are_
  registered` renamed to `test_all_eight_tools_are_registered` and its set
  extended; `tests/test_web_tools.py::test_tool_pane_lists_every_tool`
  extended with `"mail"`.
- `src/vitsc/web/templates/_tools.html`: **not modified** — it already
  iterates `all_tools()` generically (the same non-change Task 11's `kb`
  tool hit), so the plan's stated file list was inert here.
- `src/vitsc/env/simulated.py`: one-line fix to `_do_mail_set_quota`'s
  error message (`-ProhibitSendQuota must be a number.` →
  `-quota_mb must be a number.`), discovered by the plan's own test —
  see the new deviation-table row in `CLAUDE.md`/`AGENTS.md`.
- `tests/test_tools_mail.py` (new): the plan's five tests plus three more
  (`get-queue`/`restart-transport` targeting by host, and an unknown-host
  failure) — the plan's own test block didn't exercise the host-targeting
  override at all, which is exactly the part of this tool most likely to
  have a bug.
- Verified live, not just green tests: a standalone script drove every
  `mail` command directly against a real `SimulatedEnvironment` (all 8
  registered tools confirmed, correct/incorrect renders, correct
  `mutating` flags, every not-found/missing-arg path failing cleanly), then
  started the real app (`uv run python -m vitsc`) and confirmed `mail`
  appears in the tool pane and `get-mailbox`/`set-quota` work through real
  `POST /ticket/{id}/tool` calls against a running server.

### Previous sessions (superseded detail)

Tasks 1–13 (fault-aware model persona through mail query/action kinds) all
landed in earlier sessions and are described in `CLAUDE.md`/`AGENTS.md`'s
own per-task paragraphs, the current, non-duplicated record.

## Next: Task 15

**The two reference mail faults** — plan line 1697. Consumes Tasks 12–14.
Adds `catalog/mail.py` with two faults, both `FaultBase`-inheriting and
`register()`-ed:

- `mail.mailbox_full` (`difficulty=2`, not escalate-correct): `apply()`
  pushes `used_mb` just over `quota_mb`; `is_present()` is
  `used_mb >= quota_mb`. **Two** canonical resolutions —
  `mail.set_quota` and `mail.archive` — deliberately, since this is the
  catalog's clearest demonstration that the pass/fail gate is world state,
  not a chosen button. Add its id to `session/ticket.py:WORK_STOPPING`.
- `mail.external_forwarding_rule` (`difficulty=4`, **escalate-correct**):
  `apply()` adds a `MailRule` forwarding outside `meridian.local` and sets
  `forwarding_smtp`; `is_present()` checks for any such rule.
  `escalation_reason` explains this is a security incident (acting on it
  destroys evidence), and `escalation_evidence` points tier-2 at
  `mail.rules`. Note the plan's own framing: three escalate-correct faults
  now exist, each escalate-correct for a *different* reason (authorization,
  hardware, "acting is the mistake") — a better drill than three flavors of
  the same reason.

`catalog/__init__.py` needs the new module imported so registration fires.
Both faults get full conformance-harness coverage automatically via
`tests/test_catalog.py`'s parametrization — no new test needed there, just
`tests/test_faults_mail.py` for the specifics the plan lists.

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
   This session did it two ways: a standalone script exercising every
   `mail` command directly against `SimulatedEnvironment`, then a second
   pass through the real running app's HTTP surface.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this;
   Tasks 5–14 did not touch the RNG path — but re-run the full suite and
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
17. **A `DispatchTool`'s error-message wording can leak the wrong
    vocabulary layer.** `_do_mail_set_quota`'s validation error originally
    named the real cmdlet's PowerShell parameter (`-ProhibitSendQuota`)
    instead of the args-dict key the tool actually receives (`quota_mb`) —
    harmless until a test (rightly) asserts on the key a player would type
    appearing in the rejection. When a query/action handler's args dict key
    and the real cmdlet's flag name differ, decide deliberately which one
    an error message should echo, and check what any existing test already
    expects before picking.
18. **A tool's own `_tools.html`/registry "modify" instructions in the plan
    can be inert.** `_tools.html` iterates `all_tools()` and each tool's own
    `commands()` generically — Tasks 11 (`kb`) and 14 (`mail`) both needed
    zero template changes despite the plan listing the file. Check whether
    a generic loop already covers a new tool before editing the template.

## Open threads

Not blocking Task 15, but real, and none of them are recorded anywhere else.

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
  codebase already simplifies other cmdlet output, but flagging in case a
  future polish pass wants to match real `Get-Mailbox` formatting more
  closely.

## Resuming

```bash
git checkout main   # Tasks 1-14 are all here once PR #8 merges
uv sync
uv run pytest          # expect 564 passed, 0 xfailed
```

Then read Task 15 in the plan (line 1697) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
