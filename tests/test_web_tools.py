import pytest
from fastapi.testclient import TestClient

from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.fixture
def client(tmp_path):
    session = AppSession.build(db_path=tmp_path / "t.sqlite3", seed=1)
    session.queue.open_one()
    return TestClient(create_app(session)), session


def test_tool_pane_lists_every_tool(client):
    c, session = client
    ticket = session.queue.active()[0]
    body = c.get(f"/ticket/{ticket.id}/tools").text
    for name in ("ad", "net", "remote", "events", "print", "ps"):
        assert f'value="{name}"' in body


def test_running_a_tool_renders_its_output(client):
    c, session = client
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/tool",
               data={"tool": "ad", "command": "get-user", "args": "sam=m.alvarez"})
    assert r.status_code == 200
    assert "SamAccountName" in r.text


def test_tool_calls_are_recorded_on_the_ticket(client):
    c, session = client
    ticket = session.queue.active()[0]
    c.post(f"/ticket/{ticket.id}/tool",
           data={"tool": "ad", "command": "get-user", "args": "sam=m.alvarez"})
    assert len(session.queue.get(ticket.id).tool_calls) == 1


def test_unknown_tool_is_rejected_without_crashing(client):
    c, session = client
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/tool",
               data={"tool": "nope", "command": "x", "args": ""})
    assert r.status_code == 200
    assert "not recognized" in r.text.lower()


def test_malformed_args_do_not_500(client):
    c, session = client
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/tool",
               data={"tool": "ad", "command": "get-user", "args": "garbage-no-equals"})
    assert r.status_code == 200


def test_chat_appends_both_turns(client):
    c, session = client
    ticket = session.queue.active()[0]
    c.post(f"/ticket/{ticket.id}/chat", data={"message": "when did it last work?"})
    chat = session.queue.get(ticket.id).chat
    assert [t.speaker for t in chat] == ["tech", "user"]
    assert chat[1].text == ticket.symptoms.onset


def test_chat_reply_never_contains_a_leak_term(client):
    c, session = client
    from vitsc.faults.registry import get_fault
    ticket = session.queue.active()[0]
    r = c.post(f"/ticket/{ticket.id}/chat", data={"message": "what is wrong exactly?"})
    for term in get_fault(ticket.fault_id).leak_terms:
        assert term.lower() not in r.text.lower()
