"""Casos de uso del CRM.

CU-CRM-01  Crear contacto (con deduplicación por email/teléfono)
CU-CRM-02  Buscar contactos (paginado, filtros)
CU-CRM-03  Consultar contacto
CU-CRM-04  Actualizar contacto
CU-CRM-05  Cambiar etapa del ciclo de vida
CU-CRM-06  Consultar timeline
CU-CRM-07  Registrar actividad
CU-CRM-08  Insight IA del contacto (score, temperatura, siguiente mejor acción)
CU-CRM-09  Importar contactos
CU-CRM-10  Consultar pipeline
CU-CRM-11  Crear negocio
CU-CRM-12  Editar negocio
CU-CRM-13  Mover negocio de etapa (won/lost)
CU-CRM-14  Capturar lead entrante (evento LeadCaptured de Meta/WhatsApp/web)
CU-CRM-15  Registrar engagement de marketing (evento MarketingEngagementRecorded)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from oneheavy.modules.crm.application.ports import CrmUnitOfWork
from oneheavy.modules.crm.domain.model import (
    PIPELINE,
    Activity,
    ActivityKind,
    Contact,
    ContactSource,
    Deal,
    DealStage,
    LifecycleStage,
)
from oneheavy.modules.crm.domain.repositories import ContactQuery
from oneheavy.modules.crm.domain.scoring import RuleBasedScoringPolicy, ScoringPolicy
from oneheavy.shared.application.ports import LLMClient, LLMRequest
from oneheavy.shared.application.use_case import UseCase
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.access import Permission, Principal
from oneheavy.shared.domain.errors import BusinessRuleViolation, ConflictError, DomainError, NotFoundError
from oneheavy.shared.domain.value_objects import Email, PhoneNumber

log = logging.getLogger("oneheavy.crm")


async def _get_contact(uow: CrmUnitOfWork, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
    contact = await uow.contacts.get(tenant_id, contact_id)
    if contact is None:
        raise NotFoundError("Contacto no encontrado")
    return contact


def _rescore(contact: Contact, policy: ScoringPolicy) -> None:
    contact.apply_score(policy.score(contact).score)


def _email(value: str | None) -> Email | None:
    return Email(value) if value else None


def _phone(value: str | None) -> PhoneNumber | None:
    return PhoneNumber(value) if value else None


# ── CU-CRM-01 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContactData:
    first_name: str
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    job_title: str | None = None
    source: ContactSource = ContactSource.MANUAL
    tags: list[str] = field(default_factory=list)
    owner_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CreateContactCommand:
    actor: Principal
    data: ContactData


class CreateContact(UseCase[CreateContactCommand, Contact]):
    def __init__(self, uow: CrmUnitOfWork, policy: ScoringPolicy | None = None) -> None:
        self.uow, self.policy = uow, policy or RuleBasedScoringPolicy()

    async def execute(self, data: CreateContactCommand) -> Contact:
        data.actor.require(Permission.CONTACTS_MANAGE)
        d = data.data
        email, phone = _email(d.email), _phone(d.phone)
        async with self.uow:
            duplicate = await self.uow.contacts.find_duplicate(
                data.actor.tenant_id, email.value if email else None, phone.value if phone else None
            )
            if duplicate is not None:
                raise ConflictError(
                    f"Ya existe un contacto con ese email o teléfono ({duplicate.id})",
                    code="duplicate_contact",
                )
            contact = Contact.create(
                tenant_id=data.actor.tenant_id,
                first_name=d.first_name,
                last_name=d.last_name,
                email=email,
                phone=phone,
                company=d.company,
                job_title=d.job_title,
                source=d.source,
                tags=d.tags,
                owner_id=d.owner_id,
                actor_id=data.actor.user_id,
            )
            _rescore(contact, self.policy)
            await self.uow.contacts.add(contact)
            await self.uow.activities.add(
                Activity(
                    tenant_id=contact.tenant_id,
                    contact_id=contact.id,
                    kind=ActivityKind.SYSTEM,
                    summary=f"Contacto creado (fuente: {contact.source.value})",
                    actor_id=data.actor.user_id,
                )
            )
            self.uow.collect(contact.pull_events())
            await self.uow.commit()
        return contact


# ── CU-CRM-02 / 03 ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SearchContactsQuery:
    actor: Principal
    q: str | None = None
    stage: LifecycleStage | None = None
    tag: str | None = None
    owner_id: uuid.UUID | None = None
    page: int = 1
    size: int = 25


@dataclass(frozen=True)
class ContactPage:
    items: list[Contact]
    total: int
    page: int
    size: int


class SearchContacts(UseCase[SearchContactsQuery, ContactPage]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: SearchContactsQuery) -> ContactPage:
        data.actor.require(Permission.CONTACTS_READ)
        page, size = max(1, data.page), max(1, min(100, data.size))
        async with self.uow:
            items, total = await self.uow.contacts.search(
                ContactQuery(
                    tenant_id=data.actor.tenant_id,
                    q=(data.q or "").strip() or None,
                    stage=data.stage,
                    tag=(data.tag or "").strip().lower() or None,
                    owner_id=data.owner_id,
                    page=page,
                    size=size,
                )
            )
        return ContactPage(items, total, page, size)


@dataclass(frozen=True)
class ContactRef:
    actor: Principal
    contact_id: uuid.UUID


class GetContact(UseCase[ContactRef, Contact]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ContactRef) -> Contact:
        data.actor.require(Permission.CONTACTS_READ)
        async with self.uow:
            return await _get_contact(self.uow, data.actor.tenant_id, data.contact_id)


# ── CU-CRM-04 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UpdateContactCommand:
    actor: Principal
    contact_id: uuid.UUID
    changes: dict[str, Any]


class UpdateContact(UseCase[UpdateContactCommand, Contact]):
    def __init__(self, uow: CrmUnitOfWork, policy: ScoringPolicy | None = None) -> None:
        self.uow, self.policy = uow, policy or RuleBasedScoringPolicy()

    async def execute(self, data: UpdateContactCommand) -> Contact:
        data.actor.require(Permission.CONTACTS_MANAGE)
        ch = data.changes
        email = _email(ch.get("email")) if "email" in ch else None
        phone = _phone(ch.get("phone")) if "phone" in ch else None
        async with self.uow:
            contact = await _get_contact(self.uow, data.actor.tenant_id, data.contact_id)
            if email or phone:
                dup = await self.uow.contacts.find_duplicate(
                    contact.tenant_id,
                    email.value if email else None,
                    phone.value if phone else None,
                    exclude=contact.id,
                )
                if dup is not None:
                    raise ConflictError("Otro contacto ya usa ese email o teléfono", code="duplicate_contact")
            source = ch.get("source")
            contact.update_profile(
                first_name=ch.get("first_name"),
                last_name=ch.get("last_name"),
                email=email,
                phone=phone,
                company=ch.get("company"),
                job_title=ch.get("job_title"),
                tags=ch.get("tags"),
                owner_id=ch.get("owner_id"),
                source=ContactSource(source) if source else None,
            )
            _rescore(contact, self.policy)
            await self.uow.contacts.update(contact)
            self.uow.collect(contact.pull_events())
            await self.uow.commit()
        return contact


# ── CU-CRM-05 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ChangeStageCommand:
    actor: Principal
    contact_id: uuid.UUID
    stage: LifecycleStage


class ChangeContactStage(UseCase[ChangeStageCommand, Contact]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ChangeStageCommand) -> Contact:
        data.actor.require(Permission.CONTACTS_MANAGE)
        async with self.uow:
            contact = await _get_contact(self.uow, data.actor.tenant_id, data.contact_id)
            previous = contact.stage
            contact.move_to(data.stage, actor_id=data.actor.user_id)
            if previous != contact.stage:
                await self.uow.activities.add(
                    Activity(
                        tenant_id=contact.tenant_id,
                        contact_id=contact.id,
                        kind=ActivityKind.SYSTEM,
                        summary=f"Etapa: {previous.value} → {contact.stage.value}",
                        actor_id=data.actor.user_id,
                    )
                )
            await self.uow.contacts.update(contact)
            self.uow.collect(contact.pull_events())
            await self.uow.commit()
        return contact


# ── CU-CRM-06 / 07 ──────────────────────────────────────────────────────────


class GetTimeline(UseCase[ContactRef, list[Activity]]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: ContactRef) -> list[Activity]:
        data.actor.require(Permission.CONTACTS_READ)
        async with self.uow:
            await _get_contact(self.uow, data.actor.tenant_id, data.contact_id)
            return await self.uow.activities.list_for_contact(data.actor.tenant_id, data.contact_id)


@dataclass(frozen=True)
class LogActivityCommand:
    actor: Principal
    contact_id: uuid.UUID
    kind: ActivityKind
    summary: str


class LogActivity(UseCase[LogActivityCommand, Activity]):
    def __init__(self, uow: CrmUnitOfWork, policy: ScoringPolicy | None = None) -> None:
        self.uow, self.policy = uow, policy or RuleBasedScoringPolicy()

    async def execute(self, data: LogActivityCommand) -> Activity:
        data.actor.require(Permission.CONTACTS_MANAGE)
        async with self.uow:
            contact = await _get_contact(self.uow, data.actor.tenant_id, data.contact_id)
            activity = Activity(
                tenant_id=contact.tenant_id,
                contact_id=contact.id,
                kind=data.kind,
                summary=data.summary,
                actor_id=data.actor.user_id,
            )
            contact.register_activity(activity.occurred_at)
            _rescore(contact, self.policy)
            await self.uow.activities.add(activity)
            await self.uow.contacts.update(contact)
            self.uow.collect(contact.pull_events())
            await self.uow.commit()
        return activity


# ── CU-CRM-08 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContactInsight:
    score: int
    temperature: str
    explanation: str
    next_best_action: str
    source: str  # "ai" | "rules"


_NEXT_ACTION: dict[LifecycleStage, str] = {
    LifecycleStage.SUBSCRIBER: "Nutrir con contenido educativo y una oferta de bajo compromiso.",
    LifecycleStage.LEAD: "Enviar caso de éxito y proponer una llamada de diagnóstico.",
    LifecycleStage.MQL: "Asignar a ventas y contactar por WhatsApp en menos de 24 horas.",
    LifecycleStage.SQL: "Agendar demo y preparar propuesta personalizada.",
    LifecycleStage.OPPORTUNITY: "Resolver objeciones y fijar fecha de cierre.",
    LifecycleStage.CUSTOMER: "Onboarding y solicitud de referido a los 30 días.",
    LifecycleStage.EVANGELIST: "Invitar al programa de referidos y pedir testimonio.",
    LifecycleStage.LOST: "Campaña de reactivación en 60 días con una nueva oferta.",
}


def temperature_for(score: int) -> str:
    return "hot" if score >= 65 else "warm" if score >= 35 else "cold"


class GetContactInsight(UseCase[ContactRef, ContactInsight]):
    """Combina el score determinista con la narrativa del LLM.

    El LLM nunca decide el score; si responde basura o falla, se usa la
    explicación basada en reglas (degradación elegante).
    """

    def __init__(self, uow: CrmUnitOfWork, llm: LLMClient, policy: ScoringPolicy | None = None) -> None:
        self.uow, self.llm, self.policy = uow, llm, policy or RuleBasedScoringPolicy()

    async def execute(self, data: ContactRef) -> ContactInsight:
        data.actor.require(Permission.CONTACTS_READ)
        async with self.uow:
            contact = await _get_contact(self.uow, data.actor.tenant_id, data.contact_id)
            activities = await self.uow.activities.list_for_contact(contact.tenant_id, contact.id, limit=15)
        result = self.policy.score(contact)
        fallback = ContactInsight(
            score=result.score,
            temperature=temperature_for(result.score),
            explanation=result.explain(),
            next_best_action=_NEXT_ACTION[contact.stage],
            source="rules",
        )
        timeline = "\n".join(f"- {a.occurred_at:%Y-%m-%d} [{a.kind.value}] {a.summary}" for a in activities)
        prompt = (
            "Analiza este contacto de CRM y explica su nivel de interés de compra.\n"
            f"Nombre: {contact.full_name}\nEmpresa: {contact.company or '-'} · Cargo: {contact.job_title or '-'}\n"
            f"Fuente: {contact.source.value} · Etapa: {contact.stage.value} · Tags: {', '.join(contact.tags) or '-'}\n"
            f"Score calculado: {result.score}/100 · Desglose: {result.breakdown}\n"
            f"Actividad reciente:\n{timeline or '- sin actividad'}\n\n"
            'Devuelve JSON: {"temperature": "cold|warm|hot", "explanation": "2-3 frases", '
            '"next_best_action": "una acción concreta, canal y momento"}'
        )
        try:
            raw = await self.llm.complete_json(
                LLMRequest(
                    prompt=prompt, temperature=0.3, max_tokens=500, metadata={"task": "crm.contact_insight"}
                )
            )
            if not isinstance(raw, dict):
                return fallback
            temperature = str(raw.get("temperature", "")).lower()
            explanation = str(raw.get("explanation") or "").strip()
            action = str(raw.get("next_best_action") or "").strip()
            if temperature not in {"cold", "warm", "hot"} or not explanation or not action:
                return fallback
            return ContactInsight(result.score, temperature, explanation, action, source="ai")
        except (ValueError, DomainError):
            log.warning("crm_insight_fallback", extra={"contact_id": str(contact.id)})
            return fallback


# ── CU-CRM-09 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ImportContactsCommand:
    actor: Principal
    contacts: list[ContactData]


@dataclass(frozen=True)
class ImportResult:
    created: int
    merged: int
    skipped: int


class ImportContacts(UseCase[ImportContactsCommand, ImportResult]):
    MAX_BATCH = 5000

    def __init__(self, uow: CrmUnitOfWork, policy: ScoringPolicy | None = None) -> None:
        self.uow, self.policy = uow, policy or RuleBasedScoringPolicy()

    async def execute(self, data: ImportContactsCommand) -> ImportResult:
        data.actor.require(Permission.CONTACTS_MANAGE)
        if len(data.contacts) > self.MAX_BATCH:
            raise BusinessRuleViolation(
                f"Máximo {self.MAX_BATCH} contactos por importación", code="batch_too_large"
            )
        created = merged = skipped = 0
        tenant = data.actor.tenant_id
        async with self.uow:
            for d in data.contacts:
                try:
                    email, phone = _email(d.email), _phone(d.phone)
                    dup = await self.uow.contacts.find_duplicate(
                        tenant, email.value if email else None, phone.value if phone else None
                    )
                    if dup is not None:
                        dup.merge_missing(
                            last_name=d.last_name,
                            email=email,
                            phone=phone,
                            company=d.company,
                            job_title=d.job_title,
                            tags=d.tags,
                        )
                        _rescore(dup, self.policy)
                        await self.uow.contacts.update(dup)
                        self.uow.collect(dup.pull_events())
                        merged += 1
                        continue
                    contact = Contact.create(
                        tenant_id=tenant,
                        first_name=d.first_name,
                        last_name=d.last_name,
                        email=email,
                        phone=phone,
                        company=d.company,
                        job_title=d.job_title,
                        source=ContactSource.IMPORT if d.source is ContactSource.MANUAL else d.source,
                        tags=d.tags,
                        owner_id=d.owner_id,
                        actor_id=data.actor.user_id,
                    )
                    _rescore(contact, self.policy)
                    await self.uow.contacts.add(contact)
                    self.uow.collect(contact.pull_events())
                    created += 1
                except BusinessRuleViolation:
                    skipped += 1
            await self.uow.commit()
        return ImportResult(created, merged, skipped)


# ── CU-CRM-10..13 Pipeline ──────────────────────────────────────────────────


@dataclass(frozen=True)
class DealView:
    deal: Deal
    contact_name: str | None


@dataclass(frozen=True)
class PipelineView:
    stages: tuple[Any, ...]
    deals: list[DealView]


class GetPipeline(UseCase[Principal, PipelineView]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: Principal) -> PipelineView:
        data.require(Permission.CONTACTS_READ)
        async with self.uow:
            deals = await self.uow.deals.list(data.tenant_id)
            contacts = await self.uow.contacts.get_many(
                data.tenant_id, {d.contact_id for d in deals if d.contact_id}
            )
        views = [
            DealView(
                d, contacts[d.contact_id].full_name if d.contact_id and d.contact_id in contacts else None
            )
            for d in deals
        ]
        return PipelineView(PIPELINE, views)


@dataclass(frozen=True)
class CreateDealCommand:
    actor: Principal
    title: str
    amount: Decimal
    currency: str = "COP"
    contact_id: uuid.UUID | None = None
    stage: DealStage | None = None
    owner_id: uuid.UUID | None = None
    expected_close: date | None = None


async def _deal_view(uow: CrmUnitOfWork, deal: Deal) -> DealView:
    name = None
    if deal.contact_id:
        contact = await uow.contacts.get(deal.tenant_id, deal.contact_id)
        name = contact.full_name if contact else None
    return DealView(deal, name)


async def _promote_contact_on_win(uow: CrmUnitOfWork, deal: Deal, actor_id: uuid.UUID) -> None:
    """Regla: ganar un negocio convierte al contacto en cliente (si la transición es válida)."""
    if deal.stage is not DealStage.WON or deal.contact_id is None:
        return
    contact = await uow.contacts.get(deal.tenant_id, deal.contact_id)
    if contact is None:
        return
    for step in (LifecycleStage.OPPORTUNITY, LifecycleStage.CUSTOMER):
        if contact.stage is not LifecycleStage.CUSTOMER and contact.can_move_to(step):
            contact.move_to(step, actor_id=actor_id)
    await uow.contacts.update(contact)
    uow.collect(contact.pull_events())


class CreateDeal(UseCase[CreateDealCommand, DealView]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: CreateDealCommand) -> DealView:
        data.actor.require(Permission.DEALS_MANAGE)
        async with self.uow:
            if data.contact_id:
                await _get_contact(self.uow, data.actor.tenant_id, data.contact_id)
            deal = Deal.open(
                tenant_id=data.actor.tenant_id,
                title=data.title,
                amount=data.amount,
                currency=data.currency,
                contact_id=data.contact_id,
                owner_id=data.owner_id or data.actor.user_id,
                expected_close=data.expected_close,
            )
            if data.stage:
                deal.move(data.stage, actor_id=data.actor.user_id)
            await self.uow.deals.add(deal)
            await _promote_contact_on_win(self.uow, deal, data.actor.user_id)
            self.uow.collect(deal.pull_events())
            view = await _deal_view(self.uow, deal)
            await self.uow.commit()
        return view


@dataclass(frozen=True)
class UpdateDealCommand:
    actor: Principal
    deal_id: uuid.UUID
    changes: dict[str, Any]


class UpdateDeal(UseCase[UpdateDealCommand, DealView]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: UpdateDealCommand) -> DealView:
        data.actor.require(Permission.DEALS_MANAGE)
        ch = data.changes
        async with self.uow:
            deal = await self.uow.deals.get(data.actor.tenant_id, data.deal_id)
            if deal is None:
                raise NotFoundError("Negocio no encontrado")
            if ch.get("contact_id"):
                await _get_contact(self.uow, deal.tenant_id, ch["contact_id"])
            deal.edit(
                title=ch.get("title"),
                amount=ch.get("amount"),
                currency=ch.get("currency"),
                contact_id=ch.get("contact_id"),
                owner_id=ch.get("owner_id"),
                expected_close=ch.get("expected_close"),
            )
            if ch.get("stage"):
                deal.move(DealStage(ch["stage"]), actor_id=data.actor.user_id)
                await _promote_contact_on_win(self.uow, deal, data.actor.user_id)
            await self.uow.deals.update(deal)
            self.uow.collect(deal.pull_events())
            view = await _deal_view(self.uow, deal)
            await self.uow.commit()
        return view


@dataclass(frozen=True)
class MoveDealCommand:
    actor: Principal
    deal_id: uuid.UUID
    stage: DealStage


class MoveDeal(UseCase[MoveDealCommand, DealView]):
    def __init__(self, uow: CrmUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, data: MoveDealCommand) -> DealView:
        data.actor.require(Permission.DEALS_MANAGE)
        async with self.uow:
            deal = await self.uow.deals.get(data.actor.tenant_id, data.deal_id)
            if deal is None:
                raise NotFoundError("Negocio no encontrado")
            deal.move(data.stage, actor_id=data.actor.user_id)
            await self.uow.deals.update(deal)
            await _promote_contact_on_win(self.uow, deal, data.actor.user_id)
            self.uow.collect(deal.pull_events())
            view = await _deal_view(self.uow, deal)
            await self.uow.commit()
        return view


# ── CU-CRM-14 / 15 (reacciones a eventos de integración) ────────────────────

LEAD_ENGAGEMENT_POINTS = 5


def _split_name(full_name: str | None) -> tuple[str, str | None]:
    parts = (full_name or "").strip().split(maxsplit=1)
    if not parts:
        return "Lead", None
    return parts[0], parts[1] if len(parts) > 1 else None


def _safe_vo[T](factory: type[T], value: str | None) -> T | None:
    if not value:
        return None
    try:
        return factory(value)  # type: ignore[call-arg]
    except BusinessRuleViolation:
        return None


class CaptureLead(UseCase[ie.LeadCaptured, Contact | None]):
    """Crea o fusiona el contacto de un lead entrante y deja trazabilidad en el timeline."""

    def __init__(self, uow: CrmUnitOfWork, policy: ScoringPolicy | None = None) -> None:
        self.uow, self.policy = uow, policy or RuleBasedScoringPolicy()

    async def execute(self, data: ie.LeadCaptured) -> Contact | None:
        email = _safe_vo(Email, data.email)
        phone = _safe_vo(PhoneNumber, data.phone)
        if email is None and phone is None:
            log.warning(
                "lead_without_contact_data", extra={"source": data.source, "external_id": data.external_id}
            )
            return None
        try:
            source = ContactSource(data.source)
        except ValueError:
            source = ContactSource.WEB_FORM
        first, last = _split_name(data.full_name)
        tags = [f"campaign:{data.campaign_ref}"] if data.campaign_ref else []
        async with self.uow:
            contact = await self.uow.contacts.find_duplicate(
                data.tenant_id, email.value if email else None, phone.value if phone else None
            )
            is_new = contact is None
            if contact is None:
                contact = Contact.create(
                    tenant_id=data.tenant_id,
                    first_name=first,
                    last_name=last,
                    email=email,
                    phone=phone,
                    source=source,
                    tags=tags,
                    actor_id=data.actor_id,
                )
            else:
                contact.merge_missing(last_name=last, email=email, phone=phone, tags=tags)
                if contact.stage is LifecycleStage.LOST:
                    contact.move_to(LifecycleStage.LEAD)
            contact.add_engagement(LEAD_ENGAGEMENT_POINTS, data.occurred_at)
            answers = "; ".join(f"{k}: {v}" for k, v in data.answers.items())
            summary = f"Lead capturado vía {data.source}" + (
                f" (campaña {data.campaign_ref})" if data.campaign_ref else ""
            )
            await self.uow.activities.add(
                Activity(
                    tenant_id=data.tenant_id,
                    contact_id=contact.id,
                    kind=ActivityKind.ADS
                    if source is ContactSource.META_LEAD_ADS
                    else ActivityKind.MARKETING,
                    summary=summary + (f" — {answers}" if answers else ""),
                    occurred_at=data.occurred_at,
                )
            )
            _rescore(contact, self.policy)
            if is_new:
                await self.uow.contacts.add(contact)
            else:
                await self.uow.contacts.update(contact)
            self.uow.collect(contact.pull_events())
            await self.uow.commit()
        return contact


_ENGAGEMENT_LABEL = {
    "email_open": "Abrió un email",
    "email_click": "Hizo clic en un email",
    "form_submit": "Envió un formulario",
    "page_hit": "Visitó una página",
}


class RecordEngagement(UseCase[ie.MarketingEngagementRecorded, Contact | None]):
    def __init__(self, uow: CrmUnitOfWork, policy: ScoringPolicy | None = None) -> None:
        self.uow, self.policy = uow, policy or RuleBasedScoringPolicy()

    async def execute(self, data: ie.MarketingEngagementRecorded) -> Contact | None:
        async with self.uow:
            contact = None
            if data.contact_id:
                contact = await self.uow.contacts.get(data.tenant_id, data.contact_id)
            if contact is None and data.email:
                email = _safe_vo(Email, data.email)
                if email:
                    contact = await self.uow.contacts.find_duplicate(data.tenant_id, email.value, None)
            if contact is None:
                return None
            contact.add_engagement(data.points, data.occurred_at)
            await self.uow.activities.add(
                Activity(
                    tenant_id=data.tenant_id,
                    contact_id=contact.id,
                    kind=ActivityKind.MARKETING,
                    summary=f"{_ENGAGEMENT_LABEL.get(data.kind, data.kind)} (+{data.points} pts)",
                    occurred_at=data.occurred_at,
                )
            )
            _rescore(contact, self.policy)
            await self.uow.contacts.update(contact)
            self.uow.collect(contact.pull_events())
            await self.uow.commit()
        return contact
