"""SQLite persistence for closed tickets.

Only *closed* tickets persist. Live session state stays in memory —
resuming a half-worked queue is Phase 4, and building it now would mean
serialising a whole `World` per request.
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from vitsc.faults.registry import get_fault
from vitsc.session.afteraction import AfterAction
from vitsc.session.grading import Grade
from vitsc.session.ticket import Ticket

SCHEMA = """
CREATE TABLE IF NOT EXISTS closed_tickets (
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
    cascade_id       TEXT,
    session_id       TEXT,
    rowid_key        INTEGER PRIMARY KEY AUTOINCREMENT
);
"""

# Columns added after the table first shipped. `CREATE TABLE IF NOT EXISTS`
# never alters an existing table, so each one needs its own migration step, and
# a database on disk outlives any single release.
ADDED_COLUMNS = {"cascade_id": "TEXT", "session_id": "TEXT"}


class ClosedRecord(BaseModel):
    ticket_id: int
    fault_id: str
    domain: str
    disposition: str
    correct: bool
    within_sla: bool
    elapsed_minutes: float
    tool_calls_made: int
    tool_calls_min: int
    collateral_count: int
    root_cause: str
    verdict: str
    closed_at: datetime
    cascade_id: str | None = None


class DomainStat(BaseModel):
    domain: str
    total: int
    correct: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


class Store:
    """Closed tickets on disk, scoped to the run that wrote them.

    The database outlives the process: `__main__.py` keeps one at
    `~/.vitsc/sessions.sqlite3`, so every shift a player ever works lands in the
    same table. Reads are therefore scoped to this `Store`'s own `session_id` by
    default, because the questions the app asks ("how did *this* shift go") are
    all about one run — the simulated clock restarts at 09:00 every session, so
    no timestamp can separate them and nothing else could.

    Pass `all_sessions=True` to read across runs. Nothing does yet; a
    career-to-date view would.
    """

    def __init__(self, path: Path | str, session_id: str | None = None) -> None:
        self.path = Path(path)
        self.session_id = session_id or uuid.uuid4().hex

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(closed_tickets)")}
            for name, sql_type in ADDED_COLUMNS.items():
                if name not in columns:
                    # Only ever our own literals from ADDED_COLUMNS, never input.
                    conn.execute(
                        f"ALTER TABLE closed_tickets ADD COLUMN {name} {sql_type}"
                    )

    def save_closed(self, ticket: Ticket, grade: Grade, report: AfterAction) -> None:
        domain = get_fault(ticket.fault_id).domain
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO closed_tickets (
                    ticket_id, fault_id, domain, placement_key, disposition, correct,
                    within_sla, elapsed_minutes, tool_calls_made, tool_calls_min,
                    collateral_count, root_cause, verdict, closed_at, cascade_id,
                    session_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ticket.id, ticket.fault_id, domain, ticket.placement.key,
                    ticket.disposition.value, int(grade.correct), int(grade.within_sla),
                    grade.elapsed_minutes, grade.tool_calls_made, grade.tool_calls_minimum,
                    len(grade.collateral), report.root_cause, report.verdict,
                    ticket.closed_at.isoformat(), ticket.cascade_id, self.session_id,
                ),
            )

    def history(self, limit: int = 50, all_sessions: bool = False) -> list[ClosedRecord]:
        where, params = self._scope(all_sessions)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM closed_tickets{where} ORDER BY rowid_key DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [
            ClosedRecord(
                ticket_id=r["ticket_id"], fault_id=r["fault_id"], domain=r["domain"],
                disposition=r["disposition"], correct=bool(r["correct"]),
                within_sla=bool(r["within_sla"]), elapsed_minutes=r["elapsed_minutes"],
                tool_calls_made=r["tool_calls_made"], tool_calls_min=r["tool_calls_min"],
                collateral_count=r["collateral_count"], root_cause=r["root_cause"],
                verdict=r["verdict"], closed_at=datetime.fromisoformat(r["closed_at"]),
                cascade_id=r["cascade_id"],
            )
            for r in rows
        ]

    def _scope(self, all_sessions: bool) -> tuple[str, tuple[str, ...]]:
        """The WHERE clause that keeps one run's rows apart from another's.

        Rows written before the column existed have a NULL `session_id` and so
        match no current session, which is the right answer: they are somebody
        else's shift.
        """
        if all_sessions:
            return "", ()
        return " WHERE session_id = ?", (self.session_id,)

    def domain_stats(self, all_sessions: bool = False) -> dict[str, DomainStat]:
        where, params = self._scope(all_sessions)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT domain, COUNT(*) AS total, SUM(correct) AS correct "
                f"FROM closed_tickets{where} GROUP BY domain",
                params,
            ).fetchall()
        return {
            r["domain"]: DomainStat(
                domain=r["domain"], total=r["total"], correct=r["correct"] or 0
            )
            for r in rows
        }
