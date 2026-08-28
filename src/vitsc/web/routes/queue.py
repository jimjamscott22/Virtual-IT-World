from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from vitsc.session.ticket import Priority

router = APIRouter()


def _session(request: Request):
    return request.app.state.session


def _ticket_or_404(request: Request, ticket_id: int):
    try:
        return _session(request).queue.get(ticket_id)
    except StopIteration:
        raise HTTPException(status_code=404, detail="No such ticket") from None


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    from vitsc.web.app import templates
    session = _session(request)
    return templates.TemplateResponse(
        request, "index.html",
        {
            "tickets": session.queue.active(),
            "now": session.env.world.clock,
            "degraded": session.degraded,
        },
    )


@router.get("/queue", response_class=HTMLResponse)
def queue_partial(request: Request):
    from vitsc.web.app import templates
    session = _session(request)
    return templates.TemplateResponse(
        request, "_queue.html",
        {"tickets": session.queue.active(), "now": session.env.world.clock},
    )


@router.get("/ticket/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: int):
    from vitsc.web.app import templates
    ticket = _ticket_or_404(request, ticket_id)
    return templates.TemplateResponse(
        request, "_ticket.html",
        {"ticket": ticket, "priorities": list(Priority)},
    )


@router.post("/ticket/{ticket_id}/priority", response_class=HTMLResponse)
def set_priority(request: Request, ticket_id: int, priority: int = Form(...)):
    from vitsc.web.app import templates
    ticket = _ticket_or_404(request, ticket_id)
    ticket.user_priority = Priority(priority)
    return templates.TemplateResponse(
        request, "_ticket.html",
        {"ticket": ticket, "priorities": list(Priority)},
    )
