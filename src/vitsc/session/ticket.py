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

# Faults that stop a person working entirely are always top priority.
WORK_STOPPING = {"ad.account_locked", "ad.password_expired", "net.no_dhcp_lease"}
SENIOR_TITLES = {"Operations Manager", "Controller"}


class TicketState(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Disposition(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"


def priority_for(fault: Fault, user: ADUser) -> Priority:
    """The *system's* triage call, which the player's own is graded against.

    Impact first, then who is blocked, then how gnarly it looks — the same
    order a real queue triages in.
    """
    if fault.id in WORK_STOPPING:
        return Priority.P1
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
    state: TicketState = TicketState.OPEN
    disposition: Disposition | None = None
    closed_at: datetime | None = None
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
