from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from vitsc.tools.base import UNKNOWN, ToolCall
from vitsc.tools.registry import all_tools, get_tool
from vitsc.web.routes.queue import _session, _ticket_or_404

router = APIRouter()


def parse_args(raw: str) -> dict[str, str]:
    """'sam=m.alvarez host=MER-WS-001' -> dict. Malformed pairs are dropped."""
    out: dict[str, str] = {}
    for chunk in raw.split():
        if "=" in chunk:
            key, _, value = chunk.partition("=")
            out[key.strip()] = value.strip()
    return out


@router.get("/ticket/{ticket_id}/tools", response_class=HTMLResponse)
def tool_pane(request: Request, ticket_id: int):
    from vitsc.web.app import templates
    ticket = _ticket_or_404(request, ticket_id)
    return templates.TemplateResponse(
        request, "_tools.html",
        {"ticket": ticket, "tools": all_tools(), "calls": ticket.tool_calls},
    )


@router.post("/ticket/{ticket_id}/tool", response_class=HTMLResponse)
def run_tool(
    request: Request,
    ticket_id: int,
    tool: str = Form(...),
    command: str = Form(...),
    args: str = Form(""),
):
    from vitsc.web.app import templates
    session = _session(request)
    ticket = _ticket_or_404(request, ticket_id)
    log = session.log_for(ticket_id)

    try:
        implementation = get_tool(tool)
    except KeyError:
        call = ToolCall(
            tool=tool, command=command, args={}, ok=False, mutating=False,
            rendered=UNKNOWN.format(cmd=tool),
        )
        log.record(call)
    else:
        implementation.invoke(session.env, log, command, parse_args(args))

    ticket.tool_calls = list(log.calls)
    return templates.TemplateResponse(request, "_toolout.html", {"calls": log.calls})
