"""The fixed shift: when arrivals stop, and what the day added up to."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from vitsc.faults.registry import get_fault
from vitsc.session.shift import SHIFT_MINUTES, Shift, build_shift_report
from vitsc.session.store import DomainStat
from vitsc.web.app import create_app
from vitsc.web.deps import AppSession
from vitsc.web.routes.events import build_payload

START = datetime(2026, 8, 7, 9, 0)


@pytest.fixture
def app(tmp_path):
    session = AppSession.build(db_path=tmp_path / "shift.sqlite3", seed=1)
    return session, TestClient(create_app(session))


# --- the clock --------------------------------------------------------------


def test_a_shift_is_eight_hours():
    shift = Shift(started_at=START)
    assert SHIFT_MINUTES == 480
    assert shift.ends_at == datetime(2026, 8, 7, 17, 0)


@pytest.mark.parametrize(
    "minutes,elapsed,remaining,over",
    [(0, 0, 480, False), (60, 60, 420, False), (479, 479, 1, False),
     (480, 480, 0, True), (600, 480, 0, True)],
)
def test_the_clock_runs_down_and_stops(minutes, elapsed, remaining, over):
    """Past the end it clamps rather than going negative — the header renders
    this number directly."""
    shift = Shift(started_at=START)
    now = START + timedelta(minutes=minutes)
    assert shift.elapsed(now) == elapsed
    assert shift.remaining(now) == remaining
    assert shift.is_over(now) is over


def test_a_clock_that_ran_backwards_does_not_go_negative():
    shift = Shift(started_at=START)
    assert shift.elapsed(START - timedelta(minutes=30)) == 0
    assert shift.remaining(START - timedelta(minutes=30)) == 480


# --- arrivals stop, work does not -------------------------------------------


def test_no_ticket_arrives_after_the_shift_ends(app):
    session, _ = app
    queue = session.queue
    assert queue.tick(START + timedelta(minutes=30)), "the shift should deal while open"
    assert queue.shift_is_over(session.shift.ends_at) is True
    assert queue.tick(session.shift.ends_at) == []
    assert queue.tick(session.shift.ends_at + timedelta(hours=3)) == []


def test_an_open_ticket_is_still_workable_after_the_shift_ends(app):
    """The shift gates arrivals, not the technician. A ticket already open at
    five o'clock is still theirs to finish."""
    session, client = app
    fault = get_fault("ad.account_locked")
    ticket = session.queue.open_for(fault, fault.placements(session.env.world)[0])[0]
    session.env.world.clock = session.shift.ends_at + timedelta(minutes=10)

    r = client.post(f"/ticket/{ticket.id}/tool", data={
        "tool": "ad", "command": "unlock", "args": f"sam={ticket.placement.key}"})
    assert r.status_code == 200
    body = client.post(f"/ticket/{ticket.id}/close", data={"disposition": "resolved"}).text
    assert "Resolved correctly" in body


def test_a_queue_with_no_shift_deals_forever(app):
    """The shift is optional on the queue itself — every test that builds a
    bare SessionQueue predates it and must keep working."""
    session, _ = app
    session.queue.shift_ends_at = None
    assert session.queue.shift_is_over(START + timedelta(days=9)) is False


# --- the report -------------------------------------------------------------


def test_an_empty_shift_says_so():
    report = build_shift_report([], {}, unresolved=0)
    assert report.closed == 0
    assert report.accuracy == 0.0
    assert "Nothing to judge" in report.verdict


def test_the_report_sums_what_the_store_recorded(app):
    """Built from the store's own rows, so it cannot disagree with history."""
    session, client = app
    for fault_id, disposition in [("ad.account_locked", "resolved"),
                                  ("ad.password_expired", "resolved")]:
        fault = get_fault(fault_id)
        at = fault.placements(session.env.world)[0]
        ticket = session.queue.open_for(fault, at)[0]
        client.post(f"/ticket/{ticket.id}/tool", data={
            "tool": "ad", "command": "reset-password", "args": f"sam={at.key}"})
        client.post(f"/ticket/{ticket.id}/close", data={"disposition": disposition})

    report = session.shift_report()
    assert report.closed == 2
    assert report.correct == 2
    assert report.accuracy == 1.0
    assert report.unresolved == 0
    assert [s.domain for s in report.by_domain] == ["identity"]


def test_unresolved_counts_tickets_the_store_never_saw(app):
    """A ticket nobody closed was never written to the store — which is
    exactly why the report has to name it."""
    session, _ = app
    fault = get_fault("ad.account_locked")
    session.queue.open_for(fault, fault.placements(session.env.world)[0])
    report = session.shift_report()
    assert report.closed == 0
    assert report.unresolved == 1
    assert "still waiting" in report.verdict.lower() or "Nothing to judge" in report.verdict


def test_collateral_outranks_everything_in_the_verdict():
    """Breaking the estate is worse than misreading a ticket, so it is what
    the one-line verdict leads with."""
    from vitsc.session.store import ClosedRecord
    rec = ClosedRecord(
        ticket_id=1, fault_id="ad.account_locked", domain="identity",
        disposition="resolved", correct=True, within_sla=True, elapsed_minutes=5.0,
        tool_calls_made=2, tool_calls_min=1, collateral_count=1,
        root_cause="x", verdict="y", closed_at=START,
    )
    report = build_shift_report([rec], {}, unresolved=3)
    assert "broke something else" in report.verdict


def test_a_clean_shift_is_named_as_one():
    from vitsc.session.store import ClosedRecord
    recs = [
        ClosedRecord(
            ticket_id=i, fault_id="ad.account_locked", domain="identity",
            disposition="resolved", correct=True, within_sla=True,
            elapsed_minutes=5.0, tool_calls_made=2, tool_calls_min=1,
            collateral_count=0, root_cause="x", verdict="y", closed_at=START,
        )
        for i in range(3)
    ]
    report = build_shift_report(recs, {}, unresolved=0)
    assert report.accuracy == 1.0 and report.sla_rate == 1.0
    assert "clean shift" in report.verdict


def test_domain_stats_come_through_sorted():
    stats = {
        "printing": DomainStat(domain="printing", total=2, correct=1),
        "identity": DomainStat(domain="identity", total=1, correct=1),
    }
    report = build_shift_report([], stats, unresolved=0)
    assert [s.domain for s in report.by_domain] == ["identity", "printing"]


# --- the surfaces -----------------------------------------------------------


def test_the_shift_clock_reaches_the_browser(app):
    session, _ = app
    payload = build_payload(session, START + timedelta(minutes=90), [])
    assert payload["shift_remaining"] == 390
    assert payload["shift_over"] is False

    ended = build_payload(session, session.shift.ends_at, [])
    assert ended["shift_remaining"] == 0
    assert ended["shift_over"] is True


def test_the_queue_page_shows_the_shift_clock_and_hides_the_banner(app):
    _, client = app
    body = client.get("/").text
    assert 'id="shift-remaining"' in body
    assert "min left in shift" in body
    # Always rendered so the SSE handler can reveal it mid-session.
    assert 'id="shift-banner"' in body
    assert "hidden" in body.split('id="shift-banner"')[1].split(">")[0]


def test_the_banner_is_visible_once_the_shift_is_over(app):
    session, client = app
    session.env.world.clock = session.shift.ends_at
    banner = client.get("/").text.split('id="shift-banner"')[1].split(">")[0]
    assert "hidden" not in banner


def test_the_shift_summary_page_renders(app):
    session, client = app
    body = client.get("/shift").text
    assert "Shift so far" in body
    assert "09:00–17:00" in body
    assert session.shift_report().verdict in body


def test_the_summary_page_says_when_the_shift_is_over(app):
    session, client = app
    session.env.world.clock = session.shift.ends_at
    body = client.get("/shift").text
    assert "Shift over" in body
    assert "all 8 hours worked" in body
