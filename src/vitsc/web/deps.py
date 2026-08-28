from datetime import datetime
from pathlib import Path
from random import Random

from pydantic import BaseModel, ConfigDict

from vitsc.env.simulated import SimulatedEnvironment
from vitsc.persona.config import PersonaSettings, build_persona
from vitsc.persona.models import Persona
from vitsc.session.queue import SessionQueue
from vitsc.session.store import Store
from vitsc.tools.base import ToolLog
from vitsc.world.seed import load_world


class AppSession(BaseModel):
    """A single in-process session, not a per-request one — there is exactly
    one player."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    env: SimulatedEnvironment
    queue: SessionQueue
    store: Store
    logs: dict[int, ToolLog] = {}
    started_at: datetime
    # Wall-clock (time.monotonic()) timestamp of the last time the simulated
    # world.clock was advanced by an SSE connection. There is one player but
    # can be several open SSE connections (multiple tabs, a reconnect) --
    # without a shared marker each one would advance the same clock on its
    # own schedule and time would run faster than one minute per second.
    last_tick_at: float = 0.0

    @classmethod
    def build(
        cls,
        db_path: Path,
        seed: int = 0,
        persona: Persona | None = None,
        now: datetime | None = None,
    ) -> "AppSession":
        env = SimulatedEnvironment(load_world())
        now = now or env.world.clock
        store = Store(db_path)
        store.init()
        # An explicit persona wins (the whole test suite passes one); otherwise
        # the environment decides, defaulting to the model-free template.
        if persona is None:
            persona = build_persona(PersonaSettings.from_env())
        return cls(
            env=env,
            queue=SessionQueue(
                env=env, persona=persona, rng=Random(seed), now=now, distractor_count=3
            ),
            store=store,
            started_at=now,
        )

    @property
    def degraded(self) -> bool:
        """Whether the player is reading template text rather than model text.

        Read through to the persona the queue holds rather than cached, because
        an outage can start at any point in a session. `TemplatePersona` has no
        such attribute and is never degraded — it is the fallback.
        """
        return getattr(self.queue.persona, "degraded", False)

    def log_for(self, ticket_id: int) -> ToolLog:
        return self.logs.setdefault(ticket_id, ToolLog())
