"""Bus de eventos en memoria.

Los handlers se ejecutan en orden de suscripción. Una falla en un handler se
registra (nunca `except: pass`) y NO detiene a los demás suscriptores: un error
en gamificación no debe revertir una tarea de limpieza ya confirmada.

Evolución prevista: reemplazar por Redis Streams / outbox sin tocar los módulos.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from oneheavy.shared.application.ports import E, EventBus, EventHandler
from oneheavy.shared.domain.events import DomainEvent

log = logging.getLogger("oneheavy.events")


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler[Any]]] = defaultdict(list)
        self.published: list[DomainEvent] = []  # útil para auditoría y tests

    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        for event_type, handlers in self._handlers.items():
            if not isinstance(event, event_type):
                continue
            for handler in handlers:
                try:
                    await handler(event)
                except Exception:
                    log.exception(
                        "event_handler_failed",
                        extra={
                            "event": event.event_name,
                            "handler": getattr(handler, "__qualname__", handler),
                        },
                    )
