"""Bloques de construcción DDD: Entity y AggregateRoot.

Las entidades del dominio son objetos Python puros (sin SQLAlchemy ni FastAPI).
Los repositorios (adaptadores de salida) se encargan de mapearlas a persistencia.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.domain.time import utc_now


def new_id() -> uuid.UUID:
    return uuid.uuid4()


@dataclass(kw_only=True, eq=False)
class Entity:
    """Entidad con identidad. Dos entidades son iguales si comparten `id`."""

    id: uuid.UUID = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(kw_only=True, eq=False)
class AggregateRoot(Entity):
    """Raíz de agregado: frontera de consistencia que registra eventos de dominio.

    Los casos de uso extraen los eventos con `pull_events()` y los entregan a la
    Unit of Work, que los publica en el bus *después* de confirmar la transacción.
    """

    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events


@dataclass(kw_only=True, eq=False)
class TenantEntity(AggregateRoot):
    """Agregado que pertenece a un workspace (multi-tenant)."""

    tenant_id: uuid.UUID
