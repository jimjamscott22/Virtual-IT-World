# Phase 2a handoff

Written at the end of the session that landed Task 15. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/next-task-plan-y1g5ti` |
| Pull request | not yet opened this session |
| Base | `main` (Tasks 1–14 merged via [#7](https://github.com/jimjamscott22/Virtual-IT-World/pull/7), [#8](https://github.com/jimjamscott22/Virtual-IT-World/pull/8)) |
| Tests | 640 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

## What landed this session

**Task 15** from the plan (line 1706) — **the two reference mail faults**:

- `src/vitsc/faults/catalog/mail.py` (new): `MailboxFull`
  (`mail.mailbox_full`, `difficulty=2`, not escalate-correct) and
  `ExternalForwardingRule` (`mail.external_forwarding_rule`, `difficulty=4`,
  escalate-correct), both `FaultBase`-inheriting and `register()`-ed.
  `MailboxFull.apply()` pushes `used_mb` just over `quota_mb`;
  `canonical_resolutions()` offers two independently sufficient fixes —
  `mail.set_quota` and `mail.archive` — the catalog's clearest proof that
  the pass/fail gate is world state, not a chosen button.
  `ExternalForwardingRule.apply()` appends a `MailRule` forwarding to
  `s.whitfield@external-mail.example.com`-shaped address and sets
  `forwarding_smtp`; `is_present()` checks for any rule whose `forward_to`
  doesn't end in `@{world.org.domain}`. `escalation_reason` explains the
  security-incident framing (acting destroys evidence); `escalation_evidence`
  points tier-2 at `mail.rules` explicitly, even though it duplicates what
  `diagnostic_path()` would supply by fallback.
- `src/vitsc/faults/catalog/__init__.py`: imports the new module.
- `src/vitsc/session/ticket.py`: `mail.mailbox_full` added to
  `WORK_STOPPING`.
- `tests/test_faults_mail.py` (new): the plan's four tests verbatim.
- Three pre-existing tests updated to keep the suite green with a 13th and
  14th fault registered (all discovered by just running the suite — no
  surprises, but real edits): `tests/test_catalog.py`'s
  `test_v1_catalog_is_complete` (id set extended) and
  `test_exactly_two_faults_are_escalate_correct` → renamed
  `test_exactly_three_faults_are_escalate_correct` (set extended to include
  `mail.external_forwarding_rule`); `tests/test_end_to_end.py`'s `HTTP_FIX`
  gained `"mail.mailbox_full": ("mail", "set-quota")` and `TARGET_FIELD`
  gained `"set-quota": "sam"`, following the precedent already set when
  `print.server_spooler_stopped` landed (that fault's `HTTP_FIX` entry
  already existed before Task 16, despite Task 16's own text listing it as
  something still to add — whichever task registers a new escalate-incorrect
  fault keeps this table current immediately, since the guard test iterates
  `all_faults()` and fails at the next `pytest` run otherwise). New
  deviation-table rows record all three in `CLAUDE.md`/`AGENTS.md`.
- Verified live, not just green tests: a standalone script drove both
  faults' full lifecycle directly (absent → `apply()` → present, diagnostic
  query differs from clean world, every canonical resolution clears
  `is_present()` with zero invariant violations) and a second script drove
  `session/tier2.py:review_escalation()` against a real `SessionQueue`-opened
  ticket for `mail.external_forwarding_rule`: an evidence-free note bounces
  ("Tell us what you found..."), a note naming `mail.rules`/the sam is
  accepted and quotes back `escalation_reason`, and `mail.mailbox_full`
  (fixable) bounces regardless of note quality — confirming the
  ownership-before-evidence order from Task 8 holds for the new fault too.

Housekeeping: this session's branch (`claude/task-13-mail-env`, holding
Tasks 13–14) was already merged via PR #8 by the time this session resumed.
The designated branch `claude/next-task-plan-y1g5ti` had gone stale (old,
pre-Task-13 commits diverged from `main`), so it was reset from
`origin/main` before Task 15's work began — the reset commits were already
superseded/merged content, not unmerged work, so nothing was lost.

### Previous sessions (superseded detail)

Tasks 1–14 (fault-aware model persona through the mail console tool) all
landed in earlier sessions and are described in `CLAUDE.md`/`AGENTS.md`'s
own per-task paragraphs, the current, non-duplicated record.

## Next: Task 16

**End-to-end coverage for every new surface** — plan line 1788. Consumes
everything landed so far (cascades, tier-2, KB, mail, distractors). Extends
`tests/test_end_to_end.py` with:

- `test_a_cascade_can_be_worked_through_http` — open
  `print.server_spooler_stopped`'s cascade, restart the spooler once, close
  all three sibling tickets, confirm each grades correct.
- `test_a_bounced_escalation_can_be_recovered_through_http` — escalate a
  fixable fault with a weak note, confirm it bounces back to
  `in_progress`, fix it for real, confirm the after-action names the
  wrong handoff.
- `test_a_mail_ticket_can_be_worked_through_http` — a full HTTP pass on
  `mail.mailbox_full` (this session's `HTTP_FIX` entry already supports the
  existing parametrized full-pass test; Task 16 adds a dedicated test with
  richer assertions about `MailConsole`'s Exchange-shaped output).
- `test_a_seeded_distractor_does_not_block_any_ticket` — a full pass with
  `AppSession.build(seed=11)` (or any seed producing distractors) and an
  assertion that `session.queue.distractors` is non-empty.

The `HTTP_FIX`/`TARGET_FIELD` table entries this task's own plan text lists
(`print.server_spooler_stopped`, `mail.mailbox_full`) are **already present**
— Task 7 and Task 15 respectively added them proactively to keep the suite
green at each step, per convention #18 below (new). Step 1 of Task 16 is
therefore a no-op; start at Step 2 (the new tests) directly.

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
   This session did it two ways: a standalone script exercising both new
   faults' full apply/diagnose/resolve lifecycle directly against
   `SimulatedEnvironment`, then a second script driving `session/tier2.py`
   against a real `SessionQueue`-opened ticket.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this;
   Tasks 5–15 did not touch the RNG path — but re-run the full suite and
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
19. **A hardcoded "complete" id-set test (`test_v1_catalog_is_complete`) and
    a hardcoded count test (`test_exactly_two_faults_are_escalate_correct`)
    both break the moment a task registers a new fault — before the task
    that "officially" owns updating them arrives.** Keep them current in the
    same task that adds the fault, the same way `HTTP_FIX` (below) has to
    be. A future task can rename a count test again the moment it goes
    stale, same reasoning as Task 4's `test_the_catalog_is_not_empty`.
20. **`tests/test_end_to_end.py`'s `HTTP_FIX`/`TARGET_FIELD` tables must stay
    current in the task that registers a new escalate-incorrect fault, not
    whichever later task's plan text happens to mention the file.** The
    guard test (`test_every_resolvable_fault_has_an_http_fix_mapped`)
    iterates `all_faults()` and fails immediately otherwise — it does not
    wait for the task whose plan prose lists the file.

## Open threads

Not blocking Task 16, but real, and none of them are recorded anywhere else.

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
- **`mail.external_forwarding_rule` leaves `mailbox.forwarding_smtp` set
  after the canonical fix removes the rule.** `is_present()` only inspects
  `mailbox.rules`, so this isn't a correctness bug (no invariant tracks
  `forwarding_smtp`), but a technician who only reads `mail.mailbox` after
  fixing would still see a stale `ForwardingSmtpAddress`. Flagging in case a
  future pass wants `mail.remove_rule` (or the canonical resolution) to
  clear it too.

## Resuming

```bash
git checkout main   # Tasks 1-15 are all here once this session's PR merges
uv sync
uv run pytest          # expect 640 passed, 0 xfailed
```

Then read Task 16 in the plan (line 1788) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
