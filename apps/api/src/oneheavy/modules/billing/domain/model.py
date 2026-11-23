"""Dominio de Facturación: planes, suscripción, checkout y pagos (Wompi)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.entity import TenantEntity
from oneheavy.shared.domain.errors import BusinessRuleViolation, NotFoundError

BILLING_PERIOD = timedelta(days=30)
CURRENCY = "COP"


@dataclass(frozen=True)
class PlanLimits:
    properties: int
    contacts: int
    seats: int


@dataclass(frozen=True)
class PlanDefinition:
    key: str
    name: str
    price_cop: int
    features: tuple[str, ...]
    limits: PlanLimits
    period: str = "month"

    @property
    def amount_in_cents(self) -> int:
        return self.price_cop * 100


PLANS: dict[str, PlanDefinition] = {
    p.key: p
    for p in (
        PlanDefinition(
            "starter",
            "Starter",
            89_000,
            (
                "Operación Stays hasta 10 propiedades",
                "CRM con 1.000 contactos",
                "WhatsApp con tu propio número",
                "Gamificación del equipo",
            ),
            PlanLimits(properties=10, contacts=1_000, seats=3),
        ),
        PlanDefinition(
            "growth",
            "Growth",
            249_000,
            (
                "Todo Starter",
                "Mautic + IA: segmentos, emails y campañas",
                "Meta Business: Ads, Lead Ads y alertas",
                "Motor de estrategia IA (auditoría y embudos)",
                "Analítica unificada con insights IA",
            ),
            PlanLimits(properties=50, contacts=10_000, seats=10),
        ),
        PlanDefinition(
            "scale",
            "Scale",
            590_000,
            (
                "Todo Growth",
                "Propiedades y contactos ilimitados",
                "Marca blanca completa",
                "Soporte prioritario y onboarding dedicado",
            ),
            PlanLimits(properties=100_000, contacts=1_000_000, seats=50),
        ),
    )
}


def get_plan(key: str) -> PlanDefinition:
    plan = PLANS.get(key)
    if plan is None:
        raise NotFoundError(f"El plan '{key}' no existe", code="plan_not_found")
    return plan


def make_reference(tenant_id: uuid.UUID, plan: str, now: datetime) -> str:
    """`1H-<tenant corto>-<plan>-<timestamp ms>` (única por intento de pago)."""
    return f"1H-{tenant_id.hex[:8].upper()}-{plan.upper()}-{int(now.timestamp() * 1000)}"


# ── Suscripción ─────────────────────────────────────────────────────────────


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


@dataclass(kw_only=True, eq=False)
class Subscription(TenantEntity):
    plan: str = "trial"
    status: SubscriptionStatus = SubscriptionStatus.TRIALING
    current_period_end: datetime | None = None

    @classmethod
    def trial(cls, tenant_id: uuid.UUID) -> Subscription:
        return cls(tenant_id=tenant_id)

    def activate(self, plan: str, now: datetime) -> None:
        get_plan(plan)
        start = (
            self.current_period_end
            if self.current_period_end and self.current_period_end > now and self.plan == plan
            else now
        )
        self.plan = plan
        self.status = SubscriptionStatus.ACTIVE
        self.current_period_end = start + BILLING_PERIOD
        self.touch()

    def mark_past_due(self) -> None:
        if self.status is not SubscriptionStatus.ACTIVE:
            raise BusinessRuleViolation("Sólo una suscripción activa puede quedar en mora")
        self.status = SubscriptionStatus.PAST_DUE
        self.touch()

    def cancel(self) -> None:
        self.status = SubscriptionStatus.CANCELED
        self.touch()


# ── Checkout y pagos ────────────────────────────────────────────────────────


@dataclass(kw_only=True, eq=False)
class Checkout(TenantEntity):
    reference: str
    plan: str
    amount_in_cents: int
    currency: str = CURRENCY


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    VOIDED = "VOIDED"
    ERROR = "ERROR"


@dataclass(kw_only=True, eq=False)
class Payment(TenantEntity):
    external_id: str
    reference: str
    amount_in_cents: int
    currency: str
    status: TransactionStatus
    plan: str
    customer_email: str | None = None
    payment_method: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_transaction(cls, checkout: Checkout, external_id: str, data: dict[str, Any]) -> Payment:
        return cls(
            tenant_id=checkout.tenant_id,
            external_id=external_id,
            reference=checkout.reference,
            amount_in_cents=int(data.get("amount_in_cents") or 0),
            currency=str(data.get("currency") or CURRENCY),
            status=TransactionStatus.PENDING,
            plan=checkout.plan,
            customer_email=data.get("customer_email"),
            payment_method={"type": data.get("payment_method_type")},
        )

    def transition(self, status: TransactionStatus) -> bool:
        """Aplica el nuevo estado; True si cambió. Al aprobarse emite PaymentApproved."""
        if status == self.status:
            return False
        if self.status is TransactionStatus.APPROVED:
            raise BusinessRuleViolation("Un pago aprobado no puede cambiar de estado", code="payment_final")
        self.status = status
        self.touch()
        if status is TransactionStatus.APPROVED:
            self.record(
                ie.PaymentApproved(
                    tenant_id=self.tenant_id,
                    payment_id=self.id,
                    reference=self.reference,
                    amount_in_cents=self.amount_in_cents,
                    currency=self.currency,
                    plan=self.plan,
                )
            )
        return True
