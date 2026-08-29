"""The simulated tier-2 queue.

Deterministic and template-driven on purpose. The bounce decision has to be
reproducible in tests and correct with nothing running on localhost, so it
never touches a model — same reasoning as `TemplatePersona`.

Ownership is judged first: a fixable fault is bounced back regardless of how
well the note is written, because it never belonged to tier-2 at all —
`escalation_is_correct` owns that call, and no amount of evidence changes it.
Only a fault that genuinely belongs to tier-2 goes on to the evidence check:
an escalation with no findings in it is bounced even then, because "not my
problem" is not a handoff.
"""

from pydantic import BaseModel

from vitsc.faults.base import Fault, bind_query
from vitsc.session.ticket import Ticket
from vitsc.world.models import World

# "A couple of words" is not a handoff. Four is the shortest a technician
# could plausibly name what they found and where.
MIN_NOTE_WORDS = 4


class Tier2Response(BaseModel):
    accepted: bool
    text: str


def _evidence_targets(ticket: Ticket, fault: Fault, world: World) -> set[str]:
    """What a usable note could plausibly mention.

    `escalation_evidence` is the fault's own choice of what counts; when it
    declares none (the `FaultBase` default), the diagnostic path stands in —
    whatever a technician would have seen on the way to escalating.
    """
    queries = fault.escalation_evidence or fault.diagnostic_path(ticket.placement)
    targets = {ticket.placement.key}
    for query in queries:
        bound = bind_query(query, ticket.placement, world)
        if bound.target:
            targets.add(bound.target)
    return {target.lower() for target in targets if target}


def _has_evidence(ticket: Ticket, fault: Fault, world: World) -> bool:
    note = (ticket.escalation_note or "").strip()
    if len(note.split()) < MIN_NOTE_WORDS:
        return False
    lowered = note.lower()
    return any(target in lowered for target in _evidence_targets(ticket, fault, world))


def review_escalation(ticket: Ticket, fault: Fault, world: World) -> Tier2Response:
    if not fault.escalation_is_correct:
        # Careful on purpose: this is the one bounce message that must not
        # name the cause, or the "nudge" becomes the answer.
        return Tier2Response(
            accepted=False,
            text=(
                "This is within your scope to resolve. Take another look with "
                "the diagnostics you already have before escalating again."
            ),
        )
    if not _has_evidence(ticket, fault, world):
        return Tier2Response(
            accepted=False,
            text=(
                "Tell us what you found before we can take this — what did "
                "you see, and where?"
            ),
        )
    return Tier2Response(
        accepted=True,
        text=f"Accepted. {fault.escalation_reason} We'll take it from here.",
    )
