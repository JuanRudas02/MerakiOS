"""Puertos de aplicación del contexto Stays."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from oneheavy.modules.stays.domain.repositories import (
    OwnerAccountRepository,
    PropertyRepository,
    ReceiptRepository,
    SettingsRepository,
    StaffRepository,
    TaskRepository,
)
from oneheavy.shared.application.ports import UnitOfWork


class StaysUnitOfWork(UnitOfWork, ABC):
    properties: PropertyRepository
    staff: StaffRepository
    tasks: TaskRepository
    receipts: ReceiptRepository
    settings: SettingsRepository
    owners: OwnerAccountRepository


@dataclass(frozen=True)
class CalendarEvent:
    """Reserva leída de un calendario iCal (Airbnb, Booking, VRBO)."""

    uid: str
    checkout: datetime | date  # `date` cuando el feed sólo trae el día
    summary: str | None = None


class ReservationCalendar(ABC):
    """Lee reservas desde un feed iCal externo."""

    @abstractmethod
    async def fetch(self, url: str) -> list[CalendarEvent]: ...


@dataclass(frozen=True)
class UploadedFile:
    data: bytes
    filename: str
    content_type: str
