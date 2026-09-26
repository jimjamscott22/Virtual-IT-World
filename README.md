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
- Thirty-one faults across identity, networking, printing, endpoint, and mail,
  including five multi-user incidents that open several tickets from one cause.
- Four faults where escalating is the correct answer and fixing it yourself is
  not, each for a different reason.
- Eleven non-ticketable distractors that add realistic noise without causing the
  reported issue.
- A fourteen-article knowledge base of procedures, deliberately containing no
  answer keys.
- Eight technician tools: AD console, PowerShell, networking, Event Viewer,
  print management, remote session, knowledge base, and mail console.
- Template-driven user personas by default, with an optional LM Studio-backed
  persona for more natural conversations.
- Per-ticket grading, cascade-aware duplicate-fix detection, after-action
  reports, and SQLite history for closed tickets.
- A stable lab environment containing 20 users, 10 workstations, 4 servers,
  5 printers, 5 department shares, 20 mailboxes, and 4 distribution lists.
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
- [Phase 2b catalog plan](docs/superpowers/plans/2026-08-14-phase-2b-catalog.md)
- [Current development handoff](docs/handoff.md)
- [LM Studio verification guide](docs/verifying-lmstudio.md)

## License

Released under the [MIT License](LICENSE).

## Current state

As of **September 26, 2026**, Phase 1 and Phase 2a are complete, and Phase 2b
has taken the catalog to its target breadth. The repository contains 31
registered faults (identity 7, networking 6, printing 6, endpoint 6, mail 6),
11 distractors, 14 knowledge-base articles, 8 technician tools, and 1,632
automated tests.

Every item in Phase 2b's definition of done is met except one inherited from
Phase 2a: the model-backed LM Studio path still requires the manual verification
described above, because no development environment so far has had network access
to a local model. The model-free application and test suite do not depend on it.

The likely next steps, in the order they would pay off, are that verification, a
visual styling pass now that the drill is content-complete, and a career-to-date
progress view across sessions.
