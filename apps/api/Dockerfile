# syntax=docker/dockerfile:1.7
# ── Etapa 1: construir wheels ──
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip wheel --wheel-dir /wheels ".[ai]"

# ── Etapa 2: runtime mínimo, usuario no root ──
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install /wheels/* && rm -rf /wheels \
    && mkdir -p /app/storage && chown -R app:app /app
USER app
ENV PORT=8000
EXPOSE 8000
# Railway/Render inyectan PORT. Se confía en las cabeceras X-Forwarded-* del proxy
# para obtener la IP real del cliente (necesaria para el rate limiting por IP).
# Un solo proceso: el scheduler de tareas no debe correr duplicado.
CMD ["sh", "-c", "exec uvicorn oneheavy.main:app_factory --factory --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
