from datetime import datetime, timedelta
from enum import Enum, IntEnum

from pydantic import BaseModel, Field

from vitsc.env.base import Action
from vitsc.faults.base import Fault, Placement, UserSymptoms
from vitsc.persona.models import ChatTurn, PersonaCard
from vitsc.tools.base import ToolCall
from vitsc.world.models import ADUser


class Priority(IntEnum):
    """Lower is more urgent, so priorities sort naturally."""

    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


SLA_MINUTES = {Priority.P1: 60, Priority.P2: 240, Priority.P3: 480, Priority.P4: 1440}

# Faults that stop a person working entirely are always top priority. Impact
# on the person decides this, not how the ticket ends up being routed — an
# offboarded account is escalate-only, but the employee still cannot log in.
WORK_STOPPING = {
    "ad.account_locked",
    "ad.password_expired",
    "ad.offboarded_reactivation",
    "net.no_dhcp_lease",
}
SENIOR_TITLES = {"Operations Manager", "Controller"}


class TicketState(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    AWAITING_TIER2 = "awaiting_tier2"
    CLOSED = "closed"


class Disposition(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"


def priority_for(fault: Fault, user: ADUser, reporters: int = 1) -> Priority:
    """The *system's* triage call, which the player's own is graded against.

    Impact first, then who is blocked, then how gnarly it looks. A cascade is
    impact by definition: three people stopped is a P1 whatever the fault's
    own difficulty says, which is why the count is an argument and not a
    lookup.
    """
    if fault.id in WORK_STOPPING or reporters >= 3:
        return Priority.P1
    if reporters > 1:
        return Priority.P2
    if user.title in SENIOR_TITLES:
        return Priority.P2
    return Priority.P3 if fault.difficulty >= 2 else Priority.P4


class Ticket(BaseModel):
    id: int
    fault_id: str
    placement: Placement
    persona: PersonaCard
    symptoms: UserSymptoms
    report_text: str
    system_priority: Priority
    # What the player triaged it as. None means they never set one, which
    # grading treats as "no opinion" rather than as a wrong answer.
    user_priority: Priority | None = None
    opened_at: datetime
    sla_minutes: int
    # Shared by every sibling ticket the same fault instance produced. None
    # for the ordinary single-reporter case.
    cascade_id: str | None = None
    state: TicketState = TicketState.OPEN
    disposition: Disposition | None = None
    closed_at: datetime | None = None
    # Set by `escalate()`, read by `session/tier2.py:review_escalation()`.
    escalation_note: str | None = None
    # Every time a bounce sends the ticket back — grading reads this to tell
    # "escalated correctly" from "tried to hand it off, kept it in the end".
    tier2_bounces: int = 0
    chat: list[ChatTurn] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)

    @property
    def deadline(self) -> datetime:
        return self.opened_at + timedelta(minutes=self.sla_minutes)

    @property
    def elapsed_minutes(self) -> float | None:
        if self.closed_at is None:
            return None
        return (self.closed_at - self.opened_at).total_seconds() / 60

    def is_overdue(self, now: datetime) -> bool:
        return now > self.deadline

    def close(self, disposition: Disposition, at: datetime) -> None:
        if self.state is TicketState.CLOSED:
            raise ValueError(f"ticket {self.id} is already closed")
        self.state = TicketState.CLOSED
        self.disposition = disposition
        self.closed_at = at

    def escalate(self, note: str, at: datetime) -> None:
        """Hand off to tier-2. Not a close — `review_escalation()` decides
        whether it sticks. `at` matches `close()`'s signature for a future
        `escalated_at` timestamp; nothing reads it yet."""
        if self.state is TicketState.CLOSED:
            raise ValueError(f"ticket {self.id} is already closed")
        self.escalation_note = note
        self.state = TicketState.AWAITING_TIER2

    def reopen(self, text: str) -> None:
        """A tier-2 bounce: back to the technician, disposition undecided again."""
        # pylint does not model pydantic's default_factory: it infers `chat`
        # as a FieldInfo rather than the list built at runtime.
        self.chat.append(ChatTurn(speaker="tier2", text=text))  # pylint: disable=no-member
        self.tier2_bounces += 1
        self.state = TicketState.IN_PROGRESS
        self.disposition = None

    def accept_escalation(self, at: datetime) -> None:
        self.close(Disposition.ESCALATED, at=at)
