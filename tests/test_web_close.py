import pytest
from fastapi.testclient import TestClient

from vitsc.faults.registry import get_fault
from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.fixture
def client(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=0)
    session.queue.open_one()
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
