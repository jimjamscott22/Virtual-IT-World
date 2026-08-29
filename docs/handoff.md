# Phase 2a handoff

Written at the end of the session that landed Task 10. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/next-task-docs-lt883z` |
| Pull request | not yet opened this session |
| Base | `main` (Tasks 1–9 merged via [#5](https://github.com/jimjamscott22/Virtual-IT-World/pull/5) — squash-merged as one PR covering distractors through the tier-2 web flow, despite the PR title naming only Task 4) |
| Tests | 526 passing, 0 xfailed |
| Lint | 10.00/10 on `src` and on `tests` |

## What landed this session

**Task 10** from the plan (line 1242) — **knowledge base content and
loader**:

- `src/vitsc/kb/models.py` (new): `Article(id, title, domain, keywords,
  body)`. `domain` is its own `Literal` including `"general"`, a superset of
  `Fault.Domain` rather than a reuse of it — a KB page can be general triage
  advice with no single fault domain to pin it to.
- `src/vitsc/kb/loader.py` (new): `load_articles()` reads
  `src/vitsc/data/kb/*.md` via `importlib.resources.files("vitsc.data").
  joinpath("kb")` (the same access pattern `world/seed.py` uses for
  `company.yaml`), splits each file's YAML frontmatter from its body, and
  caches the result with `lru_cache`. `get_article(id)` and
  `search_articles(text)` (title/keyword/id substring scoring, ranked, `[]`
  on no hit) both read through that cache.
- `src/vitsc/data/kb/*.md` (new, 8 files): all original content, each with a
  `## Check` or `## Steps` section — procedure and Meridian's own
  conventions, never "symptom X means cause Y":
  `general-triage-first-questions`, `general-meridian-estate`,
  `identity-cannot-sign-in`, `identity-missing-drive`,
  `network-no-internet`, `printing-nothing-prints` (the plan's own worked
  example, used verbatim), `endpoint-slow-or-failing`,
  `mail-cannot-send-or-receive`.
- `tests/test_kb.py` (new): the plan's five tests, with one deliberate
  deviation — see the deviation table entry below. `test_no_article_is_an_
  answer_key` mechanically proves no article's title-plus-body contains a
  fault's `id` or its `canonical_title`.
- `kb_articles` populated on the eight faults (across identity/network/
  endpoint/printing) that have a matching article today —
  `ad.account_locked` and `ad.password_expired` both point at
  `identity-cannot-sign-in` on purpose, per the plan's Step 5. The three
  articles with no fault yet to link them (`general-triage-first-
  questions`, `general-meridian-estate`, `mail-cannot-send-or-receive`) stay
  unlinked: no fault is general-only, and the mail world model doesn't
  exist until Task 12 — `test_every_fault_kb_link_resolves` only checks
  links that exist, so this is inert, not failing, matching how the handoff
  before this one already flagged populating `kb_articles` as optional
  scope.
- Verified the mechanism, not just green tests: `search_articles("printer")`
  and `search_articles("zzzzz")` were both exercised directly at a REPL
  against the real catalog before trusting the test, and every one of the
  eight articles' frontmatter was re-read against `test_articles_load_with_
  complete_frontmatter`'s field list by hand.

### Previous sessions (superseded detail)

Tasks 1–9 (fault-aware model persona through the tier-2 web flow) all landed
in earlier sessions and are described in `CLAUDE.md`/`AGENTS.md`'s own
per-task paragraphs, which are the current, non-duplicated record — this
handoff no longer repeats them. All nine tasks are on `main` as of Task 10's
start, squash-merged via [#5](https://github.com/jimjamscott22/Virtual-IT-World/pull/5).

## Next: Task 11

**The KB tool and after-action links** — plan line 1367. Consumes Task 10's
loader. `src/vitsc/tools/kb.py`: a plain `Tool` (not `DispatchTool` — it
reads articles, not the environment, so it has no `Query` to issue), with
`search`/`read` commands; it must still record a `ToolCall` with
`mutating=False` on every call, since the log is what grading reads. Register
it in `tools/registry.py`, and add `"kb"` to
`tests/test_web_tools.py::test_tool_pane_lists_every_tool`'s enumeration.
`grading.py` gains `Grade.kb_consulted: bool` (any `kb` tool call on the
ticket) — a diligence signal only, never a correctness gate.
`afteraction.py` gains `AfterAction.kb_suggestions: list[str]` from
`fault.kb_articles`, rendered as links in `_afteraction.html`, distinguishing
an article that was read from one that would have helped; if the technician
found a distractor, name it too via `SessionQueue.distractors` and its
`note`. `web/routes/kb.py`: `GET /kb?q=` and `GET /kb/{id}` rendering
`_kb.html`, so the KB is browsable outside a ticket. Test file:
`tests/test_tools_kb.py`, `tests/test_web_kb.py` — the plan's draft
`test_the_kb_tool_does_not_import_faults_or_world` AST-walks
`tools/kb.py`'s own source, which is a stronger, more local check than the
package-wide `tests/test_architecture.py` sweep; keep both rather than
picking one.

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

Not blocking Task 11, but real, and none of them are recorded anywhere else.

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
git checkout main   # Tasks 1-10 are all here; open a new branch off it for Task 11
uv sync
uv run pytest          # expect 526 passed, 0 xfailed
```

Then read Task 11 in the plan (line 1367) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
