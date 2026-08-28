# Virtual IT Support Center — Phase 2a (Depth Mechanics) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the four subsystems Phase 2 needs — honest distractors, cascading faults, a simulated tier-2, and an original-content knowledge base — plus the mail domain's missing layer slice, against the existing ten faults. Phase 2b then authors the ~20 new faults against a finished shape instead of retrofitting them.

**Architecture:** Unchanged where it matters. Tools still read world state only through `Environment`; faults still own `is_present()` as the single source of truth; the persona still receives a card and `UserSymptoms` and nothing else. Every addition here either extends the `Fault` declaration or sits in the session layer, which is the only layer that already knows a fault id.

**Tech Stack:** Python 3.12+, uv, FastAPI, Jinja2, HTMX, SSE, Pydantic v2, SQLite, pytest, `openai` SDK against LM Studio.

**Spec:** `docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md` (§13, Phase 2)
**Prior plan:** `docs/superpowers/plans/2026-08-07-phase-1-drill.md` (Tasks 1–19, complete)

---

## Global Constraints

Every task's requirements implicitly include this section. Phase 1's constraints all still hold; the last three are new to Phase 2a.

- Python 3.12+.
- `uv` only, never `pip`. `uv add` / `uv add --dev` for dependencies, `uv run` for commands. Commit `uv.lock`; `.venv/` stays gitignored.
- All commit messages end with the trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Commit commands below omit it for brevity — add it.
- **Tools read world state only via `Environment`.** No module under `src/vitsc/tools/` may import from `vitsc.faults` or `vitsc.world`. Enforced by `tests/test_architecture.py`; a violation is review-rejectable. This binds the new `MailConsole` (Task 14) and the new KB tool (Task 11) exactly as it binds the six existing tools.
- **The persona layer never receives a fault id, a root cause, or a `World`.** Its only inputs are a `PersonaCard` and a `UserSymptoms`.
- **The full test suite must pass with no model loaded in LM Studio.** Any test touching persona behaviour uses `TemplatePersona` or a stub.
- No JS build step. Server-rendered Jinja2 partials plus HTMX attributes only.
- Package root is `src/vitsc/`; tests mirror it under `tests/`.
- Run tests with `uv run pytest`.
- **A distractor may never change whether any registered fault is present.** Enforced mechanically in Task 3. This is what the word "honest" in "honest distractors" is doing: the anomaly is real and truthfully reported, but it is never the cause of the ticket in front of you.
- **The knowledge base is procedure, not an answer key.** No article may name a fault id or a fault's `canonical_title`. Enforced in Task 10. A KB that maps symptoms to causes deletes the drill.
- **Leak terms never enter a prompt.** They reach `scrub()` only. Telling a model "do not say lockout" hands it the answer. Enforced in Task 1.

---

## Scope: what is in 2a, and what waits for 2b

Phase 2 in the spec is one paragraph covering five workstreams. It is split here because four of the five change *how a fault is declared and scheduled*, and the fifth is twenty pieces of content. Authoring the content first would mean retrofitting twenty faults with cascade reporters, KB links and escalation reasons.

**In this plan (2a) — mechanics and one reference fault per mechanic:**

| Workstream | What lands here |
|---|---|
| Fault-aware model persona | The Phase 1 leftover: `LMStudioPersona` wired into `AppSession` (Tasks 1–2) |
| Honest distractors | `Distractor` protocol, registry, conformance harness, 5 distractors, session seeding (Tasks 3–4) |
| Cascading faults | `reporters()`, `cascade_id`, multi-ticket arrival, cascade grading, one reference cascade fault (Tasks 5–7) |
| Tier-2 escalation | Escalation note, accept/bounce, `AWAITING_TIER2`, escalation-quality grading, web flow (Tasks 8–9) |
| Knowledge base | Article format, loader, 8 articles, KB tool, after-action links (Tasks 10–11) |
| Mail domain | `Mailbox`/`MailSystem` world model, `mail.*` env kinds, `MailConsole`, 2 reference faults (Tasks 12–15) |

**Deferred to 2b (its own plan, written after 2a lands):** the remaining ~18 faults to reach 30+, spread across all five domains, each authored with its cascade reporters, KB links and escalation reason from the start. An outline is at the end of this document.

**Fault count after 2a:** 13 (10 existing + `print.server_spooler_stopped` + `mail.mailbox_full` + `mail.external_forwarding_rule`), across all five domains.

---

## Protocol changes this plan makes

Four members are added to the `Fault` protocol. All ten existing faults are plain classes that would break the moment the protocol grows, so this plan introduces `FaultBase` in `vitsc/faults/base.py` carrying the defaults, and retrofits the ten to inherit it — a mechanical change with no behaviour delta, done once in Task 5 rather than piecemeal.

| Member | Type | Default | Purpose |
|---|---|---|---|
| `reporters(world, at)` | `list[str] \| None` | `None` | Who phones this in. `None` means "just the person at the placement" — today's behaviour. A list makes it a cascade. |
| `kb_articles` | `list[str]` | `[]` | Article ids that would have helped. Documentation only, like `canonical_resolutions` — never a pass/fail gate. |
| `escalation_reason` | `str` | `""` | Why tier-2 owns this. Used in the accept message and the after-action. Required non-empty when `escalation_is_correct`. |
| `escalation_evidence` | `list[Query]` | `[]` | Which diagnostic findings a good escalation note must show. Defaults to `diagnostic_path()` when empty. |

The `Persona` protocol gains one member:

| Member | Default | Purpose |
|---|---|---|
| `for_fault(leak_terms)` | returns `self` | Returns a persona bound to this ticket's forbidden vocabulary. `TemplatePersona` ignores it; `LMStudioPersona` returns a copy with new scrub terms. |

---

## Design decisions

Recorded here so they are not relitigated task-by-task.

**1. Leak terms bind per call, not per construction.** The Phase 1 blocker was that `LMStudioPersona.__init__` takes a fixed `leak_terms` list while a session runs many faults in turn. The fix is `for_fault()` rather than adding a `leak_terms` parameter to `initial_report`/`reply`, because that keeps the two speaking signatures free of anything fault-shaped — the structural half of leak prevention is that you cannot pass a cause to a persona, and a `leak_terms` argument on `reply()` weakens that by putting fault-derived data in the speaking path. `SessionQueue.persona_for(ticket)` does the registry lookup so `web/routes/chat.py` never imports `vitsc.faults`.

**2. Distractors are a separate protocol, not faults with a flag.** A `Fault` with `is_ticketable = False` would have to be excluded from the scheduler, the conformance harness, priority, grading and the after-action — five places that would each need to remember. A distractor has no `is_present`, no `symptoms`, no resolution and no ticket, because it is never diagnosed as a cause; it only has `placements()` and `apply()`. Its whole contract is the non-interference guarantee, which is a different test from the fault harness's.

**3. Distractors are seeded once at session start, before the first baseline.** They are part of the world the technician inherits, so `capture_baseline` must run after them — otherwise a pre-existing stopped service reads as the technician's collateral damage. This is the same capture-after-apply reasoning that `world/invariants.py` already documents for faults.

**4. Cascade tickets are siblings, not a parent and children.** One fault, one placement, N tickets sharing a `cascade_id`. There is no "root ticket": the technician has to notice that three tickets are one cause, which is the skill being drilled. Fixing the root clears `is_present()` and therefore clears every sibling — that falls out of grading asking the world rather than the ticket, with no special case.

**5. A cascade opens fewer tickets than it affects.** `print.server_spooler_stopped` on `MER-PRT-01` affects six users; `MAX_ACTIVE` is 4. The queue samples up to `CASCADE_MAX` (3) reporters and only picks a cascade candidate when there is room for at least two. Not everyone phones in — a partial cascade is realistic, not a compromise.

**6. Tier-2 is deterministic and template-driven, never model-driven.** The bounce decision has to be reproducible in tests and correct with nothing running on localhost. Accept/bounce keys off `escalation_is_correct` plus a mechanical evidence check against the note text; the wording comes from a phrase bank in the same spirit as `TemplatePersona`.

**7. A bounced escalation reopens the ticket.** That is the teaching moment — "this was within your scope" arriving from a queue you tried to hand it to is the thing that transfers. So `Ticket.close()` grows a sibling path rather than being the only exit: `escalate()` moves to `AWAITING_TIER2`, and tier-2 either closes it or returns it to `IN_PROGRESS` with a `tier2` chat turn.

**8. The KB is graded as diligence, not as a required step.** Reading an article is a non-mutating tool call in the log, so it already counts as looking before touching. The after-action names the article that would have helped, whether or not it was read. Nothing requires a KB read to pass, because a technician who knows the answer should not be penalised for not looking it up.

**9. Mail gets a real layer slice, not simulated symptoms.** `Domain` has carried a `"mail"` literal since Phase 1 with nothing behind it. Mail faults that are really endpoint faults wearing an Outlook costume would leave the fifth domain undiagnosable and the drill missing the single most common real helpdesk topic. So: `Mailbox` and `MailSystem` in the world model, `mail.*` query and action kinds, and a `MailConsole` rendering Exchange-shaped output.

---

## Known risks and deviations

Flagged here rather than discovered mid-task.

**`open_ticket()` changes signature.** It returns `list[Ticket]` after Task 5, because a cascade arrival is plural. Callers today: `SessionQueue.tick()`, `tests/test_queue.py`, `tests/test_web_*.py` fixtures, `tests/test_end_to_end.py`, and `web/routes/events.py` indirectly. Task 5 updates all of them; a `open_one()` convenience returning `Ticket | None` keeps the test fixtures readable.

**The LM Studio half of the Definition of Done stays unverifiable in this environment.** Nothing in the container running these tasks has network access to a local LM Studio instance. Tasks 1–2 therefore ship with a stub-driven test suite plus a documented manual verification procedure the user runs on their own machine (`docs/verifying-lmstudio.md`). Do not mark that DoD line green from CI; it is a human check.

**`endpoint.disk_full` fires below 2.0 GB free.** The low-disk distractor must sit far above that (8–15 GB against a 120 GB norm) — visibly odd, mechanically harmless. The Task 3 harness proves it, but pick the numbers deliberately.

**Six workstations, twelve users.** Half the org has no machine, so `world.machine_for()` returns `None` for them. Cascade reporter derivation must go through machines and tolerate users who have none.

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/vitsc/faults/base.py` | **Modify** — `FaultBase` defaults; `reporters`, `kb_articles`, `escalation_reason`, `escalation_evidence` on the protocol. |
| `src/vitsc/faults/catalog/printing.py` | **Modify** — add `print.server_spooler_stopped` (reference cascade). |
| `src/vitsc/faults/catalog/mail.py` | **Create** — `mail.mailbox_full`, `mail.external_forwarding_rule`. |
| `src/vitsc/distractors/base.py` | **Create** — `Distractor` protocol. |
| `src/vitsc/distractors/registry.py` | **Create** — registration and lookup. |
| `src/vitsc/distractors/catalog.py` | **Create** — the five v1 distractors. |
| `src/vitsc/kb/models.py` | **Create** — `Article`. |
| `src/vitsc/kb/loader.py` | **Create** — markdown + frontmatter → `Article`, plus keyword search. |
| `src/vitsc/data/kb/*.md` | **Create** — eight hand-authored articles. |
| `src/vitsc/tools/kb.py` | **Create** — `KnowledgeBase` tool (`kb search`, `kb read`). |
| `src/vitsc/tools/mail.py` | **Create** — `MailConsole`. |
| `src/vitsc/world/models.py` | **Modify** — `Mailbox`, `MailSystem`, `MailRule`; `World.mail`, `World.mailbox_for`. |
| `src/vitsc/data/company.yaml` | **Modify** — mailboxes and the mail server. |
| `src/vitsc/world/seed.py` | **Modify** — build the mail system. |
| `src/vitsc/env/simulated.py` | **Modify** — `_read_mail_*` / `_do_mail_*` dispatch methods. |
| `src/vitsc/session/tier2.py` | **Create** — the simulated tier-2 queue: accept/bounce and its phrase bank. |
| `src/vitsc/session/ticket.py` | **Modify** — `cascade_id`, `AWAITING_TIER2`, `escalate()`, `reopen()`, cascade-aware `priority_for`. |
| `src/vitsc/session/queue.py` | **Modify** — reporter resolution, plural arrivals, distractor seeding. |
| `src/vitsc/session/grading.py` | **Modify** — `escalation_quality`, `duplicate_mutations`, `kb_consulted`. |
| `src/vitsc/session/afteraction.py` | **Modify** — cascade line, KB link, tier-2 outcome. |
| `src/vitsc/session/store.py` | **Modify** — persist cascade id and escalation quality. |
| `src/vitsc/persona/models.py` | **Modify** — `Persona.for_fault`. |
| `src/vitsc/persona/client.py` | **Modify** — `for_fault`, config-driven construction. |
| `src/vitsc/web/routes/escalate.py` | **Create** — the tier-2 flow. |
| `src/vitsc/web/routes/kb.py` | **Create** — KB search and article pages. |
| `docs/verifying-lmstudio.md` | **Create** — the manual model-backed verification procedure. |

---

### Task 1: Bind leak terms per ticket

**Files:**
- Modify: `src/vitsc/persona/models.py`, `src/vitsc/persona/client.py`, `src/vitsc/persona/templates.py`, `src/vitsc/session/queue.py`, `src/vitsc/web/routes/chat.py`
- Test: `tests/test_persona_binding.py`

**Interfaces:**
- Consumes: `LMStudioPersona`, `TemplatePersona`, `scrub` (Phase 1 Tasks 10–11); `get_fault` (Phase 1 Task 3).
- Produces: `Persona.for_fault(leak_terms: list[str]) -> Persona`; `SessionQueue.persona_for(ticket) -> Persona`.

- [x] **Step 1: Write the failing test**

`tests/test_persona_binding.py`:

```python
from random import Random

from vitsc.faults.registry import get_fault
from vitsc.persona.client import LMStudioPersona
from vitsc.persona.personas import card_for
from vitsc.persona.prompts import build_system_prompt
from vitsc.persona.templates import TemplatePersona
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.session.queue import SessionQueue
from vitsc.world.seed import load_world


class StubClient:
    """Returns whatever it is told to, and records the prompts it saw."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, model, messages, **kwargs):
        self.prompts.append(messages[0]["content"])
        text = self.replies.pop(0)
        return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": text})()})()]})()


def test_template_persona_for_fault_is_itself():
    persona = TemplatePersona()
    assert persona.for_fault(["locked"]) is persona


def test_bound_persona_scrubs_the_terms_it_was_bound_to():
    client = StubClient(["Your account is locked out.", "I cannot get in, sorry."])
    persona = LMStudioPersona(client, "stub", leak_terms=[])
    bound = persona.for_fault(["lock"])

    world = load_world()
    card = card_for(world.org.users["m.alvarez"], Random(0))
    symptoms = get_fault("ad.account_locked").symptoms(world, get_fault("ad.account_locked").placements(world)[0])

    reply = bound.reply(card, symptoms, [], "What happens when you sign in?")
    assert "locked" not in reply.lower()


def test_binding_does_not_mutate_the_original():
    persona = LMStudioPersona(StubClient([]), "stub", leak_terms=["original"])
    persona.for_fault(["different"])
    assert persona._leak_terms == ["original"]


def test_leak_terms_never_reach_the_prompt():
    """Layer 3 filters output. Telling the model the forbidden word hands it the answer."""
    world = load_world()
    fault = get_fault("ad.account_locked")
    at = fault.placements(world)[0]
    fault.apply(world, at, Random(0))
    card = card_for(world.org.users[at.key], Random(0))
    symptoms = fault.symptoms(world, at)

    client = StubClient(["I just cannot get in this morning."])
    LMStudioPersona(client, "stub", leak_terms=[]).for_fault(fault.leak_terms).reply(
        card, symptoms, [], "What did you see?"
    )
    prompt = client.prompts[0].lower()
    for term in fault.leak_terms:
        assert term.strip().lower() not in prompt

    # And the shared builder cannot be handed them at all.
    assert "leak" not in build_system_prompt.__code__.co_varnames


def test_queue_binds_the_open_ticket_s_fault():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(3), now=env.world.clock)
    ticket = queue.open_ticket()
    bound = queue.persona_for(ticket)
    assert bound is not None
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_persona_binding.py -v`
Expected: FAIL — `TemplatePersona` has no attribute `for_fault`.

- [x] **Step 3: Add `for_fault` to the protocol and both implementations**

In `persona/models.py`, add to the `Persona` protocol:

```python
    def for_fault(self, leak_terms: list[str]) -> "Persona":
        """Return a persona bound to this ticket's forbidden vocabulary.

        Leak terms change per ticket while a session runs many faults, so they
        cannot be fixed at construction. They are deliberately *not* a
        parameter of `initial_report`/`reply`: keeping the speaking signatures
        free of fault-derived data is the structural half of leak prevention.
        """
        ...
```

`TemplatePersona.for_fault` returns `self` — it derives text from symptom fields and has nothing to scrub. `LMStudioPersona.for_fault` returns a new instance sharing the client, model and fallback, with the new terms. Do not mutate in place: two open tickets can hold two bindings at once.

- [x] **Step 4: Resolve the binding in the session layer**

Add to `SessionQueue`:

```python
    def persona_for(self, ticket: Ticket) -> Persona:
        """The persona bound to this ticket's leak terms.

        Lives here, not in the chat route, so the web layer never imports the
        fault registry to speak to a user.
        """
        return self.persona.for_fault(get_fault(ticket.fault_id).leak_terms)
```

Use it in `open_ticket` for `initial_report`, and in `web/routes/chat.py` for `reply` — replacing `session.queue.persona.reply(...)` with `session.queue.persona_for(ticket).reply(...)`.

- [x] **Step 5: Run the suite**

Run: `uv run pytest -v`
Expected: all green, including the existing persona tests.

- [x] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(persona): bind leak terms per ticket via for_fault"
```

---

### Task 2: Wire the model-backed persona into the app

**Files:**
- Modify: `src/vitsc/web/deps.py`, `src/vitsc/persona/client.py`, `src/vitsc/web/templates/layout.html`
- Create: `src/vitsc/persona/config.py`, `docs/verifying-lmstudio.md`
- Test: `tests/test_persona_config.py`

**Interfaces:**
- Consumes: `for_fault` (Task 1); `make_client`, `DEFAULT_BASE_URL` (Phase 1 Task 11).
- Produces: `PersonaSettings.from_env()`, `build_persona(settings)`; a degraded banner in the UI.

- [x] **Step 1: Write the failing test**

`tests/test_persona_config.py`:

```python
from pathlib import Path

from vitsc.persona.config import PersonaSettings, build_persona
from vitsc.persona.templates import TemplatePersona
from vitsc.web.deps import AppSession


def test_defaults_to_the_template_persona(monkeypatch):
    monkeypatch.delenv("VITSC_PERSONA", raising=False)
    assert isinstance(build_persona(PersonaSettings.from_env()), TemplatePersona)


def test_env_selects_the_model_persona(monkeypatch):
    monkeypatch.setenv("VITSC_PERSONA", "lmstudio")
    monkeypatch.setenv("VITSC_MODEL", "qwen2.5-7b-instruct")
    settings = PersonaSettings.from_env()
    assert settings.backend == "lmstudio"
    assert settings.model == "qwen2.5-7b-instruct"


def test_an_unreachable_endpoint_does_not_break_the_session(monkeypatch, tmp_path):
    """The whole drill must survive nothing running on localhost."""
    monkeypatch.setenv("VITSC_PERSONA", "lmstudio")
    monkeypatch.setenv("VITSC_BASE_URL", "http://127.0.0.1:9/v1")
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    ticket = session.queue.open_ticket()
    assert ticket.report_text          # fell back, did not raise
    assert session.degraded is True


def test_app_session_still_accepts_an_explicit_persona(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1, persona=TemplatePersona())
    assert isinstance(session.queue.persona, TemplatePersona)
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_persona_config.py -v`
Expected: FAIL — no module `vitsc.persona.config`.

- [x] **Step 3: Implement the settings and the builder**

`persona/config.py`: a `PersonaSettings` model with `backend: Literal["template", "lmstudio"] = "template"`, `base_url: str = DEFAULT_BASE_URL`, `model: str = "local-model"`, read from `VITSC_PERSONA`, `VITSC_BASE_URL`, `VITSC_MODEL`. `build_persona` returns `TemplatePersona()` for the default and an `LMStudioPersona(make_client(base_url), model, leak_terms=[])` otherwise — empty terms at construction, because Task 1 made binding per-ticket the way terms arrive.

Import `openai` lazily inside `make_client` as it already is, so the default path never touches it.

- [x] **Step 4: Wire it into `AppSession` and surface `degraded`**

`AppSession.build` calls `build_persona(PersonaSettings.from_env())` when no `persona` argument is passed. Add a `degraded` property that reads through to `getattr(self.queue.persona, "degraded", False)`, and render a banner in `layout.html` when it is true — the player must know they are reading template text rather than model text.

- [x] **Step 5: Run the suite**

Run: `uv run pytest -v`
Expected: all green with nothing on localhost:1234.

- [x] **Step 6: Write the manual verification doc**

`docs/verifying-lmstudio.md`: load an 8–14B instruct model, confirm `curl http://localhost:1234/v1/models`, run `VITSC_PERSONA=lmstudio VITSC_MODEL=<id> uv run python -m vitsc`, then work one ticket per domain and check three things — the report reads like a person, no reply names a cause, and stopping LM Studio mid-session shows the banner without breaking the queue. State plainly that this cannot be verified in CI or in a sandboxed container.

- [x] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(persona): construct the model-backed persona from config"
```

---

### Task 3: The `Distractor` protocol and its conformance harness

**Files:**
- Create: `src/vitsc/distractors/__init__.py`, `base.py`, `registry.py`
- Test: `tests/test_distractors.py`

**Interfaces:**
- Consumes: `World`, `Placement` (Phase 1 Tasks 1, 3).
- Produces: `Distractor` protocol, `register_distractor`, `all_distractors`, `get_distractor`.

- [x] **Step 1: Write the failing test**

`tests/test_distractors.py` — the harness that makes "honest" mechanical. It is parametrized over distractor × placement, mirroring `tests/test_catalog.py`:

```python
from random import Random

import pytest

import vitsc.distractors.catalog  # noqa: F401
import vitsc.faults.catalog  # noqa: F401
from vitsc.distractors.registry import all_distractors
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import all_faults
from vitsc.world.invariants import capture_baseline, check_invariants
from vitsc.world.seed import load_world


def cases():
    world = load_world()
    return [
        pytest.param(d, at, id=f"{d.id}@{at.key}")
        for d in all_distractors()
        for at in d.placements(world)
    ]


@pytest.mark.parametrize("distractor,at", cases())
def test_distractor_never_flips_a_fault(distractor, at):
    """The honesty guarantee: a distractor is real, visible, and never a cause."""
    world = load_world()
    before = {
        (f.id, p.key): f.is_present(world, p)
        for f in all_faults()
        for p in f.placements(world)
    }
    distractor.apply(world, at, Random(0))
    for f in all_faults():
        for p in f.placements(world):
            key = (f.id, p.key)
            if key in before:
                assert f.is_present(world, p) == before[key], (
                    f"{distractor.id} at {at.key} changed {f.id} at {p.key}"
                )


@pytest.mark.parametrize("distractor,at", cases())
def test_distractor_is_invariant_clean(distractor, at):
    """Seeded before the baseline, a distractor is inherited world state."""
    world = load_world()
    distractor.apply(world, at, Random(0))
    assert check_invariants(world, capture_baseline(world)) == []


@pytest.mark.parametrize("distractor,at", cases())
def test_distractor_is_visible_through_a_tool(distractor, at):
    """An invisible distractor distracts nobody."""
    clean = SimulatedEnvironment(load_world())
    world = load_world()
    distractor.apply(world, at, Random(0))
    dirty = SimulatedEnvironment(world)

    seen = [
        (dirty.read(q).rendered, clean.read(q).rendered)
        for q in distractor.visible_through(at)
    ]
    assert seen, f"{distractor.id} declares no visible query"
    assert any(d != c for d, c in seen), f"{distractor.id} at {at.key} shows nothing"


@pytest.mark.parametrize("distractor,at", cases())
def test_distractor_does_not_break_a_canonical_fix(distractor, at):
    """A seeded anomaly must not make a legitimate repair fail."""
    world = load_world()
    distractor.apply(world, at, Random(0))
    env = SimulatedEnvironment(world)
    for fault in all_faults():
        for p in fault.placements(env.world):
            if fault.is_present(env.world, p):
                continue
            snapshot = env.snapshot()
            fault.apply(env.world, p, Random(0))
            baseline = capture_baseline(env.world)
            for resolution in fault.canonical_resolutions():
                from vitsc.faults.base import bind
                for action in bind(resolution, p, env.world).actions:
                    env.execute(action)
                assert not fault.is_present(env.world, p)
                assert check_invariants(env.world, baseline) == []
                break
            env.restore(snapshot)
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_distractors.py -v`
Expected: FAIL — no module `vitsc.distractors.base`.

- [x] **Step 3: Write the protocol and registry**

`distractors/base.py`:

```python
"""Honest distractors.

A distractor is a real, truthfully-reported anomaly that is never the cause of
a ticket (spec §4). It exists so the first oddity a technician finds is not
automatically the answer.

Note what is absent compared to `Fault`: no `is_present`, no `symptoms`, no
`canonical_resolutions`, no `escalation_is_correct`. A distractor is never
diagnosed, never reported, never graded and never fixed — so it needs none of
that, and having none of it is what keeps the scheduler, grading and the
after-action from having to special-case it.
"""

from random import Random
from typing import Protocol, runtime_checkable

from vitsc.env.base import Query
from vitsc.faults.base import Placement
from vitsc.world.models import World


@runtime_checkable
class Distractor(Protocol):
    id: str
    note: str  # plain-English description, for the after-action

    def placements(self, world: World) -> list[Placement]: ...
    def apply(self, world: World, at: Placement, rng: Random) -> None: ...
    def visible_through(self, at: Placement) -> list[Query]: ...
```

`distractors/registry.py` mirrors `faults/registry.py`: a module dict, `register_distractor`, `all_distractors()` (importing the catalog to trigger registration), `get_distractor`.

- [x] **Step 4: Run the harness against an empty catalog**

Run: `uv run pytest tests/test_distractors.py -v`
Expected: 0 collected cases, no failures. The harness is ready; Task 4 fills it.

- [x] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(distractors): add the Distractor protocol and conformance harness"
```

---

### Task 4: The distractor catalog and session seeding

**Files:**
- Create: `src/vitsc/distractors/catalog.py`
- Modify: `src/vitsc/session/queue.py`, `src/vitsc/web/deps.py`
- Test: `tests/test_distractors.py` (extend), `tests/test_queue.py` (extend)

**Interfaces:**
- Consumes: Task 3's protocol and registry.
- Produces: five distractors; `seed_distractors(world, rng, count)`; `SessionQueue.distractors`.

- [x] **Step 1: Write the failing test**

Extend `tests/test_distractors.py`:

```python
def test_catalog_has_at_least_five():
    assert len(all_distractors()) >= 5


def test_ids_are_unique_and_namespaced():
    ids = [d.id for d in all_distractors()]
    assert len(ids) == len(set(ids))
    assert all("." in i for i in ids)


def test_notes_are_written_for_a_reader():
    for d in all_distractors():
        assert d.note and d.note[0].isupper()
```

And in `tests/test_queue.py`:

```python
def test_session_seeds_distractors_before_the_baseline():
    from vitsc.session.queue import SessionQueue
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(7),
                         now=env.world.clock, distractor_count=3)
    assert len(queue.distractors) == 3
    # Seeded state is inherited, not collateral damage.
    assert check_invariants(env.world, queue.baseline) == []


def test_distractors_are_off_by_default_for_deterministic_tests():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(7), now=env.world.clock)
    assert queue.distractors == []
```

- [x] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_distractors.py tests/test_queue.py -v`
Expected: FAIL — no `vitsc.distractors.catalog`, `SessionQueue` takes no `distractor_count`.

- [x] **Step 3: Author the five distractors**

`distractors/catalog.py`. Each must be plausible in a real estate of Windows machines, visible through an existing query, and mechanically inert:

| id | What it does | Visible through | Why it is safe |
|---|---|---|---|
| `disk.moderately_low` | One workstation to 8–15 GB free (norm 120) | `machine.state` | `endpoint.disk_full` fires under 2.0 GB — far below. |
| `service.wsearch_stopped` | Stops `WSearch` on one workstation | `machine.services` | No fault reads `WSearch`; search indexing is cosmetic. |
| `eventlog.old_disk_warning` | A single disk warning ~30 days before `world.clock` | `machine.eventlog` | `endpoint.failing_disk` keys on `smart_status`, not on log text. |
| `printer.offline_unused` | Marks a printer offline that no reporter's machine has installed | `printer.state` | Placement filter excludes printers in any machine's `installed_printers`. |
| `drive.stale_mapping` | Adds a `Z:` mapping to a UNC that no longer exists | `machine.state` | No fault or invariant reads `Z:`; share faults key on `S:`. |

Two rules the harness will catch but the author should hold anyway: never touch a field any fault's `is_present()` reads at a value near its threshold, and never remove something `capture_baseline` tracks as *expected* (an enabled account, a group membership) — a distractor adds oddity, it does not take away expectations.

For the offline-printer placement filter, note that all three seeded printers are installed on some workstation, so this distractor's `placements()` may legitimately return `[]` today and start applying in 2b when the estate grows. Returning `[]` is a supported answer — the harness parametrizes over zero cases and the seeder skips it.

- [x] **Step 4: Seed them at session start**

In `session/queue.py`:

```python
def seed_distractors(world: World, rng: Random, count: int) -> list[tuple[str, Placement]]:
    """Apply `count` distinct distractors before the first baseline capture.

    Order matters: these are anomalies the technician *inherits*, so the
    baseline must be captured after them. Capturing first would report the
    world's own pre-existing quirks as the technician's collateral damage —
    the same capture-after-apply rule `world/invariants.py` documents.
    """
    candidates = [(d, at) for d in all_distractors() for at in d.placements(world)]
    rng.shuffle(candidates)
    seeded: list[tuple[str, Placement]] = []
    used: set[str] = set()
    for distractor, at in candidates:
        if len(seeded) >= count:
            break
        if distractor.id in used:
            continue
        distractor.apply(world, at, rng)
        used.add(distractor.id)
        seeded.append((distractor.id, at))
    return seeded
```

`SessionQueue.__init__` gains `distractor_count: int = 0`, calls `seed_distractors` **before** `capture_baseline`, and stores the result on `self.distractors`. Default 0 keeps every existing test deterministic; `AppSession.build` passes 3 so a real session always has noise.

- [x] **Step 5: Run the suite**

Run: `uv run pytest -v`
Expected: all green, with the distractor harness now covering ~5 cases per test.

- [x] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(distractors): add the v1 catalog and seed it at session start"
```

---

### Task 5: Cascade data model — reporters, sibling tickets, plural arrivals

**Files:**
- Modify: `src/vitsc/faults/base.py`, all four `src/vitsc/faults/catalog/*.py`, `src/vitsc/session/ticket.py`, `src/vitsc/session/queue.py`
- Test: `tests/test_cascade.py`, `tests/test_queue.py` (extend)

**Interfaces:**
- Consumes: `Fault`, `Placement`, `SessionQueue`.
- Produces: `FaultBase`; `Fault.reporters`; `Ticket.cascade_id`; `SessionQueue.open_ticket() -> list[Ticket]`, `open_one() -> Ticket | None`; `CASCADE_MAX`.

- [x] **Step 1: Write the failing test**

`tests/test_cascade.py`:

```python
from random import Random

import pytest

import vitsc.faults.catalog  # noqa: F401
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import all_faults, get_fault
from vitsc.persona.templates import TemplatePersona
from vitsc.session.queue import CASCADE_MAX, SessionQueue
from vitsc.world.seed import load_world


def test_every_fault_declares_reporters():
    """FaultBase supplies the default, so this is a retrofit check."""
    world = load_world()
    for fault in all_faults():
        for at in fault.placements(world):
            assert fault.reporters(world, at) is None or isinstance(
                fault.reporters(world, at), list
            )


def test_single_reporter_faults_open_exactly_one_ticket():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(2), now=env.world.clock)
    tickets = queue.open_ticket()
    assert len(tickets) == 1
    assert tickets[0].cascade_id is None


def test_siblings_share_a_cascade_id_and_a_placement():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(0), now=env.world.clock)
    tickets = queue.open_cascade(get_fault("print.server_spooler_stopped"))
    assert 2 <= len(tickets) <= CASCADE_MAX
    assert len({t.cascade_id for t in tickets}) == 1
    assert tickets[0].cascade_id is not None
    assert len({t.placement.key for t in tickets}) == 1
    assert len({t.persona.name for t in tickets}) == len(tickets)


def test_fixing_the_root_clears_every_sibling():
    """Falls out of grading asking the world, not the ticket."""
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(0), now=env.world.clock)
    tickets = queue.open_cascade(get_fault("print.server_spooler_stopped"))
    fault = get_fault("print.server_spooler_stopped")
    at = tickets[0].placement

    from vitsc.faults.base import bind
    for action in bind(fault.canonical_resolutions()[0], at, env.world).actions:
        env.execute(action)

    for ticket in tickets:
        assert not fault.is_present(env.world, ticket.placement)


def test_a_cascade_never_exceeds_the_queue():
    from vitsc.session.queue import MAX_ACTIVE
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(5), now=env.world.clock)
    for _ in range(10):
        queue.open_ticket()
    assert len(queue.active()) <= MAX_ACTIVE


def test_open_one_is_still_available_for_single_ticket_tests():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(1), now=env.world.clock)
    ticket = queue.open_one()
    assert ticket is not None and ticket.id == 1
```

- [x] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cascade.py -v`
Expected: FAIL — no `reporters`, no `open_cascade`, no `print.server_spooler_stopped` (Task 7 adds the fault; this task may xfail that case and Task 7 removes the marker).

- [x] **Step 3: Add `FaultBase` and retrofit the ten**

In `faults/base.py`:

```python
class FaultBase:
    """Defaults for every optional `Fault` member.

    The protocol grew in Phase 2a. Ten faults predate it, so the defaults live
    here and the catalog inherits them — one mechanical change instead of forty
    copy-pasted stubs, and a 2b fault that overrides nothing still conforms.
    """

    kb_articles: list[str] = []
    escalation_reason: str = ""
    escalation_evidence: list[Query] = []

    def reporters(self, world: World, at: Placement) -> list[str] | None:
        """Who phones this in.

        `None` means "whoever the placement points at" — the session layer owns
        that resolution because it depends on `assigned_to`, which is queue
        logic rather than fault data. A list makes the fault a cascade.
        """
        return None
```

Add the four members to the `Fault` protocol, and make each of the ten catalog classes inherit `FaultBase`. No other change to them; `tests/test_catalog.py` must stay green throughout.

- [x] **Step 4: Extend the ticket and the scheduler**

`session/ticket.py`: add `cascade_id: str | None = None`. Change `priority_for` to take the reporter count — impact on several people outranks a single senior user:

```python
def priority_for(fault: Fault, user: ADUser, reporters: int = 1) -> Priority:
    """The system's triage call, which the player's own is graded against.

    Impact first, then who is blocked, then how gnarly it looks. A cascade is
    impact by definition: three people stopped is a P1 whatever the fault's own
    difficulty says, which is why the count is an argument and not a lookup.
    """
    if fault.id in WORK_STOPPING or reporters >= 3:
        return Priority.P1
    if reporters > 1:
        return Priority.P2
    ...
```

`session/queue.py`:
- `resolved_reporters(world, fault, at) -> list[str]` — `fault.reporters()` when it returns a list, else `[reporter_sam(world, at)]`, dropping `None` and anyone missing from `world.org.users`.
- `_candidates()` filters on `resolved_reporters(...)` being non-empty rather than `reporter_sam(...) is not None`, so a server placement with explicit reporters is now selectable.
- `open_ticket() -> list[Ticket]` applies the fault once, then builds one ticket per sampled reporter (`rng.sample` capped by `CASCADE_MAX = 3` and by remaining room in `MAX_ACTIVE`), sharing `cascade_id = f"C{n}"`. A candidate needing at least two tickets is skipped when only one slot is free.
- `open_one() -> Ticket | None` returns the first of `open_ticket()`, for tests and single-arrival callers.
- `open_cascade(fault) -> list[Ticket]` opens a named fault's cascade directly, for tests.
- `tick()` extends its arrival list rather than appending.

Each sibling gets its own `PersonaCard` (different person, different literacy and mood) and its own `report_text` from that person's persona — three tickets describing one outage in three voices is the thing being drilled.

- [x] **Step 5: Update every caller**

`grep -rn "open_ticket" tests/ src/` and update: `tests/test_queue.py`, `tests/test_web_*.py` fixtures, `tests/test_end_to_end.py`, `tests/test_grading.py`. Prefer `open_one()` in fixtures that want exactly one ticket.

- [x] **Step 6: Run the suite**

Run: `uv run pytest -v`
Expected: green except the `print.server_spooler_stopped` cases, which Task 7 delivers.

- [x] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(session): add cascade reporters and plural ticket arrivals"
```

---

### Task 6: Cascade-aware grading and after-action

**Files:**
- Modify: `src/vitsc/session/grading.py`, `src/vitsc/session/afteraction.py`, `src/vitsc/session/store.py`
- Test: `tests/test_grading.py` (extend), `tests/test_store.py` (extend)

**Interfaces:**
- Consumes: `cascade_id` (Task 5).
- Produces: `Grade.duplicate_mutations`; `AfterAction.cascade_note`; `grade_ticket(..., siblings=...)`.

- [x] **Step 1: Write the failing test**

Extend `tests/test_grading.py`:

```python
def test_cascade_siblings_all_grade_cleared_from_one_fix():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(0), now=env.world.clock)
    tickets = queue.open_cascade(get_fault("print.server_spooler_stopped"))
    fault = get_fault("print.server_spooler_stopped")

    from vitsc.faults.base import bind
    for action in bind(fault.canonical_resolutions()[0], tickets[0].placement, env.world).actions:
        env.execute(action)

    for ticket in tickets:
        ticket.close(Disposition.RESOLVED, at=env.world.clock)
        grade = grade_ticket(ticket, fault, env, queue.baseline, siblings=tickets)
        assert grade.fault_cleared is True
        assert grade.correct is True


def test_repeating_the_same_mutation_is_counted():
    """Fixing one root cause three times is not three fixes."""
    ticket = _ticket_with_calls([
        _call("print", "restart-spooler", {"host": "MER-PRT-01"}, mutating=True),
        _call("print", "restart-spooler", {"host": "MER-PRT-01"}, mutating=True),
    ])
    assert duplicate_mutations(ticket) == 1


def test_after_action_names_the_cascade():
    ...
    report = build_after_action(ticket, fault, grade, env.world, siblings=tickets)
    assert "3 tickets" in report.cascade_note
    assert report.cascade_note.endswith(".")


def test_after_action_has_no_cascade_note_for_a_single_ticket():
    report = build_after_action(ticket, fault, grade, world)
    assert report.cascade_note == ""
```

- [x] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_grading.py -v`
Expected: FAIL — `grade_ticket` takes no `siblings`, no `duplicate_mutations`.

- [x] **Step 3: Implement**

`grading.py`: add `duplicate_mutations(ticket) -> int` counting repeated `(tool, command, args)` mutating calls beyond the first, and a `duplicate_mutations` field on `Grade`. Add an optional `siblings: list[Ticket] | None = None` parameter to `grade_ticket`; it does **not** change the pass/fail logic — `is_present()` against the live world already covers siblings — it only feeds the report. Say so in a comment, because the temptation to special-case cascades in the gate is exactly what the core principle forbids.

`afteraction.py`: add `cascade_note: str`, empty for a single ticket, otherwise naming the count and the shared cause: `"One stopped print spooler on MER-PRT-01 was behind 3 tickets — the fix was a single service restart."` Add the duplicate-mutation line to the verdict chain only when the fault was cleared and duplicates exist: `"You fixed this three times. One root cause needs one fix."`

`store.py`: add `cascade_id` to the schema and `ClosedRecord` so history can show which closures were one outage. Use `ALTER TABLE ... ADD COLUMN` guarded by a `PRAGMA table_info` check, so an existing database survives.

- [x] **Step 4: Run the suite**

Run: `uv run pytest -v`
Expected: green except Task 7's fault.

- [x] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(session): grade and report cascades as one root cause"
```

---

### Task 7: The reference cascade fault and queue grouping

**Files:**
- Modify: `src/vitsc/faults/catalog/printing.py`, `src/vitsc/web/templates/_queue.html`
- Test: `tests/test_cascade.py` (remove xfails), `tests/test_web_queue.py` (extend)

**Interfaces:**
- Consumes: `FaultBase`, `reporters` (Task 5).
- Produces: `print.server_spooler_stopped`.

- [ ] **Step 1: Write the failing test**

Remove any xfail markers from Task 5's cascade tests, and add to `tests/test_cascade.py`:

```python
def test_server_spooler_reporters_are_users_of_that_server_s_printers():
    world = load_world()
    fault = get_fault("print.server_spooler_stopped")
    at = fault.placements(world)[0]
    assert at.key == "MER-PRT-01"

    reporters = fault.reporters(world, at)
    assert len(reporters) >= 3
    for sam in reporters:
        machine = world.machine_for(sam)
        assert machine is not None
        assert any(world.printers[p].host == at.key for p in machine.installed_printers)


def test_it_only_places_on_a_print_server():
    world = load_world()
    fault = get_fault("print.server_spooler_stopped")
    for at in fault.placements(world):
        assert world.machines[at.key].assigned_to is None
```

And in `tests/test_web_queue.py`:

```python
def test_cascade_siblings_are_visibly_related_in_the_queue():
    ...
    body = c.get("/").text
    assert body.count("C1") >= 2   # the shared cascade tag renders on each sibling
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cascade.py -v`
Expected: FAIL — `KeyError: 'print.server_spooler_stopped'`.

- [ ] **Step 3: Write the fault**

In `catalog/printing.py`, following `AccountLocked`'s shape:

- `id = "print.server_spooler_stopped"`, `domain = "printing"`, `difficulty = 2`, `escalation_is_correct = False`.
- `canonical_title`: "Print spooler service stopped on the print server".
- `placements()`: machines with `assigned_to is None` that host at least one printer — `MER-PRT-01` today.
- `apply()`: sets the server's `Spooler` service to `STOPPED`, and appends a matching event-log entry so `machine.eventlog` on the server tells the truth.
- `is_present()`: the server's `Spooler` is not `RUNNING`.
- `reporters()`: every user whose assigned machine has an installed printer hosted on this server, sorted for determinism.
- `symptoms()`: jargon-free and identical in substance across reporters — "Nothing comes out of the printer. I sent it four times." `onset`: "since about an hour ago". `scope`: "a couple of people near me said the same" — note this is the honest hint that it is a cascade, phrased as a person would.
- `diagnostic_path()`: the server's `machine.services`, then `printer.state`.
- `canonical_resolutions()`: one path, `machine.restart_service` with `service=Spooler` on `PLACEHOLDER` — the same action kind the existing workstation-level fault uses, reached through `print restart-spooler -from <server>`.
- `leak_terms`: `["spool", "service", "server", "queue"]`.
- `kb_articles`: `["printing-nothing-prints"]` (Task 10 authors it).

The existing workstation-level `print.spooler_stopped` stays. The pair is deliberate, in the same spirit as `account_locked`/`password_expired`: one person versus several is the differential, and `scope` is the tell.

- [ ] **Step 4: Show the relationship in the queue**

`_queue.html` renders `ticket.cascade_id` as a small tag on each sibling row. Do not group or merge the rows — the technician must notice the pattern, and pre-grouping does the noticing for them. A shared tag they can see is honest; a merged row is the answer.

- [ ] **Step 5: Run the suite**

Run: `uv run pytest -v`
Expected: fully green, including `tests/test_catalog.py` picking up the new fault automatically.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(faults): add print.server_spooler_stopped as the reference cascade"
```

---

### Task 8: The simulated tier-2

**Files:**
- Create: `src/vitsc/session/tier2.py`
- Modify: `src/vitsc/session/ticket.py`, `src/vitsc/persona/models.py`, `src/vitsc/session/grading.py`, `src/vitsc/faults/catalog/*.py`
- Test: `tests/test_tier2.py`

**Interfaces:**
- Consumes: `Ticket`, `Disposition`, `escalation_is_correct`, `escalation_reason`, `escalation_evidence`.
- Produces: `TicketState.AWAITING_TIER2`; `Ticket.escalate()`, `Ticket.reopen()`; `Tier2Response`, `review_escalation()`; `Grade.escalation_quality`.

- [ ] **Step 1: Write the failing test**

`tests/test_tier2.py`:

```python
from random import Random

import pytest

import vitsc.faults.catalog  # noqa: F401
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import all_faults, get_fault
from vitsc.persona.templates import TemplatePersona
from vitsc.session.queue import SessionQueue
from vitsc.session.ticket import TicketState
from vitsc.session.tier2 import review_escalation
from vitsc.world.seed import load_world


def _ticket(fault_id, seed=0):
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(seed), now=env.world.clock)
    fault = get_fault(fault_id)
    at = fault.placements(env.world)[0]
    return env, queue, fault, queue.open_for(fault, at)[0]


def test_escalating_moves_to_awaiting_not_closed():
    env, queue, fault, ticket = _ticket("ad.offboarded_reactivation")
    ticket.escalate(note="Account is disabled; HR authorisation needed.", at=env.world.clock)
    assert ticket.state is TicketState.AWAITING_TIER2
    assert ticket.closed_at is None


def test_a_good_escalation_of_an_escalate_only_fault_is_accepted():
    env, queue, fault, ticket = _ticket("ad.offboarded_reactivation")
    ticket.escalate(note=f"Account {ticket.placement.key} is disabled and was offboarded. "
                         "Needs HR authorisation before re-enabling.", at=env.world.clock)
    response = review_escalation(ticket, fault, env.world)
    assert response.accepted is True
    assert fault.escalation_reason.split()[0].lower() in response.text.lower()


def test_a_fixable_fault_is_bounced_back():
    env, queue, fault, ticket = _ticket("ad.account_locked")
    ticket.escalate(note="User cannot log in, please fix.", at=env.world.clock)
    response = review_escalation(ticket, fault, env.world)
    assert response.accepted is False
    assert "within" in response.text.lower() or "your" in response.text.lower()


def test_a_bounce_reopens_the_ticket_and_leaves_a_tier2_turn():
    env, queue, fault, ticket = _ticket("ad.account_locked")
    ticket.escalate(note="Please fix.", at=env.world.clock)
    response = review_escalation(ticket, fault, env.world)
    ticket.reopen(response.text)
    assert ticket.state is TicketState.IN_PROGRESS
    assert ticket.chat[-1].speaker == "tier2"
    assert ticket.disposition is None


def test_an_evidence_free_note_is_rejected_even_when_escalation_is_right():
    env, queue, fault, ticket = _ticket("ad.offboarded_reactivation")
    ticket.escalate(note="Not my problem.", at=env.world.clock)
    response = review_escalation(ticket, fault, env.world)
    assert response.accepted is False
    assert "what you found" in response.text.lower()


def test_every_escalate_correct_fault_explains_who_owns_it():
    for fault in all_faults():
        if fault.escalation_is_correct:
            assert fault.escalation_reason, f"{fault.id} has no escalation_reason"


def test_accepting_closes_the_ticket_as_escalated():
    env, queue, fault, ticket = _ticket("ad.offboarded_reactivation")
    ticket.escalate(note=f"{ticket.placement.key} is disabled after offboarding; HR must authorise.",
                    at=env.world.clock)
    response = review_escalation(ticket, fault, env.world)
    ticket.accept_escalation(at=env.world.clock)
    assert ticket.state is TicketState.CLOSED
    assert ticket.disposition.value == "escalated"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_tier2.py -v`
Expected: FAIL — no module `vitsc.session.tier2`.

- [ ] **Step 3: Extend the ticket lifecycle**

`session/ticket.py`:
- `TicketState` gains `AWAITING_TIER2 = "awaiting_tier2"`.
- `escalation_note: str | None` and `tier2_bounces: int = 0` on `Ticket`.
- `escalate(note, at)`: records the note, moves to `AWAITING_TIER2`. Raises if already closed.
- `reopen(text)`: appends a `tier2` `ChatTurn`, increments `tier2_bounces`, returns to `IN_PROGRESS`, leaves `disposition` `None`.
- `accept_escalation(at)`: delegates to `close(Disposition.ESCALATED, at)`.

`persona/models.py`: `ChatTurn.speaker` becomes `Literal["tech", "user", "tier2"]`. Templates rendering chat must style the third speaker distinctly — it is not the reporting user, and confusing the two would be actively misleading.

- [ ] **Step 4: Write the tier-2 reviewer**

`session/tier2.py`:

```python
"""The simulated tier-2 queue.

Deterministic and template-driven on purpose. The bounce decision has to be
reproducible in tests and correct with nothing running on localhost, so it
never touches a model — same reasoning as `TemplatePersona`.

Tier-2 judges two things, in this order:
  1. Is the note usable? An escalation with no findings in it is bounced even
     when escalating was the right call — "not my problem" is not a handoff.
  2. Does this belong to tier-2 at all? `escalation_is_correct` owns that,
     and a fixable ticket comes straight back. That bounce is the lesson.
"""
```

`Tier2Response(accepted: bool, text: str)`. `review_escalation(ticket, fault, world) -> Tier2Response`:

- **Evidence check:** the note must be more than a few words and must mention the placement target (or the bound target of any `escalation_evidence` / `diagnostic_path` query). Keep it forgiving — the drill teaches writing a usable handoff, not passing a string match. Case-insensitive, substring, and satisfied by any one of the evidence targets.
- If evidence is missing → not accepted, text asks for what they found.
- Else if `fault.escalation_is_correct` → accepted, text quotes `escalation_reason` and says what tier-2 will do next.
- Else → not accepted, text names the scope boundary and points at the fault's first diagnostic query without naming the cause. This is the one place a bounce message must be careful: "check the account's status in AD" is a nudge; "the account is locked" is the answer.

Populate `escalation_reason` on the two escalate-correct faults: `ad.offboarded_reactivation` → HR/manager authorisation before re-enabling a departed employee's account; `endpoint.failing_disk` → hardware replacement and a data-preserving swap, not a software fix.

- [ ] **Step 5: Grade the handoff**

`grading.py`: add `escalation_quality: str` — `"none"` (never escalated), `"accepted"`, `"bounced"` — and include bounces in the correctness picture without double-punishing: a ticket that was bounced and then correctly fixed is still correct, but the after-action says the escalation was wrong. Add `SessionQueue.open_for(fault, at)` (used by the tests above) opening a ticket for a named fault and placement.

- [ ] **Step 6: Run the suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(session): add a simulated tier-2 with accept and bounce"
```

---

### Task 9: The tier-2 web flow

**Files:**
- Create: `src/vitsc/web/routes/escalate.py`, `src/vitsc/web/templates/_escalate.html`, `_tier2.html`
- Modify: `src/vitsc/web/app.py`, `src/vitsc/web/templates/_ticket.html`, `_chat.html`, `src/vitsc/web/routes/close.py`, `src/vitsc/session/afteraction.py`
- Test: `tests/test_web_escalate.py`

**Interfaces:**
- Consumes: Task 8's `review_escalation`, `escalate`, `reopen`, `accept_escalation`.
- Produces: `GET /ticket/{id}/escalate`, `POST /ticket/{id}/escalate`.

- [ ] **Step 1: Write the failing test**

`tests/test_web_escalate.py`:

```python
import pytest
from fastapi.testclient import TestClient

from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.fixture
def client(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    return TestClient(create_app(session)), session


def test_the_escalation_form_asks_for_a_note(client):
    c, session = client
    ticket = session.queue.open_one()
    body = c.get(f"/ticket/{ticket.id}/escalate").text
    assert 'name="note"' in body


def test_a_bounced_escalation_returns_the_ticket_to_the_queue(client):
    c, session = client
    ticket = session.queue.open_for(get_fault("ad.account_locked"),
                                   get_fault("ad.account_locked").placements(session.env.world)[0])[0]
    r = c.post(f"/ticket/{ticket.id}/escalate", data={"note": "please fix"})
    assert r.status_code == 200
    reloaded = session.queue.get(ticket.id)
    assert reloaded.state.value == "in_progress"
    assert reloaded.tier2_bounces == 1


def test_an_accepted_escalation_renders_the_after_action(client):
    c, session = client
    fault = get_fault("ad.offboarded_reactivation")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    r = c.post(f"/ticket/{ticket.id}/escalate",
               data={"note": f"{ticket.placement.key} is disabled after offboarding, HR must authorise."})
    assert "escalated" in r.text.lower()
    assert session.queue.get(ticket.id).state.value == "closed"


def test_escalating_a_closed_ticket_is_a_conflict(client):
    c, session = client
    ticket = session.queue.open_one()
    c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
    r = c.post(f"/ticket/{ticket.id}/escalate", data={"note": "too late"})
    assert r.status_code == 409


def test_the_bounce_text_does_not_name_the_cause(client):
    """A bounce nudges. It must not hand over the diagnosis."""
    c, session = client
    fault = get_fault("ad.account_locked")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    r = c.post(f"/ticket/{ticket.id}/escalate", data={"note": "cannot log in"})
    for term in fault.leak_terms:
        assert term.strip().lower() not in r.text.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_web_escalate.py -v`
Expected: FAIL — 404, no escalate route.

- [ ] **Step 3: Implement the route**

`web/routes/escalate.py`: `GET` renders the note form (with a reminder of what a usable handoff contains). `POST` calls `ticket.escalate(note, at=world.clock)`, then `review_escalation`. On accept: `accept_escalation`, grade, build the after-action, `store.save_closed`, render `_afteraction.html` — the same tail as `close.py`, so factor that shared sequence into one helper rather than duplicating it. On bounce: `ticket.reopen(response.text)` and render `_tier2.html` inside the ticket pane. Guard `TicketState.CLOSED` with 409, matching `close_ticket`.

Register the router in `app.py`. Add an "Escalate" control to `_ticket.html` beside Close, and render `tier2` chat turns distinctly in `_chat.html`.

`afteraction.py`: add `tier2: str` carrying the outcome, and extend the verdict chain — a bounced-then-fixed ticket reads "You tried to hand this off; it was yours. You did fix it after."

- [ ] **Step 4: Run the suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(web): add the tier-2 escalation flow"
```

---

### Task 10: Knowledge base content and loader

**Files:**
- Create: `src/vitsc/kb/__init__.py`, `models.py`, `loader.py`, `src/vitsc/data/kb/*.md`
- Test: `tests/test_kb.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Article`; `load_articles()`, `get_article(id)`, `search_articles(text)`.

- [ ] **Step 1: Write the failing test**

`tests/test_kb.py`:

```python
import vitsc.faults.catalog  # noqa: F401
from vitsc.faults.registry import all_faults
from vitsc.kb.loader import get_article, load_articles, search_articles


def test_articles_load_with_complete_frontmatter():
    articles = load_articles()
    assert len(articles) >= 8
    for a in articles.values():
        assert a.id and a.title and a.keywords and a.body
        assert a.domain in {"identity", "network", "printing", "mail", "endpoint", "general"}


def test_search_finds_by_keyword_and_title():
    assert any(a.id == "printing-nothing-prints" for a in search_articles("printer"))
    assert search_articles("zzzzz") == []


def test_no_article_is_an_answer_key():
    """A KB that maps symptoms to causes deletes the drill."""
    articles = load_articles()
    for fault in all_faults():
        for a in articles.values():
            text = f"{a.title} {a.body}".lower()
            assert fault.id.lower() not in text, f"{a.id} names {fault.id}"
            assert fault.canonical_title.lower() not in text, f"{a.id} names {fault.id}'s cause"


def test_every_fault_kb_link_resolves():
    for fault in all_faults():
        for article_id in fault.kb_articles:
            assert get_article(article_id) is not None, f"{fault.id} links missing {article_id}"


def test_articles_are_procedural():
    """Each article tells you how to check something, not what the answer is."""
    for a in load_articles().values():
        assert "## Check" in a.body or "## Steps" in a.body
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_kb.py -v`
Expected: FAIL — no module `vitsc.kb.loader`.

- [ ] **Step 3: Write the format and loader**

Articles are markdown with a YAML frontmatter block (`pyyaml` is already a dependency):

```markdown
---
id: printing-nothing-prints
title: Nothing prints
domain: printing
keywords: [printer, print, spooler, queue, nothing prints]
---

Print jobs that vanish without an error are almost always stopped between the
workstation and the print server, not lost on the printer itself.

## Check

1. Ask how many people are affected. One person points at their workstation;
   several people pointing at the same printer point at the print server.
2. `remote services -host <workstation>` — confirm the local spooler.
3. `print get-printer -printer <printer>` — confirm the queue and its host.
4. `remote services -host <print server>` — confirm the server's spooler.

## Notes

Meridian hosts every printer on MER-PRT-01. Printer names carry their
department: PRT-ACC-01, PRT-OPS-01, PRT-WH-01.
```

`kb/models.py`: `Article(id, title, domain, keywords: list[str], body: str)`. `kb/loader.py`: read `src/vitsc/data/kb/*.md` via `importlib.resources` (as `world/seed.py` does), split the frontmatter, cache with `lru_cache`. `search_articles(text)` scores on keyword and title substring matches, returns them ranked, and returns `[]` on no match.

- [ ] **Step 4: Author the eight articles**

All original content — the spec forbids redistributing Microsoft docs (§2), and hand-authoring is also what makes this a portfolio artifact. Each is procedure plus Meridian's own conventions, never "symptom X means cause Y":

| id | Covers |
|---|---|
| `general-triage-first-questions` | The four questions to ask before touching anything; how scope separates one-user from many-user faults. |
| `general-meridian-estate` | Naming conventions, subnets, OUs, servers and their roles. |
| `identity-cannot-sign-in` | How to read an account's state: enabled, lock flag, bad-password count, password expiry — and that these are four different findings. |
| `identity-missing-drive` | Why a mapped drive can vanish without the drive changing; how to check membership against a share's required group. |
| `network-no-internet` | Reading `ipconfig` output; what a self-assigned address looks like; separating name resolution from reachability. |
| `printing-nothing-prints` | The workstation → queue → server chain, in that order. |
| `endpoint-slow-or-failing` | Free space, profile state, and disk health as three separate checks; when a finding is a hardware call. |
| `mail-cannot-send-or-receive` | Mailbox size against quota, rules and forwarding, transport queue — and that a forwarding rule to an outside address is a security matter, not a cleanup task. |

Cross-reference the fault catalog while writing: every fault's `kb_articles` must point at one of these, and the `no_article_is_an_answer_key` test must pass — mentioning that a bad-password count exists is procedure; writing "if the count is above 5 the account is locked, unlock it" is the answer key.

- [ ] **Step 5: Populate `kb_articles` across the catalog**

Set `kb_articles` on all thirteen faults. `ad.account_locked` and `ad.password_expired` both point at `identity-cannot-sign-in` — the shared article is exactly right, because the differential is the lesson.

- [ ] **Step 6: Run the suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(kb): add the original-content knowledge base and loader"
```

---

### Task 11: The KB tool and after-action links

**Files:**
- Create: `src/vitsc/tools/kb.py`, `src/vitsc/web/routes/kb.py`, `src/vitsc/web/templates/_kb.html`
- Modify: `src/vitsc/tools/registry.py`, `src/vitsc/session/grading.py`, `src/vitsc/session/afteraction.py`, `src/vitsc/web/app.py`, `src/vitsc/web/templates/_afteraction.html`
- Test: `tests/test_tools_kb.py`, `tests/test_web_kb.py`

**Interfaces:**
- Consumes: Task 10's loader.
- Produces: `KnowledgeBase` tool (`kb search`, `kb read`); `Grade.kb_consulted`; `AfterAction.kb_suggestions`.

- [ ] **Step 1: Write the failing test**

`tests/test_tools_kb.py`:

```python
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.tools.base import ToolLog
from vitsc.tools.registry import get_tool
from vitsc.world.seed import load_world


def test_kb_search_renders_hits():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "search", {"text": "printer"})
    assert call.ok and "printing-nothing-prints" in call.rendered


def test_kb_read_renders_the_body():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "read", {"id": "general-triage-first-questions"})
    assert call.ok and "## Check" in call.rendered


def test_kb_calls_are_never_mutating():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    for command, args in [("search", {"text": "printer"}), ("read", {"id": "general-meridian-estate"})]:
        assert tool.invoke(env, log, command, args).mutating is False


def test_a_missing_article_fails_without_raising():
    tool, env, log = get_tool("kb"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "read", {"id": "nope"})
    assert call.ok is False


def test_the_kb_tool_does_not_import_faults_or_world():
    """The architecture rule binds this tool like every other."""
    import ast, pathlib
    src = pathlib.Path("src/vitsc/tools/kb.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith(("vitsc.faults", "vitsc.world"))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_tools_kb.py -v`
Expected: FAIL — `KeyError: 'kb'`.

- [ ] **Step 3: Implement the tool**

`tools/kb.py`: a `Tool` (not a `DispatchTool` — it reads articles, not the environment, so it has no `Query` to issue). It must still record a `ToolCall` on every call with `mutating=False`, because the log is what grading reads. `vitsc.kb` is neither `vitsc.faults` nor `vitsc.world`, so importing the loader is within the architecture rule — and Task 10 already guarantees no article names a cause, which is what keeps this from being a fault import by the back door. Extend `tests/test_architecture.py` to whitelist nothing new: the existing assertions should pass unchanged.

Register it in `tools/registry.py`. Note that `tests/test_web_tools.py::test_tool_pane_lists_every_tool` enumerates tool names — add `kb` there.

- [ ] **Step 4: Grade and report the KB**

`grading.py`: `kb_consulted: bool` — any `kb` tool call on the ticket. It is a diligence signal, never a gate: no correctness field may depend on it.

`afteraction.py`: `kb_suggestions: list[str]` from `fault.kb_articles`, rendered as links in `_afteraction.html`, with a line that distinguishes the two cases — an article that was read and one that would have helped. If the technician found a distractor, name it here too using `SessionQueue.distractors` and each distractor's `note`, so "the stopped search service you found was already like that, and unrelated" is said out loud rather than left as a mystery.

`web/routes/kb.py`: `GET /kb?q=` and `GET /kb/{id}` rendering `_kb.html`, so the KB is browsable outside a ticket as well.

- [ ] **Step 5: Run the suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(kb): add the KB tool, grading signal and after-action links"
```

---

### Task 12: The mail world model

**Files:**
- Modify: `src/vitsc/world/models.py`, `src/vitsc/data/company.yaml`, `src/vitsc/world/seed.py`
- Test: `tests/test_world_seed.py` (extend)

**Interfaces:**
- Consumes: nothing.
- Produces: `Mailbox`, `MailRule`, `MailSystem`; `World.mail`, `World.mailbox_for(sam)`.

- [ ] **Step 1: Write the failing test**

Extend `tests/test_world_seed.py`:

```python
def test_every_user_has_a_mailbox():
    world = load_world()
    for sam in world.org.users:
        mailbox = world.mailbox_for(sam)
        assert mailbox is not None
        assert mailbox.primary_smtp.endswith("@meridian.local")


def test_mail_is_healthy_at_rest():
    world = load_world()
    assert world.mail.transport_state.value == "Running"
    assert world.mail.queue_depth < 10
    for mailbox in world.mail.mailboxes.values():
        assert mailbox.used_mb < mailbox.quota_mb
        assert mailbox.forwarding_smtp is None
        assert mailbox.rules == []


def test_the_mail_server_is_a_machine_like_any_other():
    world = load_world()
    assert "MER-MB-01" in world.machines
    assert world.machines["MER-MB-01"].assigned_to is None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_world_seed.py -v`
Expected: FAIL — `World` has no `mail`.

- [ ] **Step 3: Add the models**

`world/models.py`:

```python
class MailRule(BaseModel):
    name: str
    forward_to: str | None = None
    delete_after: bool = False
    created_by: str | None = None   # who set it, for an escalation's evidence


class Mailbox(BaseModel):
    owner_sam: str
    primary_smtp: str
    server: str
    quota_mb: float = 51200.0
    used_mb: float = 4096.0
    rules: list[MailRule] = Field(default_factory=list)
    forwarding_smtp: str | None = None
    litigation_hold: bool = False


class MailSystem(BaseModel):
    server: str
    transport_state: ServiceState = ServiceState.RUNNING
    queue_depth: int = 0
    mailboxes: dict[str, Mailbox] = Field(default_factory=dict)
```

`World` gains `mail: MailSystem` and `mailbox_for(sam) -> Mailbox | None`. `company.yaml` gains `MER-MB-01` under `servers` with `role: mailserver` and a `mail:` block giving the domain default quota; `seed.py` derives one mailbox per user from their `upn` — the org is hand-authored, but twelve near-identical mailbox rows are noise, and deriving them keeps a new user in `company.yaml` from silently lacking mail.

Note the invariant surface deliberately does **not** grow here: mail invariants (a deleted mailbox, a quota dropped below usage) are worth adding, but every new invariant is a new way for a fault to accuse itself, so they wait until 2b has mail faults to test them against.

- [ ] **Step 4: Run the suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(world): add mailboxes and the mail system"
```

---

### Task 13: Mail query and action kinds

**Files:**
- Modify: `src/vitsc/env/simulated.py`
- Test: `tests/test_simulated_env.py` (extend)

**Interfaces:**
- Consumes: Task 12's models.
- Produces: reads `mail.mailbox`, `mail.rules`, `mail.queue`; actions `mail.set_quota`, `mail.archive`, `mail.remove_rule`, `mail.restart_transport`.

- [ ] **Step 1: Write the failing test**

Extend `tests/test_simulated_env.py`:

```python
def test_mail_mailbox_read_renders_exchange_shaped_output():
    env = SimulatedEnvironment(load_world())
    obs = env.read(Query(kind="mail.mailbox", target="m.alvarez"))
    assert obs.ok
    assert "PrimarySmtpAddress" in obs.rendered
    assert "TotalItemSize" in obs.rendered


def test_mail_read_of_an_unknown_user_fails_cleanly():
    env = SimulatedEnvironment(load_world())
    assert env.read(Query(kind="mail.mailbox", target="nobody")).ok is False


def test_set_quota_raises_headroom():
    env = SimulatedEnvironment(load_world())
    env.world.mail.mailboxes["m.alvarez"].used_mb = 51000.0
    result = env.execute(Action(kind="mail.set_quota", target="m.alvarez",
                               args={"quota_mb": "102400"}))
    assert result.ok
    assert env.world.mail.mailboxes["m.alvarez"].quota_mb == 102400.0


def test_archive_reduces_usage_without_touching_quota():
    env = SimulatedEnvironment(load_world())
    box = env.world.mail.mailboxes["m.alvarez"]
    box.used_mb = 51000.0
    before = box.quota_mb
    assert env.execute(Action(kind="mail.archive", target="m.alvarez")).ok
    assert box.used_mb < 51000.0
    assert box.quota_mb == before


def test_remove_rule_removes_only_the_named_rule():
    env = SimulatedEnvironment(load_world())
    box = env.world.mail.mailboxes["m.alvarez"]
    box.rules = [MailRule(name="Keep"), MailRule(name="Drop", forward_to="x@example.com")]
    assert env.execute(Action(kind="mail.remove_rule", target="m.alvarez",
                             args={"name": "Drop"})).ok
    assert [r.name for r in box.rules] == ["Keep"]


def test_restart_transport_runs_the_queue_down():
    env = SimulatedEnvironment(load_world())
    env.world.mail.transport_state = ServiceState.STOPPED
    env.world.mail.queue_depth = 400
    assert env.execute(Action(kind="mail.restart_transport", target="MER-MB-01")).ok
    assert env.world.mail.transport_state is ServiceState.RUNNING
    assert env.world.mail.queue_depth == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_simulated_env.py -v`
Expected: FAIL — unknown query kind `mail.mailbox`.

- [ ] **Step 3: Implement the dispatch methods**

Dots become underscores, per the existing `getattr` dispatch: `_read_mail_mailbox`, `_read_mail_rules`, `_read_mail_queue`, `_do_mail_set_quota`, `_do_mail_archive`, `_do_mail_remove_rule`, `_do_mail_restart_transport`. Follow the established shape — `Observation(ok=..., data=..., rendered=...)` with `rendered` matching what the real cmdlet prints, and a clean `ok=False` for an unknown target rather than an exception.

Heed the harness gotcha documented in `CLAUDE.md`: `SimulatedEnvironment` is constructed *after* `apply()`, so cache nothing from mutable mail state at `__init__`. `mail.archive` must reduce `used_mb` to a fixed fraction of quota rather than to a remembered original, for exactly that reason.

- [ ] **Step 4: Run the suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(env): add mail query and action kinds"
```

---

### Task 14: The mail console tool

**Files:**
- Create: `src/vitsc/tools/mail.py`
- Modify: `src/vitsc/tools/registry.py`, `src/vitsc/web/templates/_tools.html`
- Test: `tests/test_tools_mail.py`, `tests/test_web_tools.py` (extend)

**Interfaces:**
- Consumes: Task 13's kinds.
- Produces: `MailConsole` (`mail`), commands `get-mailbox`, `get-rules`, `get-queue`, `set-quota`, `archive`, `remove-rule`, `restart-transport`.

- [ ] **Step 1: Write the failing test**

`tests/test_tools_mail.py`:

```python
def test_get_mailbox_renders_like_the_real_cmdlet():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "get-mailbox", {"sam": "m.alvarez"})
    assert call.ok and call.mutating is False
    assert "PrimarySmtpAddress" in call.rendered


def test_writes_are_flagged_mutating():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "set-quota", {"sam": "m.alvarez", "quota_mb": "102400"})
    assert call.ok and call.mutating is True


def test_a_missing_parameter_is_reported_not_raised():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "set-quota", {"sam": "m.alvarez"})
    assert call.ok is False and "quota_mb" in call.rendered


def test_an_unknown_command_matches_the_shell_s_own_error():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    call = tool.invoke(env, log, "Get-Everything", {})
    assert call.ok is False and "not recognized" in call.rendered


def test_every_call_is_logged():
    tool, env, log = get_tool("mail"), SimulatedEnvironment(load_world()), ToolLog()
    tool.invoke(env, log, "get-mailbox", {"sam": "m.alvarez"})
    tool.invoke(env, log, "nope", {})
    assert len(log.calls) == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_tools_mail.py -v`
Expected: FAIL — `KeyError: 'mail'`.

- [ ] **Step 3: Implement**

A `DispatchTool` subclass with `READS`/`WRITES` maps and `TARGET_PARAM = "sam"`, overriding `target_key` so `get-queue`/`restart-transport` target the server instead. Nothing new is needed in `DispatchTool` itself — if it looks like it is, that is a signal the tool is reaching past `Query`/`Action`.

Register in `tools/registry.py`, add to `_tools.html`, and extend `test_tool_pane_lists_every_tool` with `mail`. `tests/test_architecture.py` covers the new file automatically via its `glob`.

- [ ] **Step 4: Run the suite**

Run: `uv run pytest -v`
Expected: all green, architecture tests included.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(tools): add the mail console"
```

---

### Task 15: The two reference mail faults

**Files:**
- Create: `src/vitsc/faults/catalog/mail.py`
- Modify: `src/vitsc/faults/catalog/__init__.py`, `src/vitsc/session/ticket.py`
- Test: covered by `tests/test_catalog.py`; add `tests/test_faults_mail.py` for the specifics

**Interfaces:**
- Consumes: Tasks 12–14.
- Produces: `mail.mailbox_full`, `mail.external_forwarding_rule`.

- [ ] **Step 1: Write the failing test**

`tests/test_faults_mail.py`:

```python
def test_mailbox_full_has_two_honest_fix_paths():
    """Raise the quota or reduce the usage — both are real answers."""
    fault = get_fault("mail.mailbox_full")
    assert len(fault.canonical_resolutions()) == 2
    labels = {r.label for r in fault.canonical_resolutions()}
    assert any("quota" in l.lower() for l in labels)
    assert any("archive" in l.lower() for l in labels)


def test_forwarding_rule_is_escalate_correct_and_says_why():
    fault = get_fault("mail.external_forwarding_rule")
    assert fault.escalation_is_correct is True
    assert fault.escalation_reason
    assert "security" in fault.escalation_reason.lower()


def test_forwarding_symptoms_describe_what_a_person_would_notice():
    world = load_world()
    fault = get_fault("mail.external_forwarding_rule")
    at = fault.placements(world)[0]
    fault.apply(world, at, Random(0))
    symptoms = fault.symptoms(world, at)
    for term in ("rule", "forward", "mailbox", "exfil"):
        assert term not in symptoms.opening.lower()


def test_mail_faults_are_priced_into_triage():
    from vitsc.session.ticket import WORK_STOPPING
    assert "mail.mailbox_full" in WORK_STOPPING
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_faults_mail.py -v`
Expected: FAIL — `KeyError: 'mail.mailbox_full'`.

- [ ] **Step 3: Write the faults**

`catalog/mail.py`, both inheriting `FaultBase` and registering via `register()`:

**`mail.mailbox_full`** — `domain="mail"`, `difficulty=2`, not escalate-correct. `apply()` sets `used_mb` just over `quota_mb`. `is_present()`: `used_mb >= quota_mb`. Symptoms: "My emails are all sitting in the outbox and nothing is going out." Two canonical resolutions — `mail.set_quota` (grant headroom) and `mail.archive` (reduce usage) — which is the point of picking this fault: it is the clearest demonstration in the catalog that the gate is world state and not a chosen button. `diagnostic_path()`: `mail.mailbox` on `PLACEHOLDER`. `leak_terms`: `["quota", "mailbox", "full", "limit", "archive"]`. Add it to `WORK_STOPPING` — a person who cannot send mail is stopped.

**`mail.external_forwarding_rule`** — `domain="mail"`, `difficulty=4`, **escalate-correct**. `apply()` adds a `MailRule` forwarding to an outside address and sets `forwarding_smtp`. `is_present()`: any rule forwarding outside `meridian.local`. Symptoms: "Customers keep replying to messages I never sent them." — perceivable, jargon-free, and genuinely alarming rather than merely broken. `escalation_reason`: the account is compromised, so this is a security incident — deleting the rule destroys the evidence of when it was created and by whom, and the response has to include a credential reset and a review of what was sent. `escalation_evidence`: `mail.rules` on `PLACEHOLDER`, so tier-2 wants the finding in the note. `leak_terms`: `["forward", "rule", "compromis", "phish", "hack"]`.

Note the deliberate asymmetry with the other two escalate-correct faults: `ad.offboarded_reactivation` needs authorisation and `endpoint.failing_disk` needs hardware, but this one is escalate-correct because *acting* is the mistake. Three different reasons a ticket is not yours is a better drill than three flavours of the same reason.

`catalog/__init__.py` imports the new module so registration fires.

- [ ] **Step 4: Run the conformance harness**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: the two new faults conform across every placement with no new test written — absent-then-present, a discoverable diagnostic path, every canonical resolution clearing `is_present()` with no invariant violations, and symptoms free of both their own leak terms and the shared `JARGON` set. If the symptom check trips, rewrite the symptom, never the check.

- [ ] **Step 5: Run the suite**

Run: `uv run pytest -v`
Expected: all green, 13 faults registered.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(faults): add the mail domain's reference faults"
```

---

### Task 16: End-to-end coverage for every new surface

**Files:**
- Modify: `tests/test_end_to_end.py`
- Test: itself

**Interfaces:**
- Consumes: everything above.
- Produces: `HTTP_FIX` entries for the three new faults; cascade and tier-2 end-to-end paths.

- [ ] **Step 1: Extend the HTTP fix table**

`tests/test_end_to_end.py` already asserts every non-escalation fault has an `HTTP_FIX` entry and resolves it by posting through `POST /ticket/{id}/tool` — that guard will fail on the new faults until entries exist. Add them:

| fault | `HTTP_FIX` entry | `TARGET_FIELD` |
|---|---|---|
| `print.server_spooler_stopped` | `("print", "restart-spooler")` | `restart-spooler` → `from` (already present) |
| `mail.mailbox_full` | `("mail", "set-quota")` | add `set-quota` → `sam` |

Note the print entry reuses the existing `restart-spooler` command rather than needing a new one: `PrintManagement.restart-spooler` maps to `machine.restart_service`, hardcodes `service=Spooler` in `query_args`, and takes its target from the `from` field — so a server hostname is a legal target already. The `remote` tool has no service-restart command (only `inspect`, `services`, `clear-disk`); do not add one for this.

`mail.external_forwarding_rule` is escalate-correct and needs no entry — but the existing guard must keep proving that only escalate-correct faults are absent from the table, not merely that the table is non-empty.

- [ ] **Step 2: Write the new end-to-end tests**

```python
def test_a_cascade_can_be_worked_through_http():
    """Three tickets, one fix, all three grade cleared — over HTTP only."""
    ...
    tickets = session.queue.open_cascade(get_fault("print.server_spooler_stopped"))
    c.post(f"/ticket/{tickets[0].id}/tool", data={
        "tool": "print", "command": "restart-spooler", "args": "from=MER-PRT-01"})
    for ticket in tickets:
        r = c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
        assert "Resolved correctly" in r.text


def test_a_bounced_escalation_can_be_recovered_through_http():
    """The teaching path: hand it off, get it back, fix it."""
    ...
    c.post(f"/ticket/{t.id}/escalate", data={"note": "cannot log in"})
    assert session.queue.get(t.id).state.value == "in_progress"
    c.post(f"/ticket/{t.id}/tool", data={"tool": "ad", "command": "unlock", "args": f"sam={sam}"})
    r = c.post(f"/ticket/{t.id}/close", data={"disposition": "resolved"})
    assert "escalat" in r.text.lower()   # the report says the handoff was wrong


def test_a_mail_ticket_can_be_worked_through_http():
    ...


def test_a_seeded_distractor_does_not_block_any_ticket():
    """A full pass with noise in the world."""
    session = AppSession.build(db_path=..., seed=11)
    assert session.queue.distractors
    ...
```

- [ ] **Step 3: Run the suite**

Run: `uv run pytest -v`
Expected: all green.

- [ ] **Step 4: Drive it manually**

```bash
uv run python -m vitsc
```

Work four tickets at `http://127.0.0.1:8000`: a cascade (confirm three tickets share a tag and one restart closes all three), a bounced escalation (confirm the bounce text nudges without naming the cause), a mail ticket (confirm `MailConsole` output reads like Exchange), and any ticket while a distractor is seeded (confirm the after-action says the anomaly was pre-existing).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test: cover cascades, tier-2, mail and distractors end to end"
```

---

### Task 17: Documentation refresh

**Files:**
- Modify: `CLAUDE.md`, `docs/superpowers/specs/2026-08-07-virtual-it-support-center-design.md`
- Create: `docs/superpowers/plans/2026-08-14-phase-2b-catalog.md` (outline only)

- [ ] **Step 1: Update `CLAUDE.md`**

The "What this is" section still says Phase 1 is complete and Phase 2 planning has not started. Rewrite it for the 2a state, and add to the architecture section: the `Distractor` layer, `session/tier2.py`, `vitsc.kb`, the mail slice, and `FaultBase`. Add the new mechanical guarantees to the list of things enforced by tests rather than convention — distractor non-interference, the KB answer-key check, leak terms never reaching a prompt.

- [ ] **Step 2: Extend the "deliberately diverges" table**

Add any place 2a's implementation departed from this plan, with the reason — that table is the most useful thing in `CLAUDE.md` for the next session and it only stays useful if it is written while the reason is fresh.

- [ ] **Step 3: Update the spec's catalog table**

Spec §6's "v1 catalog (10 faults)" table now understates reality. Add the three new faults with a note that the catalog is mid-expansion, and add the `Fault` protocol's four new members to the §6 listing so the spec and the code agree.

- [ ] **Step 4: Outline Phase 2b**

Write the 2b plan's skeleton only — goal, constraints, the fault-per-task breakdown, and the Definition of Done. The detail belongs in a plan written against the finished 2a code, not guessed at now.

- [ ] **Step 5: Commit and push**

```bash
git add -A && git commit -m "docs: refresh CLAUDE.md and the spec for Phase 2a"
git push -u origin claude/app-development-status-l2rqpe
```

---

## Definition of Done

Phase 2a is complete when all of the following hold:

- [ ] `uv run pytest` is green with LM Studio **not** running.
- [ ] `uv run pytest` is green with LM Studio **running** — a manual check on the user's own machine, per `docs/verifying-lmstudio.md`. Not verifiable in CI or in a sandboxed container; do not mark it from a test run.
- [ ] `VITSC_PERSONA=lmstudio uv run python -m vitsc` roleplays every ticket through the model, and stopping LM Studio mid-session shows the degraded banner without breaking the queue.
- [ ] Thirteen faults conform across every placement, in all five domains.
- [ ] Every distractor passes the non-interference harness: it changes no fault's `is_present()`, trips no invariant, is visible through a declared query, and breaks no canonical fix.
- [ ] A cascade opens several tickets from one placement, one fix clears all of them, and the after-action names the shared root cause.
- [ ] Escalating a fixable ticket bounces back with a nudge that contains none of the fault's leak terms; escalating an escalate-correct ticket with evidence is accepted and closes it.
- [ ] No KB article names a fault id or a `canonical_title`, and every `kb_articles` link resolves.
- [ ] `grep -r "from vitsc.faults" src/vitsc/tools/` returns nothing, and `tests/test_architecture.py` is green with `mail.py` and `kb.py` present.
- [ ] No leak term appears in any system prompt.
- [ ] A full ticket can be worked in the browser in all five domains.

---

## Phase 2b outline (not this plan)

Written properly once 2a lands. Target: 30+ faults total, so ~18 more.

| Domain | Have | Add | Candidates |
|---|---|---|---|
| identity | 4 | +3 | expired cached credentials on a laptop; a group nested one level deeper than the obvious one; a UPN/sam mismatch after a name change (escalate-correct — needs HR to confirm the legal name) |
| network | 2 | +4 | wrong subnet mask; a duplicate static IP (a cascade — two machines, two tickets); gateway unreachable; a proxy setting left behind |
| printing | 2 | +3 | printer offline at the device; a stuck job at the head of the queue; a driver mismatch after a model swap |
| endpoint | 2 | +4 | corrupt user profile; a service set to Disabled rather than merely stopped; time skew breaking authentication; RAM failure (escalate-correct) |
| mail | 2 | +4 | transport queue stalled (a cascade — several people report late mail); a delegate left over from a departed employee; an autodiscover failure; a distribution list nobody owns |

Each 2b fault is authored complete: placements, symptoms that survive the `JARGON` check, a diagnostic path, canonical resolutions, `kb_articles`, and `reporters()`/`escalation_reason` where they apply. New KB articles as the estate grows. Mail invariants (deleted mailbox, quota below usage) land here, where there are mail faults to test them against.
