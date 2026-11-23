"""Value Objects compartidos: inmutables y auto-validados."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from oneheavy.shared.domain.errors import BusinessRuleViolation

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_CLEAN_RE = re.compile(r"[\s\-().]")


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise BusinessRuleViolation(f"Email inválido: {self.value!r}", code="invalid_email")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PhoneNumber:
    """Teléfono en formato E.164 (+573001234567).

    `default_country_code` se usa cuando el número llega sin prefijo (caso común
    en operadores colombianos que escriben 300 123 4567).
    """

    value: str

    def __post_init__(self) -> None:
        raw = _PHONE_CLEAN_RE.sub("", self.value.strip())
        if raw.startswith("00"):
            raw = "+" + raw[2:]
        if not raw.startswith("+"):
            raw = "+57" + raw if len(raw) == 10 else "+" + raw
        digits = raw[1:]
        if not digits.isdigit() or not 8 <= len(digits) <= 15:
            raise BusinessRuleViolation(f"Teléfono inválido: {self.value!r}", code="invalid_phone")
        object.__setattr__(self, "value", raw)

    @property
    def digits(self) -> str:
        """Formato que espera WhatsApp/Evolution API (sin '+')."""
        return self.value[1:]

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "COP"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        object.__setattr__(self, "amount", self.amount.quantize(Decimal("0.01"), ROUND_HALF_UP))
        object.__setattr__(self, "currency", self.currency.upper())

    @property
    def cents(self) -> int:
        return int(self.amount * 100)

    def __add__(self, other: Money) -> Money:
        if other.currency != self.currency:
            raise BusinessRuleViolation("No se pueden sumar montos de monedas distintas")
        return Money(self.amount + other.amount, self.currency)
