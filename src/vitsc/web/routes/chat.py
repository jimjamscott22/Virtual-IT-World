from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from vitsc.persona.models import ChatTurn
from vitsc.web.routes.queue import _session, _ticket_or_404

router = APIRouter()


@router.post("/ticket/{ticket_id}/chat", response_class=HTMLResponse)
def send_message(request: Request, ticket_id: int, message: str = Form(...)):
    from vitsc.web.app import templates
    session = _session(request)
    ticket = _ticket_or_404(request, ticket_id)

    ticket.chat.append(ChatTurn(speaker="tech", text=message))
    reply = session.queue.persona_for(ticket).reply(
        ticket.persona, ticket.symptoms, ticket.chat[:-1], message
    )
    ticket.chat.append(ChatTurn(speaker="user", text=reply))

    return templates.TemplateResponse(request, "_chat.html", {"ticket": ticket})
