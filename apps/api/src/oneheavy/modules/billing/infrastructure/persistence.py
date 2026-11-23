"""Adaptador de salida: persistencia SQLAlchemy de Facturación."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Self

from sqlalchemy import JSON, DateTime, Integer, String, Uuid, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.billing.application.ports import BillingUnitOfWork
from oneheavy.modules.billing.domain.model import (
    Checkout,
    Payment,
    Subscription,
    SubscriptionStatus,
    TransactionStatus,
)
from oneheavy.modules.billing.domain.repositories import (
    CheckoutRepository,
    PaymentRepository,
    SubscriptionRepository,
)
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin


class SubscriptionRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "billing_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    plan: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CheckoutRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "billing_checkouts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20))
    amount_in_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))


class PaymentRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "billing_payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    reference: Mapped[str] = mapped_column(String(80), index=True)
    amount_in_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(12))
    plan: Mapped[str] = mapped_column(String(20))
    customer_email: Mapped[str | None] = mapped_column(String(254))
    payment_method: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SqlSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tenant_id: uuid.UUID) -> Subscription | None:
        row = await self._s.scalar(select(SubscriptionRow).where(SubscriptionRow.tenant_id == tenant_id))
        if row is None:
            return None
        return Subscription(
            id=row.id,
            tenant_id=row.tenant_id,
            plan=row.plan,
            status=SubscriptionStatus(row.status),
            current_period_end=ensure_aware(row.current_period_end) if row.current_period_end else None,
            created_at=ensure_aware(row.created_at),
            updated_at=ensure_aware(row.updated_at),
        )

    async def save(self, subscription: Subscription) -> None:
        s = subscription
        row = await self._s.get(SubscriptionRow, s.id)
        if row is None:
            row = SubscriptionRow(id=s.id, tenant_id=s.tenant_id, created_at=s.created_at)
            self._s.add(row)
        row.plan, row.status, row.current_period_end = s.plan, s.status.value, s.current_period_end
        row.updated_at = s.updated_at


class SqlCheckoutRepository(CheckoutRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, checkout: Checkout) -> None:
        c = checkout
        self._s.add(
            CheckoutRow(
                id=c.id,
                tenant_id=c.tenant_id,
                reference=c.reference,
                plan=c.plan,
                amount_in_cents=c.amount_in_cents,
                currency=c.currency,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    async def get_by_reference(self, reference: str) -> Checkout | None:
        row = await self._s.scalar(select(CheckoutRow).where(CheckoutRow.reference == reference))
        if row is None:
            return None
        return Checkout(
            id=row.id,
            tenant_id=row.tenant_id,
            reference=row.reference,
            plan=row.plan,
            amount_in_cents=row.amount_in_cents,
            currency=row.currency,
            created_at=ensure_aware(row.created_at),
            updated_at=ensure_aware(row.updated_at),
        )


class SqlPaymentRepository(PaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_external_id(self, external_id: str) -> Payment | None:
        row = await self._s.scalar(select(PaymentRow).where(PaymentRow.external_id == external_id))
        if row is None:
            return None
        return Payment(
            id=row.id,
            tenant_id=row.tenant_id,
            external_id=row.external_id,
            reference=row.reference,
            amount_in_cents=row.amount_in_cents,
            currency=row.currency,
            status=TransactionStatus(row.status),
            plan=row.plan,
            customer_email=row.customer_email,
            payment_method=dict(row.payment_method or {}),
            created_at=ensure_aware(row.created_at),
            updated_at=ensure_aware(row.updated_at),
        )

    async def save(self, payment: Payment) -> None:
        p = payment
        row = await self._s.get(PaymentRow, p.id)
        if row is None:
            row = PaymentRow(
                id=p.id, tenant_id=p.tenant_id, external_id=p.external_id, created_at=p.created_at
            )
            self._s.add(row)
        row.reference, row.amount_in_cents, row.currency = p.reference, p.amount_in_cents, p.currency
        row.status, row.plan, row.customer_email = p.status.value, p.plan, p.customer_email
        row.payment_method, row.updated_at = p.payment_method, p.updated_at


class SqlBillingUnitOfWork(SqlAlchemyUnitOfWork, BillingUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.subscriptions = SqlSubscriptionRepository(self.session)
        self.checkouts = SqlCheckoutRepository(self.session)
        self.payments = SqlPaymentRepository(self.session)
        return self
