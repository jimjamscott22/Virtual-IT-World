from random import Random

import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import all_faults, get_fault
from vitsc.persona.templates import TemplatePersona
from vitsc.session.queue import CASCADE_MAX, SessionQueue
from vitsc.world.seed import load_world

# `print.server_spooler_stopped` is the reference cascade fault, but it does
# not exist until Task 7. These two tests are what proves the mechanism this
# task adds once that fault lands; until then they xfail on the lookup.
NO_CASCADE_FAULT_YET = pytest.mark.xfail(
    raises=KeyError, reason="print.server_spooler_stopped lands in Task 7", strict=True
)


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


@NO_CASCADE_FAULT_YET
def test_siblings_share_a_cascade_id_and_a_placement():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(0), now=env.world.clock)
    tickets = queue.open_cascade(get_fault("print.server_spooler_stopped"))
    assert 2 <= len(tickets) <= CASCADE_MAX
    assert len({t.cascade_id for t in tickets}) == 1
    assert tickets[0].cascade_id is not None
    assert len({t.placement.key for t in tickets}) == 1
    assert len({t.persona.name for t in tickets}) == len(tickets)


@NO_CASCADE_FAULT_YET
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
