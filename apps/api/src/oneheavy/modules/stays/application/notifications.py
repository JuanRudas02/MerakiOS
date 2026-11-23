"""Servicio de notificaciones operativas por WhatsApp.

- Plantillas por workspace (`StaysSettings.templates`) con valores por defecto.
- Los fallos de envío se registran con traza completa y NO revierten el caso de uso
  (antes había `except: pass` silenciosos).
- Nunca se envían contraseñas por WhatsApp.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

from oneheavy.modules.stays.domain.model import (
    CleaningTask,
    Property,
    Service,
    StaffMember,
    StaysSettings,
)
from oneheavy.shared.application.ports import InteractiveButton, MessageSender

log = logging.getLogger("oneheavy.stays.notifications")


class _SafeDict(dict[str, object]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render(template: str, **values: object) -> str:
    """`str.format_map` tolerante: una variable desconocida no rompe el envío."""
    return template.format_map(_SafeDict(values))


DEFAULTS = {
    "task_assigned": (
        "✅ *NUEVA TAREA ASIGNADA*\n\n"
        "📍 *Unidad:* {property_name}\n"
        "⏰ *Fecha/Hora:* {date}\n"
        "🧳 *Equipaje:* {luggage}\n"
        "📝 *Obs:* {observations}\n\n"
        "🔗 *Acceso:* {login_url}\n\n"
        "Te pediremos confirmar tu llegada unos minutos antes. ¡Buen trabajo, {staff_name}!"
    ),
    "daily_summary": (
        "📅 *Recordatorio:* {staff_name}, mañana tienes {count} limpieza(s):\n{lines}\n\n"
        "*RECUERDA:* si faltan insumos (esponjas, toallas, etc.) avisa al supervisor de inmediato."
    ),
    "property_welcome": (
        "🏠 *¡Nueva unidad registrada!*\n\n"
        "Hola *{owner_name}*, su propiedad *{property_name}* quedó vinculada a nuestra operación.\n\n"
        "📍 *Fechas de corte configuradas:*\n{cutoffs}\n\n"
        "🔔 Recibirá un aviso automático *5 días antes* de cada fecha de corte."
    ),
    "billing_reminder": (
        "⏳ *RECORDATORIO DE PAGO*\n\n"
        "Hola *{owner_name}*, en *5 días* vence el recibo de *{service}* de la unidad *{property_name}*.\n"
        "Cuando pagues, adjunta el comprobante en la plataforma. ¡Gracias!"
    ),
    "billing_overdue": (
        "❌ *PAGO VENCIDO*\n\n"
        "*{owner_name}*, el recibo de *{service}* de la unidad *{property_name}* vence hoy y no tiene "
        "comprobante verificado.\n⚠️ Los avisos automáticos se pausarán hasta verificar el soporte."
    ),
    "escalation": "🚨 *ALERTA OPERATIVA*\n\n{message}",
}

LUGGAGE_LABELS = {"none": "Sin indicación", "leave": "Dejar equipaje", "collect": "Recoger equipaje"}


class StaysNotifier:
    def __init__(self, sender: MessageSender, *, login_url: str, tz: ZoneInfo) -> None:
        self._sender = sender
        self._login_url = login_url
        self._tz = tz

    def _fmt(self, dt: datetime, pattern: str = "%d/%m/%Y %H:%M") -> str:
        return dt.astimezone(self._tz).strftime(pattern)

    async def _send(self, to: str | None, message: str, settings: StaysSettings, *, kind: str) -> bool:
        if not to:
            log.warning("whatsapp_skipped_no_phone", extra={"kind": kind, "tenant": str(settings.tenant_id)})
            return False
        try:
            await self._sender.send_whatsapp(to, message, instance=settings.whatsapp_instance)
            return True
        except Exception:
            log.exception("whatsapp_send_failed", extra={"kind": kind, "tenant": str(settings.tenant_id)})
            return False

    async def task_assigned(
        self, task: CleaningTask, prop: Property, staff: StaffMember, settings: StaysSettings
    ) -> bool:
        message = render(
            settings.template("task_assigned", DEFAULTS["task_assigned"]),
            property_name=prop.name,
            property_code=prop.code,
            date=self._fmt(task.scheduled_at),
            luggage=LUGGAGE_LABELS[task.luggage.value],
            observations=task.observations or "Sin observaciones adicionales",
            staff_name=staff.name,
            login_url=self._login_url,
        )
        return await self._send(
            staff.phone.digits if staff.phone else None, message, settings, kind="task_assigned"
        )

    async def daily_summary(
        self,
        staff: StaffMember,
        tasks: Sequence[CleaningTask],
        properties: Mapping[uuid.UUID, Property],
        settings: StaysSettings,
    ) -> bool:
        lines = "\n".join(
            f"• {properties[t.property_id].name if t.property_id in properties else t.property_id} "
            f"a las {self._fmt(t.scheduled_at, '%H:%M')}"
            for t in sorted(tasks, key=lambda t: t.scheduled_at)
        )
        message = render(
            settings.template("daily_summary", DEFAULTS["daily_summary"]),
            staff_name=staff.name,
            count=len(tasks),
            lines=lines,
        )
        return await self._send(
            staff.phone.digits if staff.phone else None, message, settings, kind="daily_summary"
        )

    async def arrival_prompt(
        self, task: CleaningTask, prop: Property, staff: StaffMember, settings: StaysSettings
    ) -> bool:
        if not staff.phone:
            return False
        buttons = [
            InteractiveButton(f"arrival_{task.id}", "Ya llegué"),
            InteractiveButton(f"no_out_{task.id}", "No han salido"),
            InteractiveButton(f"problem_{task.id}", "Tengo un problema"),
        ]
        try:
            await self._sender.send_buttons(
                staff.phone.digits,
                "Confirmación de llegada",
                f"¿Ya llegaste a {prop.name} ({self._fmt(task.scheduled_at, '%H:%M')})?",
                buttons,
                footer="1heavy Ops",
                instance=settings.whatsapp_instance,
            )
            return True
        except Exception:
            log.exception("whatsapp_buttons_failed", extra={"task": str(task.id)})
            return False

    async def escalate(self, settings: StaysSettings, message: str) -> bool:
        text = render(settings.template("escalation", DEFAULTS["escalation"]), message=message)
        phone = settings.supervisor_phone.digits if settings.supervisor_phone else None
        if phone is None:
            log.error("escalation_without_supervisor", extra={"tenant": str(settings.tenant_id)})
        return await self._send(phone, text, settings, kind="escalation")

    async def property_welcome(self, prop: Property, settings: StaysSettings) -> bool:
        cutoffs = (
            "\n".join(f"• {s.label}: día {d}" for s, d in prop.billing_cutoffs.configured()) or "Por definir"
        )
        message = render(
            settings.template("property_welcome", DEFAULTS["property_welcome"]),
            owner_name=prop.owner_name or "Propietario",
            property_name=prop.name,
            cutoffs=cutoffs,
        )
        phone = prop.owner_phone.digits if prop.owner_phone else None
        return await self._send(phone, message, settings, kind="property_welcome")

    async def billing(
        self, prop: Property, service: Service, settings: StaysSettings, *, overdue: bool
    ) -> bool:
        key = "billing_overdue" if overdue else "billing_reminder"
        message = render(
            settings.template(key, DEFAULTS[key]),
            owner_name=prop.owner_name or "Propietario",
            property_name=prop.name,
            service=service.label,
        )
        phone = prop.owner_phone.digits if prop.owner_phone else None
        return await self._send(phone, message, settings, kind=key)
