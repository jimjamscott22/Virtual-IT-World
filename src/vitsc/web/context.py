"""Shared template context for full-page application views."""

from fastapi import Request


def shell_context(request: Request, **values: object) -> dict[str, object]:
    """Return the live shift state used by the application shell."""
    session = request.app.state.session
    now = session.env.world.clock
    progress = 100 * session.shift.elapsed(now) / session.shift.minutes
    return {
        "degraded": session.degraded,
        "shift_remaining": session.shift.remaining(now),
        "shift_over": session.shift.is_over(now),
        "shift_progress": round(max(0.0, min(100.0, progress)), 2),
        **values,
    }
