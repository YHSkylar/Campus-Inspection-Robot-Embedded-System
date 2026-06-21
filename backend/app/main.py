from __future__ import annotations

from contextlib import asynccontextmanager
import sys
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.db import init_db
from app.routes import api_router


APP_DESCRIPTION = (
    "Backend API for the campus inspection robot, covering the core business "
    "flows from FU-001 to FU-007."
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    settings.snapshot_path.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.current_version,
        description=APP_DESCRIPTION,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    register_snapshot_files(app)
    register_frontend(app)

    return app


def register_snapshot_files(app: FastAPI) -> None:
    settings.snapshot_path.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/snapshots",
        StaticFiles(directory=settings.snapshot_path),
        name="snapshots",
    )


def register_frontend(app: FastAPI) -> None:
    index_file = FRONTEND_DIST / "index.html"
    assets_dir = FRONTEND_DIST / "assets"
    if not index_file.exists():
        return

    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="frontend-assets",
        )

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str = "") -> FileResponse:
        if full_path == settings.api_prefix.strip("/") or full_path.startswith(
            f"{settings.api_prefix.strip('/')}/"
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        requested_file = FRONTEND_DIST / full_path
        if requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(index_file)


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
