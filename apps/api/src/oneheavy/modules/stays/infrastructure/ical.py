"""Adaptador iCal (Airbnb, Booking, VRBO) sobre httpx + icalendar."""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx
from icalendar import Calendar

from oneheavy.modules.stays.application.ports import CalendarEvent, ReservationCalendar
from oneheavy.shared.domain.errors import ExternalServiceError

log = logging.getLogger("oneheavy.stays.ical")


def parse_ical(content: bytes) -> list[CalendarEvent]:
    """El check-out de una reserva es el DTEND del VEVENT."""
    events: list[CalendarEvent] = []
    for component in Calendar.from_ical(content).walk("VEVENT"):
        dtend = component.get("DTEND")
        if dtend is None:
            continue
        value = dtend.dt
        if not isinstance(value, datetime | date):
            continue
        uid = str(component.get("UID") or f"{value.isoformat()}-{component.get('SUMMARY')}")
        summary = component.get("SUMMARY")
        events.append(CalendarEvent(uid=uid, checkout=value, summary=str(summary) if summary else None))
    return events


class HttpReservationCalendar(ReservationCalendar):
    def __init__(self, timeout: float = 20.0) -> None:
        self._timeout = timeout

    async def fetch(self, url: str) -> list[CalendarEvent]:
        url = url.replace("webcal://", "https://", 1)
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.exception("ical_fetch_failed")
            raise ExternalServiceError("No fue posible leer el calendario iCal") from exc
        try:
            return parse_ical(resp.content)
        except ValueError as exc:
            raise ExternalServiceError("El calendario iCal no tiene un formato válido") from exc
