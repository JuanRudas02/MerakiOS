"""Persistencia: SQLAlchemy 2.0 async + Unit of Work."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Self

from sqlalchemy import DateTime, MetaData, Uuid
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from oneheavy.shared.application.ports import EventBus, UnitOfWork
from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.domain.time import utc_now

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TenantMixin:
    """Toda tabla de negocio está particionada lógicamente por workspace."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)


def build_engine(url: str, *, echo: bool = False, pool_size: int = 5, max_overflow: int = 5) -> AsyncEngine:
    if url.startswith("sqlite"):
        # SQLite en memoria para tests: una sola conexión compartida
        return create_async_engine(
            url, echo=echo, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    return create_async_engine(
        url, echo=echo, pool_pre_ping=True, pool_size=pool_size, max_overflow=max_overflow, pool_recycle=1800
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> None:
        self._session_factory = session_factory
        self._bus = bus
        self._events: list[DomainEvent] = []
        self._committed = False

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        self._events = []
        self._committed = False
        return self

    async def __aexit__(self, *exc: object) -> None:
        if not self._committed:
            await self.session.rollback()
        await self.session.close()

    def collect(self, events: Sequence[DomainEvent]) -> None:
        self._events.extend(events)

    async def commit(self) -> None:
        await self.session.commit()
        self._committed = True
        events, self._events = self._events, []
        # Los eventos se publican sólo si la transacción se confirmó.
        await self._bus.publish_all(events)

    async def rollback(self) -> None:
        await self.session.rollback()
        self._events = []
