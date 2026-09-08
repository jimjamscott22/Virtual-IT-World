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
    """User, machine and printer placements must all resolve to a real person.

    Deals until the queue is full rather than a fixed number of times: a
    cascade fills three slots in one call, so `MAX_ACTIVE` calls to
    `open_one()` would run past the end and get `None`.
    """
    names = {u.display_name for u in queue.env.world.org.users.values()}
    dealt = 0
    while tickets := queue.open_ticket():
        for ticket in tickets:
            assert ticket.persona.name in names
            dealt += 1
    assert dealt == MAX_ACTIVE


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
    """One arrival, one fault+placement — counted per *arrival*, not per ticket.

    A cascade is several tickets that deliberately share a fault and a
    placement, so comparing against the ticket count asserts that cascades
    cannot happen. What the scheduler actually promises is that it never deals
    the same fault+placement as two separate arrivals.
    """
    for _ in range(MAX_ACTIVE):
        queue.open_ticket()
    active = queue.active()
    arrivals = {t.cascade_id or f"solo-{t.id}" for t in active}
    seen = {(t.fault_id, t.placement.key) for t in active}
    assert len(seen) == len(arrivals)


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
    """The arrival *interval* is what this pins down.

    Not the ticket count: one arrival is several tickets when the fault dealt
    is a cascade, so counting tickets here would quietly assert that the
    scheduler never deals one.
    """
    queue.open_ticket()
    assert queue.tick(NOW + timedelta(minutes=1)) == []
    assert queue.tick(NOW + timedelta(minutes=12)) != []
    # Same instant again: the interval has not elapsed a second time.
    assert queue.tick(NOW + timedelta(minutes=12)) == []


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


# --- how the scheduler picks --------------------------------------------------


def _candidate_pairs():
    from vitsc.faults.registry import all_faults
    world = load_world()
    return [(f, p) for f in all_faults() for p in f.placements(world)], world


def test_difficulty_weights_cover_every_difficulty_a_fault_may_declare():
    """`test_catalog.py` allows 1-5; a gap here would silently fall back to 1."""
    from vitsc.faults.registry import all_faults
    from vitsc.session.queue import DIFFICULTY_WEIGHTS
    assert set(DIFFICULTY_WEIGHTS) == {1, 2, 3, 4, 5}
    for fault in all_faults():
        assert fault.difficulty in DIFFICULTY_WEIGHTS


def test_easier_faults_are_dealt_more_often():
    """A real queue is mostly routine. The hard ticket has to stay rare enough
    to be surprising, or 'probably a password' stops being the sane guess."""
    from collections import Counter
    from vitsc.session.queue import choose_fault_and_placement
    candidates, _ = _candidate_pairs()
    rng = Random(0)
    seen = Counter(
        choose_fault_and_placement(candidates, rng)[0].difficulty for _ in range(20000)
    )
    total = sum(seen.values())
    assert seen[1] / total > seen[3] / total > seen[4] / total
    # Difficulty 4 is the rarest thing in the catalog, by a clear margin.
    assert seen[4] / total < 0.15


def test_placement_count_does_not_decide_how_often_a_fault_comes_up():
    """The bug this scheduler exists to fix.

    Drawing uniformly from (fault, placement) pairs weighted every fault by
    how many valid targets it happened to have. `print.server_spooler_stopped`
    has one placement and `mail.external_forwarding_rule` has twenty, so the
    catalog's only cascade was dealt twenty times less often than a mail
    fault — an accident of the estate, not a decision about the drill.
    """
    from collections import Counter
    from vitsc.session.queue import choose_fault_and_placement
    candidates, world = _candidate_pairs()
    rng = Random(0)
    drawn = Counter(
        choose_fault_and_placement(candidates, rng)[0].id for _ in range(20000)
    )
    cascade = get_fault("print.server_spooler_stopped")
    forwarding = get_fault("mail.external_forwarding_rule")
    assert len(cascade.placements(world)) == 1
    assert len(forwarding.placements(world)) == 20
    # One placement versus twenty, yet the cascade is dealt *more* often —
    # because it is the easier fault, which is the only thing that should
    # decide this.
    assert drawn[cascade.id] > drawn[forwarding.id]


def test_every_placement_of_the_chosen_fault_stays_reachable():
    from vitsc.session.queue import choose_fault_and_placement
    candidates, world = _candidate_pairs()
    fault = get_fault("ad.account_locked")
    only_this = [(f, p) for f, p in candidates if f.id == fault.id]
    rng = Random(0)
    keys = {choose_fault_and_placement(only_this, rng)[1].key for _ in range(400)}
    assert keys == {p.key for p in fault.placements(world)}


def test_a_single_candidate_is_returned_unchanged():
    from vitsc.session.queue import choose_fault_and_placement
    candidates, _ = _candidate_pairs()
    one = candidates[:1]
    assert choose_fault_and_placement(one, Random(0)) == one[0]


def test_the_choice_is_reproducible_for_a_seed():
    """Fixed-seed tests across the suite depend on this."""
    from vitsc.session.queue import choose_fault_and_placement
    candidates, _ = _candidate_pairs()
    first = [choose_fault_and_placement(candidates, Random(4)) for _ in range(5)]
    again = [choose_fault_and_placement(candidates, Random(4)) for _ in range(5)]
    assert [(f.id, p.key) for f, p in first] == [(f.id, p.key) for f, p in again]
