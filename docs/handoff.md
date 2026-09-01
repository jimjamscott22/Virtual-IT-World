# Phase 2a handoff

Written at the end of the session that landed Tasks 11–12. Delete this file
when Phase 2a is complete — it records *situational* state (branch, PR, what
is half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/next-task-plan-y1g5ti` |
| Pull request | [#7](https://github.com/jimjamscott22/Virtual-IT-World/pull/7), draft, both tasks in one PR by design (see below) |
| Base | `main` (Tasks 1–10 merged via [#6](https://github.com/jimjamscott22/Virtual-IT-World/pull/6)) |
| Tests | 544 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

PR #7 was opened after Task 11 alone; Task 12 was deliberately stacked onto
the same branch/PR rather than split into a second one — a user call made
mid-session, not a plan requirement. Update the PR title/description to cover
both tasks before merging, and check whether CI is still green and no review
comments landed on the Task-11-only version before pushing Task 12's commit.

## What landed this session

**Task 11** from the plan (line 1367) — **the KB tool and after-action
links**:

- `src/vitsc/tools/kb.py` (new): `KnowledgeBase`, a plain `Tool` (not a
  `DispatchTool` — it reads `vitsc.kb`'s article catalog, not the simulated
  environment, so it has no `Query` to issue). `search`/`read` are its only
  commands; every call still records a `ToolCall` with `mutating=False`,
  because the log is what grading reads. A missing argument or unknown
  command renders the same `MISSING`/`UNKNOWN` text every other tool uses.
- `src/vitsc/tools/registry.py`: `KnowledgeBase()` registered, bringing the
  tool roster to seven. `tests/test_tools_rest.py::test_all_six_tools_are_
  registered` renamed to `test_all_seven_tools_are_registered` and its set
  extended; `tests/test_web_tools.py::test_tool_pane_lists_every_tool`
  extended with `"kb"`.
- `tests/test_tools_kb.py` (new): the plan's five tests verbatim.
- `src/vitsc/session/grading.py`: `Grade.kb_consulted: bool` — any `kb` tool
  call on the ticket. Diligence signal only; no correctness field reads it.
- `src/vitsc/session/afteraction.py`: `AfterAction.kb_suggestions: list[str]`
  — one `<a href="/kb/{id}">` line per `fault.kb_articles` entry (marked
  "already read" when the ticket's own `kb read` calls named that id,
  "would have helped" otherwise), plus one plain-text line per
  `SessionQueue.distractors` entry quoting that distractor's own `note`.
  `build_after_action()` gained a keyword-only `distractors` parameter
  (and made `siblings` keyword-only too, to keep pylint's
  `too-many-positional-arguments` happy); `web/routes/close.py`'s
  `render_after_action()` passes `session.queue.distractors` through.
  `_afteraction.html` renders the list as a "Knowledge base" section with
  `| safe` — deliberately, since every string here is built from static
  catalog content (`fault.kb_articles`, `Distractor.note`), never from a
  ticket/persona/chat source, unlike `report_text`'s autoescaping fix. See
  the new deviation-table row in `CLAUDE.md`/`AGENTS.md`.
- `src/vitsc/web/routes/kb.py` + `src/vitsc/web/templates/_kb.html` (new):
  `GET /kb?q=` (lists all articles, or search hits; "No matching articles."
  on a miss) and `GET /kb/{id}` (404 on an unknown id), so the KB is
  browsable outside a ticket. Registered in `web/app.py`.
- `tests/test_web_kb.py` (new), and new grading/after-action tests in
  `tests/test_grading.py` (`kb_consulted` true/false, an unread article
  reported as "would have helped", a read one as "already read", a seeded
  distractor named by its own `note`).
- Verified live, not just green tests: started the real app
  (`uv run python -m vitsc`), opened `/events` to drive a real ticket
  arrival off the simulated clock, ran `kb search`/`kb read` through actual
  `POST /ticket/{id}/tool` calls against the running server, and closed the
  ticket to confirm the after-action's "Knowledge base" section named the
  article as already-read and quoted a seeded distractor's note.

**Task 12** from the plan (line 1454) — **the mail world model**:

- `src/vitsc/world/models.py`: `MailRule(name, forward_to, delete_after,
  created_by)`, `Mailbox(owner_sam, primary_smtp, server, quota_mb, used_mb,
  rules, forwarding_smtp, litigation_hold)`, `MailSystem(server,
  transport_state, queue_depth, mailboxes)`. `World` gains a required
  `mail: MailSystem` field and `mailbox_for(sam) -> Mailbox | None`.
- `src/vitsc/data/company.yaml`: `MER-MB-01` (`role: mailserver`, ip
  `10.20.10.8`) added under `servers` — no `seed.py` change was needed to
  turn it into a `Machine`, since the existing servers loop already builds
  one generically from any `hostname`/`ip` pair (`role` is metadata nothing
  reads). A small `mail:` block (`server: MER-MB-01`, `quota_mb: 51200`)
  gives the domain default.
- `src/vitsc/world/seed.py`: `load_world()` derives one `Mailbox` per user
  from their already-computed `upn`, rather than hand-authoring twelve
  near-identical rows in `company.yaml` — the same reasoning that already
  keeps `company.yaml` as the one hand-authored file. A new user added there
  automatically gets a mailbox; there's no separate list to forget.
- Deliberately **not** added: any mail invariant (a deleted mailbox, a quota
  dropped below usage). Every invariant is a new way for a fault to accuse
  itself, and there's nothing to test one against until 2b's mail faults
  exist — adding it now would be untested by construction.
- `tests/test_world_seed.py`: the plan's three tests verbatim.
- Verified live: `uv run python3 -c "..."` against a fresh `load_world()`
  confirmed all 12 users have a mailbox ending `@meridian.local`, the mail
  system reports `MER-MB-01`/`Running`/queue depth 0/12 mailboxes,
  `MER-MB-01` is a normal `Machine` with `assigned_to is None`, and
  `mailbox_for("nope")` returns `None` rather than raising.
- `mail-cannot-send-or-receive.md` (shipped inert in Task 10's KB) still
  links to no fault — Task 13 (mail query/action kinds) and the mail fault
  catalog after it are what make this load-bearing.

### Previous sessions (superseded detail)

Tasks 1–10 (fault-aware model persona through the KB content/loader) all
landed in earlier sessions and are described in `CLAUDE.md`/`AGENTS.md`'s own
per-task paragraphs, the current, non-duplicated record.

## Next: Task 13

**Mail query and action kinds** — plan line 1546. Consumes Task 12's models.
Adds `_read_mail_mailbox`/`_read_mail_rules`/`_read_mail_queue` and
`_do_mail_set_quota`/`_do_mail_archive`/`_do_mail_remove_rule`/
`_do_mail_restart_transport` to `env/simulated.py`'s `getattr` dispatch (dots
become underscores, same as every other kind). `mail.archive` must reduce
`used_mb` to a fixed fraction of quota rather than to a remembered original —
`SimulatedEnvironment` is constructed *after* `apply()`, so nothing cached at
`__init__` reflects pre-fault state (the same gotcha `CLAUDE.md` already
documents for `machine.renew_dhcp`). Extend `tests/test_simulated_env.py`
with the plan's six tests.

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
   This session did it by starting the real app and driving `kb search`/
   `kb read` and a ticket close through `curl` against a live server, not
   just `TestClient` — confirming the "already read" vs "would have helped"
   distinction actually renders, not just that a test asserts it does.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this;
   Tasks 5–12 did not touch the RNG path — but re-run the full suite and
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
    cases of trusting the actual behavioral requirement (what a worked
    example needs to pass, what the *scrub* convention already established
    elsewhere) over a plan's literal prose or literal draft test code.
13. **A raw substring check for a leak term against a *whole rendered page*
    is unreliable — check the specific generated text instead.** A bounce
    or reply's own text is small and controlled; the page around it is not,
    and ordinary words ("already", "load") accidentally contain short
    stripped terms like `"ad"`. Use `persona/client.py:scrub()` against the
    generated text (a chat turn, a persona reply), not `in page_html`.
14. **`| safe` in a template is not categorically forbidden — only for text
    that can trace back to a ticket, a persona, or a chat turn.** `report_text`
    is autoescaped because a persona could inject markup (see the deviation
    table). `AfterAction.kb_suggestions` is `| safe` because every string in
    it is built in `afteraction.py` from static local content
    (`fault.kb_articles`, `Distractor.note`) that never touches user or
    model input. Check the data's provenance before copying either pattern.
15. **A `World` field with no default (`mail: MailSystem`) makes every direct
    `World(...)` construction outside `world/seed.py` a build error until
    updated.** None exist today — every test builds a world via `load_world()`
    — but the next task that adds a second required field should grep for
    `World(` call sites first rather than assume `load_world()` is the only
    constructor in play.

## Open threads

Not blocking Task 13, but real, and none of them are recorded anywhere else.

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
  from the main queue page. Not required by Task 11's stated scope, but
  worth a look if a future task does navigation/UX passes.

## Resuming

```bash
git checkout main   # Tasks 1-12 are all here once PR #7 merges
uv sync
uv run pytest          # expect 544 passed, 0 xfailed
```

Then read Task 13 in the plan (line 1546) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
