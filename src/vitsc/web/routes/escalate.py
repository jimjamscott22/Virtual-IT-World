from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from vitsc.faults.registry import get_fault
from vitsc.session.tier2 import review_escalation
from vitsc.session.ticket import Priority, TicketState
from vitsc.web.routes.close import render_after_action
from vitsc.web.routes.queue import _session, _ticket_or_404

router = APIRouter()


@router.get("/ticket/{ticket_id}/escalate", response_class=HTMLResponse)
def escalate_form(request: Request, ticket_id: int):
    from vitsc.web.app import templates
    ticket = _ticket_or_404(request, ticket_id)
    return templates.TemplateResponse(
        request, "_escalate.html", {"ticket": ticket},
    )


@router.post("/ticket/{ticket_id}/escalate", response_class=HTMLResponse)
def escalate_ticket(request: Request, ticket_id: int, note: str = Form(...)):
    from vitsc.web.app import templates
    session = _session(request)
    ticket = _ticket_or_404(request, ticket_id)
    if ticket.state is TicketState.CLOSED:
        raise HTTPException(status_code=409, detail="Ticket is already closed")

    fault = get_fault(ticket.fault_id)
    ticket.escalate(note=note, at=session.env.world.clock)
    response = review_escalation(ticket, fault, session.env.world)

    if response.accepted:
        ticket.accept_escalation(at=session.env.world.clock)
        return render_after_action(request, session, ticket)

    ticket.reopen(response.text)
    return templates.TemplateResponse(
        request, "_tier2.html",
        {"ticket": ticket, "priorities": list(Priority)},
    )
