import pytest
from fastapi.testclient import TestClient

from vitsc.faults.registry import get_fault
from vitsc.persona.client import scrub
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
    fault = get_fault("ad.account_locked")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    r = c.post(f"/ticket/{ticket.id}/escalate", data={"note": "please fix"})
    assert r.status_code == 200
    reloaded = session.queue.get(ticket.id)
    assert reloaded.state.value == "in_progress"
    assert reloaded.tier2_bounces == 1


def test_an_accepted_escalation_renders_the_after_action(client):
    c, session = client
    fault = get_fault("ad.offboarded_reactivation")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    r = c.post(
        f"/ticket/{ticket.id}/escalate",
        data={"note": f"{ticket.placement.key} is disabled after offboarding, HR must authorise."},
    )
    assert "escalated" in r.text.lower()
    assert session.queue.get(ticket.id).state.value == "closed"


def test_an_accepted_escalation_persists_to_the_store(client):
    c, session = client
    fault = get_fault("ad.offboarded_reactivation")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    c.post(
        f"/ticket/{ticket.id}/escalate",
        data={"note": f"{ticket.placement.key} is disabled after offboarding, HR must authorise."},
    )
    assert len(session.store.history()) == 1


def test_escalating_a_closed_ticket_is_a_conflict(client):
    c, session = client
    ticket = session.queue.open_one()
    c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"})
    r = c.post(f"/ticket/{ticket.id}/escalate", data={"note": "too late"})
    assert r.status_code == 409


def test_the_bounce_text_does_not_name_the_cause(client):
    """A bounce nudges. It must not hand over the diagnosis.

    Checked with `scrub()` (word-boundary anchored) against the tier-2
    response itself (the chat turn it produced), not a raw substring against
    the whole rendered page: a bare stripped term like "ad" is a substring of
    ordinary words ("already", "load" in `hx-trigger="load"`) that have
    nothing to do with leaking the cause — the same false-positive class
    `scrub()` was written to avoid for persona text.
    """
    c, session = client
    fault = get_fault("ad.account_locked")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    c.post(f"/ticket/{ticket.id}/escalate", data={"note": "cannot log in"})
    bounce_text = session.queue.get(ticket.id).chat[-1].text
    assert scrub(bounce_text, fault.leak_terms) is not None


def test_a_bounce_shows_the_tier2_turn_in_chat(client):
    c, session = client
    fault = get_fault("ad.account_locked")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    r = c.post(f"/ticket/{ticket.id}/escalate", data={"note": "please fix"})
    assert "tier-2" in r.text.lower()
