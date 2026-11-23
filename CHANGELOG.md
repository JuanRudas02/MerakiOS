# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [SemVer](https://semver.org/lang/es/).

## [Unreleased]

## [2.0.0] — 2026-11-22 · Unificación 1heavy

### Añadido
- **Plataforma 1heavy**: fusión de MerakiOS y 1heavy Stays en un monorepo (`apps/api`, `apps/web`, `infra`, `docs`).
- Backend reescrito como **monolito modular hexagonal**: kernel compartido (entidades, value objects, RBAC, Unit of Work, bus de eventos, puertos) y módulos `identity`, `stays`, `crm`, `marketing`, `meta`, `growth`, `gamification`, `analytics`, `billing`.
- Multi-tenancy por workspace con 8 roles y permisos granulares; marca blanca por workspace.
- CRM con ciclo de vida, pipeline y lead scoring explicado por IA.
- Integración con **Mautic** (segmentos, emails y campañas generados por IA, webhooks de engagement).
- **Meta Business**: insights de campañas, Lead Ads → CRM, alertas de rendimiento, Conversions API.
- **Gamificación** basada en eventos de dominio y **Analytics** unificado con insights IA.
- Catálogo de eventos de integración y contrato REST v1.
- CI (ruff, mypy, pytest+cobertura, eslint, tsc, build, imágenes Docker), CodeQL, Dependabot, pre-commit.
- Stack local con Docker Compose: Postgres + pgvector, Redis, Mautic 5 + MariaDB, Evolution API.
- Documentación de producto, casos de uso, arquitectura (C4, ADRs), procesos y design system.

### Cambiado
- Los agentes Genesis/Blueprint/Director de MerakiOS pasan de LangGraph a pipelines OOP sobre un puerto `LLMClient` agnóstico al proveedor.
- Login por email **o** usuario; tokens JWT con workspace y rol.

### Corregido (heredado de los proyectos originales)
- Fechas del scheduler calculadas al arrancar el servidor (los recordatorios usaban siempre la misma fecha).
- Mezcla de datetimes naive/aware → todo UTC aware.
- `except: pass` silenciosos y `print()` en producción → logging estructurado.
- Uploads sin validación → validación por *magic bytes* y tamaño.
- Login sin rate limiting → ventana deslizante configurable.
- Firma de webhooks de Wompi que siempre devolvía `True`.
- Contraseñas enviadas por WhatsApp → nunca se envían.
- Errores 500 que exponían `str(exc)` al cliente.
- MerakiOS: `status` sin importar en login, función de fondo duplicada, proyectos creados con `user_id` aleatorio, endpoints sin autenticación.

### Eliminado
- Script de arranque con credenciales en texto plano (`setup_and_run.sh`). **Rotar** cualquier credencial que haya estado ahí.
- Dependencias LangChain/LangGraph y la integración Supabase no usada.
