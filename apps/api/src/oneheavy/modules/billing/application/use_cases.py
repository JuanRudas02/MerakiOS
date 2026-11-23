"""Casos de uso de Facturación.

CU-BI-01  Consultar catálogo de planes (público)
CU-BI-02  Consultar suscripción del workspace
CU-BI-03  Iniciar checkout Wompi (referencia + firma de integridad)
CU-BI-04  Procesar webhook de Wompi (firma verificada, idempotente) → activa plan
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from oneheavy.modules.billing.application.ports import BillingUnitOfWork
from oneheavy.modules.billing.domain.model import (
    CURRENCY,
    PLANS,
    Checkout,
    Payment,
    PlanDefinition,
    Subscription,
    TransactionStatus,
    get_plan,
    make_reference,
)
from oneheavy.modules.billing.domain.signatures import integrity_signature, verify_event
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import AuthenticationError, BusinessRuleViolation
from oneheavy.shared.domain.time import utc_now

log = logging.getLogger("oneheavy.billing")


class ListPlans(UseCase[None, list[PlanDefinition]]):
    async def execute(self, data: None = None) -> list[PlanDefinition]:
        return list(PLANS.values())


class GetSubscription(UseCase[Principal, Subscription]):
    def __init__(self, uow: BillingUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> Subscription:
        data.require(Permission.BILLING_MANAGE)
        async with self.uow:
            sub = await self.uow.subscriptions.get(data.tenant_id)
        return sub or Subscription.trial(data.tenant_id)


# ── CU-BI-03 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WompiConfig:
    public_key: str | None
    integrity_secret: str | None
    events_secret: str | None
    redirect_url: str
    allow_unsigned_events: bool  # sólo local/test


@dataclass(frozen=True)
class CheckoutCommand:
    actor: Principal
    plan: str


@dataclass(frozen=True)
class CheckoutSession:
    reference: str
    amount_in_cents: int
    currency: str
    public_key: str
    signature: str
    redirect_url: str


class StartCheckout(UseCase[CheckoutCommand, CheckoutSession]):
    def __init__(self, uow: BillingUnitOfWork, config: WompiConfig) -> None:
        self.uow, self.config = uow, config

    async def execute(self, data: CheckoutCommand) -> CheckoutSession:
        data.actor.require(Permission.BILLING_MANAGE)
        plan = get_plan(data.plan)
        if not self.config.public_key or not self.config.integrity_secret:
            raise BusinessRuleViolation(
                "Los pagos no están configurados (llaves Wompi)", code="payments_disabled"
            )
        checkout = Checkout(
            tenant_id=data.actor.tenant_id,
            reference=make_reference(data.actor.tenant_id, plan.key, utc_now()),
            plan=plan.key,
            amount_in_cents=plan.amount_in_cents,
            currency=CURRENCY,
        )
        async with self.uow:
            await self.uow.checkouts.add(checkout)
            await self.uow.commit()
        return CheckoutSession(
            reference=checkout.reference,
            amount_in_cents=checkout.amount_in_cents,
            currency=checkout.currency,
            public_key=self.config.public_key,
            signature=integrity_signature(
                checkout.reference, checkout.amount_in_cents, checkout.currency, self.config.integrity_secret
            ),
            redirect_url=self.config.redirect_url,
        )


# ── CU-BI-04 ────────────────────────────────────────────────────────────────


class WebhookOutcome(StrEnum):
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"


@dataclass(frozen=True)
class WompiEventCommand:
    payload: dict[str, Any]
    header_checksum: str | None = None


class ProcessWompiEvent(UseCase[WompiEventCommand, WebhookOutcome]):
    def __init__(self, uow: BillingUnitOfWork, config: WompiConfig) -> None:
        self.uow, self.config = uow, config

    def _authenticate(self, cmd: WompiEventCommand) -> None:
        secret = self.config.events_secret
        if not secret:
            if self.config.allow_unsigned_events:
                log.warning("wompi_event_unsigned_accepted")
                return
            raise AuthenticationError("Webhook de Wompi sin secreto configurado", code="webhook_unverified")
        if not verify_event(cmd.payload, secret, cmd.header_checksum):
            raise AuthenticationError("Firma de Wompi inválida", code="invalid_signature")

    async def execute(self, data: WompiEventCommand) -> WebhookOutcome:
        self._authenticate(data)
        if data.payload.get("event") != "transaction.updated":
            return WebhookOutcome.IGNORED
        tx = (data.payload.get("data") or {}).get("transaction") or {}
        external_id, reference = str(tx.get("id") or ""), str(tx.get("reference") or "")
        try:
            status = TransactionStatus(str(tx.get("status")))
        except ValueError:
            return WebhookOutcome.IGNORED
        if not external_id or not reference:
            return WebhookOutcome.IGNORED

        async with self.uow:
            checkout = await self.uow.checkouts.get_by_reference(reference)
            if checkout is None:
                log.warning("wompi_unknown_reference", extra={"reference": reference})
                return WebhookOutcome.IGNORED
            if int(tx.get("amount_in_cents") or 0) != checkout.amount_in_cents:
                log.warning("wompi_amount_mismatch", extra={"reference": reference})
                return WebhookOutcome.IGNORED

            payment = await self.uow.payments.get_by_external_id(external_id)
            if payment is None:
                payment = Payment.from_transaction(checkout, external_id, tx)
                payment.transition(status)  # nuevo: se persiste aunque siga PENDING
            elif payment.status is TransactionStatus.APPROVED or not payment.transition(status):
                return WebhookOutcome.DUPLICATE  # reintento de Wompi: idempotente
            await self.uow.payments.save(payment)

            if status is TransactionStatus.APPROVED:
                sub = await self.uow.subscriptions.get(checkout.tenant_id) or Subscription.trial(
                    checkout.tenant_id
                )
                sub.activate(checkout.plan, utc_now())
                await self.uow.subscriptions.save(sub)
            self.uow.collect(payment.pull_events())
            await self.uow.commit()
        return WebhookOutcome.PROCESSED
