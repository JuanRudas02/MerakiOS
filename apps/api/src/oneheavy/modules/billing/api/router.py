"""Adaptador REST de Facturación (/api/v1/billing)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from oneheavy.modules.billing.application.use_cases import (
    CheckoutCommand,
    GetSubscription,
    ListPlans,
    ProcessWompiEvent,
    StartCheckout,
    WompiConfig,
    WompiEventCommand,
)
from oneheavy.modules.billing.infrastructure.persistence import SqlBillingUnitOfWork
from oneheavy.shared.domain.access import Principal
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, get_principal

router = APIRouter(prefix="/billing", tags=["Billing"])


def _uow(container: Container = Depends(get_container)) -> SqlBillingUnitOfWork:
    return SqlBillingUnitOfWork(container.session_factory, container.bus)


def _config(container: Container = Depends(get_container)) -> WompiConfig:
    s = container.settings
    return WompiConfig(
        public_key=s.wompi_public_key,
        integrity_secret=s.wompi_integrity_secret.get_secret_value() if s.wompi_integrity_secret else None,
        events_secret=s.wompi_events_secret.get_secret_value() if s.wompi_events_secret else None,
        redirect_url=f"{s.public_app_url.rstrip('/')}/app/ajustes/facturacion",
        allow_unsigned_events=s.env in ("local", "test"),
    )


class PlanLimitsOut(BaseModel):
    properties: int
    contacts: int
    seats: int


class PlanOut(BaseModel):
    key: str
    name: str
    price_cop: int
    period: str
    features: list[str]
    limits: PlanLimitsOut


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    current_period_end: datetime | None


class CheckoutIn(BaseModel):
    plan: str


class CheckoutOut(BaseModel):
    reference: str
    amount_in_cents: int
    currency: str
    public_key: str
    signature: str
    redirect_url: str


@router.get("/plans", response_model=list[PlanOut])
async def plans() -> list[PlanOut]:
    return [
        PlanOut(
            key=p.key,
            name=p.name,
            price_cop=p.price_cop,
            period=p.period,
            features=list(p.features),
            limits=PlanLimitsOut(
                properties=p.limits.properties, contacts=p.limits.contacts, seats=p.limits.seats
            ),
        )
        for p in await ListPlans().execute()
    ]


@router.get("/subscription", response_model=SubscriptionOut)
async def subscription(
    principal: Principal = Depends(get_principal), uow: SqlBillingUnitOfWork = Depends(_uow)
) -> SubscriptionOut:
    sub = await GetSubscription(uow).execute(principal)
    return SubscriptionOut(plan=sub.plan, status=sub.status.value, current_period_end=sub.current_period_end)


@router.post("/checkout", response_model=CheckoutOut)
async def checkout(
    body: CheckoutIn,
    principal: Principal = Depends(get_principal),
    uow: SqlBillingUnitOfWork = Depends(_uow),
    config: WompiConfig = Depends(_config),
) -> CheckoutOut:
    s = await StartCheckout(uow, config).execute(CheckoutCommand(principal, body.plan))
    return CheckoutOut(
        reference=s.reference,
        amount_in_cents=s.amount_in_cents,
        currency=s.currency,
        public_key=s.public_key,
        signature=s.signature,
        redirect_url=s.redirect_url,
    )


@router.post("/webhooks/wompi")
async def wompi_webhook(
    request: Request,
    x_event_checksum: str | None = Header(default=None),
    uow: SqlBillingUnitOfWork = Depends(_uow),
    config: WompiConfig = Depends(_config),
) -> dict[str, Any]:
    try:
        payload = json.loads(await request.body())
    except json.JSONDecodeError as exc:
        raise BusinessRuleViolation("Payload inválido", code="invalid_payload") from exc
    if not isinstance(payload, dict):
        raise BusinessRuleViolation("Payload inválido", code="invalid_payload")
    outcome = await ProcessWompiEvent(uow, config).execute(WompiEventCommand(payload, x_event_checksum))
    return {"ok": True, "outcome": outcome.value}
