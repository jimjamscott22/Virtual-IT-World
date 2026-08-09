# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-user helpdesk simulator (`vitsc` — Virtual IT Support Center), built as personal practice for desktop-support/helpdesk job applications. The player works tickets against a simulated Windows/AD environment (`Meridian Freight Co.`) using tools that mirror real utilities (AD console, PowerShell, network tools, event viewer, print management, remote session).

Full context lives in:
- Design spec: `docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`
- Phase 1 plan: `docs/superpowers/plans/2026-08-07-phase-1-drill.md`

Currently implemented: Phase 1, Tasks 1–10 — the world model, `SimulatedEnvironment`, the full v1 fault catalog (all ten faults across identity/network/printing/endpoint), the six player-facing tools, and the model-free half of the persona layer (`PersonaCard`, the `Persona` protocol, `TemplatePersona`). Not yet implemented: the LM Studio persona client and leak filter (Task 11), tickets/queue/SLA (12–13), grading and after-action reports (14), SQLite persistence (15), and the FastAPI + HTMX web portal (16–19). Next up: Task 11 in `docs/superpowers/plans/2026-08-07-phase-1-drill.md`.

## Commands

```bash
uv sync                                    # install deps (Python 3.12+, uv required)
uv run pytest                              # run the full suite
uv run pytest tests/test_catalog.py        # just the fault conformance harness
uv run pytest -k account_locked            # run tests matching a name/id
uv run pytest tests/test_catalog.py -k "ad.account_locked@abrooks"  # one fault@placement case
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
- **`vitsc.faults`** — the `Fault` protocol (`vitsc/faults/base.py`): `placements()` finds valid targets in a `World`, `apply()` mutates it, `is_present()` is the single source of truth for both "is it broken" and "was it fixed", `symptoms()` returns only what a non-technical user could perceive (must contain no leaked jargon — see below), `diagnostic_path()` declares which queries should reveal it, `canonical_resolutions()` is documentation/test fixture only, never the pass/fail gate. New faults self-register via `register()` in `vitsc/faults/registry.py` at import time; `catalog/__init__.py` is what triggers that registration.
- **`vitsc.tools`** — thin `DispatchTool` subclasses (`vitsc/tools/base.py`) that map command names to read/write `Query`/`Action` kinds and render output in the shape of the real utility (e.g. `Get-ADUser`-style field dumps, `ipconfig`-style block). Every call is logged to a `ToolLog`, which is what grading will read later (tool efficiency, whether the technician looked before touching). `PowerShellConsole` is a *defined* command set, not a parser — anything outside it returns the same `CommandNotFoundException` text the real shell would, deliberately, rather than faking a general shell.
- **`vitsc.persona`** — the `Persona` protocol (`persona/models.py`) plus `PersonaCard` (built from an `ADUser` by `persona/personas.py:card_for`, seeded off `sam` so a person's mood/literacy is stable across sessions) and `TemplatePersona` (`persona/templates.py`), the model-free fallback. A persona's signatures take only a card and a `UserSymptoms` — never a `World` or a `Fault` — which is leak-prevention layer 1, enforced structurally. `TemplatePersona` keyword-matches the technician's question onto a symptom field and deflects everything else; it is what the whole test suite uses, so nothing downstream can depend on a model being loaded.

## The conformance harness

`tests/test_catalog.py` is parametrized over every registered fault × every placement it declares (`fault.id@placement.key`). For each case it mechanically proves: absent before `apply()` and present after; the declared `diagnostic_path` actually surfaces something and actually differs from the clean world; every `canonical_resolutions()` path drives `is_present()` false with zero invariant violations; and `symptoms()` contains none of the fault's own `leak_terms` and none of the shared `JARGON` set (dns, dhcp, active directory, lockout, etc — the player is meant to diagnose the mechanism, not read it off the ticket). A new fault gets full coverage from this harness with no new test written — just register it correctly.

When adding a fault, `docs/superpowers/plans/2026-08-07-phase-1-drill.md` has the task-by-task detail for the remaining catalog entries; `catalog/identity.py`'s `AccountLocked` is the reference example for the shape (placements/apply/is_present/symptoms/diagnostic_path/canonical_resolutions).

## Placement sentinels

`Fault.diagnostic_path()` and `canonical_resolutions()` receive only a `Placement` (kind + key), never a `World` — faults stay pure data, not closures over world state. When a query/action target needs something only `World` can resolve (a user's assigned hostname, a printer's parent machine, a share's required group), the fault embeds a sentinel string (`PLACEHOLDER`, `PLACEHOLDER_MACHINE`, `PLACEHOLDER_GROUP`, `PLACEHOLDER_PRINTER` in `vitsc/faults/base.py`) and the caller resolves it with `bind()` / `bind_query()` once `World` is in scope. `tests/test_catalog.py` is the current caller; `session/grading.py` and `session/afteraction.py` (Tasks 14+) will be others.
