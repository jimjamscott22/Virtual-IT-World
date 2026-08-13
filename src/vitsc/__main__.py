"""`uv run python -m vitsc` — the normal way to start the drill.

Uses `TemplatePersona`, not `LMStudioPersona`: the model-backed persona takes
a fixed `leak_terms` list at construction (Task 11), but a session runs
tickets against many faults in turn, each with its own leak terms. Wiring a
fault-aware model persona needs the chat route (Task 17), which has the open
ticket's `fault_id` in hand when it calls `reply()`; nothing before that does.
"""

from pathlib import Path

import uvicorn

from vitsc.web.app import create_app
from vitsc.web.deps import AppSession

DB_PATH = Path.home() / ".vitsc" / "sessions.sqlite3"


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    session = AppSession.build(db_path=DB_PATH)
    app = create_app(session)
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
