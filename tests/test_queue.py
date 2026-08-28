from datetime import datetime, timedelta
from random import Random

import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import get_fault
from vitsc.persona.templates import TemplatePersona
from vitsc.session.queue import MAX_ACTIVE, SessionQueue
from vitsc.session.ticket import Disposition
from vitsc.world.invariants import check_invariants
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)


def make_queue(seed: int = 1) -> SessionQueue:
    return SessionQueue(
        env=SimulatedEnvironment(load_world()),
        persona=TemplatePersona(),
        rng=Random(seed),
        now=NOW,
    )


@pytest.fixture
def queue():
    return make_queue()


def test_opening_a_ticket_applies_a_real_fault(queue):
    ticket = queue.open_one()
    fault = get_fault(ticket.fault_id)
    assert fault.is_present(queue.env.world, ticket.placement) is True


def test_ticket_text_comes_from_the_persona(queue):
    ticket = queue.open_one()
    assert ticket.symptoms.opening in ticket.report_text


def test_the_reporter_is_the_person_the_fault_actually_affects(queue):
    """User, machine and printer placements must all resolve to a real person."""
    for _ in range(MAX_ACTIVE):
        ticket = queue.open_one()
        assert ticket.persona.name in {
            u.display_name for u in queue.env.world.org.users.values()
        }


def test_baseline_is_captured_after_the_fault_is_applied(queue):
    queue.open_ticket()
    assert check_invariants(queue.env.world, queue.baseline) == []


@pytest.mark.parametrize("seed", range(12))
def test_no_seed_opens_a_ticket_that_reports_itself_as_damage(seed):
    """Whatever the scheduler picks, a fresh fault is never collateral damage."""
    queue = make_queue(seed)
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    assert check_invariants(queue.env.world, queue.baseline) == []


def test_a_new_arrival_does_not_launder_earlier_collateral_damage(queue):
    """Damage done on ticket 1 must still be visible after ticket 2 arrives.

    Re-snapshotting the baseline on every arrival would erase it, and grading
    reads this baseline — a wrong fix would score clean.
    """
    queue.open_ticket()
    queue.env.world.org.users["d.okafor"].enabled = False
    assert check_invariants(queue.env.world, queue.baseline) != []
    queue.open_ticket()
    assert any("d.okafor" in v for v in check_invariants(queue.env.world, queue.baseline))


def test_damage_survives_every_remaining_arrival(queue):
    queue.open_ticket()
    queue.env.world.org.groups["ACC-Share-RW"].members.remove("m.alvarez")
    while queue.open_ticket():
        pass
    assert any("m.alvarez" in v for v in check_invariants(queue.env.world, queue.baseline))


def test_queue_stops_at_max_active(queue):
    for _ in range(MAX_ACTIVE + 3):
        queue.open_ticket()
    assert len(queue.active()) == MAX_ACTIVE


def test_closing_frees_a_slot(queue):
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    assert queue.open_ticket() == []
    queue.active()[0].close(Disposition.RESOLVED, at=NOW)
    assert queue.open_ticket() != []


def test_no_duplicate_fault_and_placement_while_active(queue):
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    seen = {(t.fault_id, t.placement.key) for t in queue.active()}
    assert len(seen) == len(queue.active())


def test_an_unfixed_fault_is_not_handed_out_again(queue):
    """Closing a ticket without fixing it must not re-deal the same fault."""
    ticket = queue.open_one()
    ticket.close(Disposition.ESCALATED, at=NOW)
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    repeats = [
        t
        for t in queue.tickets
        if t.id != ticket.id
        and (t.fault_id, t.placement.key) == (ticket.fault_id, ticket.placement.key)
    ]
    assert repeats == []


def test_ids_are_unique_and_get_finds_them(queue):
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    ids = [t.id for t in queue.tickets]
    assert len(set(ids)) == len(ids)
    assert all(queue.get(i).id == i for i in ids)


def test_tick_opens_a_ticket_once_the_interval_elapses(queue):
    queue.open_ticket()
    assert queue.tick(NOW + timedelta(minutes=1)) == []
    arrivals = queue.tick(NOW + timedelta(minutes=12))
    assert len(arrivals) == 1


def test_tick_does_not_backfill_a_long_gap_past_max_active(queue):
    arrivals = queue.tick(NOW + timedelta(hours=8))
    assert len(arrivals) == MAX_ACTIVE
    assert len(queue.active()) == MAX_ACTIVE


def test_active_is_sorted_by_priority_then_age(queue):
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    priorities = [t.system_priority for t in queue.active()]
    assert priorities == sorted(priorities)


def _dealt(seed: int) -> list[tuple[str, str]]:
    queue = make_queue(seed)
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    return [(t.fault_id, t.placement.key) for t in queue.tickets]


def test_the_same_seed_deals_the_same_session():
    assert _dealt(7) == _dealt(7)


def test_different_seeds_deal_different_sessions():
    assert _dealt(7) != _dealt(8)


def test_session_seeds_distractors_before_the_baseline():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(
        env=env, persona=TemplatePersona(), rng=Random(7), now=NOW, distractor_count=3
    )
    assert len(queue.distractors) == 3
    # Seeded state is inherited, not collateral damage.
    assert check_invariants(env.world, queue.baseline) == []


def test_distractors_are_off_by_default_for_deterministic_tests():
    env = SimulatedEnvironment(load_world())
    queue = SessionQueue(env=env, persona=TemplatePersona(), rng=Random(7), now=NOW)
    assert queue.distractors == []
