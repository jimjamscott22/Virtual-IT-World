"""The fixed shift, and the report that closes it.

A drill needs an end. Without one the queue deals forever, and the
technician's work never adds up to anything — the after-action answers "how
did that ticket go" and nothing answered "how did the shift go".

Eight hours of *simulated* time. `web/routes/events.py` advances
`world.clock` one minute per real second, so a shift is eight real minutes at
the keyboard: long enough to work a queue and be surprised by it, short
enough to run twice in a sitting.

What ends is the *arrivals*, not the session. Tickets already open stay
workable, the way a real shift's last call does not evaporate at five
o'clock. `SessionQueue.tick()` is the only thing the shift gates, which is
the honest seam: `open_for()` and `open_cascade()` are explicit test hooks
and stay usable regardless.
"""

from datetime import datetime, timedelta

from pydantic import BaseModel

from vitsc.session.store import ClosedRecord, DomainStat

SHIFT_MINUTES = 8 * 60


class Shift(BaseModel):
    """One fixed-length working day on the simulated clock."""

    started_at: datetime
    minutes: int = SHIFT_MINUTES

    @property
    def ends_at(self) -> datetime:
        return self.started_at + timedelta(minutes=self.minutes)

    def elapsed(self, now: datetime) -> int:
        """Simulated minutes worked, never negative and never past the end."""
        worked = (now - self.started_at).total_seconds() / 60
        return int(max(0.0, min(worked, float(self.minutes))))

    def remaining(self, now: datetime) -> int:
        return self.minutes - self.elapsed(now)

    def is_over(self, now: datetime) -> bool:
        return now >= self.ends_at


class ShiftReport(BaseModel):
    """What the whole shift added up to.

    Deliberately the same shape of judgement the per-ticket after-action
    makes — closed correctly, inside SLA, without collateral — just summed.
    Nothing here is a new opinion about the technician's work; it is the
    existing per-ticket verdicts counted.
    """

    closed: int
    correct: int
    within_sla: int
    escalated: int
    collateral: int
    unresolved: int
    by_domain: list[DomainStat] = []
    verdict: str = ""

    @property
    def accuracy(self) -> float:
        return self.correct / self.closed if self.closed else 0.0

    @property
    def sla_rate(self) -> float:
        return self.within_sla / self.closed if self.closed else 0.0


def shift_verdict(report: "ShiftReport") -> str:
    """One line for the whole day, in the after-action's voice.

    Ordered worst-first on purpose: collateral damage outranks accuracy,
    because breaking the estate is worse than misreading a ticket, and an
    abandoned queue outranks both — the tickets nobody worked are the ones
    the person on the other end is still waiting on.
    """
    if report.closed == 0:
        return "No tickets closed. Nothing to judge yet."
    if report.collateral:
        return (
            f"You closed {report.closed}, but broke something else on "
            f"{report.collateral} of them. Fix the ticket, not the symptom."
        )
    if report.unresolved:
        return (
            f"{report.closed} closed, {report.unresolved} left open at the end "
            "of the shift. Someone is still waiting on those."
        )
    if report.accuracy == 1.0 and report.sla_rate == 1.0:
        return f"A clean shift: {report.closed} closed, all correct, all inside SLA."
    if report.accuracy == 1.0:
        return (
            f"All {report.closed} closed correctly, but "
            f"{report.closed - report.within_sla} ran past SLA."
        )
    return (
        f"{report.correct} of {report.closed} closed correctly. "
        "The after-action on each one says where the rest went wrong."
    )


def build_shift_report(
    records: list[ClosedRecord],
    domain_stats: dict[str, DomainStat],
    unresolved: int,
) -> ShiftReport:
    """Sum the shift from what the store already knows.

    Takes the store's own rows rather than the live queue, so the report says
    what was actually recorded — the same source `history()` renders — instead
    of re-deriving a second, possibly disagreeing, account of the day.
    """
    report = ShiftReport(
        closed=len(records),
        correct=sum(1 for r in records if r.correct),
        within_sla=sum(1 for r in records if r.within_sla),
        escalated=sum(1 for r in records if r.disposition == "escalated"),
        collateral=sum(1 for r in records if r.collateral_count),
        unresolved=unresolved,
        by_domain=sorted(domain_stats.values(), key=lambda s: s.domain),
    )
    report.verdict = shift_verdict(report)
    return report
