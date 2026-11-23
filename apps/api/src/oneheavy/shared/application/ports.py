"""Puertos (interfaces) transversales de la capa de aplicación.

Los casos de uso dependen de estas abstracciones; las implementaciones
concretas viven en `shared/infrastructure` y se inyectan desde el Container.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Self, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from oneheavy.shared.domain.events import DomainEvent

E = TypeVar("E", bound=DomainEvent)
EventHandler = Callable[[E], Awaitable[None]]


# ── Eventos ─────────────────────────────────────────────────────────────────


class EventBus(ABC):
    """Bus de eventos en proceso (patrón Observer / Pub-Sub)."""

    @abstractmethod
    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None: ...

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...

    async def publish_all(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)


# ── Unidad de trabajo ───────────────────────────────────────────────────────


class UnitOfWork(ABC):
    """Frontera transaccional de un caso de uso.

    Uso:
        async with uow:
            repo = SqlPropertyRepository(uow.session)
            ...
            uow.collect(aggregate.pull_events())
            await uow.commit()   # confirma y LUEGO publica eventos
    """

    session: AsyncSession

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(self, *exc: object) -> None: ...

    @abstractmethod
    def collect(self, events: Sequence[DomainEvent]) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...


# ── Mensajería (WhatsApp / SMS / Push) ──────────────────────────────────────


@dataclass(frozen=True)
class InteractiveButton:
    id: str
    label: str


class MessageSender(ABC):
    """Canal saliente. Cada workspace usa su propia instancia de WhatsApp (QR)."""

    @abstractmethod
    async def send_whatsapp(self, to: str, message: str, *, instance: str | None = None) -> None: ...

    @abstractmethod
    async def send_buttons(
        self,
        to: str,
        title: str,
        description: str,
        buttons: Sequence[InteractiveButton],
        *,
        footer: str = "1heavy",
        instance: str | None = None,
    ) -> None: ...


# ── IA generativa ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    system: str = "Eres el copiloto de 1heavy. Responde en español, claro y accionable."
    temperature: float = 0.2
    max_tokens: int = 1500
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMClient(ABC):
    """Proveedor de lenguaje (OpenAI, Anthropic, local...)."""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> str: ...

    async def complete_json(self, request: LLMRequest) -> dict[str, Any] | list[Any]:
        """Pide JSON estricto y lo parsea de forma tolerante (```json ... ```)."""
        import json

        system = request.system + "\nDevuelve EXCLUSIVAMENTE JSON válido, sin texto adicional."
        raw = await self.complete(
            LLMRequest(request.prompt, system, request.temperature, request.max_tokens, request.metadata)
        )
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned[4:] if cleaned.lower().startswith("json") else cleaned
        parsed: dict[str, Any] | list[Any] = json.loads(cleaned)
        return parsed


class WebSearch(ABC):
    """Investigación de mercado (Tavily u otro)."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 3) -> list[dict[str, Any]]: ...


# ── Almacenamiento de archivos (fotos, comprobantes) ────────────────────────


class FileStorage(ABC):
    @abstractmethod
    async def save(self, data: bytes, *, folder: str, filename: str, content_type: str) -> str:
        """Guarda el archivo y devuelve su URL pública/relativa."""
