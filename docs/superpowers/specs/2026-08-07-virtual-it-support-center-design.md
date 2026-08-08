# Virtual IT Support Center — Design Spec

**Date:** 2026-08-07
**Status:** Approved for implementation planning
**Supersedes:** `Virtual-IT-Support-Center.md` (original pitch document)

---

## 1. Purpose

A single-user helpdesk simulator, built as personal practice for desktop-support / helpdesk job applications.

The user is both the author and the only player. That creates the central design constraint: **faults must be generated and placed by the system, never hand-authored per session**, or solving them teaches nothing. Every architectural decision below serves that constraint.

### What it must teach

Helpdesk work splits into two halves that need different tools:

- **Technical execution** — unlocking accounts, fixing DNS, reinstalling drivers. Best learned against real systems.
- **Process and communication** — triaging a vague report, asking the right diagnostic questions before touching anything, setting priority, deciding when to escalate, documenting the resolution, working a queue under SLA pressure.

The second half is what interviews probe hardest and what a homelab cannot teach at all. v1 targets it directly. The first half is served initially by a simulated environment and later by real Windows guests, without a rewrite (§4).

### Success criteria

1. The user can sit down and work a queue of unfamiliar tickets, having not placed the faults.
2. Every ticket is provably solvable with the tools available (§9).
3. After each ticket, the user learns something specific about what they did inefficiently (§8).
4. First playable version is reachable in days, not weeks.

---

## 2. Non-goals

Explicitly cut from the original pitch, and not to be reintroduced without a new design round:

| Cut | Reason |
|---|---|
| Multiplayer (co-op, competitive, roleplay) | Single user. Retrofitting is a rewrite; designing for it now is waste. |
| 3D / first-person environments | The interface is simulated desktop windows. 3D is set dressing at 10x the cost. |
| Monetization, DLC, cosmetics, Early Access | Personal use only. |
| Mod support | The user is the only author. Faults are self-contained declarative units either way (§6), so opening them up later stays cheap. |
| Named real certifications (CompTIA A+, CCNA) | Trademarks. Also irrelevant — the goal is the real certs, not in-game ones. |
| Embedded Microsoft Docs / man pages | Not redistributable. Any knowledge base is original content. |
| Cloud console (AWS/Azure/GCP) | Wrong role. Also trade-dress risk if closely replicated. |
| Sandbox mode | The simulated environment is already consequence-free; a separate mode adds nothing. |
| Career progression, avatars, workspace upgrades | Motivational scaffolding that costs build time and teaches nothing. Performance history (§13, P4) covers the useful part. |

---

## 3. Core design principle

**Tools read world state. They never read the fault.**

A fault mutates the world. Tools query the world. A resolution mutates it back. The validator asks the world whether the fault condition still holds.

Nothing anywhere contains logic of the form "if fault X is active, tool Y prints Z."

This single rule buys, at no extra cost:

- **Multiple valid fix paths.** Any action sequence that clears the condition counts, including ones not anticipated.
- **Honest distractors.** Unrelated harmless anomalies can be seeded into the world and tools will report them truthfully, so the first oddity found is not automatically the cause.
- **Backend portability.** A driver that talks to real Windows guests satisfies the same interface, and existing faults and validators work unchanged (§4).
- **Cheap correctness testing.** The world is pure data with no I/O, so every fault can be machine-verified as solvable (§9).

---

## 4. Architecture

```
                 ┌──────────────────────────┐
   browser ◄────►│  web  (FastAPI + HTMX)   │
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐      ┌──────────────┐
                 │        session           │◄────►│   persona    │──► LM Studio
                 │  queue · SLA · grading   │      │ (user agent) │    :1234/v1
                 └────────────┬─────────────┘      └──────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │          tools           │
                 │ AD · PS · net · events · │
                 │ remote · printing        │
                 └────────────┬─────────────┘
                              │  read() / execute()
                 ┌────────────▼─────────────┐
                 │   Environment (Protocol)  │   ◄── the swap point
                 ├───────────────┬───────────┤
                 │ Simulated     │  WinRM    │
                 │  (v1)         │  (P3)     │
                 └───────┬───────┴─────┬─────┘
                         │             │
                 ┌───────▼──────┐  ┌───▼────────────┐
                 │ world model  │  │ libvirt/KVM    │
                 │ (pure data)  │  │ Windows guests │
                 └───────▲──────┘  └────────────────┘
                         │
                 ┌───────┴──────┐
                 │ fault catalog│
                 └──────────────┘
```

The `Environment` protocol is the spine. Everything above it is written once and never changes when the backend does.

```python
class Environment(Protocol):
    def read(self, query: Query) -> Observation: ...
    def execute(self, action: Action) -> ActionResult: ...
    def snapshot(self) -> SnapshotId: ...
    def restore(self, snapshot: SnapshotId) -> None: ...
```

- `SimulatedEnvironment` — operates on the in-memory world model. `snapshot`/`restore` are deep copies.
- `WinRMEnvironment` (Phase 3) — translates queries and actions into PowerShell over WinRM against real guests. `snapshot`/`restore` are libvirt domain snapshots.

Faults declare `supported_backends`, so a fault about explaining a fix to a frustrated user stays simulated forever while an AD lockout graduates to a real domain controller.

---

## 5. World model

Pure data, no I/O, Pydantic models. Seeded from a single `company.yaml`.

The fictional company is **stable across sessions**. The user learns its OUs, subnets, print servers, and naming conventions the way they would learn a real employer's — that familiarity is itself part of the drill, and it makes "this machine is on the wrong subnet" a discoverable fact rather than an arbitrary one.

```python
class World(BaseModel):
    org:      Organization      # users, groups, OUs, computers
    machines: dict[str, Machine]
    network:  Network           # subnets, DNS servers, DHCP scopes, gateways
    printers: dict[str, Printer]
    shares:   dict[str, Share]
    clock:    datetime

class ADUser(BaseModel):
    sam: str; display_name: str; upn: str
    enabled: bool; locked_out: bool
    bad_pwd_count: int; pwd_last_set: datetime; pwd_expires: datetime
    groups: list[str]; ou: str; home_drive: str | None

class Machine(BaseModel):
    hostname: str; assigned_to: str | None
    ip: str | None; dns_servers: list[str]; dhcp_enabled: bool
    services: dict[str, ServiceState]
    disk_free_gb: float; disk_total_gb: float; smart_status: SmartStatus
    mapped_drives: dict[str, str]; installed_printers: list[str]
    event_log: list[EventEntry]
    profile_state: ProfileState
```

Machine state is deliberately shallow. It models what helpdesk tools can *see*, not a real OS. Depth arrives with the WinRM backend, where the real OS provides it.

### Invariants

`world.check_invariants()` returns violations — things that must be true of a healthy org regardless of any active fault:

- No user account disabled or deleted that was enabled at session start
- No service stopped that was running at session start, unless a fault stopped it
- No machine's DNS pointed outside the org's configured resolvers
- No group membership removed that was present at session start

These exist so that **wrong fixes have teeth**. Clearing a symptom by disabling a service or stripping a group membership will pass the fault check and fail the invariant check, and grading reports it as collateral damage.

---

## 6. Fault catalog

Each fault is a declarative unit. `is_present()` is the single source of truth for both "is this broken" and "did the user fix it."

```python
class Fault(Protocol):
    id: str                              # "ad.account_locked"
    domain: Domain                       # identity | network | printing | mail | endpoint
    difficulty: int                      # 1..5
    canonical_title: str                 # shown only in the after-action report
    supported_backends: frozenset[Backend]
    leak_terms: list[str]                # phrases the persona must never say (§7)
    escalation_is_correct: bool          # some tickets are correctly escalated, not fixed

    def placements(self, world: World) -> list[Placement]: ...
    def apply(self, world: World, at: Placement, rng: Random) -> None: ...
    def is_present(self, world: World, at: Placement) -> bool: ...
    def symptoms(self, world: World, at: Placement) -> UserSymptoms: ...
    def canonical_resolutions(self) -> list[ResolutionPath]: ...
```

- `placements()` returns every world entity the fault could legally attach to. Empty means it cannot be placed in the current world; the scheduler moves on.
- `symptoms()` returns only what a non-technical user can perceive — an error message, a behaviour, a time it started. It is the sole input to the persona layer.
- `canonical_resolutions()` is **documentation and test fixture, not the pass/fail gate.** The gate is `is_present()` going false with invariants intact. Any path there counts.

### Resolution validation

A ticket is correctly resolved when:

1. `fault.is_present(world, placement)` is `False`, **and**
2. `world.check_invariants()` is empty, **and**
3. the user's disposition matches `escalation_is_correct` — escalating a fixable ticket and fixing an escalate-only one are both wrong.

### v1 catalog (10 faults)

| ID | Domain | Notes |
|---|---|---|
| `ad.account_locked` | identity | Bad password attempts; classic P1. |
| `ad.password_expired` | identity | Symptom looks like a lockout. Trains differential diagnosis. |
| `ad.offboarded_reactivation` | identity | **Escalate-correct** — needs HR/manager authorisation, not a technician's click. |
| `share.group_membership_removed` | identity | Presents as "the S: drive vanished." Cause is in AD, not the drive. |
| `print.spooler_stopped` | printing | Service state on the endpoint. |
| `print.wrong_driver` | printing | Prints garbage rather than failing outright. |
| `net.static_dns_misconfig` | network | "Internet is down" but only for name resolution. |
| `net.no_dhcp_lease` | network | APIPA address. |
| `endpoint.disk_full` | endpoint | Presents as Outlook failing or profile not loading. |
| `endpoint.failing_disk` | endpoint | **Escalate-correct** — SMART failure, hardware replacement is out of scope. |

Two escalate-correct faults are deliberate. Without them the drill teaches "always try to fix it," which is the wrong instinct and a common interview trap. Pairs like `ad.account_locked` / `ad.password_expired` and `net.static_dns_misconfig` / `net.no_dhcp_lease` exist to punish pattern-matching on the user's opening line.

---

## 7. Persona layer

An LM Studio client against the OpenAI-compatible endpoint at `http://localhost:1234/v1`, driven through the `openai` SDK with a custom `base_url`. That choice makes swapping to Ollama or a hosted API a base-URL-and-model-name change with no other code touched.

The RTX 5070's 12 GB VRAM comfortably runs an 8–14B instruct model, which is ample — the model's job is small and heavily constrained.

### Hard constraint

**The model never owns ground truth.** It receives a persona card (name, role, technical literacy 1–3, current mood, what they were doing when it broke) plus `UserSymptoms`. It never receives the fault ID, the root cause, or world state.

Two operations:

- `initial_report(persona, symptoms) -> str` — the vague ticket text.
- `reply(persona, symptoms, history, question) -> str` — an in-character answer to a diagnostic question.

A weak model therefore degrades flavour, never correctness.

### Leak prevention

Three layers, because an 8B model given "your account is locked" will say exactly that:

1. **Input filtering** — symptoms only, never causes. The model literally cannot state what it was not told.
2. **Literacy cap** — the system prompt binds vocabulary to the persona's literacy level. A literacy-1 receptionist does not say "DNS" or "group policy."
3. **Output filter** — replies are scanned for the fault's `leak_terms`. On a hit, retry once with a stricter reminder; on a second hit, substitute a canned in-character deflection ("I'm not sure, sorry — I don't really know the computer stuff").

### Fallback

If LM Studio is unreachable or returns an error, `TemplatePersona` produces symptom-derived text from a phrase bank. The application and the entire test suite run with no model loaded. This is a requirement, not a nicety — tests must never depend on a model being warm.

---

## 8. Session, grading, and after-action

**Queue.** 3–4 concurrent tickets, each with a priority (P1–P4) and an SLA clock. New tickets arrive on a timer while others are open, so triage is forced rather than theoretical. Priority is assigned by the fault plus the persona's role, and the user's *own* triage decision is recorded and graded separately from the system's.

**Ticket lifecycle:** `open → in_progress → resolved | escalated → graded`.

**Grading dimensions**, recorded per ticket:

| Dimension | Measure |
|---|---|
| Correctness | `is_present` false, invariants clean, disposition matches |
| Collateral damage | Invariant violations introduced |
| Time | Wall time vs SLA |
| Tool efficiency | Tool calls made vs shortest known diagnostic path |
| Information gathering | Diagnostic questions asked before the first *mutating* action |
| Triage accuracy | User-assigned priority vs system-assigned |

**After-action report.** The actual learning mechanism, and the piece entirely absent from the original pitch. On close, it shows: the real root cause; the shortest diagnostic path and which single tool call would have revealed it; which of the user's calls returned nothing useful; whether they touched anything before asking the user a question; and any collateral damage caused.

A score without this is just a number. The report is why the exercise transfers.

---

## 9. Testing strategy

The failure mode of this design is an unsolvable or unfair ticket. Prevention is a parametrized test over the whole catalog, made cheap by the world being pure data:

For every fault, and every placement it declares:

1. Placement succeeds against the seeded world.
2. `is_present()` is `False` before `apply()` and `True` after.
3. At least one tool observation differs pre- and post-`apply` — i.e. the fault is *discoverable*.
4. Each `canonical_resolution` drives `is_present()` to `False`.
5. `check_invariants()` is clean after each canonical resolution.
6. `symptoms()` contains no `leak_terms` and no jargon outside a shared end-user vocabulary list — symptoms are what a non-technical person can perceive, independent of which persona ends up reporting them.

Beyond that: unit tests on world mutation and invariants; persona layer tested against a stub client; one end-to-end test driving a full ticket from generation to graded close through the FastAPI test client.

`pytest`, run via `uv run pytest`.

---

## 10. Error handling

| Condition | Behaviour |
|---|---|
| LM Studio unreachable or erroring | Fall back to `TemplatePersona`; show a persistent banner. Never block the queue. |
| Model leaks a `leak_term` | Retry once with stricter prompt, then canned deflection (§7). |
| No placement available for a chosen fault | Scheduler picks another; log it. Repeated failures surface as a catalog warning. |
| User submits an unknown or malformed action | Tool returns a realistic error, exactly as the real tool would. Not a crash, not a hint. |
| Session interrupted | State persists to SQLite; the queue and its clocks resume. |

---

## 11. Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.12+ |
| Env & packaging | `uv` — `pyproject.toml`, `uv sync`, `uv run`. Commit `uv.lock`, gitignore `.venv/` |
| Web | FastAPI, Jinja2 templates, HTMX for partial updates, SSE for SLA clocks and ticket arrivals |
| Models | Pydantic v2 |
| Persistence | SQLite (session history, grading records) |
| LLM client | `openai` SDK pointed at `http://localhost:1234/v1` |
| Tests | pytest |

No JS build step, no frontend toolchain. HTMX plus server-rendered partials covers the whole interface.

---

## 12. Repository layout

```
virtual-it-support-center/
├── pyproject.toml
├── uv.lock
├── README.md
├── docs/superpowers/specs/
│   └── 2026-08-07-virtual-it-support-center-design.md
├── src/vitsc/
│   ├── world/       models.py  seed.py  invariants.py
│   ├── faults/      base.py  registry.py  catalog/*.py
│   ├── env/         base.py  simulated.py          # winrm.py in P3
│   ├── tools/       ad.py  powershell.py  network.py
│   │                eventlog.py  remote.py  printing.py  registry.py
│   ├── persona/     client.py  prompts.py  personas.py  templates.py
│   ├── session/     queue.py  ticket.py  sla.py  grading.py  afteraction.py
│   ├── web/         app.py  routes/  templates/  static/
│   └── data/        company.yaml
└── tests/
    ├── test_catalog.py        # parametrized over every fault (§9)
    ├── test_world.py
    ├── test_persona.py
    └── test_end_to_end.py
```

### Tool surface

Each tool is a thin wrapper over `env.read()` / `env.execute()` that renders output in the format of the real utility. Every call is logged; the log feeds grading.

- **AD console** — `get_user`, `unlock`, `reset_password`, `enable`/`disable`, `get_group_members`, `add`/`remove_member`
- **PowerShell console** — a *defined command set*, not a free shell: `Get-Service`, `Restart-Service`, `Get-Printer`, `Get-PSDrive`, `Test-NetConnection`, `Get-EventLog`, `gpupdate`. A free-form parser cannot be honestly simulated in v1; unrecognised commands return a realistic `CommandNotFoundException`.
- **Network** — `ping`, `nslookup`, `ipconfig /all`, `ipconfig /renew`
- **Event Viewer** — filtered log reads per machine
- **Remote session** — read-only machine state: disk, services, mapped drives, installed printers, profile state
- **Print management** — `get_printer`, `restart_spooler`, `reinstall_driver`

---

## 13. Phase map

**Phase 1 — v1, the drill (target: days)**
One company (~12 users, ~8 machines). The 10 faults in §6. Simulated backend. LM Studio persona with template fallback. Queue of 3–4 with SLA. Grading and after-action. Full catalog test suite.

*Done when:* the user works a queue of tickets they did not place, and the after-action report tells them something they did not already know.

**Phase 2 — depth**
Catalog to 30+ faults across all five domains. Honest distractors seeded into the world. Cascading faults (one root cause producing several tickets). Escalation path with a simulated tier-2. Original-content knowledge base.

**Phase 3 — real systems**
`WinRMEnvironment` plus a libvirt/KVM lab: Windows Server as domain controller, two Windows 11 clients, from Microsoft evaluation ISOs (Server 180-day, Windows 11 Enterprise 90-day). Snapshot/restore between tickets. Faults tagged `winrm` graduate over; the rest stay simulated. Requires installing `libvirt` and `virt-manager` — `virsh` is not currently present, though KVM, QEMU, and VT-x all are.

*Hardware is already sufficient:* 30 GB RAM (21 free), 24 cores, VT-x, `/dev/kvm` present, ~496 GB free. A DC plus two clients is roughly 12 GB.

**Phase 4 — feedback loop**
Performance history across sessions. Per-domain weak-spot statistics. Ticket replay. Targeted drill mode that biases fault selection toward the user's weakest domain.

---

## 14. Decisions carried from review

Recorded so they are not silently relitigated:

- **Simulated-first with a swappable driver**, not real VMs immediately and not simulated forever. Reaching the drill fast matters more than initial fidelity, and the driver boundary means fidelity costs no rewrite.
- **Local model over hosted API.** No key, no per-ticket cost, fully offline. Accepted trade: weaker roleplay, mitigated by the model owning no ground truth.
- **Browser UI over TUI.** Roughly a week more work, but the portal shape matches the ServiceNow/Jira Service Desk muscle memory the target role uses, and it doubles as a portfolio artifact.
- **Escalation as a first-class correct outcome.** Prevents the drill from teaching "always fix it."
- **The world validates, not the button.** Resolution is judged by world state, which is what permits multiple fix paths and the later backend swap.

---

## 15. Startup tasks before implementation

1. `uv init` the repository; add FastAPI, Jinja2, Pydantic, `openai`, pytest.
2. Load an 8–14B instruct model in LM Studio and confirm `http://localhost:1234/v1/models` responds. (This could not be verified during design — the check was not run.)
3. Author `company.yaml` — the fictional org, once, by hand. This is the only content the user authors, and knowing it is intended.
