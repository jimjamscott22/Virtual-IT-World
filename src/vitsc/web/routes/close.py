from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from vitsc.faults.registry import get_fault
from vitsc.session.afteraction import build_after_action
from vitsc.session.grading import grade_ticket
from vitsc.session.ticket import Disposition, TicketState
from vitsc.web.routes.queue import _session, _ticket_or_404

router = APIRouter()


@router.post("/ticket/{ticket_id}/close", response_class=HTMLResponse)
def close_ticket(request: Request, ticket_id: int, disposition: str = Form(...)):
    from vitsc.web.app import templates
    session = _session(request)
    ticket = _ticket_or_404(request, ticket_id)
    if ticket.state is TicketState.CLOSED:
        raise HTTPException(status_code=409, detail="Ticket is already closed")

    fault = get_fault(ticket.fault_id)
    ticket.tool_calls = list(session.log_for(ticket_id).calls)
    ticket.close(Disposition(disposition), at=session.env.world.clock)

    siblings = (
        [t for t in session.queue.tickets if t.cascade_id == ticket.cascade_id]
        if ticket.cascade_id is not None
        else None
    )
    grade = grade_ticket(ticket, fault, session.env, session.queue.baseline, siblings=siblings)
    report = build_after_action(ticket, fault, grade, session.env.world, siblings=siblings)
    session.store.save_closed(ticket, grade, report)

    return templates.TemplateResponse(
        request, "_afteraction.html",
        {"ticket": ticket, "grade": grade, "report": report},
    )


@router.get("/history", response_class=HTMLResponse)
def history(request: Request):
    from vitsc.web.app import templates
    session = _session(request)
    return templates.TemplateResponse(
        request, "history.html",
        {"records": session.store.history(), "stats": session.store.domain_stats()},
    )
