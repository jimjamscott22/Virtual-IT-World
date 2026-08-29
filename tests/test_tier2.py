from random import Random

import pytest

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import all_faults, get_fault
from vitsc.persona.templates import TemplatePersona
from vitsc.session.queue import SessionQueue
from vitsc.session.ticket import Disposition, TicketState
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
    ticket.escalate(
        note=f"Account {ticket.placement.key} is disabled and was offboarded. "
        "Needs HR authorisation before re-enabling.",
        at=env.world.clock,
    )
    response = review_escalation(ticket, fault, env.world)
    assert response.accepted is True
    assert fault.escalation_reason.split()[0].lower() in response.text.lower()


def test_a_fixable_fault_is_bounced_back():
    env, queue, fault, ticket = _ticket("ad.account_locked")
    ticket.escalate(note="User cannot log in, please fix.", at=env.world.clock)
    response = review_escalation(ticket, fault, env.world)
    assert response.accepted is False
    assert "within" in response.text.lower() or "your" in response.text.lower()


def test_a_fixable_fault_is_bounced_even_with_a_well_evidenced_note():
    """Ownership is judged first: a good note doesn't change who owns it."""
    env, queue, fault, ticket = _ticket("ad.account_locked")
    ticket.escalate(
        note=f"Ran Get-ADUser on {ticket.placement.key}, account is flagged and locked out.",
        at=env.world.clock,
    )
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
    assert ticket.tier2_bounces == 1


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
    ticket.escalate(
        note=f"{ticket.placement.key} is disabled after offboarding; HR must authorise.",
        at=env.world.clock,
    )
    review_escalation(ticket, fault, env.world)
    ticket.accept_escalation(at=env.world.clock)
    assert ticket.state is TicketState.CLOSED
    assert ticket.disposition.value == "escalated"


def test_escalating_a_closed_ticket_raises():
    env, queue, fault, ticket = _ticket("ad.account_locked")
    ticket.close(Disposition.RESOLVED, at=env.world.clock)
    with pytest.raises(ValueError, match="already closed"):
        ticket.escalate(note="too late", at=env.world.clock)
