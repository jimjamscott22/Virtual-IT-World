# Virtual IT Support Center — Phase 1 (v1 Drill) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single-user helpdesk simulator that generates unfamiliar, provably-solvable tickets against a simulated Windows/AD environment, roleplays the reporting user with a local LLM, and grades each ticket with an after-action report.

**Architecture:** A pure-data world model is mutated by declarative faults. Tools read that world exclusively through an `Environment` protocol — never through the fault — so resolutions are validated by world state rather than by which button was pressed, and a real-WinRM backend can be dropped in later unchanged. A FastAPI + HTMX server renders the helpdesk portal; a local LM Studio model writes and roleplays the user but is given only observable symptoms and never owns ground truth.

**Tech Stack:** Python 3.12+, uv, FastAPI, Jinja2, HTMX, SSE, Pydantic v2, SQLite, pytest, `openai` SDK against LM Studio.

**Spec:** `docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- Python 3.12+.
- `uv` only, never `pip`. `uv add` / `uv add --dev` for dependencies, `uv run` for commands. Commit `uv.lock`; `.venv/` stays gitignored.
- All commit messages end with the trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Commit commands below omit it for brevity — add it.
- **Tools read world state only via `Environment`.** No module under `src/vitsc/tools/` may import from `src/vitsc/faults/`. This is the spec's core principle (§3) and a review-rejectable violation.
- **The persona layer never receives a fault id, a root cause, or a `World`.** Its only inputs are a `PersonaCard` and a `UserSymptoms`.
- **The full test suite must pass with no model loaded in LM Studio.** Any test touching persona behaviour uses `TemplatePersona` or a stub.
- No JS build step. Server-rendered Jinja2 partials plus HTMX attributes only.
- Package root is `src/vitsc/`; tests mirror it under `tests/`.
- Run tests with `uv run pytest`.

## Spec Addendum

The spec's `Fault` protocol (§6) omits one member that §8 (tool efficiency, shortest diagnostic path) and §9 (discoverability test) both require. This plan adds it:

```python
def diagnostic_path(self, at: Placement) -> list[Query]:
    """Minimal ordered queries that reveal this fault. Used by the
    discoverability test, the efficiency grade, and the after-action report."""
```

## Deviation from the spec

One spec requirement is deliberately deferred, flagged here rather than dropped silently.

**Spec §10, "Session interrupted → state persists to SQLite; the queue and its clocks resume."** This plan persists only *closed* tickets (Task 15). Resuming a half-worked queue means serialising the entire mutated `World` — every fault applied so far, the baseline, per-ticket tool logs and chat history — and reloading it into a live `SimulatedEnvironment`. That is a meaningful chunk of work serving a session you can simply restart, in a drill designed to be picked up in twenty-minute bursts.

The cost of deferring is low: `World` and `Ticket` are already Pydantic models, so mid-session resume is `model_dump_json` into one more table plus a load path. Nothing in this plan blocks it. If you want it in v1 instead, say so and it becomes Task 16 — roughly one extra task.

## File Structure

| Path | Responsibility |
|---|---|
| `src/vitsc/world/models.py` | Pydantic world entities. Pure data, no logic beyond validation. |
| `src/vitsc/world/seed.py` | `company.yaml` → `World`. |
| `src/vitsc/world/invariants.py` | Baseline capture and `check_invariants`. |
| `src/vitsc/data/company.yaml` | The fictional org. Hand-authored once. |
| `src/vitsc/env/base.py` | `Query`, `Observation`, `Action`, `ActionResult`, `Environment` protocol. |
| `src/vitsc/env/simulated.py` | `SimulatedEnvironment` over the world model. |
| `src/vitsc/faults/base.py` | `Domain`, `Backend`, `Placement`, `UserSymptoms`, `ResolutionPath`, `Fault` protocol. |
| `src/vitsc/faults/registry.py` | Catalog registration and lookup. |
| `src/vitsc/faults/catalog/*.py` | One module per domain; the 10 v1 faults. |
| `src/vitsc/tools/base.py` | `ToolCall`, `Tool` protocol, `ToolLog`. |
| `src/vitsc/tools/{ad,network,remote,eventlog,printing,powershell}.py` | Player-facing tools. |
| `src/vitsc/tools/registry.py` | Tool lookup by name. |
| `src/vitsc/persona/models.py` | `PersonaCard`, `ChatTurn`, `Persona` protocol. |
| `src/vitsc/persona/templates.py` | `TemplatePersona` — the no-model fallback. |
| `src/vitsc/persona/prompts.py` | System prompt construction and literacy caps. |
| `src/vitsc/persona/client.py` | `LMStudioPersona` plus the leak filter. |
| `src/vitsc/session/ticket.py` | `Ticket`, `TicketState`, `Disposition`, `Priority`. |
| `src/vitsc/session/queue.py` | Fault selection, placement, ticket arrival scheduling. |
| `src/vitsc/session/grading.py` | `Grade` and the grading rules. |
| `src/vitsc/session/afteraction.py` | `AfterAction` report construction. |
| `src/vitsc/session/store.py` | SQLite persistence for sessions and grades. |
| `src/vitsc/web/app.py` | FastAPI app factory, session wiring. |
| `src/vitsc/web/routes/*.py` | Queue, ticket, tools, chat, close, SSE endpoints. |
| `src/vitsc/web/templates/` | Jinja2 pages and HTMX partials. |

---

### Task 1: Project scaffold, world models, and seed

**Files:**
- Create: `pyproject.toml`, `src/vitsc/__init__.py`, `src/vitsc/world/__init__.py`
- Create: `src/vitsc/world/models.py`
- Create: `src/vitsc/data/company.yaml`
- Create: `src/vitsc/world/seed.py`
- Test: `tests/test_world_seed.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `World`, `Organization`, `ADUser`, `ADGroup`, `Machine`, `Printer`, `Share`, `Network`, `ServiceState`, `SmartStatus`, `ProfileState`, `EventEntry`; `load_world(path: Path | None = None) -> World`.

- [ ] **Step 1: Scaffold the project**

```bash
uv init --package --name vitsc .
uv add pydantic pyyaml
uv add --dev pytest
```

Set `requires-python = ">=3.12"` in `pyproject.toml`. Confirm `src/vitsc/` exists.

- [ ] **Step 2: Write the failing test**

`tests/test_world_seed.py`:

```python
from vitsc.world.seed import load_world


def test_seed_loads_expected_org():
    world = load_world()
    assert "m.alvarez" in world.org.users
    assert world.org.users["m.alvarez"].enabled is True
    assert world.org.users["m.alvarez"].locked_out is False


def test_seed_machines_reference_real_users():
    world = load_world()
    for machine in world.machines.values():
        if machine.assigned_to is not None:
            assert machine.assigned_to in world.org.users


def test_seed_group_members_exist():
    world = load_world()
    for group in world.org.groups.values():
        for sam in group.members:
            assert sam in world.org.users


def test_seed_is_healthy_at_rest():
    world = load_world()
    assert all(u.locked_out is False for u in world.org.users.values())
    assert all(m.disk_free_gb > 5 for m in world.machines.values())
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_world_seed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.world.seed'`

- [ ] **Step 4: Write the models**

`src/vitsc/world/models.py`:

```python
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ServiceState(str, Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"


class SmartStatus(str, Enum):
    OK = "OK"
    PRED_FAIL = "Pred Fail"


class ProfileState(str, Enum):
    NORMAL = "Normal"
    TEMPORARY = "Temporary"
    CORRUPT = "Corrupt"


class EventEntry(BaseModel):
    log: str
    source: str
    event_id: int
    level: str
    at: datetime
    message: str


class ADUser(BaseModel):
    sam: str
    display_name: str
    upn: str
    department: str
    title: str
    enabled: bool = True
    locked_out: bool = False
    bad_pwd_count: int = 0
    pwd_last_set: datetime
    pwd_expires: datetime
    ou: str
    home_drive: str | None = None


class ADGroup(BaseModel):
    name: str
    members: list[str] = Field(default_factory=list)


class Organization(BaseModel):
    domain: str
    users: dict[str, ADUser]
    groups: dict[str, ADGroup]


class Machine(BaseModel):
    hostname: str
    assigned_to: str | None = None
    ip: str | None = None
    subnet_mask: str = "255.255.255.0"
    gateway: str | None = None
    dns_servers: list[str] = Field(default_factory=list)
    dhcp_enabled: bool = True
    services: dict[str, ServiceState] = Field(default_factory=dict)
    disk_free_gb: float = 120.0
    disk_total_gb: float = 256.0
    smart_status: SmartStatus = SmartStatus.OK
    mapped_drives: dict[str, str] = Field(default_factory=dict)
    installed_printers: list[str] = Field(default_factory=list)
    printer_drivers: dict[str, str] = Field(default_factory=dict)
    profile_state: ProfileState = ProfileState.NORMAL
    event_log: list[EventEntry] = Field(default_factory=list)


class Printer(BaseModel):
    name: str
    host: str
    model: str
    correct_driver: str
    online: bool = True


class Share(BaseModel):
    unc: str
    host: str
    required_group: str
    drive_letter: str


class Network(BaseModel):
    subnet: str
    gateway: str
    dns_servers: list[str]
    dhcp_server: str
    external_probe: str = "8.8.8.8"


class World(BaseModel):
    org: Organization
    machines: dict[str, Machine]
    printers: dict[str, Printer]
    shares: dict[str, Share]
    network: Network
    clock: datetime

    def machine_for(self, sam: str) -> Machine | None:
        for machine in self.machines.values():
            if machine.assigned_to == sam:
                return machine
        return None

    def groups_of(self, sam: str) -> list[str]:
        return [g.name for g in self.org.groups.values() if sam in g.members]
```

- [ ] **Step 5: Write `company.yaml`**

`src/vitsc/data/company.yaml`. Meridian Freight Co., domain `meridian.local`, subnet `10.20.10.0/24`, DNS/DC at `10.20.10.5`.

```yaml
domain: meridian.local
clock: 2026-08-07T09:00:00

network:
  subnet: 10.20.10.0/24
  gateway: 10.20.10.1
  dns_servers: ["10.20.10.5"]
  dhcp_server: 10.20.10.5

users:
  - {sam: m.alvarez,   display_name: Maria Alvarez,   department: Accounting, title: Accounting Clerk,     ou: "OU=Accounting,DC=meridian,DC=local"}
  - {sam: d.okafor,    display_name: Daniel Okafor,   department: Accounting, title: Accounts Payable,     ou: "OU=Accounting,DC=meridian,DC=local"}
  - {sam: e.novak,     display_name: Emil Novak,      department: Accounting, title: Controller,           ou: "OU=Accounting,DC=meridian,DC=local"}
  - {sam: s.whitfield, display_name: Sandra Whitfield, department: Operations, title: Operations Manager,  ou: "OU=Operations,DC=meridian,DC=local"}
  - {sam: t.nakamura,  display_name: Tomo Nakamura,   department: Operations, title: Dispatcher,           ou: "OU=Operations,DC=meridian,DC=local"}
  - {sam: r.gallagher, display_name: Ryan Gallagher,  department: Operations, title: Dispatcher,           ou: "OU=Operations,DC=meridian,DC=local"}
  - {sam: p.mensah,    display_name: Priya Mensah,    department: Sales,      title: Sales Representative, ou: "OU=Sales,DC=meridian,DC=local"}
  - {sam: c.donnelly,  display_name: Colin Donnelly,  department: Sales,      title: Sales Representative, ou: "OU=Sales,DC=meridian,DC=local"}
  - {sam: b.ferreira,  display_name: Bruno Ferreira,  department: Warehouse,  title: Warehouse Lead,       ou: "OU=Warehouse,DC=meridian,DC=local"}
  - {sam: k.lindqvist, display_name: Kari Lindqvist,  department: Warehouse,  title: Warehouse Associate,  ou: "OU=Warehouse,DC=meridian,DC=local"}
  - {sam: j.abiodun,   display_name: Joy Abiodun,     department: HR,         title: HR Coordinator,       ou: "OU=HR,DC=meridian,DC=local"}
  - {sam: h.reyes,     display_name: Hector Reyes,    department: Operations, title: Night Dispatcher,     ou: "OU=Operations,DC=meridian,DC=local"}

groups:
  ACC-Share-RW:   [m.alvarez, d.okafor, e.novak]
  OPS-Share-RW:   [s.whitfield, t.nakamura, r.gallagher, h.reyes]
  SALES-Share-RW: [p.mensah, c.donnelly]
  WH-Share-RW:    [b.ferreira, k.lindqvist]
  HR-Share-RW:    [j.abiodun]

servers:
  - {hostname: MER-DC-01,  ip: 10.20.10.5,  role: dc}
  - {hostname: MER-FS-01,  ip: 10.20.10.6,  role: fileserver}
  - {hostname: MER-PRT-01, ip: 10.20.10.7,  role: printserver}

workstations:
  - {hostname: MER-WS-001, assigned_to: m.alvarez,   ip: 10.20.10.41, printers: [PRT-ACC-01]}
  - {hostname: MER-WS-002, assigned_to: d.okafor,    ip: 10.20.10.42, printers: [PRT-ACC-01]}
  - {hostname: MER-WS-003, assigned_to: s.whitfield, ip: 10.20.10.43, printers: [PRT-OPS-01]}
  - {hostname: MER-WS-004, assigned_to: t.nakamura,  ip: 10.20.10.44, printers: [PRT-OPS-01]}
  - {hostname: MER-WS-005, assigned_to: p.mensah,    ip: 10.20.10.45, printers: [PRT-OPS-01]}
  - {hostname: MER-WS-006, assigned_to: b.ferreira,  ip: 10.20.10.46, printers: [PRT-WH-01]}

printers:
  - {name: PRT-ACC-01, host: MER-PRT-01, model: "HP LaserJet M507", correct_driver: "HP LaserJet M507 PCL-6"}
  - {name: PRT-OPS-01, host: MER-PRT-01, model: "HP LaserJet M507", correct_driver: "HP LaserJet M507 PCL-6"}
  - {name: PRT-WH-01,  host: MER-PRT-01, model: "Zebra ZT411",      correct_driver: "Zebra ZT411 ZPL"}

shares:
  - {unc: "\\\\MER-FS-01\\Accounting", host: MER-FS-01, required_group: ACC-Share-RW,   drive_letter: "S:"}
  - {unc: "\\\\MER-FS-01\\Operations", host: MER-FS-01, required_group: OPS-Share-RW,   drive_letter: "S:"}
  - {unc: "\\\\MER-FS-01\\Sales",      host: MER-FS-01, required_group: SALES-Share-RW, drive_letter: "S:"}
  - {unc: "\\\\MER-FS-01\\Warehouse",  host: MER-FS-01, required_group: WH-Share-RW,    drive_letter: "S:"}
```

- [ ] **Step 6: Write the seed loader**

`src/vitsc/world/seed.py`:

```python
from datetime import timedelta
from importlib.resources import files
from pathlib import Path

import yaml

from vitsc.world.models import (
    ADGroup, ADUser, Machine, Network, Organization, Printer,
    ServiceState, Share, World,
)

WORKSTATION_SERVICES = {
    "Spooler": ServiceState.RUNNING,
    "Dhcp": ServiceState.RUNNING,
    "Dnscache": ServiceState.RUNNING,
    "WSearch": ServiceState.RUNNING,
}


def load_world(path: Path | None = None) -> World:
    raw = yaml.safe_load(
        path.read_text() if path else files("vitsc.data").joinpath("company.yaml").read_text()
    )
    clock = raw["clock"]
    net = raw["network"]

    users: dict[str, ADUser] = {}
    for u in raw["users"]:
        users[u["sam"]] = ADUser(
            sam=u["sam"],
            display_name=u["display_name"],
            upn=f"{u['sam']}@{raw['domain']}",
            department=u["department"],
            title=u["title"],
            ou=u["ou"],
            pwd_last_set=clock - timedelta(days=30),
            pwd_expires=clock + timedelta(days=60),
            home_drive="S:",
        )

    groups = {name: ADGroup(name=name, members=list(m)) for name, m in raw["groups"].items()}

    machines: dict[str, Machine] = {}
    for s in raw["servers"]:
        machines[s["hostname"]] = Machine(
            hostname=s["hostname"], ip=s["ip"], dhcp_enabled=False,
            gateway=net["gateway"], dns_servers=list(net["dns_servers"]),
            services=dict(WORKSTATION_SERVICES), disk_free_gb=400.0, disk_total_gb=1024.0,
        )
    for w in raw["workstations"]:
        machines[w["hostname"]] = Machine(
            hostname=w["hostname"], assigned_to=w["assigned_to"], ip=w["ip"],
            gateway=net["gateway"], dns_servers=list(net["dns_servers"]),
            services=dict(WORKSTATION_SERVICES),
            installed_printers=list(w["printers"]),
            printer_drivers={},
        )

    printers = {p["name"]: Printer(**p) for p in raw["printers"]}
    shares = {s["unc"]: Share(**s) for s in raw["shares"]}

    for w in raw["workstations"]:
        machine = machines[w["hostname"]]
        for name in machine.installed_printers:
            machine.printer_drivers[name] = printers[name].correct_driver
        dept_group = next(
            (g for g in groups.values() if users[w["assigned_to"]].sam in g.members), None
        )
        if dept_group:
            share = next((s for s in shares.values() if s.required_group == dept_group.name), None)
            if share:
                machine.mapped_drives[share.drive_letter] = share.unc

    return World(
        org=Organization(domain=raw["domain"], users=users, groups=groups),
        machines=machines, printers=printers, shares=shares,
        network=Network(**net), clock=clock,
    )
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_world_seed.py -v`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src/vitsc tests/test_world_seed.py
git commit -m "feat(world): add world model and company seed"
```

---

### Task 2: Baseline capture and invariants

**Files:**
- Create: `src/vitsc/world/invariants.py`
- Test: `tests/test_invariants.py`

**Interfaces:**
- Consumes: `World`, `load_world` (Task 1).
- Produces: `Baseline`, `capture_baseline(world: World) -> Baseline`, `check_invariants(world: World, baseline: Baseline) -> list[str]`.

This is what gives wrong fixes teeth (spec §5). A technician who clears a symptom by disabling an account or stopping a service passes the fault check and fails here.

- [ ] **Step 1: Write the failing test**

`tests/test_invariants.py`:

```python
import pytest

from vitsc.world.invariants import capture_baseline, check_invariants
from vitsc.world.models import ServiceState
from vitsc.world.seed import load_world


@pytest.fixture
def world():
    return load_world()


def test_untouched_world_has_no_violations(world):
    assert check_invariants(world, capture_baseline(world)) == []


def test_disabling_an_account_is_a_violation(world):
    baseline = capture_baseline(world)
    world.org.users["m.alvarez"].enabled = False
    violations = check_invariants(world, baseline)
    assert any("m.alvarez" in v and "disabled" in v for v in violations)


def test_stopping_a_baseline_service_is_a_violation(world):
    baseline = capture_baseline(world)
    world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    violations = check_invariants(world, baseline)
    assert any("Spooler" in v and "MER-WS-001" in v for v in violations)


def test_removing_group_membership_is_a_violation(world):
    baseline = capture_baseline(world)
    world.org.groups["ACC-Share-RW"].members.remove("m.alvarez")
    violations = check_invariants(world, baseline)
    assert any("ACC-Share-RW" in v and "m.alvarez" in v for v in violations)


def test_foreign_dns_is_a_violation(world):
    baseline = capture_baseline(world)
    world.machines["MER-WS-001"].dns_servers = ["1.1.1.1"]
    violations = check_invariants(world, baseline)
    assert any("1.1.1.1" in v for v in violations)


def test_restarting_a_service_the_fault_stopped_is_not_a_violation(world):
    world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    baseline = capture_baseline(world)
    world.machines["MER-WS-001"].services["Spooler"] = ServiceState.RUNNING
    assert check_invariants(world, baseline) == []
```

The last test matters: the baseline is captured **after** the fault is applied, so repairing the fault never trips an invariant. Only *additional* damage does.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_invariants.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.world.invariants'`

- [ ] **Step 3: Write the implementation**

`src/vitsc/world/invariants.py`:

```python
from pydantic import BaseModel, Field

from vitsc.world.models import ServiceState, World


class Baseline(BaseModel):
    enabled_users: set[str] = Field(default_factory=set)
    running_services: set[tuple[str, str]] = Field(default_factory=set)
    group_members: dict[str, set[str]] = Field(default_factory=dict)
    allowed_dns: set[str] = Field(default_factory=set)


def capture_baseline(world: World) -> Baseline:
    return Baseline(
        enabled_users={u.sam for u in world.org.users.values() if u.enabled},
        running_services={
            (m.hostname, name)
            for m in world.machines.values()
            for name, state in m.services.items()
            if state is ServiceState.RUNNING
        },
        group_members={g.name: set(g.members) for g in world.org.groups.values()},
        allowed_dns=set(world.network.dns_servers),
    )


def check_invariants(world: World, baseline: Baseline) -> list[str]:
    violations: list[str] = []

    for sam in sorted(baseline.enabled_users):
        user = world.org.users.get(sam)
        if user is None:
            violations.append(f"account {sam} was deleted")
        elif not user.enabled:
            violations.append(f"account {sam} was disabled")

    for hostname, service in sorted(baseline.running_services):
        machine = world.machines.get(hostname)
        if machine is None:
            continue
        if machine.services.get(service) is not ServiceState.RUNNING:
            violations.append(f"service {service} on {hostname} was stopped")

    for group_name, members in sorted(baseline.group_members.items()):
        current = world.org.groups.get(group_name)
        if current is None:
            violations.append(f"group {group_name} was deleted")
            continue
        for sam in sorted(members - set(current.members)):
            violations.append(f"{sam} was removed from {group_name}")

    for machine in world.machines.values():
        for server in machine.dns_servers:
            if server not in baseline.allowed_dns:
                violations.append(f"{machine.hostname} points at foreign DNS {server}")

    return violations
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_invariants.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vitsc/world/invariants.py tests/test_invariants.py
git commit -m "feat(world): add baseline capture and invariant checks"
```

---

### Task 3: Environment protocol and SimulatedEnvironment

**Files:**
- Create: `src/vitsc/env/__init__.py`, `src/vitsc/env/base.py`, `src/vitsc/env/simulated.py`
- Test: `tests/test_simulated_env.py`

**Interfaces:**
- Consumes: `World` (Task 1).
- Produces: `Query`, `Observation`, `Action`, `ActionResult`, `Environment` protocol, `SimulatedEnvironment(world)`.

Query kinds implemented here: `ad.user`, `ad.group`, `machine.state`, `machine.services`, `machine.eventlog`, `net.ping`, `net.nslookup`, `net.ipconfig`, `printer.state`, `share.access`.

Action kinds implemented here: `ad.unlock`, `ad.reset_password`, `ad.enable`, `ad.disable`, `ad.add_member`, `ad.remove_member`, `machine.restart_service`, `machine.set_dns`, `machine.renew_dhcp`, `machine.clear_disk`, `printer.reinstall_driver`.

- [ ] **Step 1: Write the failing test**

`tests/test_simulated_env.py`:

```python
import pytest

from vitsc.env.base import Action, Query
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.world.models import ServiceState
from vitsc.world.seed import load_world


@pytest.fixture
def env():
    return SimulatedEnvironment(load_world())


def test_read_ad_user_returns_attributes(env):
    obs = env.read(Query(kind="ad.user", target="m.alvarez"))
    assert obs.ok
    assert obs.data["LockedOut"] is False
    assert "m.alvarez" in obs.rendered


def test_read_unknown_user_is_not_ok(env):
    obs = env.read(Query(kind="ad.user", target="nobody"))
    assert obs.ok is False
    assert "cannot find" in obs.rendered.lower()


def test_unlock_action_clears_lockout(env):
    env.world.org.users["m.alvarez"].locked_out = True
    result = env.execute(Action(kind="ad.unlock", target="m.alvarez"))
    assert result.ok
    assert env.world.org.users["m.alvarez"].locked_out is False


def test_ping_by_hostname_resolves_when_dns_is_correct(env):
    obs = env.read(Query(kind="net.ping", target="MER-FS-01", args={"from": "MER-WS-001"}))
    assert obs.ok
    assert obs.data["resolved"] is True


def test_ping_by_hostname_fails_when_dns_is_wrong(env):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    obs = env.read(Query(kind="net.ping", target="MER-FS-01", args={"from": "MER-WS-001"}))
    assert obs.ok is False
    assert obs.data["resolved"] is False


def test_ping_by_ip_still_works_with_wrong_dns(env):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    obs = env.read(Query(kind="net.ping", target="10.20.10.6", args={"from": "MER-WS-001"}))
    assert obs.ok


def test_share_access_requires_group_membership(env):
    ok_before = env.read(Query(kind="share.access", target="S:", args={"from": "MER-WS-001"}))
    assert ok_before.ok
    env.world.org.groups["ACC-Share-RW"].members.remove("m.alvarez")
    denied = env.read(Query(kind="share.access", target="S:", args={"from": "MER-WS-001"}))
    assert denied.ok is False
    assert "denied" in denied.rendered.lower()


def test_restart_service_sets_running(env):
    env.world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    env.execute(Action(kind="machine.restart_service", target="MER-WS-001", args={"service": "Spooler"}))
    assert env.world.machines["MER-WS-001"].services["Spooler"] is ServiceState.RUNNING


def test_snapshot_and_restore_round_trip(env):
    snap = env.snapshot()
    env.world.org.users["m.alvarez"].locked_out = True
    env.restore(snap)
    assert env.world.org.users["m.alvarez"].locked_out is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_simulated_env.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.env'`

- [ ] **Step 3: Write the protocol types**

`src/vitsc/env/base.py`:

```python
from typing import Any, Protocol

from pydantic import BaseModel, Field


class Query(BaseModel):
    kind: str
    target: str
    args: dict[str, str] = Field(default_factory=dict)


class Observation(BaseModel):
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    rendered: str


class Action(BaseModel):
    kind: str
    target: str
    args: dict[str, str] = Field(default_factory=dict)


class ActionResult(BaseModel):
    ok: bool
    rendered: str


class Environment(Protocol):
    def read(self, query: Query) -> Observation: ...
    def execute(self, action: Action) -> ActionResult: ...
    def snapshot(self) -> str: ...
    def restore(self, snapshot_id: str) -> None: ...
```

- [ ] **Step 4: Write SimulatedEnvironment**

`src/vitsc/env/simulated.py`. Dispatch tables keyed by `kind`; every handler reads or writes `self.world` and nothing else.

```python
import uuid

from vitsc.env.base import Action, ActionResult, Observation, Query
from vitsc.world.models import ProfileState, ServiceState, World

NOT_FOUND = "The term is not recognised, or the object cannot be found."


class SimulatedEnvironment:
    def __init__(self, world: World) -> None:
        self.world = world
        self._snapshots: dict[str, World] = {}

    # --- Environment protocol -------------------------------------------
    def read(self, query: Query) -> Observation:
        handler = getattr(self, f"_read_{query.kind.replace('.', '_')}", None)
        if handler is None:
            return Observation(ok=False, rendered=NOT_FOUND)
        return handler(query)

    def execute(self, action: Action) -> ActionResult:
        handler = getattr(self, f"_do_{action.kind.replace('.', '_')}", None)
        if handler is None:
            return ActionResult(ok=False, rendered=NOT_FOUND)
        return handler(action)

    def snapshot(self) -> str:
        snapshot_id = uuid.uuid4().hex
        self._snapshots[snapshot_id] = self.world.model_copy(deep=True)
        return snapshot_id

    def restore(self, snapshot_id: str) -> None:
        self.world = self._snapshots[snapshot_id].model_copy(deep=True)

    # --- helpers ---------------------------------------------------------
    def _resolve(self, name: str, from_host: str) -> str | None:
        """DNS resolution, honouring the querying machine's configured resolvers."""
        if name[0].isdigit():
            return name
        source = self.world.machines.get(from_host)
        if source is None or not set(source.dns_servers) & set(self.world.network.dns_servers):
            return None
        target = self.world.machines.get(name.upper())
        return target.ip if target else None

    # --- reads -----------------------------------------------------------
    def _read_ad_user(self, q: Query) -> Observation:
        user = self.world.org.users.get(q.target)
        if user is None:
            return Observation(ok=False, rendered=f"Get-ADUser: {NOT_FOUND}")
        data = {
            "SamAccountName": user.sam, "Name": user.display_name,
            "Enabled": user.enabled, "LockedOut": user.locked_out,
            "BadPwdCount": user.bad_pwd_count,
            "PasswordLastSet": user.pwd_last_set.isoformat(),
            "PasswordExpired": self.world.clock > user.pwd_expires,
            "MemberOf": self.world.groups_of(user.sam),
        }
        rendered = "\n".join(f"{k:<18}: {v}" for k, v in data.items())
        return Observation(ok=True, data=data, rendered=rendered)

    def _read_share_access(self, q: Query) -> Observation:
        machine = self.world.machines.get(q.args.get("from", ""))
        if machine is None or q.target not in machine.mapped_drives:
            return Observation(ok=False, rendered=f"{q.target} is not mapped.")
        share = self.world.shares[machine.mapped_drives[q.target]]
        if self._resolve(share.host, machine.hostname) is None:
            return Observation(
                ok=False, data={"reason": "dns"},
                rendered=f"{share.unc} is not accessible. The network path was not found.",
            )
        member = machine.assigned_to in self.world.org.groups[share.required_group].members
        if not member:
            return Observation(
                ok=False, data={"reason": "permissions"},
                rendered=f"{share.unc} is not accessible. Access is denied.",
            )
        return Observation(ok=True, data={"unc": share.unc}, rendered=f"{q.target} -> {share.unc}")
```

Implement the remaining handlers in the same shape:

- `_read_ad_group` — members list, or `NOT_FOUND`.
- `_read_machine_state` — hostname, ip, disk free/total, smart status, profile state, mapped drives, installed printers.
- `_read_machine_services` — the service dict rendered as `Get-Service` columns.
- `_read_machine_eventlog` — last `args["count"]` entries, filtered by `args.get("log")`.
- `_read_net_ping` — use `_resolve`; on failure return `ok=False`, `data={"resolved": False}`, rendered `Ping request could not find host <target>.`; on success `data={"resolved": True, "ip": ip}` and four reply lines.
- `_read_net_nslookup` — same resolution rule, rendered in `nslookup` format; failure renders `*** Request to <dns> timed-out`.
- `_read_net_ipconfig` — APIPA when `ip` is `None` and `dhcp_enabled`: render `169.254.x.x` with an empty gateway.
- `_read_printer_state` — online flag, host, model, and the driver installed on `args["from"]` versus `correct_driver`.

And the actions, each returning `ActionResult` and mutating only world state:

- `_do_ad_unlock` — clear `locked_out`, zero `bad_pwd_count`.
- `_do_ad_reset_password` — set `pwd_last_set` to `world.clock`, `pwd_expires` to `clock + 60 days`, clear lockout.
- `_do_ad_enable` / `_do_ad_disable` — set `enabled`.
- `_do_ad_add_member` / `_do_ad_remove_member` — mutate `ADGroup.members`.
- `_do_machine_restart_service` — set `ServiceState.RUNNING`.
- `_do_machine_set_dns` — replace `dns_servers` with `args["servers"].split(",")`.
- `_do_machine_renew_dhcp` — if `dhcp_enabled`, assign the machine's seeded IP from the DHCP scope; else no-op with `ok=False`.
- `_do_machine_clear_disk` — raise `disk_free_gb` by `float(args["gb"])`, capped at `disk_total_gb`, and set `profile_state` back to `ProfileState.NORMAL` if it was `TEMPORARY`.
- `_do_printer_reinstall_driver` — set `machine.printer_drivers[printer] = printers[printer].correct_driver`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_simulated_env.py -v`
Expected: 9 passed.

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v`
Expected: 19 passed.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/env tests/test_simulated_env.py
git commit -m "feat(env): add Environment protocol and simulated backend"
```

---

### Task 4: Fault framework, first fault, and the catalog conformance harness

**Files:**
- Create: `src/vitsc/faults/__init__.py`, `src/vitsc/faults/base.py`, `src/vitsc/faults/registry.py`
- Create: `src/vitsc/faults/catalog/__init__.py`, `src/vitsc/faults/catalog/identity.py`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `World`, `Query`, `Action`, `SimulatedEnvironment`, `capture_baseline`, `check_invariants`.
- Produces: `Domain`, `Backend`, `Placement`, `UserSymptoms`, `ResolutionPath`, `Fault` protocol, `register`, `all_faults()`, `get_fault(id)`, and `AccountLocked`.

The conformance harness lands here rather than at the end, so every fault added in Tasks 9–11 is automatically proven solvable the moment it registers.

- [ ] **Step 1: Write the failing test**

`tests/test_catalog.py`:

```python
import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import all_faults
from vitsc.world.invariants import capture_baseline, check_invariants
from vitsc.world.seed import load_world

JARGON = {
    "dns", "dhcp", "active directory", "group policy", "spooler", "smart",
    "driver", "subnet", "apipa", "lockout", "gpo", "registry", "wmi",
}


def fault_cases():
    for fault in all_faults():
        for placement in fault.placements(load_world()):
            yield pytest.param(fault, placement, id=f"{fault.id}@{placement.key}")


@pytest.mark.parametrize("fault,placement", list(fault_cases()))
def test_fault_conforms(fault, placement):
    world = load_world()

    # 1. Absent before, present after.
    assert fault.is_present(world, placement) is False
    fault.apply(world, placement, __import__("random").Random(0))
    assert fault.is_present(world, placement) is True

    # 2. Discoverable: at least one diagnostic query reports something.
    env = SimulatedEnvironment(world)
    path = fault.diagnostic_path(placement)
    assert path, f"{fault.id} declares no diagnostic path"
    assert any(env.read(q).rendered for q in path)

    # 3. Every canonical resolution clears it, invariants intact.
    for resolution in fault.canonical_resolutions():
        broken = load_world()
        fault.apply(broken, placement, __import__("random").Random(0))
        scoped = SimulatedEnvironment(broken)
        baseline = capture_baseline(broken)
        for action in resolution.actions:
            scoped.execute(action)
        assert fault.is_present(scoped.world, placement) is False, (
            f"{fault.id}: resolution '{resolution.label}' did not clear the fault"
        )
        assert check_invariants(scoped.world, baseline) == [], (
            f"{fault.id}: resolution '{resolution.label}' caused collateral damage"
        )


@pytest.mark.parametrize("fault,placement", list(fault_cases()))
def test_symptoms_do_not_leak(fault, placement):
    world = load_world()
    fault.apply(world, placement, __import__("random").Random(0))
    symptoms = fault.symptoms(world, placement)
    blob = " ".join(
        filter(None, [symptoms.opening, symptoms.onset, symptoms.error_text, symptoms.scope])
    ).lower()
    for term in fault.leak_terms:
        assert term.lower() not in blob, f"{fault.id} symptoms leak '{term}'"
    for term in JARGON:
        assert term not in blob, f"{fault.id} symptoms contain jargon '{term}'"


def test_discoverability_actually_differs():
    """A fault must change at least one observation, or it is invisible."""
    for fault in all_faults():
        for placement in fault.placements(load_world()):
            clean = SimulatedEnvironment(load_world())
            broken_world = load_world()
            fault.apply(broken_world, placement, __import__("random").Random(0))
            broken = SimulatedEnvironment(broken_world)
            path = fault.diagnostic_path(placement)
            assert any(
                clean.read(q).rendered != broken.read(q).rendered for q in path
            ), f"{fault.id}@{placement.key} is not observable via its diagnostic path"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.faults'`

- [ ] **Step 3: Write the fault base types**

`src/vitsc/faults/base.py`:

```python
from random import Random
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from vitsc.env.base import Action, Query
from vitsc.world.models import World

Domain = Literal["identity", "network", "printing", "mail", "endpoint"]
Backend = Literal["simulated", "winrm"]


class Placement(BaseModel):
    kind: Literal["user", "machine", "printer", "share"]
    key: str


class UserSymptoms(BaseModel):
    """Only what a non-technical person can perceive. The sole persona input."""
    opening: str
    onset: str
    scope: str
    error_text: str | None = None


class ResolutionPath(BaseModel):
    label: str
    actions: list[Action]


@runtime_checkable
class Fault(Protocol):
    id: str
    domain: Domain
    difficulty: int
    canonical_title: str
    supported_backends: frozenset[str]
    leak_terms: list[str]
    escalation_is_correct: bool

    def placements(self, world: World) -> list[Placement]: ...
    def apply(self, world: World, at: Placement, rng: Random) -> None: ...
    def is_present(self, world: World, at: Placement) -> bool: ...
    def symptoms(self, world: World, at: Placement) -> UserSymptoms: ...
    def diagnostic_path(self, at: Placement) -> list[Query]: ...
    def canonical_resolutions(self) -> list[ResolutionPath]: ...
```

- [ ] **Step 4: Write the registry**

`src/vitsc/faults/registry.py`:

```python
from vitsc.faults.base import Fault

_REGISTRY: dict[str, Fault] = {}


def register(fault: Fault) -> Fault:
    if fault.id in _REGISTRY:
        raise ValueError(f"duplicate fault id: {fault.id}")
    _REGISTRY[fault.id] = fault
    return fault


def all_faults() -> list[Fault]:
    import vitsc.faults.catalog  # noqa: F401  — triggers registration
    return sorted(_REGISTRY.values(), key=lambda f: f.id)


def get_fault(fault_id: str) -> Fault:
    all_faults()
    return _REGISTRY[fault_id]
```

`src/vitsc/faults/catalog/__init__.py`:

```python
from vitsc.faults.catalog import identity  # noqa: F401

__all__ = ["identity"]
```

- [ ] **Step 5: Write the first fault**

`src/vitsc/faults/catalog/identity.py`:

```python
from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import World

# Users who make plausible lockout victims: ordinary staff with a workstation.
def _staff_with_machines(world: World) -> list[Placement]:
    return [
        Placement(kind="user", key=m.assigned_to)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class AccountLocked:
    id = "ad.account_locked"
    domain = "identity"
    difficulty = 1
    canonical_title = "AD account locked out after repeated bad password attempts"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["locked", "lockout", "active directory", "ad ", "unlock"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_machines(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        user = world.org.users[at.key]
        user.locked_out = True
        user.bad_pwd_count = rng.randint(6, 14)

    def is_present(self, world: World, at: Placement) -> bool:
        return world.org.users[at.key].locked_out

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="I can't sign in to my computer this morning.",
            onset="It worked fine when I left on Friday.",
            scope="Just me as far as I know, the person next to me is fine.",
            error_text="The referenced account is currently disabled and may not be logged on to.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="ad.user", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(label="Unlock the account", actions=[
                Action(kind="ad.unlock", target="{placement}"),
            ]),
            ResolutionPath(label="Reset the password", actions=[
                Action(kind="ad.reset_password", target="{placement}"),
            ]),
        ]


register(AccountLocked())
```

- [ ] **Step 6: Bind `{placement}` in resolutions**

`canonical_resolutions()` cannot know its placement, so the conformance test must substitute. Add to `src/vitsc/faults/base.py`:

```python
def bind(resolution: ResolutionPath, at: Placement) -> ResolutionPath:
    """Replace the '{placement}' sentinel with the concrete target key."""
    return ResolutionPath(
        label=resolution.label,
        actions=[
            a.model_copy(update={"target": at.key if a.target == "{placement}" else a.target})
            for a in resolution.actions
        ],
    )
```

Then in `tests/test_catalog.py`, import `bind` and change the resolution loop to
`for action in bind(resolution, placement).actions:`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: passes — 6 placements × 2 conformance tests, plus the discoverability test.

- [ ] **Step 8: Commit**

```bash
git add src/vitsc/faults tests/test_catalog.py
git commit -m "feat(faults): add fault protocol, registry, and conformance harness"
```

---

### Task 5: Tool framework and the AD console

**Files:**
- Create: `src/vitsc/tools/__init__.py`, `src/vitsc/tools/base.py`, `src/vitsc/tools/ad.py`, `src/vitsc/tools/registry.py`
- Test: `tests/test_tools_ad.py`

**Interfaces:**
- Consumes: `Environment`, `Query`, `Action` (Task 3).
- Produces: `ToolCall`, `ToolLog`, `Tool` protocol, `ADConsole`, `get_tool(name)`, `all_tools()`.

Reminder from Global Constraints: nothing in `tools/` imports from `faults/`.

- [ ] **Step 1: Write the failing test**

`tests/test_tools_ad.py`:

```python
import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.tools.ad import ADConsole
from vitsc.tools.base import ToolLog
from vitsc.world.seed import load_world


@pytest.fixture
def env():
    return SimulatedEnvironment(load_world())


@pytest.fixture
def log():
    return ToolLog()


def test_get_user_renders_attributes(env, log):
    call = ADConsole().invoke(env, log, "get-user", {"sam": "m.alvarez"})
    assert "LockedOut" in call.rendered
    assert call.mutating is False


def test_unlock_is_recorded_as_mutating(env, log):
    env.world.org.users["m.alvarez"].locked_out = True
    call = ADConsole().invoke(env, log, "unlock", {"sam": "m.alvarez"})
    assert call.mutating is True
    assert env.world.org.users["m.alvarez"].locked_out is False


def test_every_call_is_logged(env, log):
    ADConsole().invoke(env, log, "get-user", {"sam": "m.alvarez"})
    ADConsole().invoke(env, log, "get-user", {"sam": "d.okafor"})
    assert len(log.calls) == 2
    assert log.calls[0].tool == "ad"


def test_unknown_command_returns_realistic_error(env, log):
    call = ADConsole().invoke(env, log, "frobnicate", {})
    assert call.ok is False
    assert "not recognized" in call.rendered.lower()


def test_missing_argument_does_not_raise(env, log):
    call = ADConsole().invoke(env, log, "get-user", {})
    assert call.ok is False


def test_mutating_calls_before_any_question_are_countable(env, log):
    ADConsole().invoke(env, log, "get-user", {"sam": "m.alvarez"})
    ADConsole().invoke(env, log, "unlock", {"sam": "m.alvarez"})
    assert log.first_mutating_index() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tools_ad.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.tools'`

- [ ] **Step 3: Write the tool base**

`src/vitsc/tools/base.py`:

```python
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, Field

from vitsc.env.base import Environment


class ToolCall(BaseModel):
    tool: str
    command: str
    args: dict[str, str] = Field(default_factory=dict)
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ok: bool
    mutating: bool
    rendered: str


class ToolLog(BaseModel):
    calls: list[ToolCall] = Field(default_factory=list)

    def record(self, call: ToolCall) -> ToolCall:
        self.calls.append(call)
        return call

    def first_mutating_index(self) -> int | None:
        for i, call in enumerate(self.calls):
            if call.mutating:
                return i
        return None


class Tool(Protocol):
    name: str

    def commands(self) -> list[str]: ...
    def invoke(
        self, env: Environment, log: ToolLog, command: str, args: dict[str, str]
    ) -> ToolCall: ...


UNKNOWN = "The term '{cmd}' is not recognized as the name of a cmdlet."
```

- [ ] **Step 4: Write the AD console**

`src/vitsc/tools/ad.py`:

```python
from vitsc.env.base import Action, Environment, Query
from vitsc.tools.base import UNKNOWN, ToolCall, ToolLog

READS = {"get-user": "ad.user", "get-group": "ad.group"}
WRITES = {
    "unlock": "ad.unlock",
    "reset-password": "ad.reset_password",
    "enable": "ad.enable",
    "disable": "ad.disable",
    "add-member": "ad.add_member",
    "remove-member": "ad.remove_member",
}


class ADConsole:
    name = "ad"

    def commands(self) -> list[str]:
        return sorted([*READS, *WRITES])

    def invoke(
        self, env: Environment, log: ToolLog, command: str, args: dict[str, str]
    ) -> ToolCall:
        target = args.get("sam") or args.get("group") or ""
        if command in READS:
            if not target:
                return log.record(ToolCall(
                    tool=self.name, command=command, args=args, ok=False, mutating=False,
                    rendered="Missing required parameter: -Identity",
                ))
            obs = env.read(Query(kind=READS[command], target=target, args=args))
            return log.record(ToolCall(
                tool=self.name, command=command, args=args,
                ok=obs.ok, mutating=False, rendered=obs.rendered,
            ))
        if command in WRITES:
            if not target:
                return log.record(ToolCall(
                    tool=self.name, command=command, args=args, ok=False, mutating=False,
                    rendered="Missing required parameter: -Identity",
                ))
            result = env.execute(Action(kind=WRITES[command], target=target, args=args))
            return log.record(ToolCall(
                tool=self.name, command=command, args=args,
                ok=result.ok, mutating=True, rendered=result.rendered,
            ))
        return log.record(ToolCall(
            tool=self.name, command=command, args=args, ok=False, mutating=False,
            rendered=UNKNOWN.format(cmd=command),
        ))
```

Note: a failed write still records `mutating=True` only when it reached `env.execute`. A missing-parameter rejection is not a mutation, which keeps the "did you touch anything before asking" grade honest.

- [ ] **Step 5: Write the tool registry**

`src/vitsc/tools/registry.py`:

```python
from vitsc.tools.ad import ADConsole
from vitsc.tools.base import Tool

_TOOLS: dict[str, Tool] = {t.name: t for t in [ADConsole()]}


def get_tool(name: str) -> Tool:
    return _TOOLS[name]


def all_tools() -> list[Tool]:
    return sorted(_TOOLS.values(), key=lambda t: t.name)


def register_tool(tool: Tool) -> None:
    _TOOLS[tool.name] = tool
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_tools_ad.py -v`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/tools tests/test_tools_ad.py
git commit -m "feat(tools): add tool framework and AD console"
```

---

### Task 6: Network, remote session, event log, printing, and PowerShell tools

**Files:**
- Create: `src/vitsc/tools/network.py`, `src/vitsc/tools/remote.py`, `src/vitsc/tools/eventlog.py`, `src/vitsc/tools/printing.py`, `src/vitsc/tools/powershell.py`
- Modify: `src/vitsc/tools/registry.py`
- Test: `tests/test_tools_rest.py`

**Interfaces:**
- Consumes: `ToolCall`, `ToolLog`, `Tool`, `UNKNOWN` (Task 5); `Query`, `Action` (Task 3).
- Produces: `NetworkTools`, `RemoteSession`, `EventViewer`, `PrintManagement`, `PowerShellConsole`, all registered in `registry.py`.

These are folded into one task because each is the same thin dispatch shape as `ADConsole` and none is independently reviewable in a meaningful way.

- [ ] **Step 1: Write the failing test**

`tests/test_tools_rest.py`:

```python
import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.tools.base import ToolLog
from vitsc.tools.eventlog import EventViewer
from vitsc.tools.network import NetworkTools
from vitsc.tools.powershell import PowerShellConsole
from vitsc.tools.printing import PrintManagement
from vitsc.tools.registry import all_tools, get_tool
from vitsc.tools.remote import RemoteSession
from vitsc.world.models import ServiceState
from vitsc.world.seed import load_world


@pytest.fixture
def env():
    return SimulatedEnvironment(load_world())


@pytest.fixture
def log():
    return ToolLog()


def test_ping_renders_replies(env, log):
    call = NetworkTools().invoke(env, log, "ping", {"host": "MER-FS-01", "from": "MER-WS-001"})
    assert call.ok and "Reply from" in call.rendered


def test_ping_fails_on_broken_dns(env, log):
    env.world.machines["MER-WS-001"].dns_servers = ["10.20.10.99"]
    call = NetworkTools().invoke(env, log, "ping", {"host": "MER-FS-01", "from": "MER-WS-001"})
    assert call.ok is False and "could not find host" in call.rendered


def test_ipconfig_shows_apipa_when_no_lease(env, log):
    env.world.machines["MER-WS-001"].ip = None
    call = NetworkTools().invoke(env, log, "ipconfig", {"from": "MER-WS-001"})
    assert "169.254." in call.rendered


def test_remote_session_reports_disk(env, log):
    env.world.machines["MER-WS-001"].disk_free_gb = 0.4
    call = RemoteSession().invoke(env, log, "inspect", {"host": "MER-WS-001"})
    assert "0.4" in call.rendered and call.mutating is False


def test_event_viewer_filters_by_log(env, log):
    call = EventViewer().invoke(env, log, "get", {"host": "MER-WS-001", "log": "System", "count": "5"})
    assert call.ok


def test_printing_reports_driver_mismatch(env, log):
    env.world.machines["MER-WS-001"].printer_drivers["PRT-ACC-01"] = "Generic / Text Only"
    call = PrintManagement().invoke(env, log, "get-printer", {"printer": "PRT-ACC-01", "from": "MER-WS-001"})
    assert "Generic / Text Only" in call.rendered


def test_powershell_restart_service_is_mutating(env, log):
    env.world.machines["MER-WS-001"].services["Spooler"] = ServiceState.STOPPED
    call = PowerShellConsole().invoke(
        env, log, "Restart-Service", {"host": "MER-WS-001", "name": "Spooler"}
    )
    assert call.mutating is True
    assert env.world.machines["MER-WS-001"].services["Spooler"] is ServiceState.RUNNING


def test_powershell_rejects_unknown_cmdlet(env, log):
    call = PowerShellConsole().invoke(env, log, "Invoke-Magic", {"host": "MER-WS-001"})
    assert call.ok is False and "not recognized" in call.rendered.lower()


def test_all_six_tools_are_registered():
    assert {t.name for t in all_tools()} == {
        "ad", "net", "remote", "events", "print", "ps"
    }
    assert get_tool("net").name == "net"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tools_rest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.tools.network'`

- [ ] **Step 3: Write the five tools**

Each follows `ADConsole`'s exact shape — a `READS` map, a `WRITES` map, `invoke` dispatching to `env.read` / `env.execute`, everything recorded to the log, unknown commands returning `UNKNOWN`.

```python
# src/vitsc/tools/network.py
READS = {"ping": "net.ping", "nslookup": "net.nslookup", "ipconfig": "net.ipconfig"}
WRITES = {"renew": "machine.renew_dhcp", "set-dns": "machine.set_dns"}
# name = "net"; target comes from args["host"] for reads that take one,
# otherwise args["from"]; "from" is always passed through in Query.args.

# src/vitsc/tools/remote.py
READS = {"inspect": "machine.state", "services": "machine.services"}
WRITES = {"clear-disk": "machine.clear_disk"}
# name = "remote"; target = args["host"].

# src/vitsc/tools/eventlog.py
READS = {"get": "machine.eventlog"}
WRITES: dict[str, str] = {}
# name = "events"; target = args["host"]; log and count pass through args.

# src/vitsc/tools/printing.py
READS = {"get-printer": "printer.state"}
WRITES = {
    "restart-spooler": "machine.restart_service",
    "reinstall-driver": "printer.reinstall_driver",
}
# name = "print"; target = args["printer"] for printer ops,
# args["from"] for restart-spooler, which also injects args={"service": "Spooler"}.

# src/vitsc/tools/powershell.py
READS = {"Get-Service": "machine.services", "Get-ADUser": "ad.user",
         "Get-Printer": "printer.state", "Get-PSDrive": "share.access",
         "Test-NetConnection": "net.ping", "Get-EventLog": "machine.eventlog"}
WRITES = {"Restart-Service": "machine.restart_service", "gpupdate": "machine.renew_dhcp"}
# name = "ps"; a *defined* command set, not a parser. Anything else -> UNKNOWN.
# Command matching is case-insensitive, PowerShell-style.
```

To avoid five near-identical `invoke` bodies, extract the dispatch from `ADConsole` into `src/vitsc/tools/base.py` as a `DispatchTool` base class holding `name`, `READS`, `WRITES`, and a `target_key(command, args) -> str` hook; then each tool is a subclass declaring its maps. Refactor `ADConsole` onto it in this task and confirm `tests/test_tools_ad.py` still passes untouched.

- [ ] **Step 4: Register them**

Update `_TOOLS` in `src/vitsc/tools/registry.py` to instantiate all six.

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -v`
Expected: all green, including `tests/test_tools_ad.py` unchanged after the refactor.

- [ ] **Step 6: Commit**

```bash
git add src/vitsc/tools tests/test_tools_rest.py
git commit -m "feat(tools): add network, remote, event log, printing, and PowerShell tools"
```

---

### Task 7: Remaining identity faults

**Files:**
- Modify: `src/vitsc/faults/catalog/identity.py`
- Test: `tests/test_catalog.py` (no changes — the harness picks these up automatically)

**Interfaces:**
- Consumes: `Placement`, `UserSymptoms`, `ResolutionPath`, `register` (Task 4).
- Produces: `PasswordExpired`, `OffboardedReactivation`, `ShareGroupRemoved`, registered.

`PasswordExpired` exists to be confused with `AccountLocked` — both present as "I can't sign in." Distinguishing them requires actually reading `PasswordExpired` in the AD output rather than pattern-matching the opening line.

- [ ] **Step 1: Add the three faults**

Append to `src/vitsc/faults/catalog/identity.py`:

```python
from datetime import timedelta

from vitsc.world.models import World


class PasswordExpired:
    id = "ad.password_expired"
    domain = "identity"
    difficulty = 2
    canonical_title = "Domain password expired; user never saw the change prompt"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["expired", "password policy", "reset"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _staff_with_machines(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        user = world.org.users[at.key]
        user.pwd_last_set = world.clock - timedelta(days=91)
        user.pwd_expires = world.clock - timedelta(days=rng.randint(1, 3))

    def is_present(self, world: World, at: Placement) -> bool:
        return world.clock > world.org.users[at.key].pwd_expires

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="It won't let me log in and I know I'm typing the right thing.",
            onset="Since this morning. Friday was fine.",
            scope="Only me, my desk neighbour got in okay.",
            error_text="You must change your password before signing in.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="ad.user", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(label="Reset the password and set a new expiry", actions=[
                Action(kind="ad.reset_password", target="{placement}"),
            ]),
        ]


class OffboardedReactivation:
    """Escalate-correct: reactivating a departed employee's account needs
    HR/manager authorisation. A technician who just clicks Enable is wrong,
    even though the symptom clears."""

    id = "ad.offboarded_reactivation"
    domain = "identity"
    difficulty = 3
    canonical_title = "Disabled account of an offboarded employee; requires HR authorisation"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["disabled", "offboard", "terminated", "hr approval"]
    escalation_is_correct = True

    def placements(self, world: World) -> list[Placement]:
        return [Placement(kind="user", key="h.reyes")]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.org.users[at.key].enabled = False

    def is_present(self, world: World, at: Placement) -> bool:
        return not world.org.users[at.key].enabled

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Hector is back on nights from this week and his login doesn't work at all.",
            onset="He left in June and started again yesterday.",
            scope="Just his account. Everyone else on the night shift is fine.",
            error_text="Your account has been turned off. Please contact your system administrator.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="ad.user", target=at.key)]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        # Present so the conformance harness can verify the fault is *technically*
        # clearable. Grading still marks a fix as wrong: escalation_is_correct.
        return [
            ResolutionPath(label="Re-enable after HR authorisation", actions=[
                Action(kind="ad.enable", target="{placement}"),
            ]),
        ]


class ShareGroupRemoved:
    id = "share.group_membership_removed"
    domain = "identity"
    difficulty = 3
    canonical_title = "User removed from the department share security group"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["group", "membership", "permission", "security group", "acl"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return [
            Placement(kind="user", key=m.assigned_to)
            for m in world.machines.values()
            if m.assigned_to and world.groups_of(m.assigned_to)
        ]

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        group_name = world.groups_of(at.key)[0]
        world.org.groups[group_name].members.remove(at.key)

    def is_present(self, world: World, at: Placement) -> bool:
        machine = world.machine_for(at.key)
        if machine is None or "S:" not in machine.mapped_drives:
            return False
        share = world.shares[machine.mapped_drives["S:"]]
        return at.key not in world.org.groups[share.required_group].members

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="My S drive is gone. There's a little red cross on it.",
            onset="It was there yesterday.",
            scope="My whole team uses that folder and they can still get in.",
            error_text="S:\\ is not accessible. Access is denied.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="share.access", target="S:", args={"from": "{machine}"}),
            Query(kind="ad.user", target=at.key),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(label="Restore group membership", actions=[
                Action(kind="ad.add_member", target="{group}", args={"sam": "{placement}"}),
            ]),
        ]


register(PasswordExpired())
register(OffboardedReactivation())
register(ShareGroupRemoved())
```

- [ ] **Step 2: Extend `bind` for `{machine}` and `{group}`**

`ShareGroupRemoved` needs two more sentinels. Replace `bind` in `src/vitsc/faults/base.py`:

```python
def bind(resolution: ResolutionPath, at: Placement, world: World) -> ResolutionPath:
    """Substitute placement sentinels with concrete world keys."""
    machine = world.machine_for(at.key) if at.kind == "user" else None
    subs = {
        "{placement}": at.key,
        "{machine}": machine.hostname if machine else "",
        "{group}": _share_group(world, at) or "",
    }
    def sub(value: str) -> str:
        return subs.get(value, value)
    return ResolutionPath(
        label=resolution.label,
        actions=[
            a.model_copy(update={
                "target": sub(a.target),
                "args": {k: sub(v) for k, v in a.args.items()},
            })
            for a in resolution.actions
        ],
    )


def _share_group(world: World, at: Placement) -> str | None:
    machine = world.machine_for(at.key)
    if machine is None or "S:" not in machine.mapped_drives:
        return None
    return world.shares[machine.mapped_drives["S:"]].required_group
```

Apply the same substitution to `diagnostic_path` results. Add to `base.py`:

```python
def bind_query(query: Query, at: Placement, world: World) -> Query:
    machine = world.machine_for(at.key) if at.kind == "user" else None
    subs = {"{placement}": at.key, "{machine}": machine.hostname if machine else ""}
    return query.model_copy(update={
        "target": subs.get(query.target, query.target),
        "args": {k: subs.get(v, v) for k, v in query.args.items()},
    })
```

- [ ] **Step 3: Update the conformance harness to bind**

In `tests/test_catalog.py`, wrap every `diagnostic_path` query in `bind_query(q, placement, world)` and every resolution in `bind(resolution, placement, broken)`. This is the only test change needed for Tasks 7–9.

- [ ] **Step 4: Run the conformance suite**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: all four identity faults conform across every placement. `OffboardedReactivation` yields exactly one placement (`h.reyes`); `ShareGroupRemoved` must clear via `ad.add_member` with invariants clean — note the baseline is captured *after* apply, so restoring the membership is not a violation.

- [ ] **Step 5: Commit**

```bash
git add src/vitsc/faults tests/test_catalog.py
git commit -m "feat(faults): add password expiry, offboarded reactivation, and share group faults"
```

---

### Task 8: Network faults

**Files:**
- Create: `src/vitsc/faults/catalog/network.py`
- Modify: `src/vitsc/faults/catalog/__init__.py`

**Interfaces:**
- Consumes: Task 4 and Task 7 base types including `bind`, `bind_query`.
- Produces: `StaticDnsMisconfig`, `NoDhcpLease`, registered.

The near-miss pair: both open with "the internet is down." `StaticDnsMisconfig` still pings by IP; `NoDhcpLease` has an APIPA address and pings nothing.

- [ ] **Step 1: Write the two faults**

`src/vitsc/faults/catalog/network.py`:

```python
from random import Random

from vitsc.env.base import Action, Query
from vitsc.faults.base import Placement, ResolutionPath, UserSymptoms
from vitsc.faults.registry import register
from vitsc.world.models import World


def _workstations(world: World) -> list[Placement]:
    return [
        Placement(kind="machine", key=m.hostname)
        for m in world.machines.values()
        if m.assigned_to is not None
    ]


class StaticDnsMisconfig:
    id = "net.static_dns_misconfig"
    domain = "network"
    difficulty = 2
    canonical_title = "Workstation pinned to a stale static DNS server"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["dns", "resolver", "name resolution", "static"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        world.machines[at.key].dns_servers = [f"10.20.10.{rng.choice([98, 99, 200])}"]

    def is_present(self, world: World, at: Placement) -> bool:
        machine = world.machines[at.key]
        return not set(machine.dns_servers) & set(world.network.dns_servers)

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="The internet's down on my machine and I can't get to any of our systems.",
            onset="Started after I restarted this morning.",
            scope="Only mine. Everyone else in the office is working.",
            error_text="Hmmm, we can't reach this page.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [
            Query(kind="net.ipconfig", target=at.key, args={"from": at.key}),
            Query(kind="net.ping", target="MER-FS-01", args={"from": at.key}),
        ]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(label="Point DNS back at the domain controller", actions=[
                Action(kind="machine.set_dns", target="{placement}",
                       args={"servers": "10.20.10.5"}),
            ]),
        ]


class NoDhcpLease:
    id = "net.no_dhcp_lease"
    domain = "network"
    difficulty = 2
    canonical_title = "Workstation failed to obtain a DHCP lease and fell back to APIPA"
    supported_backends = frozenset({"simulated", "winrm"})
    leak_terms = ["dhcp", "apipa", "lease", "169.254"]
    escalation_is_correct = False

    def placements(self, world: World) -> list[Placement]:
        return _workstations(world)

    def apply(self, world: World, at: Placement, rng: Random) -> None:
        machine = world.machines[at.key]
        machine.ip = None
        machine.dhcp_enabled = True

    def is_present(self, world: World, at: Placement) -> bool:
        return world.machines[at.key].ip is None

    def symptoms(self, world: World, at: Placement) -> UserSymptoms:
        return UserSymptoms(
            opening="Nothing loads at all on this computer, not even the intranet.",
            onset="Since I plugged it back in after the weekend.",
            scope="Just this one machine.",
            error_text="No internet, secured.",
        )

    def diagnostic_path(self, at: Placement) -> list[Query]:
        return [Query(kind="net.ipconfig", target=at.key, args={"from": at.key})]

    def canonical_resolutions(self) -> list[ResolutionPath]:
        return [
            ResolutionPath(label="Renew the DHCP lease", actions=[
                Action(kind="machine.renew_dhcp", target="{placement}"),
            ]),
        ]


register(StaticDnsMisconfig())
register(NoDhcpLease())
```

- [ ] **Step 2: Handle machine placements in `bind`**

`_workstations` yields `kind="machine"`, so `world.machine_for` is not the right lookup. Update `bind` and `bind_query` in `src/vitsc/faults/base.py`:

```python
def _machine_key(world: World, at: Placement) -> str:
    if at.kind == "machine":
        return at.key
    machine = world.machine_for(at.key)
    return machine.hostname if machine else ""
```

Use `_machine_key(world, at)` for the `{machine}` substitution in both functions.

- [ ] **Step 3: Register the module**

`src/vitsc/faults/catalog/__init__.py`:

```python
from vitsc.faults.catalog import identity, network  # noqa: F401

__all__ = ["identity", "network"]
```

- [ ] **Step 4: Run the conformance suite**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: six faults conform. Confirm `NoDhcpLease` renews to the machine's seeded IP — `_do_machine_renew_dhcp` must look the address up from `company.yaml`, not invent one, or `is_present` will stay true.

- [ ] **Step 5: Commit**

```bash
git add src/vitsc/faults tests/test_catalog.py
git commit -m "feat(faults): add DNS misconfiguration and DHCP lease faults"
```

---

### Task 9: Printing and endpoint faults

**Files:**
- Create: `src/vitsc/faults/catalog/printing.py`, `src/vitsc/faults/catalog/endpoint.py`
- Modify: `src/vitsc/faults/catalog/__init__.py`

**Interfaces:**
- Consumes: Task 4, 7, 8 base types.
- Produces: `SpoolerStopped`, `WrongDriver`, `DiskFull`, `FailingDisk`, registered. Completes the 10-fault v1 catalog.

- [ ] **Step 1: Write the printing faults**

`src/vitsc/faults/catalog/printing.py` — same shape as Task 8:

- **`SpoolerStopped`** (`print.spooler_stopped`, difficulty 1, not escalate-correct). `apply` sets `machine.services["Spooler"] = ServiceState.STOPPED`. `is_present` checks it is not `RUNNING`. Symptoms: *"Nothing comes out when I print. It doesn't even say anything, the job just disappears."* Leak terms: `["spooler", "service", "print queue"]`. Diagnostic path: `machine.services` on the workstation. Resolution: `machine.restart_service` with `args={"service": "Spooler"}`.

- **`WrongDriver`** (`print.wrong_driver`, difficulty 3, not escalate-correct). `apply` sets `machine.printer_drivers[printer] = "Generic / Text Only"`. `is_present` compares against `world.printers[name].correct_driver`. Symptoms: *"It prints but it's pages and pages of gibberish characters instead of my invoice."* Leak terms: `["driver", "pcl", "postscript", "generic"]`. Diagnostic path: `printer.state`. Resolution: `printer.reinstall_driver`. Placements: `(machine, printer)` pairs, keyed as `Placement(kind="printer", key=f"{hostname}/{printer}")` — split on `/` inside `apply`/`is_present`.

- [ ] **Step 2: Write the endpoint faults**

`src/vitsc/faults/catalog/endpoint.py`:

- **`DiskFull`** (`endpoint.disk_full`, difficulty 2, not escalate-correct). `apply` sets `disk_free_gb = rng.uniform(0.1, 0.8)` and `profile_state = ProfileState.TEMPORARY`. `is_present` is `disk_free_gb < 2.0`. Symptoms: *"Outlook won't open any more and my desktop looks completely different — none of my files are there."* Leak terms: `["disk", "full", "space", "profile", "temporary"]`. Diagnostic path: `machine.state`. Resolution: `machine.clear_disk` with `args={"gb": "40"}`.

  Note the symptom deliberately describes a *temporary profile*, not "my disk is full" — the surface complaint and the root cause differ, which is the point of the fault.

- **`FailingDisk`** (`endpoint.failing_disk`, difficulty 4, **escalate-correct**). `apply` sets `smart_status = SmartStatus.PRED_FAIL` and appends a `disk` warning to `event_log`. `is_present` is `smart_status is not SmartStatus.OK`. Symptoms: *"It's been freezing for a few seconds at a time and making a clicking noise. It happened twice during a call yesterday."* Leak terms: `["smart", "disk", "drive failure", "hardware", "replace"]`. Diagnostic path: `machine.state`, then `machine.eventlog`. `canonical_resolutions` returns an empty list.

- [ ] **Step 3: Let the harness accept escalate-only faults**

`FailingDisk` has no resolution, so the conformance test's resolution loop must not treat that as a failure. In `tests/test_catalog.py`, add before the loop:

```python
    if fault.escalation_is_correct and not fault.canonical_resolutions():
        return  # escalate-only faults have no technician fix by design
    assert fault.canonical_resolutions(), f"{fault.id} declares no resolution"
```

- [ ] **Step 4: Register both modules**

```python
from vitsc.faults.catalog import endpoint, identity, network, printing  # noqa: F401

__all__ = ["endpoint", "identity", "network", "printing"]
```

- [ ] **Step 5: Assert the catalog is complete**

Add to `tests/test_catalog.py`:

```python
def test_v1_catalog_is_complete():
    ids = {f.id for f in all_faults()}
    assert ids == {
        "ad.account_locked", "ad.password_expired", "ad.offboarded_reactivation",
        "share.group_membership_removed", "print.spooler_stopped", "print.wrong_driver",
        "net.static_dns_misconfig", "net.no_dhcp_lease",
        "endpoint.disk_full", "endpoint.failing_disk",
    }


def test_exactly_two_faults_are_escalate_correct():
    escalate = {f.id for f in all_faults() if f.escalation_is_correct}
    assert escalate == {"ad.offboarded_reactivation", "endpoint.failing_disk"}
```

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v`
Expected: all green. Ten faults, every placement conforming.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/faults tests/test_catalog.py
git commit -m "feat(faults): complete v1 catalog with printing and endpoint faults"
```

---

### Task 10: Persona protocol and the no-model fallback

**Files:**
- Create: `src/vitsc/persona/__init__.py`, `src/vitsc/persona/models.py`, `src/vitsc/persona/personas.py`, `src/vitsc/persona/templates.py`
- Test: `tests/test_persona_template.py`

**Interfaces:**
- Consumes: `UserSymptoms` (Task 4), `ADUser` (Task 1).
- Produces: `PersonaCard`, `ChatTurn`, `Persona` protocol, `card_for(user) -> PersonaCard`, `TemplatePersona`.

`TemplatePersona` is built before the LLM client on purpose: it is what the entire test suite uses, so nothing downstream can accidentally depend on a model being loaded (Global Constraints).

- [ ] **Step 1: Write the failing test**

`tests/test_persona_template.py`:

```python
from vitsc.faults.registry import get_fault
from vitsc.persona.models import ChatTurn
from vitsc.persona.personas import card_for
from vitsc.persona.templates import TemplatePersona
from vitsc.world.seed import load_world


def _symptoms():
    world = load_world()
    fault = get_fault("ad.account_locked")
    placement = fault.placements(world)[0]
    fault.apply(world, placement, __import__("random").Random(0))
    return world, placement, fault.symptoms(world, placement)


def test_card_is_derived_from_the_ad_user():
    world = load_world()
    card = card_for(world.org.users["m.alvarez"])
    assert card.name == "Maria Alvarez"
    assert card.role == "Accounting Clerk"
    assert 1 <= card.literacy <= 3


def test_initial_report_contains_the_opening_complaint():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    report = TemplatePersona().initial_report(card, symptoms)
    assert symptoms.opening in report
    assert symptoms.error_text in report


def test_reply_answers_from_symptoms_only():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    reply = TemplatePersona().reply(card, symptoms, [], "when did it last work?")
    assert symptoms.onset in reply


def test_reply_deflects_questions_it_cannot_answer():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    reply = TemplatePersona().reply(card, symptoms, [], "what is your DNS server set to?")
    assert "not sure" in reply.lower()


def test_history_is_accepted_but_does_not_crash():
    world, placement, symptoms = _symptoms()
    card = card_for(world.org.users[placement.key])
    history = [ChatTurn(speaker="tech", text="hello"), ChatTurn(speaker="user", text="hi")]
    assert TemplatePersona().reply(card, symptoms, history, "any error on screen?")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_persona_template.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.persona'`

- [ ] **Step 3: Write the models**

`src/vitsc/persona/models.py`:

```python
from typing import Literal, Protocol

from pydantic import BaseModel

from vitsc.faults.base import UserSymptoms


class PersonaCard(BaseModel):
    name: str
    role: str
    department: str
    literacy: int          # 1 = avoids all jargon, 3 = knows some terms
    mood: str              # "calm", "rushed", "frustrated"
    activity: str          # what they were doing when it broke


class ChatTurn(BaseModel):
    speaker: Literal["tech", "user"]
    text: str


class Persona(Protocol):
    def initial_report(self, card: PersonaCard, symptoms: UserSymptoms) -> str: ...
    def reply(
        self,
        card: PersonaCard,
        symptoms: UserSymptoms,
        history: list[ChatTurn],
        question: str,
    ) -> str: ...
```

- [ ] **Step 4: Write the card builder**

`src/vitsc/persona/personas.py`:

```python
import random

from vitsc.persona.models import PersonaCard
from vitsc.world.models import ADUser

LITERACY_BY_DEPARTMENT = {
    "Accounting": 1, "HR": 1, "Warehouse": 1,
    "Sales": 2, "Operations": 2,
}
MOODS = ["calm", "rushed", "frustrated"]
ACTIVITIES = [
    "trying to get a report out", "about to join a call",
    "starting the morning shift", "in the middle of a customer order",
]


def card_for(user: ADUser, rng: random.Random | None = None) -> PersonaCard:
    rng = rng or random.Random(user.sam)
    return PersonaCard(
        name=user.display_name,
        role=user.title,
        department=user.department,
        literacy=LITERACY_BY_DEPARTMENT.get(user.department, 2),
        mood=rng.choice(MOODS),
        activity=rng.choice(ACTIVITIES),
    )
```

- [ ] **Step 5: Write the template fallback**

`src/vitsc/persona/templates.py`. Keyword-matched answers drawn strictly from the symptom fields, with a deflection default:

```python
from vitsc.faults.base import UserSymptoms
from vitsc.persona.models import ChatTurn, PersonaCard

DEFLECTION = "I'm not sure, sorry — I don't really know the computer stuff."

ONSET_WORDS = {"when", "last", "start", "began", "since", "long"}
SCOPE_WORDS = {"anyone", "else", "others", "team", "only", "just you", "colleague"}
ERROR_WORDS = {"error", "message", "say", "screen", "shows", "text", "popup"}


class TemplatePersona:
    """Symptom-derived responses. Used whenever LM Studio is unavailable,
    and by every test in the suite."""

    def initial_report(self, card: PersonaCard, symptoms: UserSymptoms) -> str:
        lines = [symptoms.opening]
        if symptoms.error_text:
            lines.append(f'It says "{symptoms.error_text}".')
        if card.mood == "rushed":
            lines.append(f"I'm {card.activity} so I need this quickly.")
        return " ".join(lines)

    def reply(
        self,
        card: PersonaCard,
        symptoms: UserSymptoms,
        history: list[ChatTurn],
        question: str,
    ) -> str:
        q = question.lower()
        if any(w in q for w in ONSET_WORDS):
            return symptoms.onset
        if any(w in q for w in SCOPE_WORDS):
            return symptoms.scope
        if any(w in q for w in ERROR_WORDS):
            return f'It says "{symptoms.error_text}".' if symptoms.error_text else \
                   "No, there's no message, it just doesn't work."
        return DEFLECTION
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_persona_template.py -v`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/persona tests/test_persona_template.py
git commit -m "feat(persona): add persona protocol, cards, and template fallback"
```

---

### Task 11: LM Studio client and the leak filter

**Files:**
- Create: `src/vitsc/persona/prompts.py`, `src/vitsc/persona/client.py`
- Test: `tests/test_persona_client.py`

**Interfaces:**
- Consumes: `PersonaCard`, `ChatTurn`, `TemplatePersona` (Task 10); `UserSymptoms` (Task 4).
- Produces: `build_system_prompt(card, symptoms) -> str`, `scrub(text, leak_terms) -> str | None`, `LMStudioPersona(base_url, model, leak_terms, fallback)`.

Three leak-prevention layers per spec §7. Layer 1 (symptoms-only input) is already structural — `LMStudioPersona` is never handed a fault or a `World`. This task builds layers 2 and 3.

- [ ] **Step 1: Write the failing test**

`tests/test_persona_client.py`. The OpenAI client is stubbed throughout; no model is ever contacted.

```python
import pytest

from vitsc.faults.base import UserSymptoms
from vitsc.persona.client import LMStudioPersona, scrub
from vitsc.persona.models import PersonaCard
from vitsc.persona.prompts import build_system_prompt

CARD = PersonaCard(
    name="Maria Alvarez", role="Accounting Clerk", department="Accounting",
    literacy=1, mood="rushed", activity="trying to get a report out",
)
SYMPTOMS = UserSymptoms(
    opening="I can't sign in.", onset="Worked Friday.",
    scope="Just me.", error_text="The referenced account is currently disabled.",
)


class StubClient:
    """Mimics the surface of openai.OpenAI that LMStudioPersona uses."""

    def __init__(self, replies): self._replies = list(replies); self.calls = []

    @property
    def chat(self): return self

    @property
    def completions(self): return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self._replies.pop(0)
        return type("R", (), {"choices": [type("C", (), {
            "message": type("M", (), {"content": text})()
        })()]})()


def test_system_prompt_carries_symptoms_but_no_cause():
    prompt = build_system_prompt(CARD, SYMPTOMS)
    assert "Maria Alvarez" in prompt
    assert SYMPTOMS.opening in prompt
    assert "locked" not in prompt.lower()


def test_literacy_one_forbids_jargon_in_the_prompt():
    assert "do not use technical terms" in build_system_prompt(CARD, SYMPTOMS).lower()


def test_scrub_passes_clean_text():
    assert scrub("I can't get in.", ["locked", "unlock"]) == "I can't get in."


def test_scrub_rejects_leaking_text():
    assert scrub("My account is locked out.", ["locked"]) is None


def test_scrub_is_case_insensitive():
    assert scrub("ACCOUNT LOCKED", ["locked"]) is None


def test_client_retries_once_then_deflects():
    stub = StubClient(["my account is locked", "still locked I think"])
    persona = LMStudioPersona(client=stub, model="local", leak_terms=["locked"])
    reply = persona.reply(CARD, SYMPTOMS, [], "what happens when you try?")
    assert "locked" not in reply.lower()
    assert len(stub.calls) == 2


def test_client_accepts_a_clean_retry():
    stub = StubClient(["it says locked", "it just won't let me in"])
    persona = LMStudioPersona(client=stub, model="local", leak_terms=["locked"])
    assert persona.reply(CARD, SYMPTOMS, [], "what happens?") == "it just won't let me in"


def test_unreachable_model_falls_back_to_template():
    class Dead:
        @property
        def chat(self): return self
        @property
        def completions(self): return self
        def create(self, **kwargs): raise ConnectionError("refused")

    persona = LMStudioPersona(client=Dead(), model="local", leak_terms=["locked"])
    report = persona.initial_report(CARD, SYMPTOMS)
    assert SYMPTOMS.opening in report
    assert persona.degraded is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_persona_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.persona.prompts'`

- [ ] **Step 3: Write the prompt builder**

`src/vitsc/persona/prompts.py`:

```python
from vitsc.faults.base import UserSymptoms
from vitsc.persona.models import PersonaCard

LITERACY_RULES = {
    1: "You do not use technical terms at all. You describe what you see on screen "
       "in plain words. You do not know what DNS, a driver, or a server is.",
    2: "You use only everyday computer words like 'the internet', 'my drive', "
       "'the printer'. Do not use technical terms beyond that.",
    3: "You are moderately comfortable with computers but you are not in IT. "
       "Do not use technical terms you would not have heard at work.",
}

TEMPLATE = """You are {name}, a {role} in {department} at Meridian Freight.
You are NOT an IT technician. You are talking to the helpdesk about a problem.

You are feeling {mood}. When it happened you were {activity}.

{literacy}

This is everything you know about the problem. You know nothing beyond it:
- What you noticed: {opening}
- When it started: {onset}
- Who else is affected: {scope}
- Message on screen: {error_text}

Rules you must never break:
- Never guess or state a technical cause. You do not know why it is happening.
- If asked something outside the four facts above, say you do not know.
- Reply in one or two short sentences, the way a busy colleague would.
- Never mention that you are an AI or that this is a simulation.
"""


def build_system_prompt(card: PersonaCard, symptoms: UserSymptoms) -> str:
    return TEMPLATE.format(
        name=card.name, role=card.role, department=card.department,
        mood=card.mood, activity=card.activity,
        literacy=LITERACY_RULES[card.literacy],
        opening=symptoms.opening, onset=symptoms.onset, scope=symptoms.scope,
        error_text=symptoms.error_text or "(no message, it just does not work)",
    )
```

- [ ] **Step 4: Write the client**

`src/vitsc/persona/client.py`:

```python
from vitsc.faults.base import UserSymptoms
from vitsc.persona.models import ChatTurn, PersonaCard
from vitsc.persona.prompts import build_system_prompt
from vitsc.persona.templates import DEFLECTION, TemplatePersona

DEFAULT_BASE_URL = "http://localhost:1234/v1"
RETRY_NUDGE = (
    "That reply used a technical term you would not know. Say the same thing "
    "again in plain words, without naming any cause."
)


def scrub(text: str, leak_terms: list[str]) -> str | None:
    """Return the text if clean, or None if it leaks a forbidden term."""
    lowered = text.lower()
    return None if any(t.lower() in lowered for t in leak_terms) else text


def make_client(base_url: str = DEFAULT_BASE_URL):
    from openai import OpenAI
    return OpenAI(base_url=base_url, api_key="lm-studio")


class LMStudioPersona:
    def __init__(self, client, model: str, leak_terms: list[str], fallback=None) -> None:
        self._client = client
        self._model = model
        self._leak_terms = leak_terms
        self._fallback = fallback or TemplatePersona()
        self.degraded = False

    def initial_report(self, card: PersonaCard, symptoms: UserSymptoms) -> str:
        return self._ask(
            card, symptoms, [],
            "Write your first message to the helpdesk describing the problem.",
            lambda: self._fallback.initial_report(card, symptoms),
        )

    def reply(
        self, card: PersonaCard, symptoms: UserSymptoms,
        history: list[ChatTurn], question: str,
    ) -> str:
        return self._ask(
            card, symptoms, history, question,
            lambda: self._fallback.reply(card, symptoms, history, question),
        )

    def _ask(self, card, symptoms, history, user_text, fallback) -> str:
        messages = [{"role": "system", "content": build_system_prompt(card, symptoms)}]
        for turn in history:
            messages.append({
                "role": "user" if turn.speaker == "tech" else "assistant",
                "content": turn.text,
            })
        messages.append({"role": "user", "content": user_text})

        try:
            first = self._complete(messages)
        except Exception:
            self.degraded = True
            return fallback()

        clean = scrub(first, self._leak_terms)
        if clean is not None:
            return clean

        messages.extend([
            {"role": "assistant", "content": first},
            {"role": "user", "content": RETRY_NUDGE},
        ])
        try:
            second = self._complete(messages)
        except Exception:
            self.degraded = True
            return fallback()
        return scrub(second, self._leak_terms) or DEFLECTION

    def _complete(self, messages) -> str:
        response = self._client.chat.completions.create(
            model=self._model, messages=messages, temperature=0.7, max_tokens=120,
        )
        return response.choices[0].message.content.strip()
```

- [ ] **Step 5: Add the dependency**

```bash
uv add openai
```

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v`
Expected: all green, with LM Studio not running.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/persona tests/test_persona_client.py pyproject.toml uv.lock
git commit -m "feat(persona): add LM Studio client with leak filter and fallback"
```

---

### Task 12: Ticket model, priority, and SLA

**Files:**
- Create: `src/vitsc/session/__init__.py`, `src/vitsc/session/ticket.py`
- Test: `tests/test_ticket.py`

**Interfaces:**
- Consumes: `Placement`, `UserSymptoms` (Task 4); `PersonaCard`, `ChatTurn` (Task 10); `ToolCall` (Task 5); `Action` (Task 3).
- Produces: `Priority`, `TicketState`, `Disposition`, `Ticket`, `SLA_MINUTES`, `priority_for(fault, user) -> Priority`.

- [ ] **Step 1: Write the failing test**

`tests/test_ticket.py`:

```python
from datetime import datetime, timedelta

import pytest

from vitsc.faults.registry import get_fault
from vitsc.persona.personas import card_for
from vitsc.session.ticket import (
    SLA_MINUTES, Disposition, Priority, Ticket, TicketState, priority_for,
)
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)


def make_ticket(**overrides) -> Ticket:
    world = load_world()
    fault = get_fault("ad.account_locked")
    placement = fault.placements(world)[0]
    fault.apply(world, placement, __import__("random").Random(0))
    base = dict(
        id=1, fault_id=fault.id, placement=placement,
        persona=card_for(world.org.users[placement.key]),
        symptoms=fault.symptoms(world, placement),
        report_text="I can't sign in.",
        system_priority=Priority.P1, opened_at=NOW,
        sla_minutes=SLA_MINUTES[Priority.P1],
    )
    return Ticket(**{**base, **overrides})


def test_new_ticket_is_open_with_no_disposition():
    ticket = make_ticket()
    assert ticket.state is TicketState.OPEN
    assert ticket.disposition is None


def test_sla_deadline_is_derived_from_priority():
    ticket = make_ticket()
    assert ticket.deadline == NOW + timedelta(minutes=SLA_MINUTES[Priority.P1])


def test_ticket_is_overdue_past_its_deadline():
    ticket = make_ticket()
    assert ticket.is_overdue(NOW + timedelta(minutes=5)) is False
    assert ticket.is_overdue(NOW + timedelta(minutes=200)) is True


def test_closing_records_disposition_and_time():
    ticket = make_ticket()
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=12))
    assert ticket.state is TicketState.CLOSED
    assert ticket.disposition is Disposition.RESOLVED
    assert ticket.elapsed_minutes == pytest.approx(12.0)


def test_closing_twice_is_rejected():
    ticket = make_ticket()
    ticket.close(Disposition.RESOLVED, at=NOW)
    with pytest.raises(ValueError, match="already closed"):
        ticket.close(Disposition.ESCALATED, at=NOW)


def test_a_manager_outranks_a_clerk_for_the_same_fault():
    world = load_world()
    fault = get_fault("print.spooler_stopped")
    assert priority_for(fault, world.org.users["s.whitfield"]).value < \
           priority_for(fault, world.org.users["k.lindqvist"]).value


def test_cannot_sign_in_is_always_p1():
    world = load_world()
    assert priority_for(get_fault("ad.account_locked"),
                        world.org.users["k.lindqvist"]) is Priority.P1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ticket.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.session'`

- [ ] **Step 3: Write the implementation**

`src/vitsc/session/ticket.py`:

```python
from datetime import datetime, timedelta
from enum import Enum, IntEnum

from pydantic import BaseModel, Field

from vitsc.env.base import Action
from vitsc.faults.base import Fault, Placement, UserSymptoms
from vitsc.persona.models import ChatTurn, PersonaCard
from vitsc.tools.base import ToolCall
from vitsc.world.models import ADUser


class Priority(IntEnum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


SLA_MINUTES = {Priority.P1: 60, Priority.P2: 240, Priority.P3: 480, Priority.P4: 1440}

# Faults that stop a person working entirely are always top priority.
WORK_STOPPING = {"ad.account_locked", "ad.password_expired", "net.no_dhcp_lease"}
SENIOR_TITLES = {"Operations Manager", "Controller"}


class TicketState(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Disposition(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"


def priority_for(fault: Fault, user: ADUser) -> Priority:
    if fault.id in WORK_STOPPING:
        return Priority.P1
    if user.title in SENIOR_TITLES:
        return Priority.P2
    return Priority.P3 if fault.difficulty >= 2 else Priority.P4


class Ticket(BaseModel):
    id: int
    fault_id: str
    placement: Placement
    persona: PersonaCard
    symptoms: UserSymptoms
    report_text: str
    system_priority: Priority
    user_priority: Priority | None = None
    opened_at: datetime
    sla_minutes: int
    state: TicketState = TicketState.OPEN
    disposition: Disposition | None = None
    closed_at: datetime | None = None
    chat: list[ChatTurn] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)

    @property
    def deadline(self) -> datetime:
        return self.opened_at + timedelta(minutes=self.sla_minutes)

    @property
    def elapsed_minutes(self) -> float | None:
        if self.closed_at is None:
            return None
        return (self.closed_at - self.opened_at).total_seconds() / 60

    def is_overdue(self, now: datetime) -> bool:
        return now > self.deadline

    def close(self, disposition: Disposition, at: datetime) -> None:
        if self.state is TicketState.CLOSED:
            raise ValueError(f"ticket {self.id} is already closed")
        self.state = TicketState.CLOSED
        self.disposition = disposition
        self.closed_at = at
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ticket.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vitsc/session tests/test_ticket.py
git commit -m "feat(session): add ticket model, priority rules, and SLA"
```

---

### Task 13: Queue and scheduler

**Files:**
- Create: `src/vitsc/session/queue.py`
- Test: `tests/test_queue.py`

**Interfaces:**
- Consumes: everything from Tasks 3, 4, 10, 12.
- Produces: `SessionQueue(env, persona, rng, now)` with `open_ticket() -> Ticket | None`, `active() -> list[Ticket]`, `get(ticket_id) -> Ticket`, `tick(now) -> list[Ticket]`, and attributes `env`, `baseline`, `tickets`.

The scheduler is what makes faults *unfamiliar*: it picks a fault and a placement at random, applies it, snapshots the baseline afterwards, and hands back a ticket whose text came from the persona.

- [ ] **Step 1: Write the failing test**

`tests/test_queue.py`:

```python
from datetime import datetime, timedelta
from random import Random

import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import get_fault
from vitsc.persona.templates import TemplatePersona
from vitsc.session.queue import MAX_ACTIVE, SessionQueue
from vitsc.session.ticket import Disposition
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)


@pytest.fixture
def queue():
    return SessionQueue(
        env=SimulatedEnvironment(load_world()),
        persona=TemplatePersona(),
        rng=Random(1),
        now=NOW,
    )


def test_opening_a_ticket_applies_a_real_fault(queue):
    ticket = queue.open_ticket()
    fault = get_fault(ticket.fault_id)
    assert fault.is_present(queue.env.world, ticket.placement) is True


def test_ticket_text_comes_from_the_persona(queue):
    ticket = queue.open_ticket()
    assert ticket.symptoms.opening in ticket.report_text


def test_baseline_is_captured_after_the_fault_is_applied(queue):
    from vitsc.world.invariants import check_invariants
    queue.open_ticket()
    assert check_invariants(queue.env.world, queue.baseline) == []


def test_queue_stops_at_max_active(queue):
    for _ in range(MAX_ACTIVE + 3):
        queue.open_ticket()
    assert len(queue.active()) == MAX_ACTIVE


def test_closing_frees_a_slot(queue):
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    assert queue.open_ticket() is None
    queue.active()[0].close(Disposition.RESOLVED, at=NOW)
    assert queue.open_ticket() is not None


def test_no_duplicate_fault_and_placement_while_active(queue):
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    seen = {(t.fault_id, t.placement.key) for t in queue.active()}
    assert len(seen) == len(queue.active())


def test_tick_opens_a_ticket_once_the_interval_elapses(queue):
    queue.open_ticket()
    assert queue.tick(NOW + timedelta(minutes=1)) == []
    arrivals = queue.tick(NOW + timedelta(minutes=12))
    assert len(arrivals) == 1


def test_active_is_sorted_by_priority_then_age(queue):
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    priorities = [t.system_priority for t in queue.active()]
    assert priorities == sorted(priorities)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_queue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.session.queue'`

- [ ] **Step 3: Write the implementation**

`src/vitsc/session/queue.py`:

```python
from datetime import datetime, timedelta
from random import Random

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import all_faults
from vitsc.persona.models import Persona
from vitsc.persona.personas import card_for
from vitsc.session.ticket import (
    SLA_MINUTES, Ticket, TicketState, priority_for,
)
from vitsc.world.invariants import Baseline, capture_baseline

MAX_ACTIVE = 4
ARRIVAL_MINUTES = 10


class SessionQueue:
    def __init__(
        self,
        env: SimulatedEnvironment,
        persona: Persona,
        rng: Random,
        now: datetime,
    ) -> None:
        self.env = env
        self.persona = persona
        self.rng = rng
        self.tickets: list[Ticket] = []
        self.baseline: Baseline = capture_baseline(env.world)
        self._next_id = 1
        self._last_arrival = now

    def active(self) -> list[Ticket]:
        return sorted(
            (t for t in self.tickets if t.state is not TicketState.CLOSED),
            key=lambda t: (t.system_priority, t.opened_at),
        )

    def get(self, ticket_id: int) -> Ticket:
        return next(t for t in self.tickets if t.id == ticket_id)

    def open_ticket(self) -> Ticket | None:
        if len(self.active()) >= MAX_ACTIVE:
            return None

        taken = {(t.fault_id, t.placement.key) for t in self.active()}
        candidates = [
            (fault, placement)
            for fault in all_faults()
            for placement in fault.placements(self.env.world)
            if (fault.id, placement.key) not in taken
            and not fault.is_present(self.env.world, placement)
        ]
        if not candidates:
            return None

        fault, placement = self.rng.choice(candidates)
        fault.apply(self.env.world, placement, self.rng)

        # Baseline AFTER the fault, so repairing it is never collateral damage.
        self.baseline = capture_baseline(self.env.world)

        sam = placement.key if placement.kind == "user" else \
            self.env.world.machines[placement.key.split("/")[0]].assigned_to
        user = self.env.world.org.users[sam]
        card = card_for(user, self.rng)
        symptoms = fault.symptoms(self.env.world, placement)
        priority = priority_for(fault, user)

        ticket = Ticket(
            id=self._next_id,
            fault_id=fault.id,
            placement=placement,
            persona=card,
            symptoms=symptoms,
            report_text=self.persona.initial_report(card, symptoms),
            system_priority=priority,
            opened_at=self.env.world.clock,
            sla_minutes=SLA_MINUTES[priority],
        )
        self._next_id += 1
        self.tickets.append(ticket)
        return ticket

    def tick(self, now: datetime) -> list[Ticket]:
        """Open new tickets as the arrival interval elapses."""
        arrivals: list[Ticket] = []
        while now - self._last_arrival >= timedelta(minutes=ARRIVAL_MINUTES):
            self._last_arrival += timedelta(minutes=ARRIVAL_MINUTES)
            ticket = self.open_ticket()
            if ticket is None:
                break
            arrivals.append(ticket)
        return arrivals
```

Note the `sam` lookup handles `Placement(kind="printer", key="MER-WS-001/PRT-ACC-01")` from Task 9 by splitting on `/`. Machine placements resolve through `assigned_to`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_queue.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vitsc/session/queue.py tests/test_queue.py
git commit -m "feat(session): add fault scheduler and ticket queue"
```

---

### Task 14: Grading and the after-action report

**Files:**
- Create: `src/vitsc/session/grading.py`, `src/vitsc/session/afteraction.py`
- Test: `tests/test_grading.py`

**Interfaces:**
- Consumes: `Ticket`, `Disposition`, `Priority` (Task 12); `check_invariants`, `Baseline` (Task 2); `Fault` (Task 4); `ToolCall` (Task 5).
- Produces: `Grade`, `grade_ticket(ticket, fault, env, baseline) -> Grade`; `AfterAction`, `build_after_action(ticket, fault, grade, world) -> AfterAction`.

This is the payload of the whole exercise (spec §8). The report, not the score, is why the drill transfers.

- [ ] **Step 1: Write the failing test**

`tests/test_grading.py`:

```python
from datetime import datetime, timedelta
from random import Random

import pytest

from vitsc.env.base import Action, Query
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import get_fault
from vitsc.persona.models import ChatTurn
from vitsc.persona.personas import card_for
from vitsc.session.afteraction import build_after_action
from vitsc.session.grading import grade_ticket
from vitsc.session.ticket import Disposition, Priority, SLA_MINUTES, Ticket
from vitsc.tools.ad import ADConsole
from vitsc.tools.base import ToolLog
from vitsc.world.invariants import capture_baseline
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)


def setup(fault_id="ad.account_locked"):
    world = load_world()
    fault = get_fault(fault_id)
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    env = SimulatedEnvironment(world)
    baseline = capture_baseline(world)
    user = world.org.users[placement.key]
    ticket = Ticket(
        id=1, fault_id=fault.id, placement=placement, persona=card_for(user),
        symptoms=fault.symptoms(world, placement), report_text="can't log in",
        system_priority=Priority.P1, opened_at=NOW, sla_minutes=SLA_MINUTES[Priority.P1],
    )
    return world, fault, placement, env, baseline, ticket


def test_correct_fix_within_sla_grades_clean():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "get-user", {"sam": placement.key})
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=9))

    grade = grade_ticket(ticket, fault, env, baseline)
    assert grade.correct is True
    assert grade.within_sla is True
    assert grade.collateral == []


def test_unfixed_ticket_is_incorrect():
    world, fault, placement, env, baseline, ticket = setup()
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=3))
    assert grade_ticket(ticket, fault, env, baseline).correct is False


def test_collateral_damage_is_reported():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    env.execute(Action(kind="ad.disable", target="d.okafor"))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))

    grade = grade_ticket(ticket, fault, env, baseline)
    assert grade.correct is False
    assert any("d.okafor" in c for c in grade.collateral)


def test_escalating_a_fixable_ticket_is_wrong():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).disposition_correct is False


def test_escalating_an_escalate_only_ticket_is_right():
    world, fault, placement, env, baseline, ticket = setup("endpoint.failing_disk")
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    assert grade.disposition_correct is True
    assert grade.correct is True


def test_fixing_an_escalate_only_ticket_is_wrong():
    world, fault, placement, env, baseline, ticket = setup("endpoint.failing_disk")
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).correct is False


def test_breaching_sla_is_recorded():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=180))
    assert grade_ticket(ticket, fault, env, baseline).within_sla is False


def test_touching_before_asking_is_detected():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.chat = []
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=2))
    assert grade_ticket(ticket, fault, env, baseline).questions_before_first_mutation == 0


def test_triage_accuracy_compares_user_priority():
    world, fault, placement, env, baseline, ticket = setup()
    ticket.user_priority = Priority.P3
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).triage_correct is False


def test_after_action_names_the_root_cause_and_shortest_path():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "get-user", {"sam": "d.okafor"})   # wasted
    ADConsole().invoke(env, log, "get-user", {"sam": placement.key})
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=6))

    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert report.root_cause == fault.canonical_title
    assert report.shortest_path
    assert report.tool_calls_made == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_grading.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.session.grading'`

- [ ] **Step 3: Write grading**

`src/vitsc/session/grading.py`:

```python
from pydantic import BaseModel, Field

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.base import Fault
from vitsc.session.ticket import Disposition, Ticket
from vitsc.world.invariants import Baseline, check_invariants


class Grade(BaseModel):
    correct: bool
    fault_cleared: bool
    disposition_correct: bool
    collateral: list[str] = Field(default_factory=list)
    elapsed_minutes: float
    sla_minutes: int
    within_sla: bool
    tool_calls_made: int
    tool_calls_minimum: int
    questions_before_first_mutation: int
    triage_correct: bool


def grade_ticket(
    ticket: Ticket, fault: Fault, env: SimulatedEnvironment, baseline: Baseline
) -> Grade:
    cleared = not fault.is_present(env.world, ticket.placement)
    collateral = check_invariants(env.world, baseline)

    if fault.escalation_is_correct:
        disposition_correct = ticket.disposition is Disposition.ESCALATED
    else:
        disposition_correct = ticket.disposition is Disposition.RESOLVED and cleared

    # An escalate-only fault is correct when escalated, whether or not it is cleared.
    correct = disposition_correct and not collateral
    if not fault.escalation_is_correct:
        correct = correct and cleared

    elapsed = ticket.elapsed_minutes or 0.0
    first_mutation = next(
        (i for i, c in enumerate(ticket.tool_calls) if c.mutating), len(ticket.tool_calls)
    )
    questions_before = sum(1 for turn in ticket.chat if turn.speaker == "tech") \
        if first_mutation > 0 else 0

    return Grade(
        correct=correct,
        fault_cleared=cleared,
        disposition_correct=disposition_correct,
        collateral=collateral,
        elapsed_minutes=elapsed,
        sla_minutes=ticket.sla_minutes,
        within_sla=elapsed <= ticket.sla_minutes,
        tool_calls_made=len(ticket.tool_calls),
        tool_calls_minimum=len(fault.diagnostic_path(ticket.placement)),
        questions_before_first_mutation=questions_before,
        triage_correct=ticket.user_priority is None
        or ticket.user_priority == ticket.system_priority,
    )
```

- [ ] **Step 4: Write the after-action report**

`src/vitsc/session/afteraction.py`:

```python
from pydantic import BaseModel, Field

from vitsc.faults.base import Fault, bind_query
from vitsc.session.grading import Grade
from vitsc.session.ticket import Ticket
from vitsc.world.models import World


class AfterAction(BaseModel):
    root_cause: str
    shortest_path: list[str] = Field(default_factory=list)
    tool_calls_made: int
    tool_calls_minimum: int
    wasted_calls: list[str] = Field(default_factory=list)
    touched_before_asking: bool
    collateral: list[str] = Field(default_factory=list)
    within_sla: bool
    verdict: str


def build_after_action(
    ticket: Ticket, fault: Fault, grade: Grade, world: World
) -> AfterAction:
    path = [
        f"{q.kind} {q.target}".strip()
        for q in (bind_query(q, ticket.placement, world)
                  for q in fault.diagnostic_path(ticket.placement))
    ]
    useful = {p.split()[-1] for p in path}
    wasted = [
        f"{c.tool} {c.command} {' '.join(c.args.values())}".strip()
        for c in ticket.tool_calls
        if not c.mutating and not (set(c.args.values()) & useful)
    ]

    if grade.correct:
        verdict = "Resolved correctly."
    elif not grade.disposition_correct and fault.escalation_is_correct:
        verdict = "This one was not yours to fix — it needed escalation."
    elif not grade.disposition_correct:
        verdict = "You escalated something you had the tools and authority to fix."
    elif grade.collateral:
        verdict = "The symptom cleared, but you broke something else doing it."
    else:
        verdict = "The underlying fault was still present when you closed the ticket."

    return AfterAction(
        root_cause=fault.canonical_title,
        shortest_path=path,
        tool_calls_made=grade.tool_calls_made,
        tool_calls_minimum=grade.tool_calls_minimum,
        wasted_calls=wasted,
        touched_before_asking=grade.questions_before_first_mutation == 0,
        collateral=grade.collateral,
        within_sla=grade.within_sla,
        verdict=verdict,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_grading.py -v`
Expected: 10 passed.

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/session tests/test_grading.py
git commit -m "feat(session): add grading rules and after-action report"
```

---

### Task 15: SQLite session store

**Files:**
- Create: `src/vitsc/session/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `Ticket` (Task 12), `Grade` (Task 14), `AfterAction` (Task 14).
- Produces: `Store(path)` with `init()`, `save_closed(ticket, grade, report)`, `history(limit) -> list[ClosedRecord]`, `domain_stats() -> dict[str, DomainStat]`; models `ClosedRecord`, `DomainStat`.

Only *closed* tickets persist. Live session state stays in memory — resuming a half-worked queue is Phase 4, and building it now would mean serialising a whole `World` per request.

- [ ] **Step 1: Write the failing test**

`tests/test_store.py`:

```python
from datetime import datetime, timedelta
from random import Random

import pytest

from vitsc.env.base import Action
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import get_fault
from vitsc.persona.personas import card_for
from vitsc.session.afteraction import build_after_action
from vitsc.session.grading import grade_ticket
from vitsc.session.store import Store
from vitsc.session.ticket import Disposition, Priority, SLA_MINUTES, Ticket
from vitsc.world.invariants import capture_baseline
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)


def closed_ticket(fault_id="ad.account_locked", fix=True, ticket_id=1):
    world = load_world()
    fault = get_fault(fault_id)
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    env = SimulatedEnvironment(world)
    baseline = capture_baseline(world)
    if fix:
        env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket = Ticket(
        id=ticket_id, fault_id=fault.id, placement=placement,
        persona=card_for(world.org.users[placement.key]),
        symptoms=fault.symptoms(world, placement), report_text="can't log in",
        system_priority=Priority.P1, opened_at=NOW, sla_minutes=SLA_MINUTES[Priority.P1],
    )
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=7))
    grade = grade_ticket(ticket, fault, env, baseline)
    return ticket, grade, build_after_action(ticket, fault, grade, env.world)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "vitsc.sqlite3")
    s.init()
    return s


def test_init_is_idempotent(tmp_path):
    s = Store(tmp_path / "x.sqlite3")
    s.init()
    s.init()
    assert s.history() == []


def test_saved_ticket_appears_in_history(store):
    store.save_closed(*closed_ticket())
    records = store.history()
    assert len(records) == 1
    assert records[0].fault_id == "ad.account_locked"
    assert records[0].correct is True


def test_history_is_newest_first(store):
    store.save_closed(*closed_ticket(ticket_id=1))
    store.save_closed(*closed_ticket(ticket_id=2))
    assert [r.ticket_id for r in store.history()] == [2, 1]


def test_history_respects_limit(store):
    for i in range(1, 6):
        store.save_closed(*closed_ticket(ticket_id=i))
    assert len(store.history(limit=3)) == 3


def test_domain_stats_aggregate_by_fault_domain(store):
    store.save_closed(*closed_ticket(ticket_id=1, fix=True))
    store.save_closed(*closed_ticket(ticket_id=2, fix=False))
    stats = store.domain_stats()
    assert stats["identity"].total == 2
    assert stats["identity"].correct == 1


def test_after_action_round_trips(store):
    store.save_closed(*closed_ticket())
    assert "locked out" in store.history()[0].root_cause
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.session.store'`

- [ ] **Step 3: Write the implementation**

`src/vitsc/session/store.py`:

```python
import sqlite3
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from vitsc.faults.registry import get_fault
from vitsc.session.afteraction import AfterAction
from vitsc.session.grading import Grade
from vitsc.session.ticket import Ticket

SCHEMA = """
CREATE TABLE IF NOT EXISTS closed_tickets (
    ticket_id        INTEGER NOT NULL,
    fault_id         TEXT    NOT NULL,
    domain           TEXT    NOT NULL,
    placement_key    TEXT    NOT NULL,
    disposition      TEXT    NOT NULL,
    correct          INTEGER NOT NULL,
    within_sla       INTEGER NOT NULL,
    elapsed_minutes  REAL    NOT NULL,
    tool_calls_made  INTEGER NOT NULL,
    tool_calls_min   INTEGER NOT NULL,
    collateral_count INTEGER NOT NULL,
    root_cause       TEXT    NOT NULL,
    verdict          TEXT    NOT NULL,
    closed_at        TEXT    NOT NULL,
    rowid_key        INTEGER PRIMARY KEY AUTOINCREMENT
);
"""


class ClosedRecord(BaseModel):
    ticket_id: int
    fault_id: str
    domain: str
    disposition: str
    correct: bool
    within_sla: bool
    elapsed_minutes: float
    tool_calls_made: int
    tool_calls_min: int
    collateral_count: int
    root_cause: str
    verdict: str
    closed_at: datetime


class DomainStat(BaseModel):
    domain: str
    total: int
    correct: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


class Store:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def save_closed(self, ticket: Ticket, grade: Grade, report: AfterAction) -> None:
        domain = get_fault(ticket.fault_id).domain
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO closed_tickets (
                    ticket_id, fault_id, domain, placement_key, disposition, correct,
                    within_sla, elapsed_minutes, tool_calls_made, tool_calls_min,
                    collateral_count, root_cause, verdict, closed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ticket.id, ticket.fault_id, domain, ticket.placement.key,
                    ticket.disposition.value, int(grade.correct), int(grade.within_sla),
                    grade.elapsed_minutes, grade.tool_calls_made, grade.tool_calls_minimum,
                    len(grade.collateral), report.root_cause, report.verdict,
                    ticket.closed_at.isoformat(),
                ),
            )

    def history(self, limit: int = 50) -> list[ClosedRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM closed_tickets ORDER BY rowid_key DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            ClosedRecord(
                ticket_id=r["ticket_id"], fault_id=r["fault_id"], domain=r["domain"],
                disposition=r["disposition"], correct=bool(r["correct"]),
                within_sla=bool(r["within_sla"]), elapsed_minutes=r["elapsed_minutes"],
                tool_calls_made=r["tool_calls_made"], tool_calls_min=r["tool_calls_min"],
                collateral_count=r["collateral_count"], root_cause=r["root_cause"],
                verdict=r["verdict"], closed_at=datetime.fromisoformat(r["closed_at"]),
            )
            for r in rows
        ]

    def domain_stats(self) -> dict[str, DomainStat]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT domain, COUNT(*) AS total, SUM(correct) AS correct "
                "FROM closed_tickets GROUP BY domain"
            ).fetchall()
        return {
            r["domain"]: DomainStat(
                domain=r["domain"], total=r["total"], correct=r["correct"] or 0
            )
            for r in rows
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_store.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vitsc/session/store.py tests/test_store.py
git commit -m "feat(session): persist closed tickets and domain stats to SQLite"
```

---

### Task 16: Web app skeleton — queue and ticket detail

**Files:**
- Create: `src/vitsc/web/__init__.py`, `src/vitsc/web/app.py`, `src/vitsc/web/deps.py`
- Create: `src/vitsc/web/routes/__init__.py`, `src/vitsc/web/routes/queue.py`
- Create: `src/vitsc/web/templates/base.html`, `layout.html`, `_queue.html`, `_ticket.html`, `index.html`
- Create: `src/vitsc/web/static/app.css`
- Test: `tests/test_web_queue.py`

**Interfaces:**
- Consumes: `SessionQueue` (Task 13), `SimulatedEnvironment` (Task 3), `TemplatePersona` (Task 10), `Store` (Task 15).
- Produces: `create_app(session: AppSession) -> FastAPI`, `AppSession` holding `queue`, `env`, `log`, `store`, `persona`; routes `GET /`, `GET /queue`, `GET /ticket/{id}`, `POST /ticket/{id}/priority`.

`AppSession` is a single in-process object, not a per-request session — there is exactly one player.

- [ ] **Step 1: Add dependencies**

```bash
uv add fastapi "uvicorn[standard]" jinja2 python-multipart
uv add --dev httpx
```

- [ ] **Step 2: Write the failing test**

`tests/test_web_queue.py`:

```python
import pytest
from fastapi.testclient import TestClient

from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.fixture
def client(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    session.queue.open_ticket()
    return TestClient(create_app(session)), session


def test_index_renders_the_queue(client):
    c, session = client
    body = c.get("/").text
    assert "Meridian Freight" in body
    assert str(session.queue.active()[0].id) in body


def test_queue_partial_lists_active_tickets(client):
    c, session = client
    session.queue.open_ticket()
    body = c.get("/queue").text
    assert body.count('class="ticket-row"') == len(session.queue.active())


def test_ticket_detail_shows_the_report_but_not_the_fault(client):
    c, session = client
    ticket = session.queue.active()[0]
    body = c.get(f"/ticket/{ticket.id}").text
    assert ticket.report_text in body
    assert ticket.fault_id not in body
    assert ticket.persona.name in body


def test_ticket_detail_404s_for_unknown_id(client):
    c, _ = client
    assert c.get("/ticket/999").status_code == 404


def test_setting_priority_records_user_triage(client):
    c, session = client
    ticket = session.queue.active()[0]
    c.post(f"/ticket/{ticket.id}/priority", data={"priority": "3"})
    assert session.queue.get(ticket.id).user_priority.value == 3


def test_no_template_leaks_the_canonical_title(client):
    c, session = client
    from vitsc.faults.registry import get_fault
    ticket = session.queue.active()[0]
    title = get_fault(ticket.fault_id).canonical_title
    assert title not in c.get(f"/ticket/{ticket.id}").text
```

The last test is the important one — the whole drill collapses if any template renders the answer.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_web_queue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.web'`

- [ ] **Step 4: Write the session container**

`src/vitsc/web/deps.py`:

```python
from datetime import datetime
from pathlib import Path
from random import Random

from pydantic import BaseModel, ConfigDict

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.persona.templates import TemplatePersona
from vitsc.session.queue import SessionQueue
from vitsc.session.store import Store
from vitsc.tools.base import ToolLog
from vitsc.world.seed import load_world


class AppSession(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    env: SimulatedEnvironment
    queue: SessionQueue
    store: Store
    logs: dict[int, ToolLog] = {}
    started_at: datetime

    @classmethod
    def build(
        cls, db_path: Path, seed: int = 0, persona=None, now: datetime | None = None
    ) -> "AppSession":
        env = SimulatedEnvironment(load_world())
        now = now or env.world.clock
        store = Store(db_path)
        store.init()
        return cls(
            env=env,
            queue=SessionQueue(
                env=env, persona=persona or TemplatePersona(), rng=Random(seed), now=now
            ),
            store=store,
            started_at=now,
        )

    def log_for(self, ticket_id: int) -> ToolLog:
        return self.logs.setdefault(ticket_id, ToolLog())
```

- [ ] **Step 5: Write the app factory and queue routes**

`src/vitsc/web/app.py`:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from vitsc.web.deps import AppSession

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=HERE / "templates")


def create_app(session: AppSession) -> FastAPI:
    app = FastAPI(title="Virtual IT Support Center")
    app.state.session = session
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    from vitsc.web.routes import queue as queue_routes
    app.include_router(queue_routes.router)
    return app
```

`src/vitsc/web/routes/queue.py`:

```python
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from vitsc.session.ticket import Priority

router = APIRouter()


def _session(request: Request):
    return request.app.state.session


def _ticket_or_404(request: Request, ticket_id: int):
    try:
        return _session(request).queue.get(ticket_id)
    except StopIteration:
        raise HTTPException(status_code=404, detail="No such ticket") from None


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    from vitsc.web.app import templates
    session = _session(request)
    return templates.TemplateResponse(
        request, "index.html",
        {"tickets": session.queue.active(), "now": session.env.world.clock},
    )


@router.get("/queue", response_class=HTMLResponse)
def queue_partial(request: Request):
    from vitsc.web.app import templates
    session = _session(request)
    return templates.TemplateResponse(
        request, "_queue.html",
        {"tickets": session.queue.active(), "now": session.env.world.clock},
    )


@router.get("/ticket/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: int):
    from vitsc.web.app import templates
    ticket = _ticket_or_404(request, ticket_id)
    return templates.TemplateResponse(
        request, "_ticket.html",
        {"ticket": ticket, "priorities": list(Priority)},
    )


@router.post("/ticket/{ticket_id}/priority", response_class=HTMLResponse)
def set_priority(request: Request, ticket_id: int, priority: int = Form(...)):
    from vitsc.web.app import templates
    ticket = _ticket_or_404(request, ticket_id)
    ticket.user_priority = Priority(priority)
    return templates.TemplateResponse(
        request, "_ticket.html",
        {"ticket": ticket, "priorities": list(Priority)},
    )
```

- [ ] **Step 6: Write the templates**

`base.html` loads HTMX from a vendored copy in `static/` (no CDN, no build step — download `htmx.min.js` once into `src/vitsc/web/static/`).

`_queue.html` — one `<div class="ticket-row">` per ticket, showing id, priority badge, persona name, a truncated opening line, and remaining SLA. Each row is `hx-get="/ticket/{{ t.id }}" hx-target="#detail"`.

`_ticket.html` — persona name, role, department, `ticket.report_text`, the priority select posting to `/ticket/{id}/priority`, and empty placeholder divs `#tools`, `#chat`, `#close` filled in by Tasks 17–18.

**Never render `ticket.fault_id`, `fault.canonical_title`, or `ticket.symptoms` directly** — only `report_text` and chat turns, which are persona-mediated. Add a comment saying so at the top of `_ticket.html`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_web_queue.py -v`
Expected: 6 passed.

- [ ] **Step 8: Look at it**

```bash
uv run uvicorn --factory "vitsc.web.app:create_app" --reload
```

Add a `src/vitsc/__main__.py` that builds an `AppSession` with a real `LMStudioPersona` (falling back automatically) and runs uvicorn, so `uv run python -m vitsc` is the normal way in.

- [ ] **Step 9: Commit**

```bash
git add src/vitsc/web tests/test_web_queue.py pyproject.toml uv.lock
git commit -m "feat(web): add app skeleton with queue and ticket detail"
```

---

### Task 17: Tool panes and the chat route

**Files:**
- Create: `src/vitsc/web/routes/tools.py`, `src/vitsc/web/routes/chat.py`
- Create: `src/vitsc/web/templates/_tools.html`, `_toolout.html`, `_chat.html`
- Modify: `src/vitsc/web/app.py`, `src/vitsc/web/templates/_ticket.html`
- Test: `tests/test_web_tools.py`

**Interfaces:**
- Consumes: `get_tool`, `all_tools` (Tasks 5–6); `AppSession.log_for` (Task 16); `Persona` (Task 10).
- Produces: routes `GET /ticket/{id}/tools`, `POST /ticket/{id}/tool`, `POST /ticket/{id}/chat`.

- [ ] **Step 1: Write the failing test**

`tests/test_web_tools.py`:

```python
import pytest
from fastapi.testclient import TestClient

from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.fixture
def client(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    session.queue.open_ticket()
    return TestClient(create_app(session)), session


def test_tool_pane_lists_every_tool(client):
    c, session = client
    ticket = session.queue.active()[0]
    body = c.get(f"/ticket/{ticket.id}/tools").text
    for name in ("ad", "net", "remote", "events", "print", "ps"):
        assert f'value="{name}"' in body


def test_running_a_tool_renders_its_output(client):
    c, session = client
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/tool",
               data={"tool": "ad", "command": "get-user", "args": "sam=m.alvarez"})
    assert r.status_code == 200
    assert "SamAccountName" in r.text


def test_tool_calls_are_recorded_on_the_ticket(client):
    c, session = client
    ticket = session.queue.active()[0]
    c.post(f"/ticket/{ticket.id}/tool",
           data={"tool": "ad", "command": "get-user", "args": "sam=m.alvarez"})
    assert len(session.queue.get(ticket.id).tool_calls) == 1


def test_unknown_tool_is_rejected_without_crashing(client):
    c, session = client
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/tool",
               data={"tool": "nope", "command": "x", "args": ""})
    assert r.status_code == 200
    assert "not recognized" in r.text.lower()


def test_malformed_args_do_not_500(client):
    c, session = client
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/tool",
               data={"tool": "ad", "command": "get-user", "args": "garbage-no-equals"})
    assert r.status_code == 200


def test_chat_appends_both_turns(client):
    c, session = client
    ticket = session.queue.active()[0]
    c.post(f"/ticket/{ticket.id}/chat", data={"message": "when did it last work?"})
    chat = session.queue.get(ticket.id).chat
    assert [t.speaker for t in chat] == ["tech", "user"]
    assert chat[1].text == ticket.symptoms.onset


def test_chat_reply_never_contains_a_leak_term(client):
    c, session = client
    from vitsc.faults.registry import get_fault
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/chat", data={"message": "what is wrong exactly?"})
    for term in get_fault(ticket.fault_id).leak_terms:
        assert term.lower() not in r.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_web_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.web.routes.tools'`

- [ ] **Step 3: Write the tool route**

`src/vitsc/web/routes/tools.py`:

```python
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from vitsc.tools.base import UNKNOWN, ToolCall
from vitsc.tools.registry import all_tools, get_tool
from vitsc.web.routes.queue import _session, _ticket_or_404

router = APIRouter()


def parse_args(raw: str) -> dict[str, str]:
    """'sam=m.alvarez host=MER-WS-001' -> dict. Malformed pairs are dropped."""
    out: dict[str, str] = {}
    for chunk in raw.split():
        if "=" in chunk:
            key, _, value = chunk.partition("=")
            out[key.strip()] = value.strip()
    return out


@router.get("/ticket/{ticket_id}/tools", response_class=HTMLResponse)
def tool_pane(request: Request, ticket_id: int):
    from vitsc.web.app import templates
    ticket = _ticket_or_404(request, ticket_id)
    return templates.TemplateResponse(
        request, "_tools.html", {"ticket": ticket, "tools": all_tools()},
    )


@router.post("/ticket/{ticket_id}/tool", response_class=HTMLResponse)
def run_tool(
    request: Request,
    ticket_id: int,
    tool: str = Form(...),
    command: str = Form(...),
    args: str = Form(""),
):
    from vitsc.web.app import templates
    session = _session(request)
    ticket = _ticket_or_404(request, ticket_id)
    log = session.log_for(ticket_id)

    try:
        implementation = get_tool(tool)
    except KeyError:
        call = ToolCall(
            tool=tool, command=command, args={}, ok=False, mutating=False,
            rendered=UNKNOWN.format(cmd=tool),
        )
    else:
        call = implementation.invoke(session.env, log, command, parse_args(args))

    ticket.tool_calls = list(log.calls)
    return templates.TemplateResponse(request, "_toolout.html", {"calls": log.calls})
```

- [ ] **Step 4: Write the chat route**

`src/vitsc/web/routes/chat.py`:

```python
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from vitsc.persona.models import ChatTurn
from vitsc.web.routes.queue import _session, _ticket_or_404

router = APIRouter()


@router.post("/ticket/{ticket_id}/chat", response_class=HTMLResponse)
def send_message(request: Request, ticket_id: int, message: str = Form(...)):
    from vitsc.web.app import templates
    session = _session(request)
    ticket = _ticket_or_404(request, ticket_id)

    ticket.chat.append(ChatTurn(speaker="tech", text=message))
    reply = session.queue.persona.reply(
        ticket.persona, ticket.symptoms, ticket.chat[:-1], message
    )
    ticket.chat.append(ChatTurn(speaker="user", text=reply))

    return templates.TemplateResponse(request, "_chat.html", {"ticket": ticket})
```

The persona receives `ticket.symptoms` and nothing else — no fault, no world. That is Global Constraint layer 1, enforced here at the only call site.

- [ ] **Step 5: Write the templates and register the routers**

- `_tools.html` — a `<select name="tool">` with one `<option value="{{ t.name }}">` per tool, a command `<select>` populated from `t.commands()`, a free-text `args` input, all posting `hx-post="/ticket/{{ ticket.id }}/tool" hx-target="#toolout"`.
- `_toolout.html` — a `<pre>` per call, newest last, showing `{tool} {command} {args}` then `call.rendered`.
- `_chat.html` — the turn list plus an input posting `hx-post="/ticket/{{ ticket.id }}/chat" hx-target="#chat" hx-swap="outerHTML"`.

Include both routers in `create_app`, and replace the `#tools` / `#chat` placeholders in `_ticket.html` with `hx-get="/ticket/{{ ticket.id }}/tools" hx-trigger="load"` and the chat partial.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_web_tools.py -v`
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/web tests/test_web_tools.py
git commit -m "feat(web): add tool panes and user chat"
```

---

### Task 18: Close, escalate, after-action, and SSE clocks

**Files:**
- Create: `src/vitsc/web/routes/close.py`, `src/vitsc/web/routes/events.py`
- Create: `src/vitsc/web/templates/_afteraction.html`, `history.html`
- Modify: `src/vitsc/web/app.py`, `src/vitsc/web/templates/_ticket.html`, `base.html`
- Test: `tests/test_web_close.py`

**Interfaces:**
- Consumes: `grade_ticket`, `build_after_action` (Task 14); `Store` (Task 15).
- Produces: routes `POST /ticket/{id}/close`, `GET /history`, `GET /events` (SSE).

- [ ] **Step 1: Write the failing test**

`tests/test_web_close.py`:

```python
import pytest
from fastapi.testclient import TestClient

from vitsc.faults.registry import get_fault
from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.fixture
def client(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    session.queue.open_ticket()
    return TestClient(create_app(session)), session


def solve(session, ticket):
    """Apply the fault's canonical resolution directly through the environment."""
    from vitsc.faults.base import bind
    fault = get_fault(ticket.fault_id)
    for resolution in fault.canonical_resolutions()[:1]:
        for action in bind(resolution, ticket.placement, session.env.world).actions:
            session.env.execute(action)


def test_closing_a_solved_ticket_reports_success(client):
    c, session = client
    ticket = session.queue.active()[0]
    solve(session, ticket)
    body = c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"}).text
    assert "Resolved correctly" in body


def test_after_action_reveals_the_root_cause_only_after_closing(client):
    c, session = client
    ticket = session.queue.active()[0]
    title = get_fault(ticket.fault_id).canonical_title
    assert title not in c.get(f"/ticket/{ticket.id}").text
    solve(session, ticket)
    assert title in c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"}).text


def test_closing_an_unsolved_ticket_says_so(client):
    c, session = client
    ticket = session.queue.active()[0]
    body = c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"}).text
    assert "still present" in body


def test_closed_ticket_leaves_the_active_queue(client):
    c, session = client
    ticket = session.queue.active()[0]
    solve(session, ticket)
    c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
    assert ticket.id not in [t.id for t in session.queue.active()]


def test_closing_persists_to_the_store(client):
    c, session = client
    ticket = session.queue.active()[0]
    solve(session, ticket)
    c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
    assert len(session.store.history()) == 1


def test_double_close_returns_409(client):
    c, session = client
    ticket = session.queue.active()[0]
    solve(session, ticket)
    c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
    r = c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
    assert r.status_code == 409


def test_history_page_lists_closed_tickets(client):
    c, session = client
    ticket = session.queue.active()[0]
    solve(session, ticket)
    c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
    assert str(ticket.id) in c.get("/history").text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_web_close.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vitsc.web.routes.close'`

- [ ] **Step 3: Write the close route**

`src/vitsc/web/routes/close.py`:

```python
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from vitsc.faults.registry import get_fault
from vitsc.session.afteraction import build_after_action
from vitsc.session.grading import grade_ticket
from vitsc.session.ticket import Disposition, TicketState
from vitsc.web.routes.queue import _session, _ticket_or_404

router = APIRouter()


@router.post("/ticket/{ticket_id}/close", response_class=HTMLResponse)
def close_ticket(request: Request, ticket_id: int, disposition: str = Form(...)):
    from vitsc.web.app import templates
    session = _session(request)
    ticket = _ticket_or_404(request, ticket_id)
    if ticket.state is TicketState.CLOSED:
        raise HTTPException(status_code=409, detail="Ticket is already closed")

    fault = get_fault(ticket.fault_id)
    ticket.tool_calls = list(session.log_for(ticket_id).calls)
    ticket.close(Disposition(disposition), at=session.env.world.clock)

    grade = grade_ticket(ticket, fault, session.env, session.queue.baseline)
    report = build_after_action(ticket, fault, grade, session.env.world)
    session.store.save_closed(ticket, grade, report)

    return templates.TemplateResponse(
        request, "_afteraction.html",
        {"ticket": ticket, "grade": grade, "report": report},
    )


@router.get("/history", response_class=HTMLResponse)
def history(request: Request):
    from vitsc.web.app import templates
    session = _session(request)
    return templates.TemplateResponse(
        request, "history.html",
        {"records": session.store.history(), "stats": session.store.domain_stats()},
    )
```

Note `ticket.close()` uses `session.env.world.clock`, so SLA timing is driven by the simulated clock, not wall time. Advance `world.clock` in the SSE tick below.

- [ ] **Step 4: Write the SSE route**

`src/vitsc/web/routes/events.py`. One stream carrying clock ticks and queue changes; the simulated clock advances one minute per real second so an eight-hour shift is playable.

```python
import asyncio
import json
from datetime import timedelta

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from vitsc.web.routes.queue import _session

router = APIRouter()
TICK_SECONDS = 1.0
MINUTES_PER_TICK = 1


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    session = _session(request)

    async def stream():
        while not await request.is_disconnected():
            session.env.world.clock += timedelta(minutes=MINUTES_PER_TICK)
            now = session.env.world.clock
            arrivals = session.queue.tick(now)
            payload = {
                "clock": now.isoformat(),
                "arrivals": [t.id for t in arrivals],
                "active": [
                    {
                        "id": t.id,
                        "remaining": int((t.deadline - now).total_seconds() // 60),
                        "overdue": t.is_overdue(now),
                    }
                    for t in session.queue.active()
                ],
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(TICK_SECONDS)

    return StreamingResponse(stream(), media_type="text/event-stream")
```

In `base.html`, subscribe with a small inline script: on each message, update the SLA counters by element id, and if `arrivals` is non-empty fire `htmx.trigger('#queue', 'refresh')`. Give `#queue` `hx-get="/queue" hx-trigger="refresh"`.

- [ ] **Step 5: Write the templates**

- `_afteraction.html` — verdict banner, `report.root_cause`, `report.shortest_path` as an ordered list, calls made vs minimum, `wasted_calls`, a warning block if `report.collateral`, and a note if `report.touched_before_asking`.
- `history.html` — the closed-ticket table plus a per-domain accuracy summary from `store.domain_stats()`.

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/vitsc/web tests/test_web_close.py
git commit -m "feat(web): add close, after-action report, history, and SSE clock"
```

---

### Task 19: End-to-end drill test

**Files:**
- Create: `tests/test_end_to_end.py`
- Test: itself

**Interfaces:**
- Consumes: everything.
- Produces: nothing. This is the proof that a full ticket can be worked start to finish through the HTTP surface only.

- [ ] **Step 1: Write the test**

`tests/test_end_to_end.py`:

```python
import pytest
from fastapi.testclient import TestClient

from vitsc.faults.base import bind
from vitsc.faults.registry import all_faults, get_fault
from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.mark.parametrize("seed", range(8))
def test_a_full_ticket_can_be_worked_through_http(tmp_path, seed):
    session = AppSession.build(db_path=tmp_path / f"e2e{seed}.sqlite3", seed=seed)
    client = TestClient(create_app(session))

    ticket = session.queue.open_ticket()
    assert ticket is not None

    # The queue and the detail view render without revealing the answer.
    assert ticket.report_text in client.get("/").text
    detail = client.get(f"/ticket/{ticket.id}").text
    fault = get_fault(ticket.fault_id)
    assert fault.canonical_title not in detail
    assert fault.id not in detail

    # Ask the user something before touching anything.
    client.post(f"/ticket/{ticket.id}/chat", data={"message": "when did it last work?"})
    assert len(session.queue.get(ticket.id).chat) == 2

    # Run the fault's own diagnostic path through the tool surface.
    client.post(f"/ticket/{ticket.id}/tool",
                data={"tool": "ad", "command": "get-user", "args": f"sam={ticket.placement.key}"})

    # Resolve, or escalate when that is the correct disposition.
    if fault.escalation_is_correct:
        disposition = "escalated"
    else:
        disposition = "resolved"
        for resolution in fault.canonical_resolutions()[:1]:
            for action in bind(resolution, ticket.placement, session.env.world).actions:
                session.env.execute(action)

    body = client.post(f"/ticket/{ticket.id}/close", data={"disposition": disposition}).text

    # After-action reveals the cause, and the record persists.
    assert fault.canonical_title in body
    records = session.store.history()
    assert len(records) == 1
    assert records[0].correct is True, f"{fault.id} graded incorrect: {records[0].verdict}"


def test_every_fault_in_the_catalog_can_be_closed_correctly(tmp_path):
    """Stronger than the seeded sample: exercise all ten faults explicitly."""
    for fault in all_faults():
        session = AppSession.build(db_path=tmp_path / f"{fault.id}.sqlite3", seed=0)
        placement = fault.placements(session.env.world)[0]
        fault.apply(session.env.world, placement, __import__("random").Random(0))
        session.queue.baseline = __import__(
            "vitsc.world.invariants", fromlist=["capture_baseline"]
        ).capture_baseline(session.env.world)

        if fault.escalation_is_correct:
            continue  # covered by the parametrized test above
        for resolution in fault.canonical_resolutions()[:1]:
            for action in bind(resolution, placement, session.env.world).actions:
                session.env.execute(action)
        assert fault.is_present(session.env.world, placement) is False
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_end_to_end.py -v`
Expected: 9 passed. If a seed picks a fault whose diagnostic path is not `ad.user`, the tool call in the middle is merely wasted, not fatal — the test still closes correctly.

- [ ] **Step 3: Run the whole suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 4: Drive it manually**

```bash
uv run python -m vitsc
```

Open `http://127.0.0.1:8000`. Work one ticket end to end: read it, ask the user a question, set a priority, run tools, close it, read the after-action report. With LM Studio running, confirm the report text and chat replies read like a person and never name a cause. With LM Studio stopped, confirm the degraded banner appears and the drill still works.

- [ ] **Step 5: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "test: add end-to-end drill coverage across the catalog"
```

---

## Definition of Done

Phase 1 is complete when all of the following hold:

- [ ] `uv run pytest` is green with LM Studio **not** running.
- [ ] `uv run pytest` is green with LM Studio **running**.
- [ ] All ten catalog faults conform (Task 4 harness) across every placement.
- [ ] No template renders `fault_id`, `canonical_title`, or raw `symptoms` before a ticket is closed.
- [ ] `grep -r "from vitsc.faults" src/vitsc/tools/` returns nothing.
- [ ] A full ticket can be worked in the browser, and the after-action report says something the player did not already know.
