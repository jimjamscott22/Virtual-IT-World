import asyncio
import json
import time
from datetime import timedelta

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


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    session = _session(request)

    async def stream():
        while not await request.is_disconnected():
            advance_clock_if_due(session, time.monotonic())
            now = session.env.world.clock
            arrivals = session.queue.tick(now)
            payload = {
                "clock": now.isoformat(),
                "arrivals": [t.id for t in arrivals],
                "active": [
                    {
                        "id": t.id,
                        "remaining": int((t.deadline - now).total_seconds() // 60),
                        "overdue": t.is_overdue(now),
                    }
                    for t in session.queue.active()
                ],
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(TICK_SECONDS)

    return StreamingResponse(stream(), media_type="text/event-stream")
