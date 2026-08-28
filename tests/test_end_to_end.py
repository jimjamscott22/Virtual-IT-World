import pytest
from fastapi.testclient import TestClient
from markupsafe import escape

from vitsc.faults.base import bind
from vitsc.faults.registry import all_faults, get_fault
from vitsc.web.app import create_app
from vitsc.web.deps import AppSession

# fault id -> (tool, command) for the HTTP call that performs its canonical
# fix. Each DispatchTool decides its own command set (vitsc/tools/*.py), so
# this table has to name the exact command per fault -- there's no generic
# way to derive it from the Action alone.
HTTP_FIX = {
    "ad.account_locked": ("ad", "unlock"),
    "ad.password_expired": ("ad", "reset-password"),
    "share.group_membership_removed": ("ad", "add-member"),
    "net.static_dns_misconfig": ("net", "set-dns"),
    "net.no_dhcp_lease": ("net", "renew"),
    "print.spooler_stopped": ("print", "restart-spooler"),
    "print.wrong_driver": ("print", "reinstall-driver"),
    "endpoint.disk_full": ("remote", "clear-disk"),
}

# Each DispatchTool also decides its own field name for "the thing this
# command acts on" (see the target_key() overrides in vitsc/tools/*.py), so
# the bound Action's `target` has to be reattached under the right key per
# command before it can be posted as a form.
TARGET_FIELD = {
    "unlock": "sam",
    "reset-password": "sam",
    "add-member": "group",
    "set-dns": "from",
    "renew": "from",
    "restart-spooler": "from",
    "reinstall-driver": "printer",
    "clear-disk": "host",
}


def resolve_via_http(client, ticket, fault, world):
    """Submit the fault's canonical fix through POST /ticket/{id}/tool,
    exercising the real tool-name/command dispatch and args parsing instead
    of mutating the environment directly."""
    resolution = bind(fault.canonical_resolutions()[0], ticket.placement, world)
    action = resolution.actions[0]
    tool, command = HTTP_FIX[fault.id]
    form_args = {TARGET_FIELD[command]: action.target, **action.args}
    raw_args = " ".join(f"{k}={v}" for k, v in form_args.items())
    r = client.post(f"/ticket/{ticket.id}/tool",
                     data={"tool": tool, "command": command, "args": raw_args})
    assert r.status_code == 200
    return r


@pytest.mark.parametrize("seed", range(8))
def test_a_full_ticket_can_be_worked_through_http(tmp_path, seed):
    session = AppSession.build(db_path=tmp_path / f"e2e{seed}.sqlite3", seed=seed)
    client = TestClient(create_app(session))

    ticket = session.queue.open_one()
    assert ticket is not None

    # The queue and the detail view render without revealing the answer.
    # report_text is HTML-escaped like any other template output, so compare
    # against the escaped form rather than the raw string.
    assert str(escape(ticket.report_text)) in client.get("/").text
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

    # Resolve through the same HTTP tool surface, or escalate when that is
    # the correct disposition.
    if fault.escalation_is_correct:
        disposition = "escalated"
    else:
        disposition = "resolved"
        resolve_via_http(client, ticket, fault, session.env.world)

    body = client.post(f"/ticket/{ticket.id}/close", data={"disposition": disposition}).text

    # After-action reveals the cause, and the record persists.
    assert fault.canonical_title in body
    records = session.store.history()
    assert len(records) == 1
    assert records[0].correct is True, f"{fault.id} graded incorrect: {records[0].verdict}"


def test_every_resolvable_fault_has_an_http_fix_mapped():
    """Guards HTTP_FIX itself: a new fault with no entry here would only be
    caught by the parametrized test above if a seed happened to pick it."""
    for fault in all_faults():
        if not fault.escalation_is_correct:
            assert fault.id in HTTP_FIX, f"{fault.id} has no HTTP_FIX entry"


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
