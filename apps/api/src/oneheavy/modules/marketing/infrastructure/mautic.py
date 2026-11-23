"""Adaptadores del puerto `MauticGateway`.

- `HttpMauticGateway`: API REST de Mautic 5 (basic auth sobre HTTPS).
- `InMemoryMauticGateway`: sandbox para desarrollo local y tests.
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from oneheavy.modules.marketing.application.ports import MauticContactData, MauticGateway
from oneheavy.shared.domain.errors import ExternalServiceError

log = logging.getLogger("oneheavy.marketing.mautic")


def _contact_payload(data: MauticContactData) -> dict[str, Any]:
    payload: dict[str, Any] = {"tags": data.tags, "overwriteWithBlank": False}
    if data.email:
        payload["email"] = data.email
    if data.phone:
        payload["mobile"] = data.phone
    if data.first_name:
        payload["firstname"] = data.first_name
    if data.last_name:
        payload["lastname"] = data.last_name
    return payload


class HttpMauticGateway(MauticGateway):
    def __init__(self, base_url: str, username: str, password: str, *, timeout: float = 20.0) -> None:
        self._base = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(username, password)
        self._timeout = timeout

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, auth=self._auth) as client:
                resp = await client.request(method, f"{self._base}{path}", json=json)
                resp.raise_for_status()
                body = resp.json() if resp.content else {}
                return body if isinstance(body, dict) else {}
        except (httpx.HTTPError, ValueError) as exc:
            log.exception("mautic_request_failed", extra={"path": path, "method": method})
            raise ExternalServiceError("Mautic no respondió correctamente") from exc

    @staticmethod
    def _id(body: dict[str, Any], key: str) -> int:
        try:
            return int(body[key]["id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError(f"Respuesta inesperada de Mautic ({key})") from exc

    async def ping(self) -> bool:
        await self._request("GET", "/api/contacts?limit=1&minimal=true")
        return True

    async def upsert_contact(self, data: MauticContactData, mautic_id: int | None = None) -> int:
        if mautic_id is not None:
            body = await self._request("PATCH", f"/api/contacts/{mautic_id}/edit", _contact_payload(data))
        else:
            # /contacts/new en Mautic deduplica por los campos únicos (email por defecto).
            body = await self._request("POST", "/api/contacts/new", _contact_payload(data))
        return self._id(body, "contact")

    async def create_segment(self, name: str, description: str | None = None) -> int:
        body = await self._request(
            "POST",
            "/api/segments/new",
            {"name": name, "description": description or "", "isPublished": True, "isGlobal": False},
        )
        return self._id(body, "list")

    async def add_contacts_to_segment(self, segment_id: int, contact_ids: list[int]) -> None:
        for cid in contact_ids:
            await self._request("POST", f"/api/segments/{segment_id}/contact/{cid}/add")

    async def create_email(
        self, *, name: str, subject: str, html: str, text: str, segment_id: int | None = None
    ) -> int:
        payload: dict[str, Any] = {
            "name": name,
            "subject": subject,
            "customHtml": html,
            "plainText": text,
            "emailType": "list" if segment_id else "template",
            "isPublished": False,
        }
        if segment_id:
            payload["lists"] = [segment_id]
        return self._id(await self._request("POST", "/api/emails/new", payload), "email")

    async def create_campaign(self, *, name: str, description: str, segment_id: int | None = None) -> int:
        payload: dict[str, Any] = {"name": name, "description": description, "isPublished": False}
        if segment_id:
            payload["lists"] = [{"id": segment_id}]
        return self._id(await self._request("POST", "/api/campaigns/new", payload), "campaign")

    async def publish_campaign(self, campaign_id: int) -> None:
        await self._request("PATCH", f"/api/campaigns/{campaign_id}/edit", {"isPublished": True})


@dataclass
class InMemoryMauticGateway(MauticGateway):
    """Sandbox de Mautic: mismo contrato, sin red. Registra todo para inspección."""

    contacts: dict[int, MauticContactData] = field(default_factory=dict)
    segments: dict[int, dict[str, Any]] = field(default_factory=dict)
    emails: dict[int, dict[str, Any]] = field(default_factory=dict)
    campaigns: dict[int, dict[str, Any]] = field(default_factory=dict)
    healthy: bool = True
    _ids: itertools.count[int] = field(default_factory=lambda: itertools.count(1))

    async def ping(self) -> bool:
        return self.healthy

    def _check(self) -> None:
        if not self.healthy:
            raise ExternalServiceError("Mautic (sandbox) fuera de servicio")

    async def upsert_contact(self, data: MauticContactData, mautic_id: int | None = None) -> int:
        self._check()
        if mautic_id is None and data.email:
            mautic_id = next((k for k, v in self.contacts.items() if v.email == data.email), None)
        mid = mautic_id if mautic_id is not None else next(self._ids)
        self.contacts[mid] = data
        return mid

    async def create_segment(self, name: str, description: str | None = None) -> int:
        self._check()
        sid = next(self._ids)
        self.segments[sid] = {"name": name, "description": description, "contacts": set()}
        return sid

    async def add_contacts_to_segment(self, segment_id: int, contact_ids: list[int]) -> None:
        self._check()
        self.segments[segment_id]["contacts"].update(contact_ids)

    async def create_email(
        self, *, name: str, subject: str, html: str, text: str, segment_id: int | None = None
    ) -> int:
        self._check()
        eid = next(self._ids)
        self.emails[eid] = {
            "name": name,
            "subject": subject,
            "html": html,
            "text": text,
            "segment_id": segment_id,
        }
        return eid

    async def create_campaign(self, *, name: str, description: str, segment_id: int | None = None) -> int:
        self._check()
        cid = next(self._ids)
        self.campaigns[cid] = {
            "name": name,
            "description": description,
            "segment_id": segment_id,
            "published": False,
        }
        return cid

    async def publish_campaign(self, campaign_id: int) -> None:
        self._check()
        self.campaigns[campaign_id]["published"] = True
