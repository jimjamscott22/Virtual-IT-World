from datetime import datetime, timedelta
from random import Random

import pytest

from vitsc.faults.registry import all_faults, get_fault
from vitsc.persona.personas import card_for
from vitsc.session.ticket import (
    SLA_MINUTES,
    Disposition,
    Priority,
    Ticket,
    TicketState,
    priority_for,
)
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)


def make_ticket(**overrides) -> Ticket:
    world = load_world()
    fault = get_fault("ad.account_locked")
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    base = {
        "id": 1,
        "fault_id": fault.id,
        "placement": placement,
        "persona": card_for(world.org.users[placement.key]),
        "symptoms": fault.symptoms(world, placement),
        "report_text": "I can't sign in.",
        "system_priority": Priority.P1,
        "opened_at": NOW,
        "sla_minutes": SLA_MINUTES[Priority.P1],
    }
    return Ticket(**{**base, **overrides})


def test_new_ticket_is_open_with_no_disposition():
    ticket = make_ticket()
    assert ticket.state is TicketState.OPEN
    assert ticket.disposition is None
    assert ticket.user_priority is None
    assert ticket.elapsed_minutes is None


def test_sla_deadline_is_derived_from_priority():
    ticket = make_ticket()
    assert ticket.deadline == NOW + timedelta(minutes=SLA_MINUTES[Priority.P1])


def test_every_priority_has_an_sla():
    assert set(SLA_MINUTES) == set(Priority)
    minutes = [SLA_MINUTES[p] for p in sorted(Priority)]
    assert minutes == sorted(minutes), "a more urgent priority must not get more time"


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


def test_escalating_closes_the_ticket_too():
    ticket = make_ticket()
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=3))
    assert ticket.state is TicketState.CLOSED
    assert ticket.disposition is Disposition.ESCALATED


def test_closing_twice_is_rejected():
    ticket = make_ticket()
    ticket.close(Disposition.RESOLVED, at=NOW)
    with pytest.raises(ValueError, match="already closed"):
        ticket.close(Disposition.ESCALATED, at=NOW)


def test_a_manager_outranks_a_clerk_for_the_same_fault():
    world = load_world()
    fault = get_fault("print.spooler_stopped")
    assert (
        priority_for(fault, world.org.users["s.whitfield"]).value
        < priority_for(fault, world.org.users["k.lindqvist"]).value
    )


@pytest.mark.parametrize(
    "fault_id",
    ["ad.account_locked", "ad.password_expired", "ad.offboarded_reactivation"],
)
def test_cannot_sign_in_is_always_p1(fault_id):
    """Every sign-in blocker is P1 for the most junior user in the org.

    `ad.offboarded_reactivation` counts even though it is escalate-only: the
    priority reflects impact on the person, not who ends up fixing it.
    """
    world = load_world()
    assert priority_for(get_fault(fault_id), world.org.users["k.lindqvist"]) is Priority.P1


def test_a_harder_fault_outranks_an_easier_one_for_the_same_person():
    world = load_world()
    user = world.org.users["k.lindqvist"]
    easy = priority_for(get_fault("print.spooler_stopped"), user)
    hard = priority_for(get_fault("print.wrong_driver"), user)
    assert hard.value < easy.value


def test_every_registered_fault_gets_a_priority_and_an_sla():
    world = load_world()
    user = world.org.users["k.lindqvist"]
    for fault in all_faults():
        priority = priority_for(fault, user)
        assert priority in SLA_MINUTES
