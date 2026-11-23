"""Adaptador de salida: persistencia SQLAlchemy de Marketing."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Self

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint, Uuid, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.marketing.application.ports import MarketingUnitOfWork
from oneheavy.modules.marketing.domain.model import (
    AudienceMember,
    Campaign,
    CampaignStatus,
    CampaignStep,
    Channel,
    EmailDraft,
    EmailStatus,
    Segment,
    SegmentFilters,
)
from oneheavy.modules.marketing.domain.repositories import (
    AudienceRepository,
    CampaignRepository,
    EmailRepository,
    SegmentRepository,
)
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin

# ── ORM ─────────────────────────────────────────────────────────────────────


class AudienceRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "marketing_audience"
    __table_args__ = (
        UniqueConstraint("tenant_id", "contact_id", name="uq_marketing_audience_tenant_contact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    email: Mapped[str | None] = mapped_column(String(254), index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    stage: Mapped[str] = mapped_column(String(20))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    engagement_points: Mapped[int] = mapped_column(Integer, default=0)
    mautic_id: Mapped[int | None] = mapped_column(Integer, index=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SegmentRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "marketing_segments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(500))
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    contacts_count: Mapped[int] = mapped_column(Integer, default=0)
    mautic_id: Mapped[int | None] = mapped_column(Integer)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "marketing_emails"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    subject: Mapped[str] = mapped_column(String(150))
    preheader: Mapped[str] = mapped_column(String(200))
    body_html: Mapped[str] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10))
    segment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    mautic_id: Mapped[int | None] = mapped_column(Integer)


class CampaignRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "marketing_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    objective: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(12))
    segment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    mautic_id: Mapped[int | None] = mapped_column(Integer)


def _aware(v: datetime | None) -> datetime | None:
    return ensure_aware(v) if v else None


# ── Repositorios (upsert por id: save = add o update) ───────────────────────


class SqlAudienceRepository(AudienceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    @staticmethod
    def _to_domain(r: AudienceRow) -> AudienceMember:
        return AudienceMember(
            id=r.id,
            tenant_id=r.tenant_id,
            contact_id=r.contact_id,
            email=r.email,
            phone=r.phone,
            stage=r.stage,
            tags=list(r.tags or []),
            engagement_points=r.engagement_points,
            mautic_id=r.mautic_id,
            synced_at=_aware(r.synced_at),
            created_at=ensure_aware(r.created_at),
            updated_at=ensure_aware(r.updated_at),
        )

    async def get_by_contact(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> AudienceMember | None:
        row = await self._s.scalar(
            select(AudienceRow).where(
                AudienceRow.tenant_id == tenant_id, AudienceRow.contact_id == contact_id
            )
        )
        return self._to_domain(row) if row else None

    async def find_by_mautic_id(self, mautic_id: int) -> AudienceMember | None:
        row = (
            await self._s.scalars(select(AudienceRow).where(AudienceRow.mautic_id == mautic_id).limit(1))
        ).first()
        return self._to_domain(row) if row else None

    async def find_by_email(self, tenant_id: uuid.UUID, email: str) -> AudienceMember | None:
        row = await self._s.scalar(
            select(AudienceRow).where(AudienceRow.tenant_id == tenant_id, AudienceRow.email == email.lower())
        )
        return self._to_domain(row) if row else None

    async def list(self, tenant_id: uuid.UUID) -> list[AudienceMember]:
        rows = await self._s.scalars(select(AudienceRow).where(AudienceRow.tenant_id == tenant_id))
        return [self._to_domain(r) for r in rows]

    async def save(self, member: AudienceMember) -> None:
        row = await self._s.get(AudienceRow, member.id)
        if row is None:
            row = AudienceRow(id=member.id)
            self._s.add(row)
        row.tenant_id, row.contact_id, row.email, row.phone = (
            member.tenant_id,
            member.contact_id,
            member.email,
            member.phone,
        )
        row.stage, row.tags, row.engagement_points = member.stage, list(member.tags), member.engagement_points
        row.mautic_id, row.synced_at = member.mautic_id, member.synced_at
        row.created_at, row.updated_at = member.created_at, member.updated_at


class SqlSegmentRepository(SegmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    @staticmethod
    def _to_domain(r: SegmentRow) -> Segment:
        f = r.filters or {}
        return Segment(
            id=r.id,
            tenant_id=r.tenant_id,
            name=r.name,
            description=r.description,
            filters=SegmentFilters(
                stages=tuple(f.get("stages") or ()),
                tags=tuple(f.get("tags") or ()),
                min_score=f.get("min_score"),
            ),
            contacts_count=r.contacts_count,
            mautic_id=r.mautic_id,
            synced_at=_aware(r.synced_at),
            created_at=ensure_aware(r.created_at),
            updated_at=ensure_aware(r.updated_at),
        )

    async def get(self, tenant_id: uuid.UUID, segment_id: uuid.UUID) -> Segment | None:
        row = await self._s.get(SegmentRow, segment_id)
        return self._to_domain(row) if row and row.tenant_id == tenant_id else None

    async def list(self, tenant_id: uuid.UUID) -> list[Segment]:
        rows = await self._s.scalars(
            select(SegmentRow).where(SegmentRow.tenant_id == tenant_id).order_by(SegmentRow.created_at.desc())
        )
        return [self._to_domain(r) for r in rows]

    async def save(self, segment: Segment) -> None:
        row = await self._s.get(SegmentRow, segment.id)
        if row is None:
            row = SegmentRow(id=segment.id)
            self._s.add(row)
        row.tenant_id, row.name, row.description = segment.tenant_id, segment.name, segment.description
        row.filters, row.contacts_count = segment.filters.as_dict(), segment.contacts_count
        row.mautic_id, row.synced_at = segment.mautic_id, segment.synced_at
        row.created_at, row.updated_at = segment.created_at, segment.updated_at


class SqlEmailRepository(EmailRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    @staticmethod
    def _to_domain(r: EmailRow) -> EmailDraft:
        return EmailDraft(
            id=r.id,
            tenant_id=r.tenant_id,
            subject=r.subject,
            preheader=r.preheader,
            body_html=r.body_html,
            body_text=r.body_text,
            goal=r.goal,
            status=EmailStatus(r.status),
            segment_id=r.segment_id,
            mautic_id=r.mautic_id,
            created_at=ensure_aware(r.created_at),
            updated_at=ensure_aware(r.updated_at),
        )

    async def get(self, tenant_id: uuid.UUID, email_id: uuid.UUID) -> EmailDraft | None:
        row = await self._s.get(EmailRow, email_id)
        return self._to_domain(row) if row and row.tenant_id == tenant_id else None

    async def list(self, tenant_id: uuid.UUID) -> list[EmailDraft]:
        rows = await self._s.scalars(
            select(EmailRow).where(EmailRow.tenant_id == tenant_id).order_by(EmailRow.created_at.desc())
        )
        return [self._to_domain(r) for r in rows]

    async def save(self, email: EmailDraft) -> None:
        row = await self._s.get(EmailRow, email.id)
        if row is None:
            row = EmailRow(id=email.id)
            self._s.add(row)
        row.tenant_id, row.subject, row.preheader = email.tenant_id, email.subject, email.preheader
        row.body_html, row.body_text, row.goal = email.body_html, email.body_text, email.goal[:500]
        row.status, row.segment_id, row.mautic_id = email.status.value, email.segment_id, email.mautic_id
        row.created_at, row.updated_at = email.created_at, email.updated_at


class SqlCampaignRepository(CampaignRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    @staticmethod
    def _to_domain(r: CampaignRow) -> Campaign:
        return Campaign(
            id=r.id,
            tenant_id=r.tenant_id,
            name=r.name,
            objective=r.objective,
            status=CampaignStatus(r.status),
            segment_id=r.segment_id,
            steps=[
                CampaignStep(s["day"], Channel(s["channel"]), s["subject"], s["intent"])
                for s in r.steps or []
            ],
            mautic_id=r.mautic_id,
            created_at=ensure_aware(r.created_at),
            updated_at=ensure_aware(r.updated_at),
        )

    async def get(self, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign | None:
        row = await self._s.get(CampaignRow, campaign_id)
        return self._to_domain(row) if row and row.tenant_id == tenant_id else None

    async def list(self, tenant_id: uuid.UUID) -> list[Campaign]:
        rows = await self._s.scalars(
            select(CampaignRow)
            .where(CampaignRow.tenant_id == tenant_id)
            .order_by(CampaignRow.created_at.desc())
        )
        return [self._to_domain(r) for r in rows]

    async def save(self, campaign: Campaign) -> None:
        row = await self._s.get(CampaignRow, campaign.id)
        if row is None:
            row = CampaignRow(id=campaign.id)
            self._s.add(row)
        row.tenant_id, row.name, row.objective = campaign.tenant_id, campaign.name, campaign.objective[:500]
        row.status, row.segment_id, row.mautic_id = (
            campaign.status.value,
            campaign.segment_id,
            campaign.mautic_id,
        )
        row.steps = [
            {"day": s.day, "channel": s.channel.value, "subject": s.subject, "intent": s.intent}
            for s in campaign.steps
        ]
        row.created_at, row.updated_at = campaign.created_at, campaign.updated_at


class SqlMarketingUnitOfWork(SqlAlchemyUnitOfWork, MarketingUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.audience = SqlAudienceRepository(self.session)
        self.segments = SqlSegmentRepository(self.session)
        self.emails = SqlEmailRepository(self.session)
        self.campaigns = SqlCampaignRepository(self.session)
        return self
