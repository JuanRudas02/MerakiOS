"""Bounded context: Gamificación — puntos, niveles, insignias, retos y leaderboards.

Se alimenta exclusivamente de eventos de integración (no importa otros dominios).
"""

from __future__ import annotations

from fastapi import APIRouter

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.infrastructure.container import Container, Module


class GamificationModule(Module):
    name = "gamification"

    def router(self) -> APIRouter:
        from oneheavy.modules.gamification.api.router import router

        return router

    def register(self, container: Container) -> None:
        from oneheavy.modules.gamification.application.use_cases import AwardPointsForEvent, EnrollPlayer
        from oneheavy.modules.gamification.domain.rules import RuleEngine
        from oneheavy.modules.gamification.infrastructure.persistence import SqlGamificationUnitOfWork

        engine: RuleEngine = container.extras.setdefault("gamification.engine", RuleEngine())

        def uow() -> SqlGamificationUnitOfWork:
            return SqlGamificationUnitOfWork(container.session_factory, container.bus)

        async def on_user_registered(event: ie.UserRegistered) -> None:
            await EnrollPlayer(uow()).execute(event)

        async def on_scorable_event(event: DomainEvent) -> None:
            await AwardPointsForEvent(uow(), engine).execute(event)

        container.bus.subscribe(ie.UserRegistered, on_user_registered)
        for event_type in engine.event_types():
            container.bus.subscribe(event_type, on_scorable_event)
