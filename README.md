# Virtual-IT-World

A single-user helpdesk simulator, built as personal practice for desktop-support / helpdesk job applications.

Faults are generated and placed by the system, never hand-authored per session — otherwise solving them teaches nothing. Tools read world state; they never read the fault, so any action sequence that clears the fault condition counts as a fix.

- Design spec: [`docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`](docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md)
- Phase 1 plan: [`docs/superpowers/plans/2026-08-07-phase-1-drill.md`](docs/superpowers/plans/2026-08-07-phase-1-drill.md)

## Getting started

```bash
uv sync
uv run pytest
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). No model or network access is needed to run the suite.

## What is implemented

The foundation slice — Phase 1, Tasks 1–6 of the plan. Everything below the persona and session layers:

| Package | Contents |
|---|---|
| `vitsc.world` | Pydantic world entities, the `company.yaml` seed loader, baseline capture and invariant checks. |
| `vitsc.env` | The `Environment` protocol (`read` / `execute` / `snapshot` / `restore`) and `SimulatedEnvironment` over the in-memory world. |
| `vitsc.faults` | `Fault` protocol, registry, and the first catalog entry (`ad.account_locked`), plus the conformance harness that proves every registered fault solvable. |
| `vitsc.tools` | The six player-facing tools — AD console, network, remote session, event viewer, print management, and a defined-command-set PowerShell console. |

`Meridian Freight Co.` (`meridian.local`, `10.20.10.0/24`) is the fictional employer: 12 users, 3 servers, 6 workstations, 3 printers, 4 department shares. It is stable across sessions on purpose — learning its conventions is part of the drill.

### The conformance harness

`tests/test_catalog.py` is parametrized over every fault and every placement it declares, and asserts that the fault is absent before `apply()` and present after, that its declared diagnostic path actually changes an observation, that each canonical resolution drives `is_present()` false with no invariant violations, and that its symptoms contain no leak terms and no technical jargon. A new fault gets all of that with no new test written.

`tests/test_architecture.py` mechanically enforces that nothing under `vitsc.tools` imports from `vitsc.faults` or `vitsc.world`.

## Not yet implemented

Plan Tasks 7–19: the remaining nine faults, the persona layer (LM Studio client with a template fallback), tickets, queue and SLA, grading and the after-action report, SQLite persistence, and the FastAPI + HTMX portal.
