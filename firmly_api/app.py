"""Application composition, startup, and static interface hosting.
Changes: application factory and lifecycle-managed services.
"""

import logging
import os
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from firmly_engine.models import DEFAULT_RESEARCH_MODEL

from .catalog import ModelCatalog
from .config import ROOT
from .middleware import RequestLimits
from .research import router
from .service import JobService

logger = logging.getLogger("firmly.api")


def create_app(service: JobService | None = None) -> FastAPI:
    service = service or JobService()
    catalog = ModelCatalog()

    @asynccontextmanager
    async def lifespan(_app):
        async with AsyncExitStack() as cleanup:
            cleanup.push_async_callback(catalog.close)
            cleanup.push_async_callback(service.close)
            service.open()
            await catalog.open()
            yield

    app = FastAPI(title="Firmly", lifespan=lifespan)
    api = FastAPI(title="Firmly Research API")
    api.state.service = service
    api.state.catalog = catalog
    api.state.rate = {}
    app.state.api = api
    app.state.service = service
    api.add_middleware(RequestLimits, limits=service.limits, buckets=api.state.rate)

    @api.exception_handler(RequestValidationError)
    async def invalid_request(_request, _exc):
        return JSONResponse(
            status_code=422,
            content={"detail": "Check the company details and settings, then try again."},
        )

    @api.exception_handler(Exception)
    async def safe_error(_request, exc):
        logger.error("Request failed (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={"detail": "The request could not be completed. Please try again."},
        )

    @api.get("/config")
    async def config():
        return {
            "search_ready": bool(os.getenv("FIRMLY_SEARCH_KEY")),
            "model_gateway_ready": bool(os.getenv("FIRMLY_MODEL_KEY")),
            "direct_model_ready": bool(os.getenv("FIRMLY_DIRECT_MODEL_KEY")),
            "default_model": os.getenv("FIRMLY_MODEL") or DEFAULT_RESEARCH_MODEL,
            "storage_ready": service.storage is not None,
        }

    @api.get("/models")
    async def models():
        return await catalog.get()

    api.include_router(router)
    app.mount("/api", api)
    origins = [
        value.strip()
        for value in os.getenv(
            "FIRMLY_ALLOWED_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174"
        ).split(",")
        if value.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    dist = ROOT / "ui" / "dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}")
    async def frontend(path: str):
        candidate = (dist / path).resolve()
        if candidate.is_relative_to(dist.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        if (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
        return JSONResponse({"message": "Firmly API is running. Start the frontend on port 5174."})

    return app
