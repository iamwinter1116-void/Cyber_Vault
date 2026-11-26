"""FastAPI application entrypoint for ABHEDYA control-plane API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from core.abh_core.db import create_pool
from core.abh_core.settings import Settings
from fastapi import FastAPI

from services.api.middleware import install_middleware_and_handlers
from services.api.routes import auth, health


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    cfg = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = cfg
        app.state.db_pool = create_pool(cfg.db_dsn) if cfg.db_dsn else None
        try:
            yield
        finally:
            if app.state.db_pool is not None:
                app.state.db_pool.close()

    app = FastAPI(title="ABHEDYA API", version="1.0.0", lifespan=lifespan)
    app.state.settings = cfg
    app.state.db_pool = None
    install_middleware_and_handlers(app)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    return app


app = create_app()
