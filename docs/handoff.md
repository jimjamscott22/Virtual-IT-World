# Phase 2a handoff

Written at the end of the session that landed Task 9. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/distractor-catalog-session-seeding-yufnrd` |
| Pull request | [#5](https://github.com/jimjamscott22/Virtual-IT-World/pull/5) — **open, draft, not merged** |
| Base | `main` (Tasks 1–3 already merged via #4) |
| Tests | 521 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

## What landed this session

**Task 8** (the simulated tier-2) — see the previous handoff's content, now
folded into `CLAUDE.md`/`AGENTS.md`'s Task 8 paragraph; PR #5 already
carried it.

**Task 9** from the plan (line 1141) — **the tier-2 web flow**:

- `web/routes/escalate.py` (new): `GET`/`POST /ticket/{id}/escalate`. `GET`
  renders `_escalate.html`'s note form. `POST` calls `ticket.escalate(note,
  at)`, then `review_escalation()`; on accept, `accept_escalation()` +
  `close.py`'s shared after-action tail; on bounce, `reopen()` + render
  `_tier2.html`. Guards `TicketState.CLOSED` with 409, matching
  `close_ticket`.
- `web/routes/close.py`: extracted `render_after_action(request, session,
  ticket)` from `close_ticket()` — grade, build the report, persist it,
  render `_afteraction.html` — so both routes' terminal tail exists exactly
  once. `close_ticket()` is now three lines: fetch, guard, close, call the
  helper.
- `web/templates/_escalate.html` (new): the note textarea + submit form.
- `web/templates/_tier2.html` (new): a small "Tier-2 sent this back to you"
  banner wrapping `{% include "_ticket.html" %}` — the technician gets the
  whole live ticket pane back (priority form, tools, chat with the new
  `tier2` turn visible, both action buttons), not a dead end.
- `web/templates/_ticket.html`: an `Escalate` button beside `Close` that
  `hx-get`s the form into a dedicated `#escalate-form` slot, so opening the
  form doesn't blow away the rest of the pane.
- `web/templates/_chat.html`: a `tier2` turn renders with a capitalized
  "Tier-2:" label and its own `chat-tier2` CSS class — distinct from `user`
  and `tech`, per the plan's requirement. No CSS rule added for it, matching
  this codebase's existing precedent (`.warning`, `.ticket-cascade`, etc.
  also have no hand-authored styling — the class name is the "distinct"
  hook, not a color).
- `web/app.py`: registered the new router.
- `session/afteraction.py`: `AfterAction.tier2` (mirrors
  `Grade.escalation_quality`) and a verdict-chain entry checked **before**
  the `grade.correct` branch — `escalation_quality == "bounced" and
  fault_cleared` reads "You tried to hand this off; it was yours. You did
  fix it after." This has to come first: a bounced-then-fixed ticket is
  already `correct=True` (Task 8's design), so the existing `grade.correct`
  check would otherwise fire first and silently erase the fact that tier-2
  sent it back.
- `web/templates/_afteraction.html`: renders `report.tier2` as its own line
  when `"accepted"` or `"bounced"` (skipped for `"none"`).
- **The direct "Escalated" option in the close-ticket dropdown is
  untouched.** It still bypasses tier-2 entirely and closes straight to
  `Disposition.ESCALATED` — Task 9 adds a second, *reviewed* path to the
  same disposition; it does not retire the unreviewed one. Nothing in the
  plan asked for that removal, and the existing test suite
  (`test_web_close.py`, `test_end_to_end.py`) depends on the dropdown path
  still working exactly as before.
- `tests/test_web_escalate.py` (new): the plan's five draft tests plus two
  more (`test_an_accepted_escalation_persists_to_the_store`,
  `test_a_bounce_shows_the_tier2_turn_in_chat`). One test needed real
  correction, not just adaptation — see the deviation table entry below;
  its naive whole-page substring check for leak terms produced false
  positives against ordinary template markup ("already", `hx-trigger=
  "load"`), so it now uses `persona/client.py:scrub()` against the tier-2
  response text itself, the same technique `test_persona_binding.py`
  already uses for the analogous prompt-leak problem.
- Verified live, not just through `TestClient`: started the real app
  (`uv run python -m vitsc`), opened `/events` with `curl -N` to let the
  simulated clock actually advance and a real ticket arrive, then drove
  `GET`/`POST /ticket/{id}/escalate` against the running server with plain
  `curl` requests. Confirmed the bounce path end to end: the tier-2 nudge
  appeared in chat labeled "Tier-2:", and the returned HTML was the full,
  still-interactive ticket pane (priority form, tools, chat, both
  buttons) rather than a dead end. The accept path is covered by
  `test_web_escalate.py`'s own real FastAPI request path, which was not
  additionally hand-verified live since the scheduler doesn't offer a way
  to force a specific fault to arrive through the running app without
  waiting on random draws.

## Next: Task 10

**Knowledge base content and loader** — plan line 1242. A green-field task
(no existing module to modify): `kb/models.py` (`Article`), `kb/loader.py`
(`load_articles()`, `get_article(id)`, `search_articles(text)`), and at
least 8 markdown articles under `src/vitsc/data/kb/` with YAML frontmatter
(`id`, `title`, `domain`, `keywords`), each containing a `## Check` or
`## Steps` section — procedural, not diagnostic. The harness-style test
(`test_no_article_is_an_answer_key`) mechanically proves no article names a
fault id or its `canonical_title`, the same "prove the mechanism, not just
green tests" discipline the fault/distractor conformance harnesses already
use. `fault.kb_articles` (added in `FaultBase`, Task 5) is currently `[]` on
every fault except `print.server_spooler_stopped`
(`["printing-nothing-prints"]`, Task 7) — `test_every_fault_kb_link_resolves`
only checks links that exist, so this is the one fault this task's article
set is required to cover; populating `kb_articles` on the rest is optional
scope, not blocking.

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
   This session did it by starting the real app and driving the bounce path
   through `curl` against a live server, not just `TestClient`. Whatever
   you're adding, find the equivalent "prove it actually does the thing"
   check before moving on.
6. **A change to `SessionQueue`'s RNG consumption can silently shift which
   fault a fixed `seed=N` deals**, in any test that builds a real
   `SessionQueue` or `AppSession`. Task 4's distractor seeding did this;
   Tasks 5–9 did not touch the RNG path — but re-run the full suite and
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
    ordering (Task 8) and this session's `scrub()`-based leak check are both
    cases of trusting the actual behavioral requirement (what a worked
    example needs to pass, what the *scrub* convention already established
    elsewhere) over a plan's literal prose or literal draft test code.
13. **A raw substring check for a leak term against a *whole rendered page*
    is unreliable — check the specific generated text instead.** A bounce
    or reply's own text is small and controlled; the page around it is not,
    and ordinary words ("already", "load") accidentally contain short
    stripped terms like `"ad"`. Use `persona/client.py:scrub()` against the
    generated text (a chat turn, a persona reply), not `in page_html`.

## Open threads

Not blocking Task 10, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance. `docs/verifying-lmstudio.md`
  is the manual procedure; a green pipeline does **not** stand in for it.
- **Two ways now reach `Disposition.ESCALATED`**: the reviewed
  `/ticket/{id}/escalate` flow (Task 9), and the unreviewed "Escalated"
  option still sitting in the close-ticket dropdown (pre-existing, untouched
  — see the Task 9 summary above). Whether the dropdown option should
  eventually be removed now that a reviewed path exists is a real design
  question nothing in the plan resolves; flagging it rather than deciding it
  unilaterally.
- **No CSS was added for `.chat-tier2`, `.tier2-bounce`, `.tier2-outcome`,
  `.escalate-form`, or `.ticket-actions`.** This matches existing precedent
  (`.warning`, `.ticket-cascade`, `.cascade-note` are also unstyled), but if
  a future task does a styling pass, these are exactly the classes it would
  want to pick up.

## Resuming

```bash
git checkout claude/distractor-catalog-session-seeding-yufnrd
uv sync
uv run pytest          # expect 521 passed, 0 xfailed
```

Then read Task 10 in the plan (line 1242) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
