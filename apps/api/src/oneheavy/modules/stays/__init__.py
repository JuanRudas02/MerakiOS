"""Bounded context: Operación de alquileres de corta estadía (ex 1heavy Stays).

Propiedades, personal, limpiezas con evidencia, cortes de servicios, iCal y WhatsApp.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.infrastructure.container import Container, Module, ScheduledJob

if TYPE_CHECKING:
    from oneheavy.modules.stays.application.processes import StaysJobs

JOBS_KEY = "stays.jobs"


class StaysModule(Module):
    name = "stays"

    def router(self) -> APIRouter:
        from oneheavy.modules.stays.api.router import router

        return router

    @staticmethod
    def build_jobs(container: Container) -> StaysJobs:
        from oneheavy.modules.stays.api.router import build_notifier
        from oneheavy.modules.stays.application.processes import StaysJobs
        from oneheavy.modules.stays.infrastructure.persistence import SqlStaysUnitOfWork

        return StaysJobs(
            lambda: SqlStaysUnitOfWork(container.session_factory, container.bus),
            build_notifier(container),
            ZoneInfo(container.settings.scheduler_timezone),
        )

    def register(self, container: Container) -> None:
        from oneheavy.modules.stays.api.router import CALENDAR_KEY
        from oneheavy.modules.stays.application.processes import SyncDirectoryFromIdentity
        from oneheavy.modules.stays.infrastructure.ical import HttpReservationCalendar
        from oneheavy.modules.stays.infrastructure.persistence import SqlStaysUnitOfWork

        container.extras.setdefault(CALENDAR_KEY, HttpReservationCalendar())
        container.extras[JOBS_KEY] = self.build_jobs(container)
        container.bus.subscribe(
            ie.UserRegistered,
            SyncDirectoryFromIdentity(lambda: SqlStaysUnitOfWork(container.session_factory, container.bus)),
        )

    def jobs(self, container: Container) -> list[ScheduledJob]:
        jobs: StaysJobs = container.extras.get(JOBS_KEY) or self.build_jobs(container)

        async def daily() -> None:
            await jobs.send_daily_reminders()

        async def billing() -> None:
            await jobs.check_billing_cutoffs()

        async def arrivals() -> None:
            await jobs.check_arrivals()

        return [
            # Corre cada hora: cada workspace define su hora local de recordatorio (def. 19:00).
            ScheduledJob("stays.daily_reminders", daily, "cron", {"minute": 0}),
            ScheduledJob("stays.billing_cutoffs", billing, "cron", {"hour": 9, "minute": 0}),
            ScheduledJob("stays.arrival_check", arrivals, "interval", {"minutes": 5}),
        ]
