"""The after-action report.

The report, not the score, is why the drill transfers (spec §8): it names the
root cause the technician was never told, shows the shortest path that would
have found it, and says plainly what went wrong.
"""

from pydantic import BaseModel, Field

from vitsc.faults.base import Fault, bind_query
from vitsc.session.grading import Grade
from vitsc.session.ticket import Disposition, Ticket
from vitsc.world.models import World


class AfterAction(BaseModel):
    root_cause: str
    shortest_path: list[str] = Field(default_factory=list)
    tool_calls_made: int
    tool_calls_minimum: int
    wasted_calls: list[str] = Field(default_factory=list)
    touched_before_asking: bool
    collateral: list[str] = Field(default_factory=list)
    within_sla: bool
    verdict: str
    cascade_note: str = ""
    # Mirrors `Grade.escalation_quality` ("none"/"accepted"/"bounced") so a
    # template can render the escalation outcome without reaching into grade.
    tier2: str = "none"


def build_after_action(
    ticket: Ticket,
    fault: Fault,
    grade: Grade,
    world: World,
    siblings: list[Ticket] | None = None,
) -> AfterAction:
    path = [
        f"{q.kind} {q.target}".strip()
        for q in (
            bind_query(q, ticket.placement, world)
            for q in fault.diagnostic_path(ticket.placement)
        )
    ]
    useful = {p.split()[-1] for p in path}
    wasted = [
        f"{c.tool} {c.command} {' '.join(c.args.values())}".strip()
        for c in ticket.tool_calls
        if not c.mutating and not (set(c.args.values()) & useful)
    ]

    # Branch on what the technician actually *did*, not on disposition_correct.
    # That flag folds in "was the fault cleared", so keying the wrong-escalation
    # message off it accuses someone who closed a ticket as resolved of having
    # escalated it.
    escalated = ticket.disposition is Disposition.ESCALATED
    if grade.escalation_quality == "bounced" and grade.fault_cleared:
        # Checked before `grade.correct`, which this combination already
        # satisfies — the ticket ended up fixed and disposed correctly, but
        # that would silently erase the fact that tier-2 sent it back first.
        verdict = "You tried to hand this off; it was yours. You did fix it after."
    elif grade.correct:
        verdict = "Resolved correctly."
    elif fault.escalation_is_correct and not escalated:
        verdict = "This one was not yours to fix — it needed escalation."
    elif escalated and not fault.escalation_is_correct:
        verdict = "You escalated something you had the tools and authority to fix."
    elif grade.collateral and grade.fault_cleared:
        verdict = "The symptom cleared, but you broke something else doing it."
    elif grade.collateral:
        verdict = "You broke something else, and the original fault is still there."
    else:
        verdict = "The underlying fault was still present when you closed the ticket."

    if grade.fault_cleared and grade.duplicate_mutations:
        times = grade.duplicate_mutations + 1
        verdict = f"{verdict} You fixed this {times} times. One root cause needs one fix."

    cascade_note = ""
    if siblings and len(siblings) > 1:
        cascade_note = (
            f"One {fault.canonical_title.lower()} was behind {len(siblings)} tickets "
            "— the fix was a single fix."
        )

    return AfterAction(
        root_cause=fault.canonical_title,
        shortest_path=path,
        tool_calls_made=grade.tool_calls_made,
        tool_calls_minimum=grade.tool_calls_minimum,
        wasted_calls=wasted,
        # Only an actual mutation can be "touching" — a technician who only
        # read and then escalated has touched nothing to be accused of.
        touched_before_asking=any(c.mutating for c in ticket.tool_calls)
        and grade.questions_before_first_mutation == 0,
        collateral=grade.collateral,
        within_sla=grade.within_sla,
        verdict=verdict,
        cascade_note=cascade_note,
        tier2=grade.escalation_quality,
    )
