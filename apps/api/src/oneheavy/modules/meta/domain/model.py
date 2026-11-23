"""Dominio Meta Business: conexión publicitaria, métricas de campañas y alertas."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from oneheavy.shared.domain.entity import Entity, TenantEntity
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.domain.time import utc_now

_ACCOUNT_RE = re.compile(r"^(act_)?\d{5,25}$")


@dataclass(kw_only=True, eq=False)
class MetaConnection(TenantEntity):
    """Conexión del workspace con su cuenta publicitaria de Meta (una por tenant).

    El token se almacena pero NUNCA se expone: sólo `masked_token`.
    """

    ad_account_id: str
    access_token: str
    page_id: str | None = None
    pixel_id: str | None = None
    last_sync_at: datetime | None = None

    @staticmethod
    def normalize_account(ad_account_id: str) -> str:
        value = ad_account_id.strip()
        if not _ACCOUNT_RE.match(value):
            raise BusinessRuleViolation("ID de cuenta publicitaria inválido", code="invalid_ad_account")
        return value.removeprefix("act_")

    @classmethod
    def connect(
        cls,
        *,
        tenant_id: uuid.UUID,
        ad_account_id: str,
        access_token: str,
        page_id: str | None = None,
        pixel_id: str | None = None,
    ) -> MetaConnection:
        conn = cls(tenant_id=tenant_id, ad_account_id=cls.normalize_account(ad_account_id), access_token="")
        conn.update(
            ad_account_id=ad_account_id, access_token=access_token, page_id=page_id, pixel_id=pixel_id
        )
        return conn

    def update(
        self, *, ad_account_id: str, access_token: str, page_id: str | None, pixel_id: str | None
    ) -> None:
        token = access_token.strip()
        if len(token) < 10:
            raise BusinessRuleViolation("Token de acceso de Meta inválido", code="invalid_meta_token")
        self.ad_account_id = self.normalize_account(ad_account_id)
        self.access_token = token
        self.page_id = (page_id or "").strip() or None
        self.pixel_id = (pixel_id or "").strip() or None
        self.touch()

    @property
    def masked_token(self) -> str:
        return f"…{self.access_token[-4:]}" if self.access_token else ""

    def mark_synced(self) -> None:
        self.last_sync_at = utc_now()
        self.touch()


@dataclass(kw_only=True, eq=False)
class CampaignDailyMetric(Entity):
    """Métricas de una campaña en un día (snapshot sincronizado desde Meta)."""

    tenant_id: uuid.UUID
    external_id: str
    name: str
    status: str
    objective: str
    day: date
    spend: Decimal = Decimal("0")
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    conversions: int = 0
    revenue: Decimal = Decimal("0")


@dataclass(frozen=True)
class Performance:
    """Agregado de métricas con KPIs derivados (Value Object)."""

    spend: Decimal = Decimal("0")
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    conversions: int = 0
    revenue: Decimal = Decimal("0")

    @classmethod
    def of(cls, metrics: list[CampaignDailyMetric]) -> Performance:
        return cls(
            spend=sum((m.spend for m in metrics), Decimal("0")),
            impressions=sum(m.impressions for m in metrics),
            clicks=sum(m.clicks for m in metrics),
            leads=sum(m.leads for m in metrics),
            conversions=sum(m.conversions for m in metrics),
            revenue=sum((m.revenue for m in metrics), Decimal("0")),
        )

    @property
    def ctr(self) -> float:
        """Porcentaje (1.5 = 1.5%)."""
        return round(self.clicks / self.impressions * 100, 2) if self.impressions else 0.0

    @property
    def cpc(self) -> float:
        return round(float(self.spend) / self.clicks, 2) if self.clicks else 0.0

    @property
    def cpm(self) -> float:
        return round(float(self.spend) / self.impressions * 1000, 2) if self.impressions else 0.0

    @property
    def cpl(self) -> float:
        return round(float(self.spend) / self.leads, 2) if self.leads else 0.0

    @property
    def roas(self) -> float:
        return round(float(self.revenue) / float(self.spend), 2) if self.spend else 0.0


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(kw_only=True, eq=False)
class AdAlert(Entity):
    tenant_id: uuid.UUID
    campaign_ref: str
    metric: str
    value: float
    benchmark: float
    severity: Severity
    message: str
    dedupe_key: str


@dataclass(kw_only=True, eq=False)
class ContactFingerprint(Entity):
    """Espejo mínimo de contactos del CRM con datos ya hasheados (Conversions API)."""

    tenant_id: uuid.UUID
    contact_id: uuid.UUID
    hashed_email: str | None = None
    hashed_phone: str | None = None


def hash_email(email: str | None) -> str | None:
    if not email or not email.strip():
        return None
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def hash_phone(phone: str | None) -> str | None:
    digits = "".join(c for c in (phone or "") if c.isdigit())
    return hashlib.sha256(digits.encode()).hexdigest() if digits else None


@dataclass(frozen=True)
class LeadData:
    leadgen_id: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    campaign_ref: str | None = None
    answers: dict[str, str] = field(default_factory=dict)
