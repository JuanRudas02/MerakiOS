"""Adaptadores de mensajería (implementan `MessageSender`)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

import httpx

from oneheavy.shared.application.ports import InteractiveButton, MessageSender
from oneheavy.shared.domain.errors import ExternalServiceError

log = logging.getLogger("oneheavy.messaging")


@dataclass
class SentMessage:
    to: str
    body: str
    instance: str | None
    buttons: list[InteractiveButton] = field(default_factory=list)


class ConsoleMessageSender(MessageSender):
    """Registra los mensajes en memoria y en el log. Ideal para local/tests.

    Mantiene la MISMA interfaz que Evolution (corrige el bug #11 de Stays,
    donde el mock no era compatible).
    """

    def __init__(self) -> None:
        self.outbox: list[SentMessage] = []

    async def send_whatsapp(self, to: str, message: str, *, instance: str | None = None) -> None:
        self.outbox.append(SentMessage(to, message, instance))
        log.info("whatsapp_out", extra={"to": to, "instance": instance, "chars": len(message)})

    async def send_buttons(
        self,
        to: str,
        title: str,
        description: str,
        buttons: Sequence[InteractiveButton],
        *,
        footer: str = "1heavy",
        instance: str | None = None,
    ) -> None:
        self.outbox.append(SentMessage(to, f"{title}\n{description}\n{footer}", instance, list(buttons)))
        log.info("whatsapp_buttons_out", extra={"to": to, "instance": instance, "buttons": len(buttons)})


class EvolutionApiSender(MessageSender):
    """WhatsApp vía Evolution API. `instance` = instancia del workspace (QR propio)."""

    def __init__(self, base_url: str, api_key: str, *, default_instance: str = "oneheavy") -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"apikey": api_key, "Content-Type": "application/json"}
        self._default_instance = default_instance

    async def _post(self, path: str, payload: dict[str, object]) -> None:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(f"{self._base_url}{path}", json=payload, headers=self._headers)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.exception("evolution_send_failed", extra={"path": path})
            raise ExternalServiceError("No fue posible enviar el mensaje de WhatsApp") from exc

    async def send_whatsapp(self, to: str, message: str, *, instance: str | None = None) -> None:
        await self._post(
            f"/message/sendText/{instance or self._default_instance}",
            {"number": to.lstrip("+"), "text": message},
        )

    async def send_buttons(
        self,
        to: str,
        title: str,
        description: str,
        buttons: Sequence[InteractiveButton],
        *,
        footer: str = "1heavy",
        instance: str | None = None,
    ) -> None:
        await self._post(
            f"/message/sendButtons/{instance or self._default_instance}",
            {
                "number": to.lstrip("+"),
                "title": title,
                "description": description,
                "footer": footer,
                "buttons": [{"type": "reply", "displayText": b.label, "id": b.id} for b in buttons],
            },
        )
