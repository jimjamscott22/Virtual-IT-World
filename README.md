# Virtual IT Support Center

[![Pylint](https://github.com/jimjamscott22/Virtual-IT-World/actions/workflows/pylint.yml/badge.svg)](https://github.com/jimjamscott22/Virtual-IT-World/actions/workflows/pylint.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Virtual IT Support Center (`vitsc`) is a single-player helpdesk simulator built
for practical desktop-support and IT support practice. You work a live ticket
queue for the fictional **Meridian Freight Co.**, interview users, investigate
with familiar administrative tools, repair the simulated environment, and
receive an after-action report on each ticket.

The project is hosted at
[github.com/jimjamscott22/Virtual-IT-World](https://github.com/jimjamscott22/Virtual-IT-World).

## Why it works like a real troubleshooting drill

Faults mutate the simulated company environment; the tools only read and
change that environment. They never receive the hidden fault or a predetermined
answer. This means that any safe action sequence which restores the correct
world state can solve a ticket.

The same separation also makes the surrounding noise honest. A session can
contain harmless anomalies, shared incidents can create several related
tickets, and an unnecessary escalation can be returned by simulated tier 2.

## Features

- A FastAPI and HTMX web interface with a live ticket queue and simulated clock.
- Priority selection, SLA tracking, ticket chat, closure, and reviewed tier-2
  escalation.
- Eleven faults across identity, endpoint, networking, file shares, and
  printing, including a multi-user print-server incident.
- Five non-ticketable distractors that add realistic noise without causing the
  reported issue.
- Eight technician tools: AD console, PowerShell, networking, Event Viewer,
  print management, remote session, knowledge base, and mail console.
- Template-driven user personas by default, with an optional LM Studio-backed
  persona for more natural conversations.
- Per-ticket grading, cascade-aware duplicate-fix detection, after-action
  reports, and SQLite history for closed tickets.
- A stable lab environment containing 12 users, 6 workstations, 4 servers,
  3 printers, 4 department shares, and 12 mailboxes.
- Automated conformance checks proving that registered faults are diagnosable,
  repairable, and isolated from the technician tools.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git, if cloning the repository

No external service, model, or network connection is required for the default
experience.

## Setup and run

Clone the repository and install the locked dependencies:

```bash
git clone https://github.com/jimjamscott22/Virtual-IT-World.git
cd Virtual-IT-World
uv sync --locked
```

Start the simulator:

```bash
uv run python -m vitsc
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). Keep the terminal
open while playing and press `Ctrl+C` there to stop the server.

Closed-ticket history is stored locally in `~/.vitsc/sessions.sqlite3`
(`%USERPROFILE%\.vitsc\sessions.sqlite3` on Windows). The application creates
the directory and database on first launch.

## Working a ticket

1. Select an arriving ticket from the queue and set the priority you believe
   it deserves.
2. Ask the reporting user questions to clarify the symptom and its scope.
3. Use the available tools to inspect the simulated environment. Each tool
   lists the commands and arguments it accepts.
4. Apply a repair, verify the resulting state, and close the ticket with the
   appropriate disposition—or send a well-evidenced escalation to tier 2.
5. Review the after-action report for correctness, efficiency, SLA performance,
   repeated mutations, useful KB articles, and any harmless distractors.

The organization is intentionally stable between sessions. Learning Meridian's
hostnames, subnet, groups, shares, printers, and conventions is part of the
exercise.

## Optional: LM Studio personas

The default `template` backend is deterministic and fully playable offline. To
use a local model for more varied user dialogue, start an OpenAI-compatible
server in LM Studio, load a model, and note its model ID.

PowerShell:

```powershell
$env:VITSC_PERSONA = "lmstudio"
$env:VITSC_MODEL = "<model-id>"
uv run python -m vitsc
```

Bash or another POSIX shell:

```bash
VITSC_PERSONA=lmstudio VITSC_MODEL="<model-id>" uv run python -m vitsc
```

`VITSC_BASE_URL` defaults to `http://localhost:1234/v1`. If the model is
unavailable or produces an unsafe answer, the application falls back to the
template persona and remains playable. See
[Verifying the model-backed persona](docs/verifying-lmstudio.md) for the full
manual verification procedure.

## Development

Install dependencies, then run the full suite:

```bash
uv sync --locked
uv run pytest
```

Run lint with the package and test configurations used by the project:

```bash
uv run pylint src
uv run pylint tests --disable=redefined-outer-name,unused-variable,protected-access,use-implicit-booleaness-not-comparison
```

Useful focused commands include:

```bash
uv run pytest tests/test_catalog.py
uv run pytest -k account_locked
```

The GitHub workflow runs Pylint on Python 3.12 and 3.13. No local model is
needed for tests; the suite explicitly isolates itself from `VITSC_*`
environment variables.

## Project structure

| Path | Responsibility |
| --- | --- |
| `src/vitsc/world` | Pydantic models, company seed data, baseline capture, and invariants. |
| `src/vitsc/env` | The environment protocol and in-memory simulated backend. |
| `src/vitsc/faults` | Fault contract, registry, catalog, diagnostics, and canonical repairs. |
| `src/vitsc/distractors` | Truthful anomalies with mechanically checked non-interference guarantees. |
| `src/vitsc/tools` | Technician-facing tools that operate only through the environment protocol. |
| `src/vitsc/persona` | Deterministic and LM Studio-backed simulated users with leak filtering. |
| `src/vitsc/session` | Queue, tickets, SLA, grading, tier 2, after-action reports, and persistence. |
| `src/vitsc/kb` | Local knowledge-base article loading and search. |
| `src/vitsc/web` | FastAPI routes, HTMX templates, and static assets. |
| `tests` | Unit, conformance, architecture, HTTP, persistence, and end-to-end coverage. |

The core dependency direction is:

```text
technician tools -> Environment protocol -> SimulatedEnvironment -> World
                                                               <- faults
```

Tools are prohibited from importing the world or fault catalog directly; the
architecture tests enforce this boundary.

## Documentation

- [Phase 2a depth-mechanics plan](docs/superpowers/plans/2026-08-14-phase-2a-depth-mechanics.md)
- [Current development handoff](docs/handoff.md)
- [LM Studio verification guide](docs/verifying-lmstudio.md)

## License

Released under the [MIT License](LICENSE).

## Current state

As of **September 4, 2026**, Phase 1 is complete and Phase 2a Tasks 1–14 are
merged into `main`. The repository currently contains 11 registered faults, 5
distractors, 8 technician tools, and 564 automated tests. The mail world model,
mail query/action layer, and mail console are implemented.

The next planned checkpoint is Phase 2a Task 15: add the two reference mail
faults (`mail.mailbox_full` and `mail.external_forwarding_rule`). The
model-backed LM Studio path still requires the manual verification described
above; the model-free application and test suite do not depend on it.
