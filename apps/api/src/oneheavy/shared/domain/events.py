"""Evento de dominio base."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from oneheavy.shared.domain.time import utc_now


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Hecho inmutable que ocurrió en el dominio.

    `tenant_id` permite que los suscriptores (gamificación, analítica, CRM)
    procesen el evento dentro del workspace correcto.
    """

    tenant_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=utc_now)

    @property
    def event_name(self) -> str:
        return type(self).__name__
