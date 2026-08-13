import pytest
from fastapi.testclient import TestClient
from markupsafe import escape

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
    # report_text is rendered HTML-escaped (it's never trusted as markup, even
    # though today's only source -- TemplatePersona -- can't produce any), so
    # compare against the escaped form rather than the raw string.
    assert str(escape(ticket.report_text)) in body
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
