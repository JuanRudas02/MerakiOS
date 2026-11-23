"""Contrato base de los casos de uso (Command / Query)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class UseCase[In, Out](ABC):
    """Un caso de uso = una intención del usuario = una transacción.

    - Recibe un DTO de entrada inmutable (Command/Query).
    - Orquesta entidades de dominio y puertos; no contiene detalles de HTTP ni SQL.
    - Devuelve un DTO de salida o una entidad.
    """

    @abstractmethod
    async def execute(self, data: In) -> Out: ...
