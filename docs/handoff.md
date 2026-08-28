# Phase 2a handoff

Written at the end of the session that landed Tasks 1–3. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/next-app-task-g4vpf2` |
| Pull request | [#4](https://github.com/jimjamscott22/Virtual-IT-World/pull/4) — **open, draft, not merged** |
| Base | `main` (4 commits ahead) |
| CI | Green (Pylint, on 3.12 and 3.13) |
| Tests | 376 passing, 4 skipped |
| Lint | 10.00/10 on `src` and on `tests` |

The 4 skips are expected and deliberate: the distractor conformance harness is
parametrized over a catalog that is empty until Task 4.

## What landed

Against `docs/superpowers/plans/2026-08-14-phase-2a-depth-mechanics.md`:

- **Task 1 — bind leak terms per ticket.** `Persona.for_fault(leak_terms)`;
  `TemplatePersona` returns itself, `LMStudioPersona` returns a copy.
  `SessionQueue.persona_for(ticket)` resolves the binding so the web layer
  never imports the fault registry.
- **Task 2 — model-backed persona wired into the app.** `persona/config.py`
  (`VITSC_PERSONA` / `VITSC_BASE_URL` / `VITSC_MODEL`), `AppSession.degraded`,
  and a degraded banner driven from the SSE payload.
- **Task 3 — `Distractor` protocol, registry, conformance harness.** Mechanism
  only; `distractors/catalog.py` is intentionally empty.
- **Plus a CI fix** (not in the plan): the Pylint workflow was the unmodified
  GitHub starter template and had failed on *every* run since it was added,
  including on `main`. It is now a real check.

Every step for Tasks 1–3 is ticked in the plan file.

## Next: Task 4

**The distractor catalog and session seeding** — plan line 538. Creates
`distractors/catalog.py` (five distractors), and modifies `session/queue.py`
and `web/deps.py` to seed them at session start.

The one thing to get right, from the plan's own risk list: distractors are
seeded **once at session start, before the first baseline is captured**. They
are world state the technician inherits, so `capture_baseline` must run after
them — otherwise a pre-existing stopped service reads as the technician's own
collateral damage. Same capture-after-apply reasoning `world/invariants.py`
already documents for faults.

Also flagged in the plan: `endpoint.disk_full` fires below 2.0 GB free, so the
low-disk distractor must sit well above that (8–15 GB against a 120 GB norm) —
visibly odd, mechanically harmless. The harness proves it, but pick the numbers
deliberately.

## Conventions this codebase expects

Things that are easy to get wrong and are not obvious from the code alone.

1. **Register instances, not classes.** `register_distractor(Thing())` at the
   bottom of the module, matching `faults/catalog/identity.py`. A bare class
   fails at *collection* time with a missing `self`.
2. **Deviations from the plan get recorded.** `CLAUDE.md` and `AGENTS.md` both
   carry a "Where the code deliberately diverges from the plan" table. The plan
   contains full code listings and several are wrong against the real catalog;
   when you correct one, add a row rather than silently fixing it. Both files
   are kept identical.
3. **Lint is two commands.** `uv run pylint src` keeps the strict set;
   `tests` relaxes four pytest idioms. Both are in the Commands section of
   `CLAUDE.md` and in `.github/workflows/pylint.yml`. Prefer fixing a finding,
   or suppressing it at its own line, over adding to the global disable list in
   `pyproject.toml`.
4. **`tests/conftest.py` clears `VITSC_*` for every test.** `AppSession.build`
   reads the environment now, so without it a developer with
   `VITSC_PERSONA=lmstudio` exported would point the whole suite at a local
   model. Do not remove it.
5. **Prove a new harness actually fails.** The distractor harness was verified
   by temporarily registering two dishonest distractors and confirming each was
   rejected by the right test. A conformance harness that has never failed is
   not evidence of anything.

## Open threads

Not blocking Task 4, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it. A
  line-length fix during the CI work had to be verified by diffing rendered
  output by hand (across every machine plus the no-lease APIPA path) because
  the suite could not tell whether it had broken. Worth a real test.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance, so the model-backed half of the
  Definition of Done has never been exercised. `docs/verifying-lmstudio.md` is
  the manual procedure; it must be run on a machine with the model loaded, and
  a green pipeline does **not** stand in for it.
- **The 4 skipped tests will stay silently green if Task 4 slips.**
  `tests/test_distractor_registry.py::test_the_catalog_is_importable_and_currently_empty`
  asserts the empty state on purpose, so it fails the moment the catalog is
  filled — flip it to a non-empty assertion then, mirroring
  `test_catalog.py::test_the_catalog_is_not_empty`.
- **PR #4 is a draft carrying four commits across three tasks.** If that is too
  much to review at once, the CI fix (`f3b0999`) is independent of the persona
  work and could be split onto its own branch.

## Resuming

```bash
git checkout claude/next-app-task-g4vpf2
uv sync
uv run pytest          # expect 376 passed, 4 skipped
```

Then read Task 4 in the plan (line 538) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
