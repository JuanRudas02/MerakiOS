"""Única fuente de tiempo del sistema.

Todo el backend trabaja en UTC con datetimes *aware*. Esto elimina la mezcla de
`datetime.now()` y `datetime.now(timezone.utc)` que existía en 1heavy Stays.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_aware(value: datetime) -> datetime:
    """Normaliza un datetime naive (asumido UTC) a aware.

    SQLite devuelve datetimes naive; Postgres los devuelve aware.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
