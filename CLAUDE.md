# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-user helpdesk simulator (`vitsc` — Virtual IT Support Center), built as personal practice for desktop-support/helpdesk job applications. The player works tickets against a simulated Windows/AD environment (`Meridian Freight Co.`) using tools that mirror real utilities (AD console, PowerShell, network tools, event viewer, print management, remote session).

Full context lives in:
- Design spec: `docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`
- Phase 1 plan: `docs/superpowers/plans/2026-08-07-phase-1-drill.md`

Currently implemented: Phase 1, Tasks 1–17 — the world model, `SimulatedEnvironment`, the full v1 fault catalog (all ten faults across identity/network/printing/endpoint), the six player-facing tools, the whole persona layer (`PersonaCard`, the `Persona` protocol, `TemplatePersona`, and the LM Studio client with its leak filter), the session layer (`Ticket`, priority/SLA, `SessionQueue`, grading, and the after-action report), SQLite persistence for closed tickets (`session/store.py`: `Store`, `ClosedRecord`, `DomainStat`), and the FastAPI + HTMX web app (`web/app.py`, `web/deps.py:AppSession`, `web/routes/queue.py`: queue list, ticket detail, priority triage; `web/routes/tools.py`: the tool pane and `POST /ticket/{id}/tool`; `web/routes/chat.py`: `POST /ticket/{id}/chat`; `uv run python -m vitsc` to run it). Not yet implemented: close/escalate/after-action/SSE clocks (Task 18) and the end-to-end drill test (Task 19). Next up: Task 18 in `docs/superpowers/plans/2026-08-07-phase-1-drill.md`.

`AppSession` (Task 16) currently builds with `TemplatePersona` only, never `LMStudioPersona` — the model-backed persona takes a fixed `leak_terms` list at construction (Task 11), but a session runs many tickets against different faults in turn. Wiring a fault-aware model persona needs the chat route (Task 17), which has the open ticket's `fault_id` in hand when it calls `reply()`; nothing before that does.

## Commands

```bash
uv sync                                    # install deps (Python 3.12+, uv required)
uv run pytest                              # run the full suite
uv run pytest tests/test_catalog.py        # just the fault conformance harness
uv run pytest -k account_locked            # run tests matching a name/id
uv run pytest "tests/test_catalog.py::test_fault_conforms[ad.account_locked@m.alvarez]"  # one case
```

No model or network access is needed to run the suite.

## Core design principle

**Tools read world state. They never read the fault.** A fault mutates the `World`; tools only ever call `env.read()` / `env.execute()`; a resolution mutates the world back; a fault's own `is_present()` is what decides whether it's fixed. Nothing anywhere branches on "if fault X is active." This is what makes multiple fix paths valid, lets harmless distractors be seeded honestly, and lets a future real-Windows-backed `Environment` slot in without touching tools or faults.

This is enforced mechanically, not just by convention: `tests/test_architecture.py` asserts nothing under `src/vitsc/tools/` imports from `vitsc.faults` or `vitsc.world` (tools must go through `Environment`'s `Query`/`Action`/`Observation` types only).

**Gotcha:** the conformance harness constructs `SimulatedEnvironment(broken)` *after* calling `fault.apply()`, never before. Any per-machine value an `Environment` caches at `__init__` time from mutable `World` state will see the already-faulted value, not the original — this bit `machine.renew_dhcp` (fixed by giving `Machine` a separate `dhcp_reserved_ip` field that faults never touch, distinct from the mutable `ip`). When adding a fault that nulls/clears a field a resolution needs to restore, give the restorable value its own fault-immune field rather than deriving it at Environment construction.

## Architecture

Layered, each layer written once against the layer below's protocol:

```
tools (ad, ps, net, eventlog, printing, remote)
  │  env.read(Query) / env.execute(Action)
Environment protocol  ← the swap point (vitsc/env/base.py)
  │
SimulatedEnvironment  ← v1 backend, in-memory World (vitsc/env/simulated.py)
  │  reads/writes self.world only
World (pydantic models: Organization, Machine, Printer, Share, Network)  ← vitsc/world/models.py
  ▲
fault catalog (vitsc/faults/catalog/*)  ← applies mutations to World via a Placement
```

- **`vitsc.world`** — pydantic entities (`World`, `ADUser`, `Machine`, `Printer`, `Share`, `Network`), the `company.yaml` seed loader (`world/seed.py`, always returns a healthy world — faults are what break it), and invariant checking (`world/invariants.py`: a `Baseline` captured *after* faults are applied, so only *collateral* damage from a bad fix trips it, never the fault itself being present).
- **`vitsc.env`** — the `Environment` protocol (`read`/`execute`/`snapshot`/`restore`) and `SimulatedEnvironment`, which dispatches `Query.kind`/`Action.kind` strings (e.g. `"ad.user"`, `"machine.renew_dhcp"`) to `_read_*`/`_do_*` methods by name via `getattr`. Adding a new query/action kind means adding a matching `_read_<kind>`/`_do_<kind>` method (dots become underscores).
- **`vitsc.faults`** — the `Fault` protocol (`vitsc/faults/base.py`): `placements()` finds valid targets in a `World`, `apply()` mutates it, `is_present()` is the single source of truth for both "is it broken" and "was it fixed", `symptoms()` returns only what a non-technical user could perceive (must contain no leaked jargon — see below), `diagnostic_path()` declares which queries should reveal it, `canonical_resolutions()` is documentation/test fixture only, never the pass/fail gate. New faults self-register via `register()` in `vitsc/faults/registry.py` at import time; `catalog/__init__.py` is what triggers that registration. A fault's `leak_terms` are matched by `persona.client.scrub()` anchored at a word *start*, so a term catches its own inflections (`"lock"` → "locking") without firing on words that merely contain it (`"lease"` does not match "please"); write a term with a trailing space (`"ad "`) to mean the whole word only.
- **`vitsc.tools`** — thin `DispatchTool` subclasses (`vitsc/tools/base.py`) that map command names to read/write `Query`/`Action` kinds and render output in the shape of the real utility (e.g. `Get-ADUser`-style field dumps, `ipconfig`-style block). Every call is logged to a `ToolLog`, which is what `session/grading.py` reads for tool efficiency and whether the technician looked before touching — so `mutating` on a `ToolCall` must stay honest (a rejected call that never reached the environment is not a mutation). `PowerShellConsole` is a *defined* command set, not a parser — anything outside it returns the same `CommandNotFoundException` text the real shell would, deliberately, rather than faking a general shell.
- **`vitsc.persona`** — the `Persona` protocol (`persona/models.py`) plus `PersonaCard` (built from an `ADUser` by `persona/personas.py:card_for`, seeded off `sam` so a person's mood/literacy is stable across sessions) and `TemplatePersona` (`persona/templates.py`), the model-free fallback. A persona's signatures take only a card and a `UserSymptoms` — never a `World` or a `Fault` — which is leak-prevention layer 1, enforced structurally. `TemplatePersona` keyword-matches the technician's question onto a symptom field and deflects everything else; it is what the whole test suite uses, so nothing downstream can depend on a model being loaded. `LMStudioPersona` (`persona/client.py`) talks to an OpenAI-compatible endpoint on `localhost:1234` and adds leak-prevention layers 2 (`persona/prompts.py` forbids guessing a cause) and 3 (`scrub()` against the fault's `leak_terms`, one retry with a nudge, then deflect). Every failure path — model down, slow, absent, or leaking twice — returns `TemplatePersona` output and sets `degraded`; the drill stays fully playable with nothing running locally, and `openai` is imported lazily inside `make_client()` so the suite never touches it.
- **`vitsc.session`** — `session/ticket.py` holds `Ticket` (the whole record of one job: persona, symptoms, chat, tool calls, actions, disposition), `Priority`/`SLA_MINUTES`, and `priority_for(fault, user)`, the system's triage call that the player's `user_priority` is graded against. This is the first layer that knows a fault *id*, but only as an opaque string — grading still asks `is_present()` against the world rather than trusting the ticket. `Ticket.close()` takes an explicit `at`, because SLA timing runs on the simulated `world.clock`, never wall time. `session/queue.py`'s `SessionQueue` is the scheduler: it picks an unheld, not-already-present fault+placement at random, applies it, and opens a ticket whose text came from the persona. Its `baseline` **accumulates** rather than re-snapshotting — `forgive()` excuses only the delta the newly applied fault made, so a technician's collateral damage from an earlier ticket stays visible for the rest of the session instead of being laundered by the next arrival. `session/grading.py` and `session/afteraction.py` close the loop: `grade_ticket()` asks `is_present()` and `check_invariants()` (never "did they use the canonical fix"), and `build_after_action()` names the root cause the player was never told, binds the fault's `diagnostic_path` into a shortest path, and picks a verdict from what the technician *did* — `Disposition` and `fault_cleared` separately, not from `disposition_correct`, which folds both together.

**Two clocks, deliberately.** `Ticket.opened_at` / `closed_at` and `world.clock` are simulated time and drive SLA. `ToolCall.at` and `ChatTurn.at` are wall clock (`datetime.now(UTC)`, timezone-aware) and exist only to order chat against tool calls for `questions_before_first_mutation`. Do not set `ChatTurn.at` from `world.clock` — mixing naive and aware datetimes raises at comparison time, and the two measure different things.

## The conformance harness

`tests/test_catalog.py` is parametrized over every registered fault × every placement it declares (`fault.id@placement.key`). For each case it mechanically proves: absent before `apply()` and present after; the declared `diagnostic_path` actually surfaces something and actually differs from the clean world; every `canonical_resolutions()` path drives `is_present()` false with zero invariant violations; and `symptoms()` contains none of the fault's own `leak_terms` and none of the shared `JARGON` set (dns, dhcp, active directory, lockout, etc — the player is meant to diagnose the mechanism, not read it off the ticket). A new fault gets full coverage from this harness with no new test written — just register it correctly.

When adding a fault, `docs/superpowers/plans/2026-08-07-phase-1-drill.md` has the task-by-task detail for the remaining catalog entries; `catalog/identity.py`'s `AccountLocked` is the reference example for the shape (placements/apply/is_present/symptoms/diagnostic_path/canonical_resolutions).

## Where the code deliberately diverges from the plan

The plan contains full code listings. Tasks 10–14 were implemented from them, but the following places are **intentionally different** and should not be "corrected" back to the plan's text. Each was verified against the real catalog before changing.

| Where | Plan said | Why the code differs |
| --- | --- | --- |
| `persona/client.py:scrub` | substring match on `leak_terms` | `"lease" in "please"` and `"ad " in "bad "` — a plain-English reply got discarded as a leak. Now anchored at a word start, with a trailing space meaning whole-word. |
| `persona/templates.py:_quoted_error` | always wrap as `It says "…"` | `ad.account_locked`'s `error_text` already opens with "It says", so it double-prefixed. Never strips text, so the raw `error_text` stays a substring of what is spoken. |
| `session/ticket.py:WORK_STOPPING` | omitted `ad.offboarded_reactivation` | It is a can't-sign-in fault; priority tracks impact on the person, not who ends up fixing it. |
| `world/invariants.py:capture_baseline` | `allowed_dns` from `network.dns_servers` | Broke capture-after-apply for `net.static_dns_misconfig`, which reported itself as the technician's collateral damage. Now snapshots machine state like every other field. |
| `session/queue.py` baseline | re-snapshot on every arrival | Laundered the technician's mistakes: damage done on ticket 1 vanished when ticket 2 arrived. `forgive()` accumulates instead. |
| `session/afteraction.py` verdict | branched on `disposition_correct` | That flag folds in `fault_cleared`, so closing-without-fixing was reported as a wrong escalation, and the last branch was unreachable. Branches on the chosen `Disposition` now. |
| `session/afteraction.py:touched_before_asking` | `questions == 0` | True whenever nobody mutated anything, so a correct read-only escalation was accused. Requires an actual mutation. |
| `grading.py:questions_before_first_mutation` | count all tech turns if the first call was a read | Counted questions asked *after* the fix as diligence. `ChatTurn` gained an `at` stamp so the two logs interleave. |
| `web/templates/layout.html` | render an org display name from `World` | `Organization` has no `name` field, only `domain: meridian.local` — "Meridian Freight Co." is hardcoded static branding text, not derived from world data. |
| `web/templates/_ticket.html:report_text` | render with default autoescaping | `report_text` embeds literal `"…"` quoted error text; Jinja2's default autoescaping turned those into `&#34;`/`&#39;`, breaking the round trip. Marked `| safe` — it's system/persona-authored, never technician input, so there's no XSS exposure — while chat turns and tool output stay autoescaped. |
| `web/routes/tools.py:run_tool` | build a `ToolCall` for the unknown-tool branch and return it | The plan's version never calls `log.record(call)` on that path, so the failed call never reaches `log.calls` and never renders — `_toolout.html` would silently show nothing instead of the "not recognized" message. Now explicitly recorded, same as every call `DispatchTool.invoke` handles. |

## Placement sentinels

`Fault.diagnostic_path()` and `canonical_resolutions()` receive only a `Placement` (kind + key), never a `World` — faults stay pure data, not closures over world state. When a query/action target needs something only `World` can resolve (a user's assigned hostname, a printer's parent machine, a share's required group), the fault embeds a sentinel string (`PLACEHOLDER`, `PLACEHOLDER_MACHINE`, `PLACEHOLDER_GROUP`, `PLACEHOLDER_PRINTER` in `vitsc/faults/base.py`) and the caller resolves it with `bind()` / `bind_query()` once `World` is in scope. The callers today are `tests/test_catalog.py` and `session/afteraction.py` (which binds `diagnostic_path()` into the report's `shortest_path`). `tests/test_grading.py` asserts every fault's report comes out sentinel-free, so a new fault that forgets to bind fails there.
