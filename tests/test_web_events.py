from datetime import timedelta

import pytest

from vitsc.web.deps import AppSession
from vitsc.web.routes.events import MINUTES_PER_TICK, TICK_SECONDS, advance_clock_if_due


@pytest.fixture
def session(tmp_path):
    return AppSession.build(db_path=tmp_path / "t.sqlite3")


def test_two_connections_checking_in_within_the_same_tick_only_advance_once(session):
    before = session.env.world.clock

    # Two "SSE connections" (e.g. two browser tabs) both check in at nearly
    # the same wall-clock moment.
    advance_clock_if_due(session, wall_now=100.0)
    advance_clock_if_due(session, wall_now=100.0 + TICK_SECONDS / 2)

    assert session.env.world.clock == before + timedelta(minutes=MINUTES_PER_TICK)


def test_the_clock_advances_again_once_a_full_tick_has_elapsed(session):
    before = session.env.world.clock

    advance_clock_if_due(session, wall_now=100.0)
    advance_clock_if_due(session, wall_now=100.0 + TICK_SECONDS)

    assert session.env.world.clock == before + timedelta(minutes=2 * MINUTES_PER_TICK)


def test_three_overlapping_connections_still_advance_only_once_per_tick(session):
    before = session.env.world.clock

    for offset in (0.0, 0.1, 0.2):
        advance_clock_if_due(session, wall_now=100.0 + offset)

    assert session.env.world.clock == before + timedelta(minutes=MINUTES_PER_TICK)
