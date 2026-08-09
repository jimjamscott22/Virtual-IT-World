"""What the technician actually achieved on one ticket.

Grading never asks a fault whether it was "solved its way" — it asks
`is_present()` against the live world and `check_invariants()` against the
baseline. Any route to a healthy world counts; any route that breaks something
else does not.
"""

from pydantic import BaseModel, Field

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.base import Fault
from vitsc.session.ticket import Disposition, Ticket
from vitsc.world.invariants import Baseline, check_invariants


class Grade(BaseModel):
    correct: bool
    fault_cleared: bool
    disposition_correct: bool
    collateral: list[str] = Field(default_factory=list)
    elapsed_minutes: float
    sla_minutes: int
    within_sla: bool
    tool_calls_made: int
    tool_calls_minimum: int
    questions_before_first_mutation: int
    triage_correct: bool


def questions_before_first_mutation(ticket: Ticket) -> int:
    """How many questions the technician asked before touching anything.

    Both `ChatTurn.at` and `ToolCall.at` are wall clock, so the two lists
    interleave cleanly. Mutating tool calls are the cutoff; reads are free and
    are what the technician is *supposed* to do first.
    """
    tech_turns = [turn for turn in ticket.chat if turn.speaker == "tech"]
    mutations = [call.at for call in ticket.tool_calls if call.mutating]
    if not mutations:
        return len(tech_turns)
    cutoff = min(mutations)
    return sum(1 for turn in tech_turns if turn.at <= cutoff)


def grade_ticket(
    ticket: Ticket, fault: Fault, env: SimulatedEnvironment, baseline: Baseline
) -> Grade:
    cleared = not fault.is_present(env.world, ticket.placement)
    collateral = check_invariants(env.world, baseline)

    if fault.escalation_is_correct:
        disposition_correct = ticket.disposition is Disposition.ESCALATED
    else:
        disposition_correct = ticket.disposition is Disposition.RESOLVED and cleared

    # An escalate-only fault is correct when escalated, whether or not it is cleared.
    correct = disposition_correct and not collateral
    if not fault.escalation_is_correct:
        correct = correct and cleared

    elapsed = ticket.elapsed_minutes or 0.0

    return Grade(
        correct=correct,
        fault_cleared=cleared,
        disposition_correct=disposition_correct,
        collateral=collateral,
        elapsed_minutes=elapsed,
        sla_minutes=ticket.sla_minutes,
        within_sla=elapsed <= ticket.sla_minutes,
        tool_calls_made=len(ticket.tool_calls),
        tool_calls_minimum=len(fault.diagnostic_path(ticket.placement)),
        questions_before_first_mutation=questions_before_first_mutation(ticket),
        # No opinion is not a wrong opinion — an untriaged ticket is not
        # penalised, only a mis-triaged one.
        triage_correct=ticket.user_priority is None
        or ticket.user_priority == ticket.system_priority,
    )
