"""Puertos de aplicación de Facturación."""

from __future__ import annotations

from abc import ABC

from oneheavy.modules.billing.domain.repositories import (
    CheckoutRepository,
    PaymentRepository,
    SubscriptionRepository,
)
from oneheavy.shared.application.ports import UnitOfWork


class BillingUnitOfWork(UnitOfWork, ABC):
    subscriptions: SubscriptionRepository
    checkouts: CheckoutRepository
    payments: PaymentRepository
