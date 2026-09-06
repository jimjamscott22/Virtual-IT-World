import pytest
from fastapi.testclient import TestClient
from markupsafe import escape

from vitsc.distractors.registry import get_distractor
from vitsc.faults.base import bind
from vitsc.faults.registry import all_faults, get_fault
from vitsc.persona.client import scrub
from vitsc.tools.registry import all_tools
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
    "print.server_spooler_stopped": ("print", "restart-spooler"),
    "endpoint.disk_full": ("remote", "clear-disk"),
    "mail.mailbox_full": ("mail", "set-quota"),
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
    "set-quota": "sam",
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
    caught by the parametrized test above if a seed happened to pick it.

    Equality, not containment, in both directions — so the table cannot drift
    into listing an escalate-correct fault (which has no technician fix to
    post) or keeping an entry for a fault that no longer exists.
    """
    resolvable = {f.id for f in all_faults() if not f.escalation_is_correct}
    assert set(HTTP_FIX) == resolvable


def test_every_http_fix_names_a_real_command_and_target_field():
    """The other half: an entry can exist and still be unpostable."""
    for fault_id, (tool, command) in HTTP_FIX.items():
        assert command in TARGET_FIELD, f"{fault_id}: {command} has no TARGET_FIELD"
        registered = next(t for t in all_tools() if t.name == tool)
        assert command in registered.commands(), f"{fault_id}: {tool} has no {command}"


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


# --- Phase 2a surfaces, each worked through HTTP only ------------------------


def _app(tmp_path, name, seed=0):
    session = AppSession.build(db_path=tmp_path / f"{name}.sqlite3", seed=seed)
    return session, TestClient(create_app(session))


def test_a_cascade_can_be_worked_through_http(tmp_path):
    """Three tickets, one fix, all three grade cleared — over HTTP only.

    The point of the cascade mechanic: the technician has to notice that the
    three rows share a cause, and one restart closes all of them.
    """
    session, c = _app(tmp_path, "cascade")
    fault = get_fault("print.server_spooler_stopped")
    tickets = session.queue.open_cascade(fault)
    assert len(tickets) == 3
    assert len({t.cascade_id for t in tickets}) == 1
    assert tickets[0].cascade_id is not None

    server = tickets[0].placement.key
    r = c.post(f"/ticket/{tickets[0].id}/tool", data={
        "tool": "print", "command": "restart-spooler", "args": f"from={server}"})
    assert r.status_code == 200
    assert fault.is_present(session.env.world, tickets[0].placement) is False

    for ticket in tickets:
        body = c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"}).text
        assert "Resolved correctly" in body
        # The report names the shared root cause rather than three separate ones.
        assert "was behind 3 tickets" in body

    records = session.store.history()
    assert len(records) == 3
    assert all(record.correct for record in records)


def test_a_bounced_escalation_can_be_recovered_through_http(tmp_path):
    """The teaching path: hand it off, get it back, fix it.

    A fixable fault is bounced on ownership regardless of the note, and the
    ticket that comes back is still workable — the bounce is a nudge, not a
    dead end.
    """
    session, c = _app(tmp_path, "bounce")
    fault = get_fault("ad.account_locked")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    sam = ticket.placement.key

    bounce = c.post(f"/ticket/{ticket.id}/escalate", data={"note": "cannot log in"}).text
    assert session.queue.get(ticket.id).state.value == "in_progress"
    assert session.queue.get(ticket.id).tier2_bounces == 1
    # The nudge must not hand over the vocabulary that is the answer.
    assert scrub(session.queue.get(ticket.id).chat[-1].text, fault.leak_terms) is not None
    assert bounce

    c.post(f"/ticket/{ticket.id}/tool",
           data={"tool": "ad", "command": "unlock", "args": f"sam={sam}"})
    assert fault.is_present(session.env.world, ticket.placement) is False

    body = c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"}).text
    # The report says the handoff was wrong, even though the ticket ended right.
    assert "escalat" in body.lower()
    assert session.store.history()[0].correct is True


def test_a_mail_ticket_can_be_worked_through_http(tmp_path):
    """The mail slice end to end: a mailbox read, a quota raise, a clean close."""
    session, c = _app(tmp_path, "mail")
    fault = get_fault("mail.mailbox_full")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    sam = ticket.placement.key

    read = c.post(f"/ticket/{ticket.id}/tool", data={
        "tool": "mail", "command": "get-mailbox", "args": f"sam={sam}"}).text
    assert "ProhibitSendQuota" in read

    resolve_via_http(c, ticket, fault, session.env.world)
    assert fault.is_present(session.env.world, ticket.placement) is False

    body = c.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"}).text
    assert "Resolved correctly" in body
    assert "/kb/mail-cannot-send-or-receive" in body


def test_an_escalate_correct_mail_ticket_is_accepted_through_http(tmp_path):
    """The other half of the mail slice: the one that is not yours to fix."""
    session, c = _app(tmp_path, "mailesc")
    fault = get_fault("mail.external_forwarding_rule")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    sam = ticket.placement.key

    rules = c.post(f"/ticket/{ticket.id}/tool", data={
        "tool": "mail", "command": "get-rules", "args": f"sam={sam}"}).text
    assert "ForwardTo" in rules

    body = c.post(f"/ticket/{ticket.id}/escalate", data={
        "note": f"mail for {sam} is going to an outside address, see the rules"}).text
    assert session.queue.get(ticket.id).state.value == "closed"
    # Tier-2's own words reach the report, so the player learns why.
    assert fault.escalation_reason in body
    assert session.store.history()[0].correct is True


def test_a_seeded_distractor_does_not_block_any_ticket(tmp_path):
    """A full pass with noise in the world.

    Distractors are applied before the baseline is captured, so they must
    never make a correct fix look like collateral damage — and the report
    has to name them as pre-existing rather than leave them unexplained.
    """
    session, c = _app(tmp_path, "noise", seed=11)
    assert session.queue.distractors

    ticket = session.queue.open_one()
    assert ticket is not None
    fault = get_fault(ticket.fault_id)

    if fault.escalation_is_correct:
        disposition = "escalated"
    else:
        disposition = "resolved"
        resolve_via_http(c, ticket, fault, session.env.world)

    body = c.post(f"/ticket/{ticket.id}/close", data={"disposition": disposition}).text
    record = session.store.history()[0]
    assert record.correct is True, f"{fault.id} graded incorrect: {record.verdict}"
    assert record.collateral_count == 0, (
        f"a distractor was blamed on the technician: {record.verdict}"
    )
    # Every seeded distractor is accounted for in the report.
    for distractor_id, _ in session.queue.distractors:
        assert get_distractor(distractor_id).note in body
