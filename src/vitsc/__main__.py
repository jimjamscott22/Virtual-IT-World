"""`uv run python -m vitsc` — the normal way to start the drill.

Uses `TemplatePersona`, not `LMStudioPersona`: the model-backed persona takes
a fixed `leak_terms` list at construction (Task 11), but a session runs
tickets against many faults in turn, each with its own leak terms. Wiring a
fault-aware model persona needs the chat route (Task 17), which has the open
ticket's `fault_id` in hand when it calls `reply()`; nothing before that does.
"""

import argparse
import os
from pathlib import Path

import uvicorn

from vitsc.web.app import create_app
from vitsc.web.deps import AppSession

DB_PATH = Path.home() / ".vitsc" / "sessions.sqlite3"


def resolve_db_path(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(prog="python -m vitsc")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="SQLite database path (overrides VITSC_DB; defaults to ~/.vitsc/sessions.sqlite3).",
    )
    args = parser.parse_args(argv)
    if args.db is not None:
        return args.db.expanduser()
    env_db = os.environ.get("VITSC_DB", "").strip()
    if env_db:
        return Path(env_db).expanduser()
    return DB_PATH


def main(argv: list[str] | None = None) -> None:
    db_path = resolve_db_path(argv)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    session = AppSession.build(db_path=db_path)
    app = create_app(session)
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
