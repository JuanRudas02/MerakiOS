"""Puertos de persistencia de Facturación."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from oneheavy.modules.billing.domain.model import Checkout, Payment, Subscription


class SubscriptionRepository(ABC):
    @abstractmethod
    async def get(self, tenant_id: uuid.UUID) -> Subscription | None: ...

    @abstractmethod
    async def save(self, subscription: Subscription) -> None: ...


class CheckoutRepository(ABC):
    @abstractmethod
    async def add(self, checkout: Checkout) -> None: ...

    @abstractmethod
    async def get_by_reference(self, reference: str) -> Checkout | None: ...


class PaymentRepository(ABC):
    @abstractmethod
    async def get_by_external_id(self, external_id: str) -> Payment | None: ...

    @abstractmethod
    async def save(self, payment: Payment) -> None: ...
