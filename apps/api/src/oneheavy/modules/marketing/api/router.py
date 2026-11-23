"""Adaptador de entrada REST de Marketing (/api/v1/marketing)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, Field

from oneheavy.modules.marketing.application.ports import MauticGateway
from oneheavy.modules.marketing.application.use_cases import (
    CampaignRef,
    CreateSegment,
    CreateSegmentCommand,
    EmailRef,
    GenerateEmail,
    GenerateEmailCommand,
    GetMarketingStatus,
    HandleMauticWebhook,
    LaunchCampaign,
    ListCampaigns,
    ListEmails,
    ListSegments,
    MauticWebhookCommand,
    PlanCampaign,
    PlanCampaignCommand,
    PushEmail,
    SegmentRef,
    SyncSegment,
)
from oneheavy.modules.marketing.domain.model import Campaign, EmailDraft, Segment, SegmentFilters
from oneheavy.modules.marketing.infrastructure.persistence import SqlMarketingUnitOfWork
from oneheavy.shared.domain.access import Principal
from oneheavy.shared.domain.errors import AuthenticationError, BusinessRuleViolation
from oneheavy.shared.infrastructure.container import Container
from oneheavy.shared.infrastructure.http import get_container, get_principal

router = APIRouter(prefix="/marketing", tags=["Marketing (Mautic + IA)"])

GATEWAY_KEY = "marketing.mautic"


def _uow(container: Container = Depends(get_container)) -> SqlMarketingUnitOfWork:
    return SqlMarketingUnitOfWork(container.session_factory, container.bus)


def _gateway(container: Container = Depends(get_container)) -> MauticGateway:
    gateway: MauticGateway = container.extras[GATEWAY_KEY]
    return gateway


# ── Schemas ─────────────────────────────────────────────────────────────────


class StatusOut(BaseModel):
    mautic_enabled: bool
    connected: bool
    last_sync_at: datetime | None
    synced_contacts: int


class FiltersIn(BaseModel):
    stages: list[str] | None = None
    tags: list[str] | None = None
    min_score: int | None = Field(default=None, ge=0, le=1000)

    def to_domain(self) -> SegmentFilters:
        return SegmentFilters(
            stages=tuple(s.lower() for s in self.stages or ()),
            tags=tuple(t.strip().lower() for t in self.tags or () if t.strip()),
            min_score=self.min_score,
        )


class SegmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    filters: FiltersIn = Field(default_factory=FiltersIn)


class SegmentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    filters: dict[str, Any]
    contacts_count: int
    mautic_id: int | None
    synced_at: datetime | None

    @classmethod
    def of(cls, s: Segment) -> SegmentOut:
        return cls(
            id=s.id,
            name=s.name,
            description=s.description,
            filters=s.filters.as_dict(),
            contacts_count=s.contacts_count,
            mautic_id=s.mautic_id,
            synced_at=s.synced_at,
        )


class GenerateEmailIn(BaseModel):
    goal: str = Field(min_length=3, max_length=500)
    audience: str = Field(min_length=3, max_length=500)
    tone: str | None = Field(default=None, max_length=80)
    language: str = Field(default="es", min_length=2, max_length=10)
    segment_id: uuid.UUID | None = None
    brand: str | None = Field(default=None, max_length=120)


class EmailOut(BaseModel):
    id: uuid.UUID
    subject: str
    preheader: str
    body_html: str
    body_text: str
    goal: str
    status: str
    segment_id: uuid.UUID | None
    mautic_id: int | None
    created_at: datetime

    @classmethod
    def of(cls, e: EmailDraft) -> EmailOut:
        return cls(
            id=e.id,
            subject=e.subject,
            preheader=e.preheader,
            body_html=e.body_html,
            body_text=e.body_text,
            goal=e.goal,
            status=e.status.value,
            segment_id=e.segment_id,
            mautic_id=e.mautic_id,
            created_at=e.created_at,
        )


class PlanCampaignIn(BaseModel):
    objective: str = Field(min_length=3, max_length=500)
    segment_id: uuid.UUID | None = None
    duration_days: int = Field(ge=1, le=180)


class StepOut(BaseModel):
    day: int
    channel: str
    subject: str
    intent: str


class CampaignOut(BaseModel):
    id: uuid.UUID
    name: str
    objective: str
    status: str
    segment_id: uuid.UUID | None
    steps: list[StepOut]
    mautic_id: int | None
    created_at: datetime

    @classmethod
    def of(cls, c: Campaign) -> CampaignOut:
        return cls(
            id=c.id,
            name=c.name,
            objective=c.objective,
            status=c.status.value,
            segment_id=c.segment_id,
            steps=[
                StepOut(day=s.day, channel=s.channel.value, subject=s.subject, intent=s.intent)
                for s in c.steps
            ],
            mautic_id=c.mautic_id,
            created_at=c.created_at,
        )


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/status", response_model=StatusOut)
async def marketing_status(
    principal: Principal = Depends(get_principal),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
    gateway: MauticGateway = Depends(_gateway),
    c: Container = Depends(get_container),
) -> StatusOut:
    s = await GetMarketingStatus(uow, gateway, c.settings.mautic_enabled).execute(principal)
    return StatusOut(
        mautic_enabled=s.mautic_enabled,
        connected=s.connected,
        last_sync_at=s.last_sync_at,
        synced_contacts=s.synced_contacts,
    )


@router.get("/segments", response_model=list[SegmentOut])
async def list_segments(
    principal: Principal = Depends(get_principal), uow: SqlMarketingUnitOfWork = Depends(_uow)
) -> list[SegmentOut]:
    return [SegmentOut.of(s) for s in await ListSegments(uow).execute(principal)]


@router.post("/segments", response_model=SegmentOut, status_code=status.HTTP_201_CREATED)
async def create_segment(
    body: SegmentIn,
    principal: Principal = Depends(get_principal),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
) -> SegmentOut:
    segment = await CreateSegment(uow).execute(
        CreateSegmentCommand(principal, body.name, body.description, body.filters.to_domain())
    )
    return SegmentOut.of(segment)


@router.post("/segments/{segment_id}/sync", response_model=SegmentOut)
async def sync_segment(
    segment_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
    gateway: MauticGateway = Depends(_gateway),
    c: Container = Depends(get_container),
) -> SegmentOut:
    segment = await SyncSegment(uow, gateway, c.settings.mautic_enabled).execute(
        SegmentRef(principal, segment_id)
    )
    return SegmentOut.of(segment)


@router.get("/emails", response_model=list[EmailOut])
async def list_emails(
    principal: Principal = Depends(get_principal), uow: SqlMarketingUnitOfWork = Depends(_uow)
) -> list[EmailOut]:
    return [EmailOut.of(e) for e in await ListEmails(uow).execute(principal)]


@router.post("/emails/generate", response_model=EmailOut, status_code=status.HTTP_201_CREATED)
async def generate_email(
    body: GenerateEmailIn,
    principal: Principal = Depends(get_principal),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> EmailOut:
    draft = await GenerateEmail(uow, c.llm).execute(
        GenerateEmailCommand(actor=principal, **body.model_dump())
    )
    return EmailOut.of(draft)


@router.post("/emails/{email_id}/push", response_model=EmailOut)
async def push_email(
    email_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
    gateway: MauticGateway = Depends(_gateway),
    c: Container = Depends(get_container),
) -> EmailOut:
    draft = await PushEmail(uow, gateway, c.settings.mautic_enabled).execute(EmailRef(principal, email_id))
    return EmailOut.of(draft)


@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    principal: Principal = Depends(get_principal), uow: SqlMarketingUnitOfWork = Depends(_uow)
) -> list[CampaignOut]:
    return [CampaignOut.of(x) for x in await ListCampaigns(uow).execute(principal)]


@router.post("/campaigns/plan", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def plan_campaign(
    body: PlanCampaignIn,
    principal: Principal = Depends(get_principal),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> CampaignOut:
    campaign = await PlanCampaign(uow, c.llm).execute(
        PlanCampaignCommand(principal, body.objective, body.duration_days, body.segment_id)
    )
    return CampaignOut.of(campaign)


@router.post("/campaigns/{campaign_id}/launch", response_model=CampaignOut)
async def launch_campaign(
    campaign_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
    gateway: MauticGateway = Depends(_gateway),
    c: Container = Depends(get_container),
) -> CampaignOut:
    campaign = await LaunchCampaign(uow, gateway, c.settings.mautic_enabled, c.llm).execute(
        CampaignRef(principal, campaign_id)
    )
    return CampaignOut.of(campaign)


def verify_mautic_signature(container: Container, body: bytes, signature: str | None) -> None:
    """Mautic 5 firma cada webhook: `Webhook-Signature = base64(HMAC-SHA256(cuerpo, secreto))`.

    El secreto es el del webhook en Mautic (configurado en ONEHEAVY_MAUTIC_WEBHOOK_SECRET).
    Se verifica sobre los bytes exactos recibidos, en tiempo constante. Sin secreto
    configurado sólo se acepta en local/test.
    """
    secret = container.settings.mautic_webhook_secret
    if secret is None:
        if container.settings.env in ("local", "test"):
            return
        raise AuthenticationError("Webhook de Mautic sin secreto configurado")
    expected = base64.b64encode(hmac.new(secret.get_secret_value().encode(), body, hashlib.sha256).digest())
    if not signature or not hmac.compare_digest(signature.strip().encode(), expected):
        raise AuthenticationError("Firma de webhook inválida")


@router.post("/webhooks/mautic")
async def mautic_webhook(
    request: Request,
    tenant_id: uuid.UUID | None = None,
    webhook_signature: str | None = Header(default=None, alias="Webhook-Signature"),
    uow: SqlMarketingUnitOfWork = Depends(_uow),
    c: Container = Depends(get_container),
) -> dict[str, Any]:
    body = await request.body()
    verify_mautic_signature(c, body, webhook_signature)
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise BusinessRuleViolation("Payload JSON inválido", code="invalid_payload") from exc
    if not isinstance(payload, dict):
        raise BusinessRuleViolation("Payload JSON inválido", code="invalid_payload")
    result = await HandleMauticWebhook(uow).execute(MauticWebhookCommand(payload, tenant_id))
    return {"ok": True, "processed": result.processed, "skipped": result.skipped}
