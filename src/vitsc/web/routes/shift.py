from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from vitsc.web.routes.queue import _session

router = APIRouter()


@router.get("/shift", response_class=HTMLResponse)
def shift_summary(request: Request):
    """The whole shift, summed.

    Reachable at any point, not only once the clock runs out: a technician
    halfway through a shift should be able to see how it is going, and the
    report reads the same either way.
    """
    from vitsc.web.app import templates
    session = _session(request)
    now = session.env.world.clock
    return templates.TemplateResponse(
        request, "shift.html",
        {
            "report": session.shift_report(),
            "shift": session.shift,
            "now": now,
            "remaining": session.shift.remaining(now),
            "over": session.shift.is_over(now),
            "degraded": session.degraded,
        },
    )
