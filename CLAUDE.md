# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-user helpdesk simulator (`vitsc` — Virtual IT Support Center), built as personal practice for desktop-support/helpdesk job applications. The player works tickets against a simulated Windows/AD environment (`Meridian Freight Co.`) using tools that mirror real utilities (AD console, PowerShell, network tools, event viewer, print management, remote session).

Full context lives in:
- Phase 2a plan: `docs/superpowers/plans/2026-08-14-phase-2a-depth-mechanics.md`
  — the only one of these still in the working tree.
- Design spec and Phase 1 plan: **deleted from the tree** in commit `dbcd2bb`,
  recoverable with
  `git show dbcd2bb^:docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`
  and `git show dbcd2bb^:docs/superpowers/plans/2026-08-07-phase-1-drill.md`.
  The 2a plan still cross-references both by path, as does Task 17, which is
  what will have to restore or rewrite the spec.
- **Current state, next task, and open threads: `docs/handoff.md`** — read this
  first if you are picking the work up mid-stream.

Phase 1 (Tasks 1–19) is complete: world model, `SimulatedEnvironment`, the ten-fault v1 catalog, the six player-facing tools, the persona layer (`TemplatePersona` + `LMStudioPersona`), the session layer (ticket/priority/SLA/grading/after-action), SQLite persistence (`session/store.py`), and the FastAPI + HTMX web app (`uv run python -m vitsc`). Unverified, not failing: the model-backed path has never run against a live LM Studio instance — `docs/verifying-lmstudio.md` is the manual procedure.

Phase 2a (`docs/superpowers/plans/2026-08-14-phase-2a-depth-mechanics.md`) Tasks 1–17 have landed; see `docs/handoff.md` for exactly where work stopped and what's next. Per-task detail is in git history and the PRs — the load-bearing facts that survive are in `docs/phase-2a-notes.md`, one bullet per task — read it before changing anything a Phase 2a task introduced.

**Phase 2b groundwork** (the three questions its plan said to settle before Task 1) is done: the estate grew to 20 users / 10 workstations, the drill gained a fixed eight-hour shift, and difficulty — rather than placement count — now drives which fault gets dealt. Details in `docs/superpowers/plans/2026-08-14-phase-2b-catalog.md` under "Settled before Task 1".

**Phase 2b's catalog has landed.** Eighteen new faults took the catalog from
thirteen to **thirty-two** (a nineteenth, `ad.cached_credentials_expired`, landed
on `main` in parallel — see the collision note below), and every item in the 2b
plan's Definition of Done is met except the two LM Studio checks, which need a
machine with LM Studio running and cannot honestly be ticked from a sandbox. What
the shape is now:

| | Count | Notes |
| --- | --- | --- |
| faults | 32 | identity 8, network 6, printing 6, endpoint 6, mail 6 |
| difficulty spread | 5 / 14 / 10 / 3 | across 1–4; ~69% of dealt tickets are routine |
| cascades | 5 | printing 3, network 1, mail 1 |
| escalate-correct | 4 | one per reason, no two alike |
| distractors | 11 | ratio-guarded against the fault count |
| KB articles | 15 | no orphans in either direction |

The load-bearing facts a later session needs, beyond what the per-fault modules
say themselves:

- **The machinery landed first, on its own commit.** Most 2b faults could not be
  expressed against the Phase 2a world, so `ServiceState.DISABLED`, nested
  groups, `Machine.proxy_server` / `last_domain_sync` / `clock_offset_minutes` /
  `processes`, `Printer.jobs`, `Mailbox.delegates`, `MailSystem.autodiscover_host`
  / `distribution_lists` and `Network.netmask` all arrived together, with six new
  reads and sixteen new actions. Read that commit before adding a fault that
  needs new world state.
- **The environment routes packets now.** `_reachable()` in `env/simulated.py` is
  what makes the four network faults four *different* tickets rather than four
  spellings of "the internet is broken": on-subnet traffic needs no router, and
  anything else needs a gateway that is inside the machine's own subnet *as the
  machine computes it, wrong mask included* and is the address the site's router
  actually answers on. `_resolve()` additionally requires a running `Dnscache`
  and a reachable resolver. The four signatures are in the network commit
  message; they are the thing to preserve if that function is ever touched.
- **Difficulty is a frequency decision, and the test that says so changed
  shape.** `test_easier_faults_are_dealt_more_often` was asserting two different
  claims at once. Share-of-draw *per difficulty level* is `weight × how many
  faults sit at that level`, so it moves whenever the catalog grows — writing a
  fourth difficulty-3 fault failed a test about weighting. The mechanism claim is
  now per fault (`test_an_easier_fault_is_dealt_more_often_than_a_harder_one`,
  true at any catalog size) and the composition claim is separate
  (`test_the_catalog_deals_mostly_routine_tickets`), which is the one a
  badly-chosen difficulty should fail.
- **Two new placement kinds, and printer placements now come in two shapes.**
  `Placement.kind` gained `"list"` (a mail distribution list) and `"group"` (a
  directory group). A bare printer name means the *device* and every machine that
  has it; `HOST/PRINTER` still means one workstation's installation. Anything
  placed on a list, a group, or a server must declare its own `reporters()` —
  nothing about those resolves to a person the way `Machine.assigned_to` does,
  and `resolved_reporters` otherwise comes back empty and nobody gets the ticket.
- **Escalation has exactly one path.** The unreviewed "Escalated" option is gone
  from the close dropdown *and* refused by `web/routes/close.py`. It skipped
  `review_escalation`, so it never bounced a fixable fault and produced a report
  with no `tier2_note` — the only place `Fault.escalation_reason` is ever spoken
  (convention 20). Four escalate-correct faults made that stop being cosmetic.
- **Mail invariants exist and are reachable.** A deleted mailbox and a quota set
  below current usage are both collateral damage. `mail.remove_mailbox` exists so
  the first is reachable at all: an invariant nobody can trip teaches nobody
  anything. Adding it also made a previously-unreachable raise reachable — see
  the deviation table.
- **`~/.vitsc/sessions.sqlite3` outlives the process, so `Store` rows carry a
  `session_id`** and reads are scoped to the run that wrote them. Before this the
  shift summary counted previous shifts: four tickets closed read as seven. No
  timestamp could have separated them, because the simulated clock restarts at
  09:00 every session.
- **Two sessions built a cached-credentials fault in parallel** (convention 23,
  second occurrence after Phase 2a's Task 15). `ad.cached_credentials_expired`
  landed on `main` while this work was in flight. Both were kept, because they are
  mechanically different faults about the same relationship: *that* one stops
  `Netlogon`, so the person is signed in and cut off from drives, printers and
  mail while `ad get-user` reads clean; *this* one leaves the machine's cached
  credential older than the password, so the new password is rejected locally and
  the old one still works. The one on this branch was renamed
  `ad.password_change_not_cached` — naming it for its mechanism, because two ids
  both reading `cached_credentials_*` are indistinguishable in an after-action,
  and the unmerged one is the one to move.

`tests/conftest.py` clears the three `VITSC_*` variables for every test. Now that `AppSession.build` reads the environment, a developer with `VITSC_PERSONA=lmstudio` exported would otherwise point the entire suite at a local model; the Global Constraint that the suite passes with nothing on localhost is enforced there rather than left to habit.

## Commands

```bash
uv run pylint src                          # lint the package (CI runs this)
uv run pylint tests \
  --disable=redefined-outer-name,unused-variable,protected-access,use-implicit-booleaness-not-comparison
```

No model or network access is needed to run the suite.

**Read pylint's exit code, not its score.** A single message still leaves the
rating at `10.00/10` when the codebase is large enough for one finding to round
away, and pylint exits 8 regardless. `uv run pylint src | tail -3` therefore
prints a clean-looking rating line for a run that CI fails — which is exactly how
a `too-many-branches` finding reached CI on the Phase 2b branch. Run it without a
pipe, or check `$?`; `| tail` discards the exit status too.

Lint runs as two commands so `src/` keeps the stricter rule set; the four
disabled checks are pytest idioms that only ever fire in tests (a fixture
argument shadowing its fixture, unused halves of an unpacked setup tuple,
asserting on internals, and `== []` where the empty list is the point). Every
other disabled check, with its reason, is in the `[tool.pylint.main]` /
`[tool.pylint.design]` / `[tool.pylint."messages control"]` sections of
`pyproject.toml`; a handful of narrow `# pylint: disable` comments sit inline
where pylint cannot infer the code (the `getattr` dispatch in
`env/simulated.py`, pydantic's `default_factory` in `tools/base.py`). Prefer
fixing a finding or suppressing it at its own line over adding to the global
list.

## Core design principle

**Tools read world state. They never read the fault.** A fault mutates the `World`; tools only ever call `env.read()` / `env.execute()`; a resolution mutates the world back; a fault's own `is_present()` is what decides whether it's fixed. Nothing anywhere branches on "if fault X is active." This is what makes multiple fix paths valid, lets harmless distractors be seeded honestly, and lets a future real-Windows-backed `Environment` slot in without touching tools or faults.

This is enforced mechanically, not just by convention. The guarantees that are proved by a test rather than trusted to a reviewer:

| Guarantee | Proved by |
| --- | --- |
| No `tools/` module imports `vitsc.faults`, `vitsc.world`, or `vitsc.distractors` — tools go through `Environment`'s `Query`/`Action`/`Observation` types only | `tests/test_architecture.py` |
| Every fault is placeable, discoverable, solvable by each declared path, and jargon-free in its symptoms | `tests/test_catalog.py` (parametrized over fault × placement) |
| A distractor changes no fault's `is_present()`, trips no invariant, is visible through a declared query, and breaks no canonical fix | `tests/test_distractors.py` |
| No KB article names a fault's id or `canonical_title`, and every `kb_articles` link resolves | `tests/test_kb.py` |
| A fault's `leak_terms` never reach a model prompt — they exist for `scrub()` only | `tests/test_persona_binding.py:test_leak_terms_never_reach_the_prompt` |
| Every non-escalate-correct fault is fixable through the real HTTP surface, and the fix table has no stale or wrong entries | `tests/test_end_to_end.py` |
| How often a fault is dealt depends on its `difficulty` and not on its placement count | `tests/test_queue.py` |
| The estate is the size Phase 2b settled on, and every workstation is as complete as the original six | `tests/test_world_seed.py` |
| No KB article is unlinked and no fault is unarticled — orphans in *either* direction | `tests/test_kb.py:test_no_orphans_in_either_direction` |
| The distractor count scales with the catalog, and every distractor has somewhere to land | `tests/test_distractors.py` |
| Every field of `Baseline` is carried through `forgive()` — a forgotten one makes its invariant silently inert | `tests/test_queue.py:test_forgiving_nothing_leaves_every_baseline_field_intact` |
| `HTTP_FIX` has a step for every action of a fault's canonical path, so a multi-step repair cannot be half-posted | `tests/test_end_to_end.py` |
| Escalation is reachable only through the reviewed flow, by click *and* by crafted request | `tests/test_web_close.py` |
| One session's closed tickets are not counted in another's shift | `tests/test_store.py` |

**Gotcha:** the conformance harness constructs `SimulatedEnvironment(broken)` *after* calling `fault.apply()`, never before. Any per-machine value an `Environment` caches at `__init__` time from mutable `World` state will see the already-faulted value, not the original — this bit `machine.renew_dhcp` (fixed by giving `Machine` a separate `dhcp_reserved_ip` field that faults never touch, distinct from the mutable `ip`). When adding a fault that nulls/clears a field a resolution needs to restore, give the restorable value its own fault-immune field rather than deriving it at Environment construction.

**Second gotcha, added in 2b:** a new field on `Baseline` is not finished when
`capture_baseline()` and `check_invariants()` handle it. `session/queue.py:forgive`
rebuilds the `Baseline` by naming every field, so one left out there silently
defaults to empty on every arrival — the invariant never fires in a real session
and its own unit tests keep passing. Both mail invariants shipped in that state
for a commit. `test_forgiving_nothing_leaves_every_baseline_field_intact` is the
guard; a `check_invariants` test on its own is not sufficient coverage for a new
invariant.

## Architecture

Layered, each layer written once against the layer below's protocol:

```
session (queue, ticket, grading, afteraction, tier2, store)
  │  never branches on a fault id — asks is_present() against the world
tools (ad, ps, net, eventlog, printing, remote, kb, mail)      persona
  │  env.read(Query) / env.execute(Action)                       │  card + symptoms only
Environment protocol  ← the swap point (vitsc/env/base.py)       │  never a World or Fault
  │
SimulatedEnvironment  ← v1 backend, in-memory World (vitsc/env/simulated.py)
  │  reads/writes self.world only
World (Organization, Machine, Printer, Share, Network, MailSystem)  ← vitsc/world/models.py
  ▲                                    ▲
fault catalog                    distractor catalog
(vitsc/faults/catalog/*)         (vitsc/distractors/catalog.py)
  applies mutations via a          applies harmless anomalies
  Placement; is_present() is       before the baseline is captured;
  the pass/fail gate               has no is_present() at all
```

The `kb` tool is the one exception to "a tool wraps the environment": it reads
`vitsc.kb` (static Markdown under `src/vitsc/data/kb/`) rather than world
state, so it is a plain `Tool` and not a `DispatchTool`.

Per-package detail — what each of `vitsc.world`, `env`, `faults`, `distractors`, `kb`, `tools`, `persona`
and `session` owns, and the rationale and gotchas behind each — is in `src/vitsc/CLAUDE.md`. It loads on its
own when working under `src/vitsc/`; read it explicitly before working in `tests/`.

**Two clocks, deliberately.** `Ticket.opened_at` / `closed_at` and `world.clock` are simulated time and drive SLA. `ToolCall.at` and `ChatTurn.at` are wall clock (`datetime.now(UTC)`, timezone-aware) and exist only to order chat against tool calls for `questions_before_first_mutation`. Do not set `ChatTurn.at` from `world.clock` — mixing naive and aware datetimes raises at comparison time, and the two measure different things.

## The conformance harness

`tests/test_catalog.py` is parametrized over every registered fault × every placement it declares (`fault.id@placement.key`). For each case it mechanically proves: absent before `apply()` and present after; the declared `diagnostic_path` actually surfaces something and actually differs from the clean world; every `canonical_resolutions()` path drives `is_present()` false with zero invariant violations; and `symptoms()` contains none of the fault's own `leak_terms` and none of the shared `JARGON` set (dns, dhcp, active directory, lockout, etc — the player is meant to diagnose the mechanism, not read it off the ticket). A new fault gets full coverage from this harness with no new test written — just register it correctly.

When adding a fault, the Phase 1 plan (deleted; see the top of this file for how to recover it) has the task-by-task detail for the original catalog entries; `catalog/identity.py`'s `AccountLocked` is the reference example for the shape (placements/apply/is_present/symptoms/diagnostic_path/canonical_resolutions).

## Where the code deliberately diverges from the plan

The plan contains full code listings. Tasks 10–14 were implemented from them, but the following places are **intentionally different** and should not be "corrected" back to the plan's text. Each was verified against the real catalog before changing.

The table itself — one row per deviation: where, what the plan said, why the code differs — is in
`docs/plan-deviations.md`. **Read it before changing code to match a plan listing or "fixing" something
that looks like a departure from one, and add a row there when a new deviation is made.**

## Placement sentinels

`Fault.diagnostic_path()` and `canonical_resolutions()` receive only a `Placement` (kind + key), never a `World` — faults stay pure data, not closures over world state. When a query/action target needs something only `World` can resolve (a user's assigned hostname, a printer's parent machine, a share's required group, the mail server's name), the fault embeds a sentinel string (`PLACEHOLDER`, `PLACEHOLDER_MACHINE`, `PLACEHOLDER_GROUP`, `PLACEHOLDER_PRINTER`, `PLACEHOLDER_SUB_GROUP`, `PLACEHOLDER_MAIL_SERVER` in `vitsc/faults/base.py`) and the caller resolves it with `bind()` / `bind_query()` once `World` is in scope. `sub_group_name()` lives in `base.py` beside the sentinel that resolves it, because `ad.nested_group_membership` creates that group and `bind()` names it, and two copies of a naming rule is one copy too many.

**A printer placement has two shapes and the sentinels handle both**: `HOST/PRINTER` is one workstation's installation of a printer (`print.wrong_driver`), while a bare printer name is the device itself and everyone who has it (`print.printer_offline`, `print.stuck_job`, `print.driver_after_model_swap`). `_machine_key` resolves a bare name to the first workstation holding it, and `session/queue.py:reporter_sam` does the same — before Phase 2b it split on `/` unconditionally, which would have raised `IndexError` inside `bind()` and handed the ticket to nobody. The callers today are `tests/test_catalog.py` and `session/afteraction.py` (which binds `diagnostic_path()` into the report's `shortest_path`). `tests/test_grading.py` asserts every fault's report comes out sentinel-free, so a new fault that forgets to bind fails there.
