"""The fault scheduler and the ticket queue.

This is what makes a session *unfamiliar*: it picks a fault and a placement at
random from the whole catalog, applies it, re-snapshots the baseline, and hands
back a ticket whose opening text came from the persona rather than from the
fault's own vocabulary.
"""

from datetime import datetime, timedelta
from random import Random

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.base import Fault, Placement
from vitsc.faults.registry import all_faults, get_fault
from vitsc.persona.models import Persona
from vitsc.persona.personas import card_for
from vitsc.session.ticket import SLA_MINUTES, Ticket, TicketState, priority_for
from vitsc.world.invariants import Baseline, capture_baseline
from vitsc.world.models import World

MAX_ACTIVE = 4
ARRIVAL_MINUTES = 10


def forgive(standing: Baseline, before: Baseline, after: Baseline) -> Baseline:
    """Fold a newly applied fault into the standing baseline.

    Overwriting the baseline on every arrival would launder the technician's
    mistakes: damage done while working ticket 1 is simply *absent* from a
    baseline captured when ticket 2 arrives, so grading sees a clean world.

    So instead of re-snapshotting, forgive exactly what the new fault changed —
    the difference its `apply()` made — and keep every older expectation. A
    disabled account or stopped service stays a violation for the rest of the
    session; the fault that legitimately caused one does not.
    """
    def dropped(name: str) -> set[str]:
        return before.group_members.get(name, set()) - after.group_members.get(name, set())

    return Baseline(
        enabled_users=standing.enabled_users
        - (before.enabled_users - after.enabled_users),
        running_services=standing.running_services
        - (before.running_services - after.running_services),
        group_members={
            name: members - dropped(name)
            for name, members in standing.group_members.items()
        },
        # DNS is the one invariant a fault *adds* to rather than removes from.
        allowed_dns=standing.allowed_dns | (after.allowed_dns - before.allowed_dns),
    )


def reporter_sam(world: World, at: Placement) -> str | None:
    """Who phones this in.

    User placements name the person directly. Machine placements resolve
    through `assigned_to`, and printer placements carry a `hostname/printer`
    key, so both reduce to the same machine lookup.
    """
    if at.kind == "user":
        return at.key
    machine = world.machines.get(at.key.split("/")[0])
    return machine.assigned_to if machine else None


class SessionQueue:
    def __init__(
        self,
        env: SimulatedEnvironment,
        persona: Persona,
        rng: Random,
        now: datetime,
    ) -> None:
        self.env = env
        self.persona = persona
        self.rng = rng
        self.tickets: list[Ticket] = []
        self.baseline: Baseline = capture_baseline(env.world)
        self._next_id = 1
        self._last_arrival = now

    def active(self) -> list[Ticket]:
        return sorted(
            (t for t in self.tickets if t.state is not TicketState.CLOSED),
            key=lambda t: (t.system_priority, t.opened_at),
        )

    def get(self, ticket_id: int) -> Ticket:
        return next(t for t in self.tickets if t.id == ticket_id)

    def persona_for(self, ticket: Ticket) -> Persona:
        """The persona bound to this ticket's leak terms.

        Lives here, not in the chat route, so the web layer never imports the
        fault registry to speak to a user.
        """
        return self.persona.for_fault(get_fault(ticket.fault_id).leak_terms)

    def _candidates(self) -> list[tuple[Fault, Placement]]:
        taken = {(t.fault_id, t.placement.key) for t in self.active()}
        return [
            (fault, placement)
            for fault in all_faults()
            for placement in fault.placements(self.env.world)
            if (fault.id, placement.key) not in taken
            # A fault already present has no one left to report it — this also
            # covers a closed ticket the technician never actually fixed.
            and not fault.is_present(self.env.world, placement)
            and reporter_sam(self.env.world, placement) is not None
        ]

    def open_ticket(self) -> Ticket | None:
        if len(self.active()) >= MAX_ACTIVE:
            return None

        candidates = self._candidates()
        if not candidates:
            return None

        fault, placement = self.rng.choice(candidates)
        before = capture_baseline(self.env.world)
        fault.apply(self.env.world, placement, self.rng)

        # Forgive this fault's own damage, so repairing it is never a violation,
        # while keeping every expectation the technician has already broken.
        self.baseline = forgive(self.baseline, before, capture_baseline(self.env.world))

        user = self.env.world.org.users[reporter_sam(self.env.world, placement)]
        card = card_for(user, self.rng)
        symptoms = fault.symptoms(self.env.world, placement)
        priority = priority_for(fault, user)

        ticket = Ticket(
            id=self._next_id,
            fault_id=fault.id,
            placement=placement,
            persona=card,
            symptoms=symptoms,
            # Bound the same way `persona_for` binds an open ticket; the
            # fault is already in hand here, so no registry round-trip.
            report_text=self.persona.for_fault(fault.leak_terms).initial_report(
                card, symptoms
            ),
            system_priority=priority,
            opened_at=self.env.world.clock,
            sla_minutes=SLA_MINUTES[priority],
        )
        self._next_id += 1
        self.tickets.append(ticket)
        return ticket

    def tick(self, now: datetime) -> list[Ticket]:
        """Open new tickets as the arrival interval elapses."""
        arrivals: list[Ticket] = []
        while now - self._last_arrival >= timedelta(minutes=ARRIVAL_MINUTES):
            self._last_arrival += timedelta(minutes=ARRIVAL_MINUTES)
            ticket = self.open_ticket()
            if ticket is None:
                break
            arrivals.append(ticket)
        return arrivals
