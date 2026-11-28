"""FastAPI application factory. Run with: python -m app"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import get_settings
from .services import Services, build_services
from .worker import Worker

STATIC = Path(__file__).parent / "static"


def create_app(services: Services | None = None, start_worker: bool | None = None) -> FastAPI:
    svc = services or build_services(get_settings())
    run_worker = svc.settings.worker_enabled if start_worker is None else start_worker

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker = Worker(svc) if run_worker else None
        if worker:
            worker.start()
        yield
        if worker:
            worker.stop()

    app = FastAPI(title="Lecture VideoRAG", version="0.1.0", lifespan=lifespan)
    app.state.services = svc
    app.include_router(router)
    app.mount("/media/frames", StaticFiles(directory=svc.settings.frames_dir), name="frames")
    # LMS video files, played in the page; StaticFiles answers Range requests so the player can seek
    app.mount("/media/videos", StaticFiles(directory=svc.settings.uploads_dir), name="videos")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    return app


def main() -> None:
    import argparse

    import uvicorn

    p = argparse.ArgumentParser(description="Lecture VideoRAG server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
