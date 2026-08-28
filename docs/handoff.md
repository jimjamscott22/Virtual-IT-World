# Phase 2a handoff

Written at the end of the session that landed Task 4. Delete this file when
Phase 2a is complete — it records *situational* state (branch, PR, what is
half-done), not architecture. Architecture lives in `CLAUDE.md`.

## Where things stand

| | |
| --- | --- |
| Branch | `claude/distractor-catalog-session-seeding-yufnrd` |
| Base | `main` (Tasks 1–3 already merged via PR #4) |
| Tests | 477 passing, 0 skipped |
| Lint | 10.00/10 on `src` and on `tests` |

The distractor conformance harness now runs real cases (previously 4 skips
against an empty catalog); the 4 skips are gone.

## What landed this session

Task 4 from `docs/superpowers/plans/2026-08-14-phase-2a-depth-mechanics.md`
(line 538) — **the distractor catalog and session seeding**:

- `distractors/catalog.py`: five distractors — `disk.moderately_low`,
  `service.wsearch_stopped`, `eventlog.old_disk_warning`,
  `printer.offline_unused` (placements is `[]` today — every seeded printer
  is already installed somewhere; it starts applying once Phase 2b grows the
  estate), and `drive.stale_mapping`.
- `session/queue.py`: `seed_distractors(world, rng, count)`, called from
  `SessionQueue.__init__` *before* `capture_baseline`, result stored on
  `self.distractors`. `distractor_count` defaults to 0 (existing tests stay
  deterministic).
- `web/deps.py`: `AppSession.build` passes `distractor_count=3`.
- `tests/test_distractor_registry.py`: the empty-catalog assertion flipped to
  `test_the_catalog_is_not_empty`.
- **One bug fix not in the plan's file list**: `env/simulated.py:_read_share_access`
  indexed `world.shares[machine.mapped_drives[q.target]]` directly. Nothing
  before `drive.stale_mapping` ever put a value in `mapped_drives` that
  wasn't a real `world.shares` key, so this was latent — but a player can
  type `Get-PSDrive -Name Z:` freely (`PowerShellConsole.target_key` passes
  whatever drive letter through), which would `KeyError` into an unhandled
  500 the moment that distractor was seeded. Fixed to return the same
  "network path was not found" text the DNS-failure branch already renders.
  Recorded in the deviations table in `CLAUDE.md`/`AGENTS.md`.
- `pyproject.toml`: `max-attributes = 8` added to `[tool.pylint.design]`,
  following the existing "raise a little rather than disable" convention —
  `SessionQueue` gained `distractors` as its 8th attribute.
- Verified the harness actually fails: temporarily set `disk.moderately_low`
  to a fault-flipping value (0.5 GB, under `endpoint.disk_full`'s threshold)
  and confirmed `test_distractor_never_flips_a_fault` caught it, per the
  "prove a new harness actually fails" convention from Task 3.

One incidental fix: `tests/test_web_close.py`'s fixture used `seed=1`, which
after distractor seeding started consuming from the RNG stream landed on
`endpoint.failing_disk` (an escalate-only fault with no canonical
resolution) as the first ticket, breaking two tests that assumed a
resolvable fault. Changed to `seed=0`, which still deals a resolvable fault
after seeding.

## Next: Task 5

**Cascade data model — reporters, sibling tickets, plural arrivals** — plan
line 652. Adds `FaultBase` (defaults for `kb_articles`, `escalation_reason`,
`escalation_evidence`, `reporters`), retrofits all ten catalog faults to
inherit it, extends `Ticket` with `cascade_id`, and changes
`SessionQueue.open_ticket()` to return `list[Ticket]` (`open_one()` stays
for single-ticket callers). This is a wider-reaching change than Task 4 —
`grep -rn "open_ticket"` across `tests/` and `src/` first, per the plan's own
Step 5, to find every caller that needs updating.

Task 7 (the reference cascade fault, `print.server_spooler_stopped`) is what
actually exercises the cascade path end to end; Task 5's own tests are
expected to fail or xfail against it until Task 7 lands.

## Conventions this codebase expects

Things that are easy to get wrong and are not obvious from the code alone.

1. **Register instances, not classes.** `register_distractor(Thing())` /
   `register(Thing())` at the bottom of the module. A bare class fails at
   *collection* time with a missing `self`.
2. **Deviations from the plan get recorded.** `CLAUDE.md` and `AGENTS.md`
   both carry a "Where the code deliberately diverges from the plan" table.
   When you correct something the plan gets wrong, or fix something the plan
   doesn't mention, add a row rather than silently fixing it. Both files are
   kept identical except their first-line title/tool-name.
3. **Lint is two commands.** `uv run pylint src` keeps the strict set;
   `tests` relaxes four pytest idioms. Prefer fixing a finding, or
   suppressing it at its own line, over adding to the global disable list in
   `pyproject.toml` — a design-limit bump (`max-locals`, `max-args`,
   `max-attributes`) is one line in `[tool.pylint.design]` with a comment
   explaining which module needed it.
4. **`tests/conftest.py` clears `VITSC_*` for every test.** `AppSession.build`
   reads the environment now, so without it a developer with
   `VITSC_PERSONA=lmstudio` exported would point the whole suite at a local
   model. Do not remove it.
5. **Prove a new harness actually fails.** Verified again this session:
   temporarily break a distractor so it flips a real fault, confirm the
   right test in `tests/test_distractors.py` catches it, then revert. A
   conformance harness that has never failed is not evidence of anything.
6. **A seed baked into a fixture is coupled to RNG consumption order.**
   Adding `distractor_count` to `SessionQueue.__init__` moved every
   downstream `rng.choice()` call, which silently changed which fault a
   fixed `seed=N` deals first in any test that builds a real `AppSession`.
   If a seeded test starts failing after a scheduling change, check whether
   the picked fault changed before assuming the test's own logic broke.

## Open threads

Not blocking Task 5, but real, and none of them are recorded anywhere else.

- **`ipconfig` rendering has no test coverage.** `env/simulated.py`'s
  `_read_net_ipconfig` builds `ipconfig`-shaped output whose dotted-leader
  spacing deliberately mimics the real utility, and nothing asserts on it.
  Worth a real test.
- **The LM Studio path is still unverified.** No environment used so far has
  network access to a local LM Studio instance, so the model-backed half of
  the Definition of Done has never been exercised. `docs/verifying-lmstudio.md`
  is the manual procedure; it must be run on a machine with the model
  loaded, and a green pipeline does **not** stand in for it.

## Resuming

```bash
git checkout claude/distractor-catalog-session-seeding-yufnrd
uv sync
uv run pytest          # expect 477 passed, 0 skipped
```

Then read Task 5 in the plan (line 652) and continue. `CLAUDE.md` is the
architectural brief and is current as of this handoff.
