"""Template context shared by every full-page route.

The header carries live shift state on every page — the remaining time, the
progress rail, and the two banners the SSE tick reveals mid-session. Each
full-page route used to compute its own subset of that, so the knowledge base
and history pages simply did not have it. One helper means one calculation,
and the SSE payload (`routes/events.py:build_payload`) uses the same
`shift_progress()` so the first render and every later tick agree.

Partial routes (`/queue`, `/ticket/{id}`, ...) keep their own focused
contexts: they render inside a page that already has a header.
"""

from datetime import datetime

from fastapi import Request

from vitsc.session.shift import Shift


def shift_progress(shift: Shift, now: datetime) -> float:
    """Percentage of the shift worked, bounded to 0–100 by `Shift.elapsed()`."""
    return round(100 * shift.elapsed(now) / shift.minutes, 2)


def shell_context(request: Request, **values: object) -> dict[str, object]:
    session = request.app.state.session
    now = session.env.world.clock
    return {
        "degraded": session.degraded,
        "shift_remaining": session.shift.remaining(now),
        "shift_over": session.shift.is_over(now),
        "shift_progress": shift_progress(session.shift, now),
        "shift_starts": session.shift.started_at.strftime("%H:%M"),
        "shift_ends": session.shift.ends_at.strftime("%H:%M"),
        **values,
    }
