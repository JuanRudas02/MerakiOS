# Contribuir a 1heavy

Guía corta. Las reglas completas están en [docs/process/flujo-de-desarrollo.md](docs/process/flujo-de-desarrollo.md).

## 1. Antes de programar
- Debe existir un issue con **caso de uso** (`CU-XX-NN`) que cumpla la *Definition of Ready*.
- Si cambia la API, primero se actualiza [`docs/architecture/api-contract.md`](docs/architecture/api-contract.md).

## 2. Rama y commits
```bash
git switch main && git pull
git switch -c feat/crm-lead-scoring      # feat/ fix/ chore/ docs/ refactor/
git commit -m "feat(crm): calcular score con señales de engagement"
```
Conventional Commits: `tipo(alcance): resumen en imperativo`. Alcances = nombres de módulo, `web`, `infra`, `ci`, `docs`.

## 3. Reglas de arquitectura (no negociables)
1. `domain/` es Python puro: sin FastAPI, SQLAlchemy ni httpx.
2. Un módulo **no importa** otro módulo. Se comunican por `shared/domain/integration_events.py`.
3. Los casos de uso son la frontera transaccional: `async with uow:` … `await uow.commit()`.
4. Todo acceso a datos filtra por `tenant_id` tomado del token.
5. Las integraciones externas (Mautic, Meta, WhatsApp, LLM, Wompi) se acceden por un **puerto** con adaptador HTTP y un *fake* para tests.
6. Nada de `print()`, `except: pass` ni secretos en código.

## 4. Antes del PR
```bash
make fmt && make ci
```
Abre el PR con la plantilla, ≤ 400 líneas de cambio efectivo, y pide revisión. Se integra con *squash merge*.
