"""Adaptadores de seguridad: hashing de contraseñas y tokens JWT."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from oneheavy.shared.domain.access import Principal, Role
from oneheavy.shared.domain.errors import AuthenticationError, BusinessRuleViolation
from oneheavy.shared.domain.time import utc_now

MIN_PASSWORD_LENGTH = 10


class PasswordHasher:
    def hash(self, plain: str) -> str:
        self.validate_strength(plain)
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except ValueError:
            return False

    @staticmethod
    def validate_strength(plain: str) -> None:
        has_letter = any(c.isalpha() for c in plain)
        has_digit = any(c.isdigit() for c in plain)
        if len(plain) < MIN_PASSWORD_LENGTH or not (has_letter and has_digit):
            raise BusinessRuleViolation(
                f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres, letras y números",
                code="weak_password",
            )


class TokenService:
    def __init__(self, secret: str, algorithm: str = "HS256", ttl_minutes: int = 720) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=ttl_minutes)

    def issue(self, principal: Principal) -> str:
        now = utc_now()
        payload: dict[str, Any] = {
            "sub": str(principal.user_id),
            "tid": str(principal.tenant_id),
            "role": principal.role.value,
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> Principal:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return Principal.for_role(
                user_id=uuid.UUID(payload["sub"]),
                tenant_id=uuid.UUID(payload["tid"]),
                role=Role(payload["role"]),
            )
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise AuthenticationError("Token inválido o expirado") from exc
