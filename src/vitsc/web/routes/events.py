import asyncio
import json
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from vitsc.web.deps import AppSession
from vitsc.web.routes.queue import _session

router = APIRouter()
TICK_SECONDS = 1.0
MINUTES_PER_TICK = 1


def advance_clock_if_due(session: AppSession, wall_now: float) -> None:
    """Advance the shared world clock at most once per `TICK_SECONDS` of real
    time, no matter how many SSE connections are open.

    Each browser tab (or an `EventSource` reconnect) runs its own copy of the
    stream loop below. Without this guard, every connection would advance the
    same shared `world.clock` on its own one-second cadence, so N open
    connections would make time -- and therefore ticket arrivals and SLA
    deadlines -- run N times too fast.
    """
    if wall_now - session.last_tick_at >= TICK_SECONDS:
        session.env.world.clock += timedelta(minutes=MINUTES_PER_TICK)
        session.last_tick_at = wall_now


def build_payload(session: AppSession, now: datetime, arrivals: list) -> dict:
    """One tick's worth of state for the browser.

    Split out of the stream loop for the same reason `advance_clock_if_due`
    was: the loop itself never terminates, so driving it through TestClient
    hangs. Everything worth asserting lives here instead.
    """
    return {
        "clock": now.isoformat(),
        "arrivals": [t.id for t in arrivals],
        # Degradation starts mid-session, long after the page was rendered,
        # so the banner has to be driven from here rather than from the
        # initial render alone.
        "degraded": session.degraded,
        "active": [
            {
                "id": t.id,
                "remaining": int((t.deadline - now).total_seconds() // 60),
                "overdue": t.is_overdue(now),
            }
            for t in session.queue.active()
        ],
    }


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    session = _session(request)

    async def stream():
        while not await request.is_disconnected():
            advance_clock_if_due(session, time.monotonic())
            now = session.env.world.clock
            arrivals = session.queue.tick(now)
            payload = build_payload(session, now, arrivals)
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(TICK_SECONDS)

    return StreamingResponse(stream(), media_type="text/event-stream")
