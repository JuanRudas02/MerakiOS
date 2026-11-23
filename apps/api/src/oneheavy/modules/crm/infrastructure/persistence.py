"""Adaptador de salida: persistencia SQLAlchemy del CRM."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from oneheavy.modules.crm.application.ports import CrmUnitOfWork
from oneheavy.modules.crm.domain.model import (
    Activity,
    ActivityKind,
    Contact,
    ContactSource,
    Deal,
    DealStage,
    LifecycleStage,
)
from oneheavy.modules.crm.domain.repositories import (
    ActivityRepository,
    ContactQuery,
    ContactRepository,
    DealRepository,
)
from oneheavy.shared.domain.time import ensure_aware
from oneheavy.shared.domain.value_objects import Email, PhoneNumber
from oneheavy.shared.infrastructure.db import Base, SqlAlchemyUnitOfWork, TenantMixin, TimestampMixin

# ── ORM ─────────────────────────────────────────────────────────────────────


class ContactRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "crm_contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_crm_contacts_tenant_email"),
        UniqueConstraint("tenant_id", "phone", name="uq_crm_contacts_tenant_phone"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254), index=True)
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    company: Mapped[str | None] = mapped_column(String(160))
    job_title: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(30))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags_text: Mapped[str] = mapped_column(String(2000), default="")  # ",tag1,tag2," para filtrar portable
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    stage: Mapped[str] = mapped_column(String(20), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    engagement_points: Mapped[int] = mapped_column(Integer, default=0)
    mautic_id: Mapped[int | None] = mapped_column(Integer)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActivityRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "crm_activities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    kind: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DealRow(TenantMixin, TimestampMixin, Base):
    __tablename__ = "crm_deals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    stage: Mapped[str] = mapped_column(String(20), index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    expected_close: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ── Mappers ─────────────────────────────────────────────────────────────────


def _aware(value: datetime | None) -> datetime | None:
    return ensure_aware(value) if value else None


def _contact_to_domain(r: ContactRow) -> Contact:
    return Contact(
        id=r.id,
        tenant_id=r.tenant_id,
        first_name=r.first_name,
        last_name=r.last_name,
        email=Email(r.email) if r.email else None,
        phone=PhoneNumber(r.phone) if r.phone else None,
        company=r.company,
        job_title=r.job_title,
        source=ContactSource(r.source),
        tags=list(r.tags or []),
        owner_id=r.owner_id,
        stage=LifecycleStage(r.stage),
        score=r.score,
        engagement_points=r.engagement_points,
        mautic_id=r.mautic_id,
        last_activity_at=_aware(r.last_activity_at),
        created_at=ensure_aware(r.created_at),
        updated_at=ensure_aware(r.updated_at),
    )


def _contact_apply(r: ContactRow, c: Contact) -> None:
    r.tenant_id, r.first_name, r.last_name = c.tenant_id, c.first_name, c.last_name
    r.email = str(c.email) if c.email else None
    r.phone = str(c.phone) if c.phone else None
    r.company, r.job_title, r.source = c.company, c.job_title, c.source.value
    r.tags = list(c.tags)
    r.tags_text = "," + ",".join(c.tags) + "," if c.tags else ""
    r.owner_id, r.stage, r.score = c.owner_id, c.stage.value, c.score
    r.engagement_points, r.mautic_id, r.last_activity_at = (
        c.engagement_points,
        c.mautic_id,
        c.last_activity_at,
    )
    r.created_at, r.updated_at = c.created_at, c.updated_at


def _activity_to_domain(r: ActivityRow) -> Activity:
    return Activity(
        id=r.id,
        tenant_id=r.tenant_id,
        contact_id=r.contact_id,
        kind=ActivityKind(r.kind),
        summary=r.summary,
        actor_id=r.actor_id,
        occurred_at=ensure_aware(r.occurred_at),
        created_at=ensure_aware(r.created_at),
        updated_at=ensure_aware(r.updated_at),
    )


def _deal_to_domain(r: DealRow) -> Deal:
    return Deal(
        id=r.id,
        tenant_id=r.tenant_id,
        title=r.title,
        contact_id=r.contact_id,
        amount=Decimal(r.amount),
        currency=r.currency,
        stage=DealStage(r.stage),
        owner_id=r.owner_id,
        expected_close=r.expected_close,
        closed_at=_aware(r.closed_at),
        created_at=ensure_aware(r.created_at),
        updated_at=ensure_aware(r.updated_at),
    )


def _deal_apply(r: DealRow, d: Deal) -> None:
    r.tenant_id, r.title, r.contact_id, r.amount, r.currency = (
        d.tenant_id,
        d.title,
        d.contact_id,
        d.amount,
        d.currency,
    )
    r.stage, r.owner_id, r.expected_close, r.closed_at = (
        d.stage.value,
        d.owner_id,
        d.expected_close,
        d.closed_at,
    )
    r.created_at, r.updated_at = d.created_at, d.updated_at


# ── Repositorios ────────────────────────────────────────────────────────────


class SqlContactRepository(ContactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _row(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> ContactRow | None:
        row = await self._s.get(ContactRow, contact_id)
        return row if row and row.tenant_id == tenant_id else None

    async def get(self, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Contact | None:
        row = await self._row(tenant_id, contact_id)
        return _contact_to_domain(row) if row else None

    async def get_many(self, tenant_id: uuid.UUID, ids: set[uuid.UUID]) -> dict[uuid.UUID, Contact]:
        if not ids:
            return {}
        rows = await self._s.scalars(
            select(ContactRow).where(ContactRow.tenant_id == tenant_id, ContactRow.id.in_(ids))
        )
        return {r.id: _contact_to_domain(r) for r in rows}

    async def find_duplicate(
        self, tenant_id: uuid.UUID, email: str | None, phone: str | None, *, exclude: uuid.UUID | None = None
    ) -> Contact | None:
        conditions = []
        if email:
            conditions.append(ContactRow.email == email)
        if phone:
            conditions.append(ContactRow.phone == phone)
        if not conditions:
            return None
        stmt = select(ContactRow).where(ContactRow.tenant_id == tenant_id, or_(*conditions))
        if exclude:
            stmt = stmt.where(ContactRow.id != exclude)
        row = (await self._s.scalars(stmt.order_by(ContactRow.created_at).limit(1))).first()
        return _contact_to_domain(row) if row else None

    async def search(self, query: ContactQuery) -> tuple[list[Contact], int]:
        stmt = select(ContactRow).where(ContactRow.tenant_id == query.tenant_id)
        if query.q:
            like = f"%{query.q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ContactRow.first_name).like(like),
                    func.lower(ContactRow.last_name).like(like),
                    func.lower(ContactRow.email).like(like),
                    ContactRow.phone.like(f"%{query.q.lstrip('+')}%"),
                    func.lower(ContactRow.company).like(like),
                )
            )
        if query.stage:
            stmt = stmt.where(ContactRow.stage == query.stage.value)
        if query.tag:
            stmt = stmt.where(ContactRow.tags_text.like(f"%,{query.tag},%"))
        if query.owner_id:
            stmt = stmt.where(ContactRow.owner_id == query.owner_id)
        total = int(await self._s.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        rows = await self._s.scalars(
            stmt.order_by(ContactRow.created_at.desc())
            .offset((query.page - 1) * query.size)
            .limit(query.size)
        )
        return [_contact_to_domain(r) for r in rows], total

    async def add(self, contact: Contact) -> None:
        row = ContactRow(id=contact.id)
        _contact_apply(row, contact)
        self._s.add(row)

    async def update(self, contact: Contact) -> None:
        row = await self._row(contact.tenant_id, contact.id)
        if row is not None:
            _contact_apply(row, contact)


class SqlActivityRepository(ActivityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, activity: Activity) -> None:
        self._s.add(
            ActivityRow(
                id=activity.id,
                tenant_id=activity.tenant_id,
                contact_id=activity.contact_id,
                kind=activity.kind.value,
                summary=activity.summary,
                actor_id=activity.actor_id,
                occurred_at=activity.occurred_at,
                created_at=activity.created_at,
                updated_at=activity.updated_at,
            )
        )

    async def list_for_contact(
        self, tenant_id: uuid.UUID, contact_id: uuid.UUID, limit: int = 200
    ) -> list[Activity]:
        rows = await self._s.scalars(
            select(ActivityRow)
            .where(ActivityRow.tenant_id == tenant_id, ActivityRow.contact_id == contact_id)
            .order_by(ActivityRow.occurred_at.desc(), ActivityRow.created_at.desc())
            .limit(limit)
        )
        return [_activity_to_domain(r) for r in rows]


class SqlDealRepository(DealRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _row(self, tenant_id: uuid.UUID, deal_id: uuid.UUID) -> DealRow | None:
        row = await self._s.get(DealRow, deal_id)
        return row if row and row.tenant_id == tenant_id else None

    async def get(self, tenant_id: uuid.UUID, deal_id: uuid.UUID) -> Deal | None:
        row = await self._row(tenant_id, deal_id)
        return _deal_to_domain(row) if row else None

    async def list(self, tenant_id: uuid.UUID) -> list[Deal]:
        rows = await self._s.scalars(
            select(DealRow).where(DealRow.tenant_id == tenant_id).order_by(DealRow.created_at.desc())
        )
        return [_deal_to_domain(r) for r in rows]

    async def add(self, deal: Deal) -> None:
        row = DealRow(id=deal.id)
        _deal_apply(row, deal)
        self._s.add(row)

    async def update(self, deal: Deal) -> None:
        row = await self._row(deal.tenant_id, deal.id)
        if row is not None:
            _deal_apply(row, deal)


class SqlCrmUnitOfWork(SqlAlchemyUnitOfWork, CrmUnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.contacts = SqlContactRepository(self.session)
        self.activities = SqlActivityRepository(self.session)
        self.deals = SqlDealRepository(self.session)
        return self
