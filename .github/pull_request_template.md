## ¿Qué cambia y por qué?

<!-- 1–3 frases. Enlaza el issue: Closes #123 -->

**Caso(s) de uso:** CU-XX-NN <!-- docs/product/casos-de-uso.md -->
**Módulo(s):** identity · stays · crm · marketing · meta · growth · gamification · analytics · billing · web · infra

## Tipo
- [ ] feat · [ ] fix · [ ] refactor · [ ] docs · [ ] chore/ci · [ ] breaking change

## Checklist (Definition of Done)
- [ ] Título en Conventional Commits (`feat(crm): ...`)
- [ ] El dominio no importa FastAPI/SQLAlchemy; ningún módulo importa el dominio de otro (sólo `integration_events`)
- [ ] Toda consulta filtra por `tenant_id`; permisos validados con `Principal.require(...)`
- [ ] Pruebas unitarias del dominio + integración del endpoint (incluye caso de error y aislamiento entre tenants)
- [ ] `make ci` en verde (ruff, mypy, pytest, eslint, tsc, build)
- [ ] Si cambia la API: actualizado `docs/architecture/api-contract.md` y el cliente en `apps/web`
- [ ] Si agrega/cambia eventos: actualizado `docs/architecture/events.md`
- [ ] Si agrega configuración: actualizados `infra/.env.example` y `apps/api/.env.example`
- [ ] Sin secretos, `print()` ni `except: pass`
- [ ] CHANGELOG actualizado (sección *Unreleased*)

## Evidencia
<!-- Capturas, salida de tests, request/response de ejemplo -->

## Riesgos y rollback
<!-- ¿Migración de datos? ¿Feature flag? ¿Cómo se revierte? -->
