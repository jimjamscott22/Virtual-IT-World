"""The fault scheduler and the ticket queue.

This is what makes a session *unfamiliar*: it picks a fault and a placement at
random from the whole catalog, applies it, re-snapshots the baseline, and hands
back a ticket whose opening text came from the persona rather than from the
fault's own vocabulary.
"""

from datetime import datetime, timedelta
from random import Random

from vitsc.distractors.registry import all_distractors
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
CASCADE_MAX = 3


def seed_distractors(world: World, rng: Random, count: int) -> list[tuple[str, Placement]]:
    """Apply `count` distinct distractors before the first baseline capture.

    Order matters: these are anomalies the technician *inherits*, so the
    baseline must be captured after them. Capturing first would report the
    world's own pre-existing quirks as the technician's collateral damage —
    the same capture-after-apply rule `world/invariants.py` documents.
    """
    candidates = [(d, at) for d in all_distractors() for at in d.placements(world)]
    rng.shuffle(candidates)
    seeded: list[tuple[str, Placement]] = []
    used: set[str] = set()
    for distractor, at in candidates:
        if len(seeded) >= count:
            break
        if distractor.id in used:
            continue
        distractor.apply(world, at, rng)
        used.add(distractor.id)
        seeded.append((distractor.id, at))
    return seeded


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
    """Who phones this in, for a fault that does not declare its own reporters.

    User placements name the person directly. Machine placements resolve
    through `assigned_to`, and printer placements carry a `hostname/printer`
    key, so both reduce to the same machine lookup.
    """
    if at.kind == "user":
        return at.key
    machine = world.machines.get(at.key.split("/")[0])
    return machine.assigned_to if machine else None


def resolved_reporters(world: World, fault: Fault, at: Placement) -> list[str]:
    """Who actually gets a ticket for this fault instance.

    `fault.reporters()` names an explicit list for faults that affect several
    people at once, which is what makes a fault a cascade. Every other fault
    returns `None` (`FaultBase`'s default), which reduces to the single person
    `reporter_sam` resolves. Anyone missing from `world.org.users` is
    dropped — a malformed reporter list must not crash ticket creation.
    """
    reporters = fault.reporters(world, at)
    if reporters is None:
        single = reporter_sam(world, at)
        reporters = [single] if single is not None else []
    return [sam for sam in reporters if sam in world.org.users]


class SessionQueue:
    def __init__(
        self,
        env: SimulatedEnvironment,
        persona: Persona,
        rng: Random,
        now: datetime,
        distractor_count: int = 0,
    ) -> None:
        self.env = env
        self.persona = persona
        self.rng = rng
        self.tickets: list[Ticket] = []
        # Seeded before the baseline is captured, so this noise is inherited
        # world state rather than the technician's own collateral damage.
        self.distractors = seed_distractors(env.world, rng, distractor_count)
        self.baseline: Baseline = capture_baseline(env.world)
        self._next_id = 1
        self._next_cascade_id = 1
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
            and resolved_reporters(self.env.world, fault, placement)
        ]

    def _open(self, fault: Fault, placement: Placement) -> list[Ticket]:
        """Apply `fault` at `placement` and build one ticket per reporter.

        Shared by `open_ticket()` (which picks the fault) and `open_cascade()`
        (which is handed one), so the actual bookkeeping — applying the fault,
        forgiving its own damage, capping the reporter count, minting tickets —
        exists exactly once.
        """
        before = capture_baseline(self.env.world)
        fault.apply(self.env.world, placement, self.rng)

        # Forgive this fault's own damage, so repairing it is never a violation,
        # while keeping every expectation the technician has already broken.
        self.baseline = forgive(self.baseline, before, capture_baseline(self.env.world))

        reporters = resolved_reporters(self.env.world, fault, placement)
        room = MAX_ACTIVE - len(self.active())
        count = max(0, min(len(reporters), CASCADE_MAX, room))
        if count == 0:
            return []
        sampled = self.rng.sample(reporters, count)

        cascade_id = None
        if count > 1:
            cascade_id = f"C{self._next_cascade_id}"
            self._next_cascade_id += 1

        symptoms = fault.symptoms(self.env.world, placement)
        tickets: list[Ticket] = []
        for sam in sampled:
            user = self.env.world.org.users[sam]
            # Each sibling gets its own card and its own persona-spoken report
            # text — three tickets describing one outage in three voices.
            card = card_for(user, self.rng)
            priority = priority_for(fault, user, reporters=count)
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
                cascade_id=cascade_id,
            )
            self._next_id += 1
            tickets.append(ticket)
        self.tickets.extend(tickets)
        return tickets

    def open_ticket(self) -> list[Ticket]:
        room = MAX_ACTIVE - len(self.active())
        if room <= 0:
            return []

        # A candidate whose full cascade would not fit in the room left is
        # skipped entirely rather than dealt partially.
        candidates = [
            (fault, placement)
            for fault, placement in self._candidates()
            if min(len(resolved_reporters(self.env.world, fault, placement)), CASCADE_MAX)
            <= room
        ]
        if not candidates:
            return []

        fault, placement = self.rng.choice(candidates)
        return self._open(fault, placement)

    def open_one(self) -> Ticket | None:
        """The first ticket of whatever `open_ticket()` deals, for callers
        that only ever want a single arrival."""
        tickets = self.open_ticket()
        return tickets[0] if tickets else None

    def open_for(self, fault: Fault, at: Placement) -> list[Ticket]:
        """Open a named fault at a named placement directly, bypassing the
        scheduler. For tests that want a specific fault/placement rather than
        whatever the random candidate pool would deal.
        """
        return self._open(fault, at)

    def open_cascade(self, fault: Fault) -> list[Ticket]:
        """Open a named fault's cascade directly, at its first placement."""
        return self.open_for(fault, fault.placements(self.env.world)[0])

    def tick(self, now: datetime) -> list[Ticket]:
        """Open new tickets as the arrival interval elapses."""
        arrivals: list[Ticket] = []
        while now - self._last_arrival >= timedelta(minutes=ARRIVAL_MINUTES):
            self._last_arrival += timedelta(minutes=ARRIVAL_MINUTES)
            tickets = self.open_ticket()
            if not tickets:
                break
            arrivals.extend(tickets)
        return arrivals
