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
    duplicate_mutations: int = 0
    # "none": never escalated. "accepted": tier-2 took it (closed as escalated).
    # "bounced": escalated at least once but closed some other way — sent
    # somewhere it didn't belong, then kept and (maybe) fixed anyway.
    escalation_quality: str = "none"
    # A diligence signal only — never a correctness gate. Whether the
    # technician consulted the KB has no bearing on `correct`.
    kb_consulted: bool = False


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


def duplicate_mutations(ticket: Ticket, siblings: list[Ticket] | None = None) -> int:
    """How many times an identical mutating call was repeated beyond its first use.

    Fixing one root cause three times is one fix, not three. `siblings`, when
    given, folds in every other ticket the same cascade produced, so a
    technician who re-runs the same repair once per sibling ticket is counted
    the same as one who repeats it within a single ticket.
    """
    tickets = [ticket]
    seen_ids = {id(ticket)}
    for sibling in siblings or []:
        if id(sibling) not in seen_ids:
            seen_ids.add(id(sibling))
            tickets.append(sibling)

    counts: dict[tuple[str, str, tuple[tuple[str, str], ...]], int] = {}
    for one in tickets:
        for call in one.tool_calls:
            if not call.mutating:
                continue
            key = (call.tool, call.command, tuple(sorted(call.args.items())))
            counts[key] = counts.get(key, 0) + 1
    return sum(count - 1 for count in counts.values() if count > 1)


def grade_ticket(
    ticket: Ticket,
    fault: Fault,
    env: SimulatedEnvironment,
    baseline: Baseline,
    siblings: list[Ticket] | None = None,
) -> Grade:
    # `siblings` only feeds the report (`duplicate_mutations`), never pass/fail —
    # `is_present()` against the live world already covers every sibling, so
    # special-casing a cascade in the gate itself would be exactly the kind of
    # fault-aware branching the core design principle forbids.
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

    if ticket.disposition is Disposition.ESCALATED:
        escalation_quality = "accepted"
    elif ticket.tier2_bounces > 0:
        escalation_quality = "bounced"
    else:
        escalation_quality = "none"

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
        duplicate_mutations=duplicate_mutations(ticket, siblings),
        escalation_quality=escalation_quality,
        kb_consulted=any(call.tool == "kb" for call in ticket.tool_calls),
    )
