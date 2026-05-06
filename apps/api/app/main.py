from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import get_settings
from app.routers import cases, health, observations, uploads


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TibetanUrineAI API",
        version="0.1.0",
        description="API service for the Tibetan urine observation assistant.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(cases.router, prefix="/api")
    app.include_router(observations.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")

    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    return app


app = create_app()
