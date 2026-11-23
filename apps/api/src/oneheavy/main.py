"""Punto de entrada de la API de 1heavy (app factory)."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from oneheavy.modules.analytics import AnalyticsModule
from oneheavy.modules.billing import BillingModule
from oneheavy.modules.crm import CrmModule
from oneheavy.modules.gamification import GamificationModule
from oneheavy.modules.growth import GrowthModule
from oneheavy.modules.identity import IdentityModule
from oneheavy.modules.marketing import MarketingModule
from oneheavy.modules.meta import MetaModule
from oneheavy.modules.stays import StaysModule
from oneheavy.shared.infrastructure.config import Settings, get_settings
from oneheavy.shared.infrastructure.container import Container, Module
from oneheavy.shared.infrastructure.db import create_schema
from oneheavy.shared.infrastructure.http import install_error_handlers
from oneheavy.shared.infrastructure.logging import configure_logging
from oneheavy.shared.infrastructure.scheduler import Scheduler

API_VERSION = "2.0.0"
log = logging.getLogger("oneheavy")


def default_modules() -> list[Module]:
    return [
        IdentityModule(),
        StaysModule(),
        CrmModule(),
        MarketingModule(),
        MetaModule(),
        GrowthModule(),
        GamificationModule(),
        AnalyticsModule(),
        BillingModule(),
    ]


def create_app(
    settings: Settings | None = None,
    container: Container | None = None,
    modules: list[Module] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    container = container or Container.from_settings(settings)
    modules = modules if modules is not None else default_modules()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.db_auto_create:
            await create_schema(container.engine)
        scheduler: Scheduler | None = None
        if settings.scheduler_enabled:
            scheduler = Scheduler(settings.scheduler_timezone)
            for module in modules:
                scheduler.add(module.jobs(container))
            scheduler.start()
        log.info("api_started", extra={"env": settings.env, "modules": [m.name for m in modules]})
        yield
        if scheduler:
            scheduler.shutdown()
        await container.engine.dispose()

    app = FastAPI(
        title="1heavy API",
        version=API_VERSION,
        description="Growth & Operations OS — CRM, Meta Business, Mautic + IA, gamificación, analítica y Stays.",
        lifespan=lifespan,
    )
    app.state.container = container
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    for module in modules:
        module.register(container)
        router = module.router()
        if router is not None:
            app.include_router(router, prefix="/api/v1")

    os.makedirs(settings.storage_dir, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")

    @app.get("/health", tags=["Ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": API_VERSION, "env": settings.env}

    return app


def app_factory() -> FastAPI:  # uvicorn oneheavy.main:app_factory --factory
    return create_app()
