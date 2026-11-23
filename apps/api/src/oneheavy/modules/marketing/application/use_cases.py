"""Casos de uso de Marketing (Mautic + IA).

CU-MKT-01  Consultar estado de la integración con Mautic
CU-MKT-02  Listar segmentos (re-evaluados contra la audiencia)
CU-MKT-03  Crear segmento por filtros (etapa, tags, engagement mínimo)
CU-MKT-04  Sincronizar segmento con Mautic
CU-MKT-05  Listar emails
CU-MKT-06  Generar email con IA (copy de respuesta directa, HTML sanitizado)
CU-MKT-07  Publicar email en Mautic
CU-MKT-08  Listar campañas
CU-MKT-09  Planificar campaña multicanal con IA
CU-MKT-10  Lanzar campaña (Mautic si está habilitado) → CampaignLaunched
CU-MKT-11  Procesar webhook de Mautic → MarketingEngagementRecorded
CU-MKT-12  Proyectar contactos del CRM en la audiencia (ContactCreated / ContactLifecycleChanged)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from oneheavy.modules.marketing.application.ports import (
    MarketingUnitOfWork,
    MauticCampaignEmail,
    MauticContactData,
    MauticGateway,
)
from oneheavy.modules.marketing.domain.html import html_to_text, normalize_mautic_tokens, sanitize_html
from oneheavy.modules.marketing.domain.model import (
    ENGAGEMENT_POINTS,
    AudienceMember,
    Campaign,
    CampaignStep,
    Channel,
    EmailDraft,
    EngagementKind,
    Segment,
    SegmentFilters,
)
from oneheavy.shared.application.ports import LLMClient, LLMRequest
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import BusinessRuleViolation, DomainError, NotFoundError
from oneheavy.shared.domain.events import DomainEvent

log = logging.getLogger("oneheavy.marketing")


def _require_mautic(enabled: bool) -> None:
    if not enabled:
        raise BusinessRuleViolation(
            "Mautic no está habilitado para este entorno (ONEHEAVY_MAUTIC_ENABLED)", code="mautic_disabled"
        )


async def _segment_or_404(uow: MarketingUnitOfWork, tenant_id: uuid.UUID, segment_id: uuid.UUID) -> Segment:
    segment = await uow.segments.get(tenant_id, segment_id)
    if segment is None:
        raise NotFoundError("Segmento no encontrado")
    return segment


# ── CU-MKT-01 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MarketingStatus:
    mautic_enabled: bool
    connected: bool
    last_sync_at: datetime | None
    synced_contacts: int


class GetMarketingStatus(UseCase[Principal, MarketingStatus]):
    def __init__(self, uow: MarketingUnitOfWork, gateway: MauticGateway, enabled: bool) -> None:
        self.uow, self.gateway, self.enabled = uow, gateway, enabled

    async def execute(self, data: Principal) -> MarketingStatus:
        data.require(Permission.MARKETING_MANAGE)
        async with self.uow:
            audience = await self.uow.audience.list(data.tenant_id)
            segments = await self.uow.segments.list(data.tenant_id)
        sync_dates = [m.synced_at for m in audience if m.synced_at] + [
            s.synced_at for s in segments if s.synced_at
        ]
        connected = False
        if self.enabled:
            try:
                connected = await self.gateway.ping()
            except DomainError:
                connected = False
        return MarketingStatus(
            mautic_enabled=self.enabled,
            connected=connected,
            last_sync_at=max(sync_dates) if sync_dates else None,
            synced_contacts=sum(1 for m in audience if m.mautic_id),
        )


# ── CU-MKT-02..04 Segmentos ─────────────────────────────────────────────────


class ListSegments(UseCase[Principal, list[Segment]]):
    def __init__(self, uow: MarketingUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[Segment]:
        data.require(Permission.MARKETING_MANAGE)
        async with self.uow:
            audience = await self.uow.audience.list(data.tenant_id)
            segments = await self.uow.segments.list(data.tenant_id)
        for segment in segments:
            segment.evaluate(audience)  # conteo en vivo, no se persiste en lectura
        return segments


@dataclass(frozen=True)
class CreateSegmentCommand:
    actor: Principal
    name: str
    description: str | None
    filters: SegmentFilters


class CreateSegment(UseCase[CreateSegmentCommand, Segment]):
    def __init__(self, uow: MarketingUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: CreateSegmentCommand) -> Segment:
        data.actor.require(Permission.MARKETING_MANAGE)
        async with self.uow:
            segment = Segment(
                tenant_id=data.actor.tenant_id,
                name=data.name,
                description=data.description,
                filters=data.filters,
            )
            segment.evaluate(await self.uow.audience.list(data.actor.tenant_id))
            await self.uow.segments.save(segment)
            await self.uow.commit()
        return segment


@dataclass(frozen=True)
class SegmentRef:
    actor: Principal
    segment_id: uuid.UUID


class SyncSegment(UseCase[SegmentRef, Segment]):
    """Empuja a Mautic los contactos faltantes, crea el segmento y lo puebla."""

    def __init__(self, uow: MarketingUnitOfWork, gateway: MauticGateway, enabled: bool) -> None:
        self.uow, self.gateway, self.enabled = uow, gateway, enabled

    async def execute(self, data: SegmentRef) -> Segment:
        data.actor.require(Permission.MARKETING_MANAGE)
        _require_mautic(self.enabled)
        async with self.uow:
            segment = await _segment_or_404(self.uow, data.actor.tenant_id, data.segment_id)
            members = segment.evaluate(await self.uow.audience.list(data.actor.tenant_id))
            for member in members:
                if member.mautic_id is None:
                    mid = await self.gateway.upsert_contact(
                        MauticContactData(email=member.email, phone=member.phone, tags=member.tags)
                    )
                    member.link_mautic(mid)
                    await self.uow.audience.save(member)
            mautic_segment = segment.mautic_id or await self.gateway.create_segment(
                segment.name, segment.description
            )
            await self.gateway.add_contacts_to_segment(
                mautic_segment, [m.mautic_id for m in members if m.mautic_id]
            )
            segment.mark_synced(mautic_segment)
            await self.uow.segments.save(segment)
            await self.uow.commit()
        return segment


# ── CU-MKT-05..07 Emails con IA ─────────────────────────────────────────────


class ListEmails(UseCase[Principal, list[EmailDraft]]):
    def __init__(self, uow: MarketingUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[EmailDraft]:
        data.require(Permission.MARKETING_MANAGE)
        async with self.uow:
            return await self.uow.emails.list(data.tenant_id)


@dataclass(frozen=True)
class GenerateEmailCommand:
    actor: Principal
    goal: str
    audience: str
    tone: str | None = None
    language: str = "es"
    segment_id: uuid.UUID | None = None
    brand: str | None = None


EMAIL_SYSTEM_PROMPT = (
    "Eres un copywriter senior de respuesta directa para LATAM. Escribes emails que se leen en móvil: "
    "asunto ≤ 50 caracteres con curiosidad o beneficio concreto, preheader que complementa (no repite) el asunto, "
    "un solo objetivo y un solo CTA, párrafos de 1-3 líneas, prueba social o dato concreto, tono humano. "
    "Nunca prometas resultados garantizados ni uses MAYÚSCULAS sostenidas o spam words. "
    "El HTML es simple y compatible con clientes de correo: <p>, <strong>, <a>, <ul>/<li>, <h2>; sin <script> ni CSS externo. "
    'Incluye al final <p><a href="{unsubscribe_url}">Darme de baja</a></p>.'
)


class GenerateEmail(UseCase[GenerateEmailCommand, EmailDraft]):
    def __init__(self, uow: MarketingUnitOfWork, llm: LLMClient) -> None:
        self.uow, self.llm = uow, llm

    async def execute(self, data: GenerateEmailCommand) -> EmailDraft:
        data.actor.require(Permission.MARKETING_MANAGE)
        tenant = data.actor.tenant_id
        async with self.uow:
            segment = await _segment_or_404(self.uow, tenant, data.segment_id) if data.segment_id else None
            prompt = (
                f"Objetivo del email: {data.goal}\n"
                f"Audiencia: {data.audience}\n"
                + (
                    f"Segmento: {segment.name} ({segment.description or 'sin descripción'})\n"
                    if segment
                    else ""
                )
                + (f"Marca: {data.brand}\n" if data.brand else "")
                + f"Tono: {data.tone or 'cercano y profesional'}\nIdioma: {data.language}\n\n"
                "El email se envía con Mautic: para personalizar usa exactamente los tokens "
                "{contactfield=firstname} y {contactfield=company}; no uses otros marcadores.\n"
                'Devuelve JSON: {"subject": "...", "preheader": "...", "body_html": "...", "body_text": "..."}'
            )
            draft = await self._generate(prompt, data, tenant)
            await self.uow.emails.save(draft)
            await self.uow.commit()
        return draft

    async def _generate(self, prompt: str, data: GenerateEmailCommand, tenant: uuid.UUID) -> EmailDraft:
        try:
            raw = await self.llm.complete_json(
                LLMRequest(
                    prompt=prompt,
                    system=EMAIL_SYSTEM_PROMPT,
                    temperature=0.7,
                    max_tokens=1800,
                    metadata={"task": "marketing.email"},
                )
            )
            if isinstance(raw, dict):
                return EmailDraft.compose(
                    tenant_id=tenant,
                    subject=normalize_mautic_tokens(str(raw.get("subject") or "")),
                    preheader=normalize_mautic_tokens(str(raw.get("preheader") or "")),
                    body_html=normalize_mautic_tokens(str(raw.get("body_html") or "")),
                    body_text=normalize_mautic_tokens(str(raw.get("body_text") or "")) or None,
                    goal=data.goal,
                    segment_id=data.segment_id,
                )
        except (ValueError, DomainError):
            log.warning("marketing_email_llm_fallback")
        # Degradación elegante: plantilla base editable por el equipo.
        return EmailDraft.compose(
            tenant_id=tenant,
            subject=data.goal[:50],
            preheader=f"Pensado para {data.audience}"[:200],
            body_html=(
                f"<p>Hola {{contactfield=firstname}},</p><p>{data.goal}.</p>"
                '<p><a href="#">Quiero saber más</a></p>'
                '<p><a href="{unsubscribe_url}">Darme de baja</a></p>'
            ),
            body_text=None,
            goal=data.goal,
            segment_id=data.segment_id,
        )


@dataclass(frozen=True)
class EmailRef:
    actor: Principal
    email_id: uuid.UUID


class PushEmail(UseCase[EmailRef, EmailDraft]):
    def __init__(self, uow: MarketingUnitOfWork, gateway: MauticGateway, enabled: bool) -> None:
        self.uow, self.gateway, self.enabled = uow, gateway, enabled

    async def execute(self, data: EmailRef) -> EmailDraft:
        data.actor.require(Permission.MARKETING_MANAGE)
        _require_mautic(self.enabled)
        async with self.uow:
            draft = await self.uow.emails.get(data.actor.tenant_id, data.email_id)
            if draft is None:
                raise NotFoundError("Email no encontrado")
            segment_mautic = None
            if draft.segment_id:
                segment = await self.uow.segments.get(draft.tenant_id, draft.segment_id)
                segment_mautic = segment.mautic_id if segment else None
            mautic_id = await self.gateway.create_email(
                name=f"[1heavy] {draft.subject}",
                subject=draft.subject,
                html=draft.body_html,
                text=draft.body_text,
                segment_id=segment_mautic,
            )
            draft.mark_pushed(mautic_id)
            await self.uow.emails.save(draft)
            await self.uow.commit()
        return draft


# ── CU-MKT-08..10 Campañas ──────────────────────────────────────────────────


class ListCampaigns(UseCase[Principal, list[Campaign]]):
    def __init__(self, uow: MarketingUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> list[Campaign]:
        data.require(Permission.MARKETING_MANAGE)
        async with self.uow:
            return await self.uow.campaigns.list(data.tenant_id)


@dataclass(frozen=True)
class PlanCampaignCommand:
    actor: Principal
    objective: str
    duration_days: int
    segment_id: uuid.UUID | None = None


def default_plan(objective: str, duration_days: int) -> list[CampaignStep]:
    """Secuencia probada (bienvenida → valor → prueba social → oferta → último aviso)."""
    d = max(1, duration_days)
    blueprint = [
        (0, Channel.EMAIL, "Bienvenida y promesa", "Presentar la propuesta de valor"),
        (round(d * 0.2), Channel.EMAIL, "Contenido de valor", "Educar sobre el problema"),
        (round(d * 0.4), Channel.WHATSAPP, "Caso de éxito", "Prueba social"),
        (round(d * 0.7), Channel.EMAIL, f"Oferta: {objective[:40]}", "Llamado a la acción"),
        (d, Channel.EMAIL, "Último aviso", "Urgencia y cierre"),
    ]
    return [CampaignStep(day, ch, subject, intent) for day, ch, subject, intent in blueprint]


def parse_steps(raw: Any, duration_days: int) -> list[CampaignStep]:
    steps: list[CampaignStep] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            day = int(item.get("day", -1))
            channel = Channel(str(item.get("channel", "")).lower())
        except (TypeError, ValueError):
            continue
        subject = str(item.get("subject") or "").strip()
        intent = str(item.get("intent") or "").strip()
        if 0 <= day <= duration_days and subject and intent:
            steps.append(CampaignStep(day, channel, subject[:150], intent[:300]))
    return steps[:30]


class PlanCampaign(UseCase[PlanCampaignCommand, Campaign]):
    def __init__(self, uow: MarketingUnitOfWork, llm: LLMClient) -> None:
        self.uow, self.llm = uow, llm

    async def execute(self, data: PlanCampaignCommand) -> Campaign:
        data.actor.require(Permission.MARKETING_MANAGE)
        if not 1 <= data.duration_days <= 180:
            raise BusinessRuleViolation("La duración debe estar entre 1 y 180 días", code="invalid_duration")
        tenant = data.actor.tenant_id
        async with self.uow:
            segment = await _segment_or_404(self.uow, tenant, data.segment_id) if data.segment_id else None
            name, steps = await self._plan(data, segment)
            campaign = Campaign(
                tenant_id=tenant,
                name=name,
                objective=data.objective.strip(),
                steps=steps,
                segment_id=data.segment_id,
            )
            await self.uow.campaigns.save(campaign)
            await self.uow.commit()
        return campaign

    async def _plan(
        self, data: PlanCampaignCommand, segment: Segment | None
    ) -> tuple[str, list[CampaignStep]]:
        fallback_name = f"Campaña: {data.objective.strip()[:60]}"
        prompt = (
            f"Diseña una campaña de nurturing multicanal de {data.duration_days} días.\n"
            f"Objetivo: {data.objective}\n"
            + (f"Segmento: {segment.name} · filtros {segment.filters.as_dict()}\n" if segment else "")
            + "Canales permitidos: email, whatsapp, ads. Entre 4 y 10 pasos, con escalamiento de intensidad.\n"
            'Devuelve JSON: {"name": "...", "steps": [{"day": 0, "channel": "email", "subject": "...", "intent": "..."}]}'
        )
        try:
            raw = await self.llm.complete_json(
                LLMRequest(
                    prompt=prompt, temperature=0.5, max_tokens=1200, metadata={"task": "marketing.campaign"}
                )
            )
            if isinstance(raw, dict):
                steps = parse_steps(raw.get("steps"), data.duration_days)
                if steps:
                    return (str(raw.get("name") or "").strip()[:120] or fallback_name), steps
        except (ValueError, DomainError):
            log.warning("marketing_campaign_llm_fallback")
        return fallback_name, default_plan(data.objective, data.duration_days)


@dataclass(frozen=True)
class CampaignRef:
    actor: Principal
    campaign_id: uuid.UUID


class LaunchCampaign(UseCase[CampaignRef, Campaign]):
    """Lanza la campaña. Con Mautic activo la crea de verdad:

    1. Claude redacta, en paralelo, el email de cada paso de canal email.
    2. Se crean como emails publicados (plantillas) en Mautic.
    3. Se crea la campaña con un paso por email en su día y se publica.
    Los pasos de WhatsApp/anuncios no son de Mautic: quedan en la descripción.
    """

    def __init__(
        self, uow: MarketingUnitOfWork, gateway: MauticGateway, enabled: bool, llm: LLMClient | None = None
    ) -> None:
        self.uow, self.gateway, self.enabled, self.llm = uow, gateway, enabled, llm

    async def execute(self, data: CampaignRef) -> Campaign:
        data.actor.require(Permission.MARKETING_MANAGE)
        async with self.uow:
            campaign = await self.uow.campaigns.get(data.actor.tenant_id, data.campaign_id)
            if campaign is None:
                raise NotFoundError("Campaña no encontrada")
            mautic_id = campaign.mautic_id
            if self.enabled and mautic_id is None:
                mautic_id = await self._build_in_mautic(campaign)
            if self.enabled and mautic_id is not None:
                await self.gateway.publish_campaign(mautic_id)
            campaign.launch(actor_id=data.actor.user_id, mautic_id=mautic_id)
            await self.uow.campaigns.save(campaign)
            self.uow.collect(campaign.pull_events())
            await self.uow.commit()
        return campaign

    async def _build_in_mautic(self, campaign: Campaign) -> int:
        email_steps = [s for s in campaign.steps if s.channel is Channel.EMAIL]
        if not email_steps:
            raise BusinessRuleViolation(
                "Mautic necesita al menos un paso de email en la campaña", code="campaign_without_email"
            )
        segment_mautic = None
        if campaign.segment_id:
            segment = await self.uow.segments.get(campaign.tenant_id, campaign.segment_id)
            segment_mautic = segment.mautic_id if segment else None
        contents = await asyncio.gather(*(self._write(campaign, step) for step in email_steps))
        mautic_emails = []
        for step, (subject, html, text) in zip(email_steps, contents, strict=True):
            email_id = await self.gateway.create_email(
                name=f"{campaign.name} · día {step.day}",
                subject=subject,
                html=html,
                text=text,
                published=True,
            )
            mautic_emails.append(
                MauticCampaignEmail(day=step.day, name=f"Día {step.day} · {subject}", email_id=email_id)
            )
        others = [
            f"día {s.day} · {s.channel.value}: {s.subject}"
            for s in campaign.steps
            if s.channel is not Channel.EMAIL
        ]
        description = campaign.objective + (
            f"\n\nPasos fuera de Mautic: {'; '.join(others)}" if others else ""
        )
        return await self.gateway.create_campaign(
            name=campaign.name, description=description, emails=mautic_emails, segment_id=segment_mautic
        )

    async def _write(self, campaign: Campaign, step: CampaignStep) -> tuple[str, str, str]:
        """Redacta un email del plan; si la IA falla usa una plantilla editable."""
        if self.llm is not None:
            prompt = (
                f"Campaña: {campaign.name}\nObjetivo: {campaign.objective}\n"
                f"Paso del día {step.day}. Asunto propuesto: {step.subject}\nIntención del email: {step.intent}\n\n"
                "El email se envía con Mautic: para personalizar usa exactamente {contactfield=firstname} "
                "y {contactfield=company}.\n"
                'Devuelve JSON: {"subject": "...", "body_html": "..."}'
            )
            try:
                raw = await self.llm.complete_json(
                    LLMRequest(
                        prompt=prompt,
                        system=EMAIL_SYSTEM_PROMPT,
                        max_tokens=1500,
                        metadata={"task": "marketing.campaign_email"},
                    )
                )
                if isinstance(raw, dict) and raw.get("body_html"):
                    html = sanitize_html(normalize_mautic_tokens(str(raw["body_html"])))
                    subject = normalize_mautic_tokens(str(raw.get("subject") or step.subject))[:190]
                    return subject, html, html_to_text(html)
            except (ValueError, DomainError):
                log.warning("marketing_campaign_email_fallback", extra={"day": step.day})
        html = sanitize_html(
            f"<p>Hola {{contactfield=firstname}},</p><p>{step.intent}</p>"
            '<p><a href="{unsubscribe_url}">Darme de baja</a></p>'
        )
        return step.subject[:190], html, html_to_text(html)


# ── CU-MKT-11 Webhook de Mautic ─────────────────────────────────────────────

# Eventos reales de Mautic 5 (verificados contra una instancia real). Mautic no
# tiene "email_on_click": los clics en emails llegan como page_on_hit con `hit.email`.
MAUTIC_EVENT_MAP: dict[str, EngagementKind] = {
    "mautic.email_on_open": EngagementKind.EMAIL_OPEN,
    "mautic.form_on_submit": EngagementKind.FORM_SUBMIT,
    "mautic.page_on_hit": EngagementKind.PAGE_HIT,
}


def _container(item: dict[str, Any]) -> dict[str, Any]:
    for key in ("stat", "submission", "hit"):
        nested = item.get(key)
        if isinstance(nested, dict):
            return nested
    return item


def _extract_lead(item: dict[str, Any]) -> dict[str, Any]:
    lead = _container(item).get("lead") or item.get("lead") or item.get("contact")
    return dict(lead) if isinstance(lead, dict) else {}


def _extract_email(item: dict[str, Any], lead: dict[str, Any]) -> str | None:
    """El email viaja en lugares distintos según el evento (formatos reales de Mautic 5):
    apertura → stat.emailAddress · formulario → submission.results.email (el contacto
    puede llegar aún anónimo) · resto → campos del contacto."""
    box = _container(item)
    fields = lead.get("fields") or {}
    core = fields.get("core") if isinstance(fields, dict) else None
    candidates = [
        box.get("emailAddress"),
        (box.get("results") or {}).get("email") if isinstance(box.get("results"), dict) else None,
        lead.get("email"),
        ((core or {}).get("email") or {}).get("value") if isinstance(core, dict) else None,
        (fields.get("all") or {}).get("email") if isinstance(fields, dict) else None,
    ]
    email = next((c for c in candidates if isinstance(c, str) and "@" in c), None)
    return email.strip().lower() if email else None


def _kind(event: str, item: dict[str, Any]) -> EngagementKind:
    if event == "mautic.page_on_hit" and _container(item).get("email"):
        return EngagementKind.EMAIL_CLICK  # visita que viene de un enlace de email
    return MAUTIC_EVENT_MAP[event]


@dataclass(frozen=True)
class MauticWebhookCommand:
    payload: dict[str, Any]
    tenant_hint: uuid.UUID | None = None


@dataclass(frozen=True)
class WebhookResult:
    processed: int
    skipped: int


class HandleMauticWebhook(UseCase[MauticWebhookCommand, WebhookResult]):
    def __init__(self, uow: MarketingUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: MauticWebhookCommand) -> WebhookResult:
        processed = skipped = 0
        async with self.uow:
            for key in MAUTIC_EVENT_MAP:
                items = data.payload.get(key) or []
                for item in [items] if isinstance(items, dict) else items:
                    if not isinstance(item, dict):
                        skipped += 1
                        continue
                    kind = _kind(key, item)
                    lead = _extract_lead(item)
                    email = _extract_email(item, lead)
                    lead_id = int(lead["id"]) if str(lead.get("id", "")).isdigit() else None
                    member = (
                        await self.uow.audience.find_by_mautic_id(lead_id) if lead_id is not None else None
                    )
                    if member is None and email and data.tenant_hint:
                        member = await self.uow.audience.find_by_email(data.tenant_hint, email)
                    if member is None:
                        skipped += 1
                        continue
                    events: list[DomainEvent] = []
                    if lead_id is not None and member.mautic_id != lead_id:
                        # Mautic fusiona contactos duplicados y cambia el id: se re-vincula.
                        member.link_mautic(lead_id)
                        events.append(
                            ie.MarketingContactSynced(
                                tenant_id=member.tenant_id, contact_id=member.contact_id, mautic_id=lead_id
                            )
                        )
                    points = ENGAGEMENT_POINTS[kind]
                    member.engage(points)
                    await self.uow.audience.save(member)
                    events.append(
                        ie.MarketingEngagementRecorded(
                            tenant_id=member.tenant_id,
                            contact_id=member.contact_id,
                            email=member.email or email,
                            kind=kind.value,
                            points=points,
                        )
                    )
                    self.uow.collect(events)
                    processed += 1
            await self.uow.commit()
        return WebhookResult(processed, skipped)


# ── CU-MKT-12 Proyección de la audiencia ────────────────────────────────────


class ProjectContactCreated(UseCase[ie.ContactCreated, AudienceMember]):
    def __init__(self, uow: MarketingUnitOfWork, gateway: MauticGateway, enabled: bool) -> None:
        self.uow, self.gateway, self.enabled = uow, gateway, enabled

    async def execute(self, data: ie.ContactCreated) -> AudienceMember:
        async with self.uow:
            member = await self.uow.audience.get_by_contact(data.tenant_id, data.contact_id)
            if member is None:
                member = AudienceMember(
                    tenant_id=data.tenant_id,
                    contact_id=data.contact_id,
                    stage=data.stage,
                )
            member.email = data.email.lower() if data.email else member.email
            member.phone = data.phone or member.phone
            member.tags = sorted({*member.tags, *data.tags, f"source:{data.source}"})
            if self.enabled and member.mautic_id is None and (member.email or member.phone):
                try:
                    mid = await self.gateway.upsert_contact(
                        MauticContactData(
                            email=member.email,
                            phone=member.phone,
                            first_name=data.first_name,
                            last_name=data.last_name,
                            tags=member.tags,
                        )
                    )
                    member.link_mautic(mid)
                    self.uow.collect(
                        [
                            ie.MarketingContactSynced(
                                tenant_id=data.tenant_id, contact_id=data.contact_id, mautic_id=mid
                            )
                        ]
                    )
                except DomainError:
                    # El espejo se guarda igual; el próximo sync de segmento reintenta.
                    log.warning("mautic_upsert_failed", extra={"contact_id": str(data.contact_id)})
            await self.uow.audience.save(member)
            await self.uow.commit()
        return member


class ProjectLifecycleChanged(UseCase[ie.ContactLifecycleChanged, AudienceMember]):
    def __init__(self, uow: MarketingUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ie.ContactLifecycleChanged) -> AudienceMember:
        async with self.uow:
            member = await self.uow.audience.get_by_contact(data.tenant_id, data.contact_id)
            if member is None:
                member = AudienceMember(tenant_id=data.tenant_id, contact_id=data.contact_id)
            member.stage = data.to_stage
            member.touch()
            await self.uow.audience.save(member)
            await self.uow.commit()
        return member
