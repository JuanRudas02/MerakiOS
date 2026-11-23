"""Bounded context: Analítica unificada — proyección de eventos a hechos, KPIs e insights IA."""

from __future__ import annotations

from fastapi import APIRouter

from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.infrastructure.container import Container, Module


class AnalyticsModule(Module):
    name = "analytics"

    def router(self) -> APIRouter:
        from oneheavy.modules.analytics.api.router import router

        return router

    def register(self, container: Container) -> None:
        from oneheavy.modules.analytics.application.use_cases import ProjectEvent
        from oneheavy.modules.analytics.domain.model import EventProjector
        from oneheavy.modules.analytics.infrastructure.persistence import SqlAnalyticsUnitOfWork

        async def on_event(event: DomainEvent) -> None:
            await ProjectEvent(SqlAnalyticsUnitOfWork(container.session_factory, container.bus)).execute(
                event
            )

        for event_type in EventProjector.event_types():
            container.bus.subscribe(event_type, on_event)
