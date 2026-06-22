"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from planguide.application.services import build_services
from planguide.infrastructure.db import SessionFactory, create_tables
from planguide.infrastructure.storage import PlanRepository
from planguide.interface.routes import create_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    services = build_services(PlanRepository(SessionFactory))
    await services["templates"].ensure_system_templates()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PlanManager", version="1.0.0", lifespan=lifespan)
    services = build_services(PlanRepository(SessionFactory))
    app.include_router(create_router(services))
    _mount_static(app)
    return app


def _mount_static(app: FastAPI):
    static_dir = Path(__file__).resolve().parents[1] / "static"
    app.mount("/plan/assets", StaticFiles(directory=static_dir), name="plan-assets")

    @app.get("/")
    async def root():
        return RedirectResponse("/plan")

    @app.get("/plan")
    async def plan_root():
        return FileResponse(static_dir / "index.html")

    @app.get("/plan/")
    async def plan_slash():
        return FileResponse(static_dir / "index.html")


app = create_app()
