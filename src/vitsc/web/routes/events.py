import asyncio
import json
from datetime import timedelta

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from vitsc.web.routes.queue import _session

router = APIRouter()
TICK_SECONDS = 1.0
MINUTES_PER_TICK = 1


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    session = _session(request)

    async def stream():
        while not await request.is_disconnected():
            session.env.world.clock += timedelta(minutes=MINUTES_PER_TICK)
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
