"""Composition Root: construye e inyecta todas las dependencias.

Es el ÚNICO lugar que conoce las implementaciones concretas de los puertos.
Los tests crean un Container con dobles (FakeLLM, ConsoleMessageSender, SQLite).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from oneheavy.shared.application.ports import (
    EventBus,
    FileStorage,
    LLMClient,
    MessageSender,
    UnitOfWork,
    WebSearch,
)
from oneheavy.shared.infrastructure.adapters import LocalFileStorage, NullWebSearch, TavilyWebSearch
from oneheavy.shared.infrastructure.config import Settings
from oneheavy.shared.infrastructure.db import SqlAlchemyUnitOfWork, build_engine, build_session_factory
from oneheavy.shared.infrastructure.event_bus import InMemoryEventBus
from oneheavy.shared.infrastructure.llm import FakeLLMClient, OpenAIChatClient
from oneheavy.shared.infrastructure.messaging import ConsoleMessageSender, EvolutionApiSender
from oneheavy.shared.infrastructure.security import PasswordHasher, TokenService


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    bus: EventBus
    llm: LLMClient
    sender: MessageSender
    search: WebSearch
    storage: FileStorage
    tokens: TokenService
    hasher: PasswordHasher
    # Singletons específicos de cada módulo (p. ej. "marketing.mautic").
    extras: dict[str, Any] = field(default_factory=dict)

    def uow(self) -> UnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory, self.bus)

    @classmethod
    def from_settings(cls, settings: Settings, **overrides: Any) -> Container:
        engine = overrides.pop("engine", None) or build_engine(settings.database_url, echo=settings.db_echo)
        llm: LLMClient
        if settings.llm_provider == "openai" and settings.openai_api_key:
            llm = OpenAIChatClient(settings.openai_api_key.get_secret_value(), settings.openai_model)
        else:
            llm = FakeLLMClient()
        sender: MessageSender
        if settings.messaging_provider == "evolution" and settings.evolution_api_key:
            sender = EvolutionApiSender(
                settings.evolution_api_url, settings.evolution_api_key.get_secret_value()
            )
        else:
            sender = ConsoleMessageSender()
        search: WebSearch = (
            TavilyWebSearch(settings.tavily_api_key.get_secret_value())
            if settings.tavily_api_key
            else NullWebSearch()
        )
        defaults: dict[str, Any] = {
            "settings": settings,
            "engine": engine,
            "session_factory": build_session_factory(engine),
            "bus": InMemoryEventBus(),
            "llm": llm,
            "sender": sender,
            "search": search,
            "storage": LocalFileStorage(settings.storage_dir, max_mb=settings.max_upload_mb),
            "tokens": TokenService(
                settings.jwt_secret.get_secret_value(), settings.jwt_algorithm, settings.jwt_ttl_minutes
            ),
            "hasher": PasswordHasher(),
        }
        defaults.update(overrides)
        return cls(**defaults)


# ── Contrato de módulo (bounded context) ────────────────────────────────────


@dataclass(frozen=True)
class ScheduledJob:
    """Proceso batch del módulo. `func` abre su propia UoW."""

    id: str
    func: Callable[[], Awaitable[None]]
    trigger: Literal["cron", "interval"]
    params: dict[str, Any]


class Module(ABC):
    """Cada bounded context se registra en la app a través de este contrato."""

    name: str

    @abstractmethod
    def router(self) -> APIRouter | None:
        """Router FastAPI del módulo (se monta en /api/v1)."""

    def register(self, container: Container) -> None:  # noqa: B027 - hook opcional
        """Suscribe handlers al bus y registra singletons en `container.extras`."""

    def jobs(self, container: Container) -> list[ScheduledJob]:
        return []
