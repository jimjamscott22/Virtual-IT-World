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

    from vitsc.web.routes import queue as queue_routes
    app.include_router(queue_routes.router)
    return app
