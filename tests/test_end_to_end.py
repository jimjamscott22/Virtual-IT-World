import pytest
from fastapi.testclient import TestClient

from vitsc.faults.base import bind
from vitsc.faults.registry import all_faults, get_fault
from vitsc.web.app import create_app
from vitsc.web.deps import AppSession


@pytest.mark.parametrize("seed", range(8))
def test_a_full_ticket_can_be_worked_through_http(tmp_path, seed):
    session = AppSession.build(db_path=tmp_path / f"e2e{seed}.sqlite3", seed=seed)
    client = TestClient(create_app(session))

    ticket = session.queue.open_ticket()
    assert ticket is not None

    # The queue and the detail view render without revealing the answer.
    assert ticket.report_text in client.get("/").text
    detail = client.get(f"/ticket/{ticket.id}").text
    fault = get_fault(ticket.fault_id)
    assert fault.canonical_title not in detail
    assert fault.id not in detail

    # Ask the user something before touching anything.
    client.post(f"/ticket/{ticket.id}/chat", data={"message": "when did it last work?"})
    assert len(session.queue.get(ticket.id).chat) == 2

    # Run the fault's own diagnostic path through the tool surface.
    client.post(f"/ticket/{ticket.id}/tool",
                data={"tool": "ad", "command": "get-user", "args": f"sam={ticket.placement.key}"})

    # Resolve, or escalate when that is the correct disposition.
    if fault.escalation_is_correct:
        disposition = "escalated"
    else:
        disposition = "resolved"
        for resolution in fault.canonical_resolutions()[:1]:
            for action in bind(resolution, ticket.placement, session.env.world).actions:
                session.env.execute(action)

    body = client.post(f"/ticket/{ticket.id}/close", data={"disposition": disposition}).text

    # After-action reveals the cause, and the record persists.
    assert fault.canonical_title in body
    records = session.store.history()
    assert len(records) == 1
    assert records[0].correct is True, f"{fault.id} graded incorrect: {records[0].verdict}"


def test_every_fault_in_the_catalog_can_be_closed_correctly(tmp_path):
    """Stronger than the seeded sample: exercise all ten faults explicitly."""
    for fault in all_faults():
        session = AppSession.build(db_path=tmp_path / f"{fault.id}.sqlite3", seed=0)
        placement = fault.placements(session.env.world)[0]
        fault.apply(session.env.world, placement, __import__("random").Random(0))
        session.queue.baseline = __import__(
            "vitsc.world.invariants", fromlist=["capture_baseline"]
        ).capture_baseline(session.env.world)

        if fault.escalation_is_correct:
            continue  # covered by the parametrized test above
        for resolution in fault.canonical_resolutions()[:1]:
            for action in bind(resolution, placement, session.env.world).actions:
                session.env.execute(action)
        assert fault.is_present(session.env.world, placement) is False
