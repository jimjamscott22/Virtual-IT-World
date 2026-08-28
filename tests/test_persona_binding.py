from random import Random

from vitsc.faults.registry import get_fault
from vitsc.persona.client import LMStudioPersona, scrub
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
    # Matched with `scrub`, the project's own rule, not a raw substring: the
    # prompt legitimately carries the fault's `error_text` ("contact my system
    # administrator"), and a substring test reads the "ad " term out of
    # "administrator". The conformance harness already proves symptom text
    # carries no leak terms under this rule, so the two agree on what a leak is.
    assert scrub(client.prompts[0], fault.leak_terms) is not None

    # And the shared builder cannot be handed them at all.
    assert "leak" not in build_system_prompt.__code__.co_varnames


def test_queue_binds_the_open_ticket_s_fault():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(3), now=env.world.clock)
    ticket = queue.open_ticket()
    bound = queue.persona_for(ticket)
    assert bound is not None


class DeadClient:
    """Nothing listening on localhost."""

    def __init__(self):
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, model, messages, **kwargs):
        raise ConnectionError("connection refused")


def test_a_bindings_fallback_marks_the_origin_degraded():
    """Degradation is session state, so it has to travel back to the origin.

    The queue holds the unbound persona and the web layer's "you are reading
    template text" banner reads `queue.persona.degraded` — but after this task
    every model call goes through a binding instead. A per-instance flag would
    record the outage on an object nobody looks at.
    """
    world = load_world()
    card = card_for(world.org.users["m.alvarez"], Random(0))
    symptoms = get_fault("ad.account_locked").symptoms(
        world, get_fault("ad.account_locked").placements(world)[0]
    )

    origin = LMStudioPersona(DeadClient(), "stub", leak_terms=[])
    bound = origin.for_fault(["lock"])
    assert bound.reply(card, symptoms, [], "What did you see?")  # fell back, did not raise
    assert bound.degraded is True
    assert origin.degraded is True
