"""Adaptador de entrada REST del CRM (/api/v1/crm)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, model_validator

from oneheavy.modules.crm.application.use_cases import (
    ChangeContactStage,
    ChangeStageCommand,
    ContactData,
    ContactRef,
    CreateContact,
    CreateContactCommand,
    CreateDeal,
    CreateDealCommand,
    DealView,
    GetContact,
    GetContactInsight,
    GetPipeline,
    GetTimeline,
    ImportContacts,
    ImportContactsCommand,
    LogActivity,
    LogActivityCommand,
    MoveDeal,
    MoveDealCommand,
    SearchContacts,
    SearchContactsQuery,
    UpdateContact,
    UpdateContactCommand,
    UpdateDeal,
    UpdateDealCommand,
)
from oneheavy.modules.crm.domain.model import (
    Activity,
    ActivityKind,
    Contact,
    ContactSource,
    DealStage,
    LifecycleStage,
)
from oneheavy.modules.crm.infrastructure.persistence import SqlCrmUnitOfWork
from oneheavy.shared.domain.access import Principal
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, get_principal

router = APIRouter(prefix="/crm", tags=["CRM"])


def _uow(container: Container = Depends(get_container)) -> SqlCrmUnitOfWork:
    return SqlCrmUnitOfWork(container.session_factory, container.bus)


# ── Schemas ─────────────────────────────────────────────────────────────────


class ContactIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=120)
    source: ContactSource = ContactSource.MANUAL
    tags: list[str] = Field(default_factory=list, max_length=30)
    owner_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _reachable(self) -> ContactIn:
        if not self.email and not self.phone:
            raise ValueError("Se requiere email o teléfono")
        return self

    def to_data(self) -> ContactData:
        return ContactData(**self.model_dump())


class ContactPatch(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=120)
    source: ContactSource | None = None
    tags: list[str] | None = Field(default=None, max_length=30)
    owner_id: uuid.UUID | None = None


class ContactOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str | None
    full_name: str
    email: str | None
    phone: str | None
    company: str | None
    job_title: str | None
    source: ContactSource
    tags: list[str]
    owner_id: uuid.UUID | None
    stage: LifecycleStage
    score: int
    mautic_id: int | None
    last_activity_at: datetime | None
    created_at: datetime

    @classmethod
    def of(cls, c: Contact) -> ContactOut:
        return cls(
            id=c.id,
            first_name=c.first_name,
            last_name=c.last_name,
            full_name=c.full_name,
            email=str(c.email) if c.email else None,
            phone=str(c.phone) if c.phone else None,
            company=c.company,
            job_title=c.job_title,
            source=c.source,
            tags=c.tags,
            owner_id=c.owner_id,
            stage=c.stage,
            score=c.score,
            mautic_id=c.mautic_id,
            last_activity_at=c.last_activity_at,
            created_at=c.created_at,
        )


class ContactPageOut(BaseModel):
    items: list[ContactOut]
    total: int
    page: int
    size: int


class StageIn(BaseModel):
    stage: LifecycleStage


class ActivityIn(BaseModel):
    kind: ActivityKind
    summary: str = Field(min_length=1, max_length=4000)


class ActivityOut(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    kind: ActivityKind
    summary: str
    actor_id: uuid.UUID | None
    occurred_at: datetime

    @classmethod
    def of(cls, a: Activity) -> ActivityOut:
        return cls(
            id=a.id,
            contact_id=a.contact_id,
            kind=a.kind,
            summary=a.summary,
            actor_id=a.actor_id,
            occurred_at=a.occurred_at,
        )


class InsightOut(BaseModel):
    score: int
    temperature: str
    explanation: str
    next_best_action: str


class ImportIn(BaseModel):
    contacts: list[dict[str, object]] = Field(max_length=5000)


class ImportOut(BaseModel):
    created: int
    merged: int
    skipped: int


class StageDef(BaseModel):
    key: DealStage
    name: str
    order: int
    probability: float


class DealOut(BaseModel):
    id: uuid.UUID
    title: str
    contact_id: uuid.UUID | None
    contact_name: str | None
    amount: float
    currency: str
    stage: DealStage
    owner_id: uuid.UUID | None
    expected_close: date | None
    created_at: datetime
    closed_at: datetime | None

    @classmethod
    def of(cls, v: DealView) -> DealOut:
        d = v.deal
        return cls(
            id=d.id,
            title=d.title,
            contact_id=d.contact_id,
            contact_name=v.contact_name,
            amount=float(d.amount),
            currency=d.currency,
            stage=d.stage,
            owner_id=d.owner_id,
            expected_close=d.expected_close,
            created_at=d.created_at,
            closed_at=d.closed_at,
        )


class PipelineOut(BaseModel):
    stages: list[StageDef]
    deals: list[DealOut]


class DealIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    contact_id: uuid.UUID | None = None
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="COP", min_length=3, max_length=3)
    stage: DealStage | None = None
    owner_id: uuid.UUID | None = None
    expected_close: date | None = None


class DealPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    contact_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    stage: DealStage | None = None
    owner_id: uuid.UUID | None = None
    expected_close: date | None = None


class MoveIn(BaseModel):
    stage: DealStage


# ── Endpoints: contactos ────────────────────────────────────────────────────


@router.get("/contacts", response_model=ContactPageOut)
async def list_contacts(
    q: str | None = None,
    stage: LifecycleStage | None = None,
    tag: str | None = None,
    owner_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> ContactPageOut:
    result = await SearchContacts(uow).execute(
        SearchContactsQuery(principal, q, stage, tag, owner_id, page, size)
    )
    return ContactPageOut(
        items=[ContactOut.of(c) for c in result.items], total=result.total, page=result.page, size=result.size
    )


@router.post("/contacts", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactIn, principal: Principal = Depends(get_principal), uow: SqlCrmUnitOfWork = Depends(_uow)
) -> ContactOut:
    return ContactOut.of(await CreateContact(uow).execute(CreateContactCommand(principal, body.to_data())))


@router.post("/contacts/import", response_model=ImportOut)
async def import_contacts(
    body: ImportIn, principal: Principal = Depends(get_principal), uow: SqlCrmUnitOfWork = Depends(_uow)
) -> ImportOut:
    # Validación fila a fila: una fila inválida se cuenta como "skipped" en vez de abortar el lote.
    rows: list[ContactData] = []
    invalid = 0
    for raw in body.contacts:
        try:
            rows.append(ContactIn.model_validate(raw).to_data())
        except ValueError:
            invalid += 1
    result = await ImportContacts(uow).execute(ImportContactsCommand(principal, rows))
    return ImportOut(created=result.created, merged=result.merged, skipped=result.skipped + invalid)


@router.get("/contacts/{contact_id}", response_model=ContactOut)
async def get_contact(
    contact_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> ContactOut:
    return ContactOut.of(await GetContact(uow).execute(ContactRef(principal, contact_id)))


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: uuid.UUID,
    body: ContactPatch,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> ContactOut:
    changes = body.model_dump(exclude_unset=True)
    return ContactOut.of(
        await UpdateContact(uow).execute(UpdateContactCommand(principal, contact_id, changes))
    )


@router.post("/contacts/{contact_id}/stage", response_model=ContactOut)
async def change_stage(
    contact_id: uuid.UUID,
    body: StageIn,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> ContactOut:
    return ContactOut.of(
        await ChangeContactStage(uow).execute(ChangeStageCommand(principal, contact_id, body.stage))
    )


@router.get("/contacts/{contact_id}/timeline", response_model=list[ActivityOut])
async def timeline(
    contact_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> list[ActivityOut]:
    return [ActivityOut.of(a) for a in await GetTimeline(uow).execute(ContactRef(principal, contact_id))]


@router.post(
    "/contacts/{contact_id}/activities", response_model=ActivityOut, status_code=status.HTTP_201_CREATED
)
async def log_activity(
    contact_id: uuid.UUID,
    body: ActivityIn,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> ActivityOut:
    activity = await LogActivity(uow).execute(
        LogActivityCommand(principal, contact_id, body.kind, body.summary)
    )
    return ActivityOut.of(activity)


@router.post("/contacts/{contact_id}/insight", response_model=InsightOut)
async def insight(
    contact_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> InsightOut:
    result = await GetContactInsight(uow, c.llm).execute(ContactRef(principal, contact_id))
    return InsightOut(
        score=result.score,
        temperature=result.temperature,
        explanation=result.explanation,
        next_best_action=result.next_best_action,
    )


# ── Endpoints: pipeline ─────────────────────────────────────────────────────


@router.get("/pipeline", response_model=PipelineOut)
async def pipeline(
    principal: Principal = Depends(get_principal), uow: SqlCrmUnitOfWork = Depends(_uow)
) -> PipelineOut:
    view = await GetPipeline(uow).execute(principal)
    return PipelineOut(
        stages=[
            StageDef(key=s.key, name=s.name, order=s.order, probability=s.probability) for s in view.stages
        ],
        deals=[DealOut.of(d) for d in view.deals],
    )


@router.post("/deals", response_model=DealOut, status_code=status.HTTP_201_CREATED)
async def create_deal(
    body: DealIn, principal: Principal = Depends(get_principal), uow: SqlCrmUnitOfWork = Depends(_uow)
) -> DealOut:
    view = await CreateDeal(uow).execute(CreateDealCommand(actor=principal, **body.model_dump()))
    return DealOut.of(view)


@router.patch("/deals/{deal_id}", response_model=DealOut)
async def update_deal(
    deal_id: uuid.UUID,
    body: DealPatch,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> DealOut:
    view = await UpdateDeal(uow).execute(
        UpdateDealCommand(principal, deal_id, body.model_dump(exclude_unset=True))
    )
    return DealOut.of(view)


@router.post("/deals/{deal_id}/move", response_model=DealOut)
async def move_deal(
    deal_id: uuid.UUID,
    body: MoveIn,
    principal: Principal = Depends(get_principal),
    uow: SqlCrmUnitOfWork = Depends(_uow),
) -> DealOut:
    return DealOut.of(await MoveDeal(uow).execute(MoveDealCommand(principal, deal_id, body.stage)))
