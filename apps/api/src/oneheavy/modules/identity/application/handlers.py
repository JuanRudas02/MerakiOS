"""Handlers de eventos de integración consumidos por Identidad.

CU-ID-07  Actualizar el plan del workspace cuando se aprueba un pago (billing → identity)
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from oneheavy.modules.identity.application.ports import IdentityUnitOfWork
from oneheavy.modules.identity.domain.model import Plan
from oneheavy.shared.domain import integration_events as ie

log = logging.getLogger("oneheavy.identity")


class ApplyPaidPlan:
    def __init__(self, uow_factory: Callable[[], IdentityUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def __call__(self, event: ie.PaymentApproved) -> None:
        if not event.plan:
            return
        try:
            plan = Plan(event.plan)
        except ValueError:
            log.warning("unknown_plan_in_payment", extra={"plan": event.plan})
            return
        async with self._uow_factory() as uow:
            workspace = await uow.workspaces.get(event.tenant_id)
            if workspace is None or workspace.plan is plan:
                return
            workspace.change_plan(plan)
            await uow.workspaces.update(workspace)
            await uow.commit()
