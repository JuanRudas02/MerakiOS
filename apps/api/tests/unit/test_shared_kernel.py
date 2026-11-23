from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from oneheavy.shared.domain.access import Permission, Principal, Role
from oneheavy.shared.domain.errors import BusinessRuleViolation, PermissionDenied
from oneheavy.shared.domain.events import DomainEvent
from oneheavy.shared.domain.value_objects import Email, Money, PhoneNumber
from oneheavy.shared.infrastructure.adapters import sniff_content_type
from oneheavy.shared.infrastructure.event_bus import InMemoryEventBus
from oneheavy.shared.infrastructure.http.rate_limit import SlidingWindowLimiter, parse_rate
from oneheavy.shared.infrastructure.security import PasswordHasher, TokenService


class TestValueObjects:
    def test_email_is_normalized(self) -> None:
        assert Email("  Ana@Acme.CO ").value == "ana@acme.co"

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            Email("no-es-email")

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("300 123 4567", "+573001234567"),
            ("+57 (300) 123-4567", "+573001234567"),
            ("0034600111222", "+34600111222"),
        ],
    )
    def test_phone_normalized_to_e164(self, raw: str, expected: str) -> None:
        assert PhoneNumber(raw).value == expected
        assert PhoneNumber(raw).digits == expected[1:]

    def test_invalid_phone_raises(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            PhoneNumber("abc")

    def test_money_sum_and_cents(self) -> None:
        total = Money(10.5) + Money("2.25")
        assert total.cents == 1275

    def test_money_currency_mismatch(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            Money(1, "COP") + Money(1, "USD")


class TestAccess:
    def test_staff_cannot_manage_tasks(self) -> None:
        p = Principal.for_role(uuid.uuid4(), uuid.uuid4(), Role.STAFF)
        assert p.can(Permission.TASKS_EXECUTE)
        with pytest.raises(PermissionDenied):
            p.require(Permission.TASKS_MANAGE)

    def test_owner_has_everything(self) -> None:
        p = Principal.for_role(uuid.uuid4(), uuid.uuid4(), Role.OWNER)
        assert all(p.can(perm) for perm in Permission)


class TestSecurity:
    def test_password_roundtrip_and_strength(self) -> None:
        hasher = PasswordHasher()
        hashed = hasher.hash("ClaveSegura123")
        assert hasher.verify("ClaveSegura123", hashed)
        assert not hasher.verify("otra", hashed)
        with pytest.raises(BusinessRuleViolation):
            hasher.hash("corta1")

    def test_token_roundtrip(self) -> None:
        tokens = TokenService("x" * 32)
        p = Principal.for_role(uuid.uuid4(), uuid.uuid4(), Role.MARKETER)
        decoded = tokens.decode(tokens.issue(p))
        assert decoded == p


@dataclass(frozen=True, kw_only=True)
class _Ping(DomainEvent):
    n: int


async def test_event_bus_isolates_failing_handlers() -> None:
    bus = InMemoryEventBus()
    received: list[int] = []

    async def boom(_: _Ping) -> None:
        raise RuntimeError("falla aislada")

    async def ok(e: _Ping) -> None:
        received.append(e.n)

    bus.subscribe(_Ping, boom)
    bus.subscribe(_Ping, ok)
    await bus.publish(_Ping(tenant_id=uuid.uuid4(), n=7))
    assert received == [7]


def test_rate_limiter() -> None:
    limit, window = parse_rate("2/minute")
    limiter = SlidingWindowLimiter()
    assert limiter.hit("k", limit, window)
    assert limiter.hit("k", limit, window)
    assert not limiter.hit("k", limit, window)


def test_sniff_content_type_rejects_scripts() -> None:
    assert sniff_content_type(b"\x89PNG\r\n\x1a\n....") == "image/png"
    assert sniff_content_type(b"<script>alert(1)</script>") is None
