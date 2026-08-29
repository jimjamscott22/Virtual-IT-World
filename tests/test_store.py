import sqlite3
from datetime import datetime, timedelta
from random import Random

import pytest

from vitsc.env.base import Action
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import get_fault
from vitsc.persona.personas import card_for
from vitsc.session.afteraction import build_after_action
from vitsc.session.grading import grade_ticket
from vitsc.session.store import Store
from vitsc.session.ticket import Disposition, Priority, SLA_MINUTES, Ticket
from vitsc.world.invariants import capture_baseline
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)


def closed_ticket(fault_id="ad.account_locked", fix=True, ticket_id=1, cascade_id=None):
    world = load_world()
    fault = get_fault(fault_id)
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    env = SimulatedEnvironment(world)
    baseline = capture_baseline(world)
    if fix:
        env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket = Ticket(
        id=ticket_id, fault_id=fault.id, placement=placement,
        persona=card_for(world.org.users[placement.key]),
        symptoms=fault.symptoms(world, placement), report_text="can't log in",
        system_priority=Priority.P1, opened_at=NOW, sla_minutes=SLA_MINUTES[Priority.P1],
        cascade_id=cascade_id,
    )
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=7))
    grade = grade_ticket(ticket, fault, env, baseline)
    return ticket, grade, build_after_action(ticket, fault, grade, env.world)


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "vitsc.sqlite3")
    s.init()
    return s


def test_init_is_idempotent(tmp_path):
    s = Store(tmp_path / "x.sqlite3")
    s.init()
    s.init()
    assert s.history() == []


def test_saved_ticket_appears_in_history(store):
    store.save_closed(*closed_ticket())
    records = store.history()
    assert len(records) == 1
    assert records[0].fault_id == "ad.account_locked"
    assert records[0].correct is True


def test_history_is_newest_first(store):
    store.save_closed(*closed_ticket(ticket_id=1))
    store.save_closed(*closed_ticket(ticket_id=2))
    assert [r.ticket_id for r in store.history()] == [2, 1]


def test_history_respects_limit(store):
    for i in range(1, 6):
        store.save_closed(*closed_ticket(ticket_id=i))
    assert len(store.history(limit=3)) == 3


def test_domain_stats_aggregate_by_fault_domain(store):
    store.save_closed(*closed_ticket(ticket_id=1, fix=True))
    store.save_closed(*closed_ticket(ticket_id=2, fix=False))
    stats = store.domain_stats()
    assert stats["identity"].total == 2
    assert stats["identity"].correct == 1


def test_after_action_round_trips(store):
    store.save_closed(*closed_ticket())
    assert "locked out" in store.history()[0].root_cause


def test_cascade_id_round_trips(store):
    store.save_closed(*closed_ticket(cascade_id="C1"))
    assert store.history()[0].cascade_id == "C1"


def test_cascade_id_is_none_for_a_single_ticket(store):
    store.save_closed(*closed_ticket())
    assert store.history()[0].cascade_id is None


def test_init_on_a_pre_cascade_database_adds_the_column(tmp_path):
    """A database created before Task 6 must survive `init()` being called again."""
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """CREATE TABLE closed_tickets (
                ticket_id        INTEGER NOT NULL,
                fault_id         TEXT    NOT NULL,
                domain           TEXT    NOT NULL,
                placement_key    TEXT    NOT NULL,
                disposition      TEXT    NOT NULL,
                correct          INTEGER NOT NULL,
                within_sla       INTEGER NOT NULL,
                elapsed_minutes  REAL    NOT NULL,
                tool_calls_made  INTEGER NOT NULL,
                tool_calls_min   INTEGER NOT NULL,
                collateral_count INTEGER NOT NULL,
                root_cause       TEXT    NOT NULL,
                verdict          TEXT    NOT NULL,
                closed_at        TEXT    NOT NULL,
                rowid_key        INTEGER PRIMARY KEY AUTOINCREMENT
            );"""
        )

    s = Store(path)
    s.init()
    s.save_closed(*closed_ticket(cascade_id="C2"))
    assert s.history()[0].cascade_id == "C2"
