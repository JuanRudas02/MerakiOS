"""Planificador de procesos batch (APScheduler).

Corrige el bug de Stays donde `datetime.now()` se evaluaba UNA vez al arrancar
el servidor: aquí cada job calcula la fecha en tiempo de ejecución.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from oneheavy.shared.infrastructure.container import ScheduledJob

log = logging.getLogger("oneheavy.scheduler")


class Scheduler:
    def __init__(self, timezone: str) -> None:
        self._scheduler = AsyncIOScheduler(timezone=timezone)

    def add(self, jobs: Iterable[ScheduledJob]) -> None:
        for job in jobs:
            self._scheduler.add_job(
                job.func, job.trigger, id=job.id, replace_existing=True, coalesce=True, **job.params
            )
            log.info("job_registered", extra={"job": job.id, "trigger": job.trigger})

    def start(self) -> None:
        self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
