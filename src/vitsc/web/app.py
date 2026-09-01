from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from vitsc.web.deps import AppSession

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=HERE / "templates")


def create_app(session: AppSession) -> FastAPI:
    app = FastAPI(title="Virtual IT Support Center")
    app.state.session = session
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    from vitsc.web.routes import chat as chat_routes
    from vitsc.web.routes import close as close_routes
    from vitsc.web.routes import escalate as escalate_routes
    from vitsc.web.routes import events as event_routes
    from vitsc.web.routes import kb as kb_routes
    from vitsc.web.routes import queue as queue_routes
    from vitsc.web.routes import tools as tool_routes
    app.include_router(queue_routes.router)
    app.include_router(tool_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(close_routes.router)
    app.include_router(escalate_routes.router)
    app.include_router(event_routes.router)
    app.include_router(kb_routes.router)
    return app
