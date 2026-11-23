# Documentación de 1heavy

| Área | Documento | Para qué |
|---|---|---|
| Producto | [analisis-producto.md](product/analisis-producto.md) | visión, ICP, modelo de negocio, KPIs, roadmap, riesgos |
| | [casos-de-uso.md](product/casos-de-uso.md) | catálogo CU-XX-NN con reglas REG-XX |
| | [mapa-de-actores.md](product/mapa-de-actores.md) | actores × módulos |
| Arquitectura | [overview.md](architecture/overview.md) | C4, capas hexagonales, UoW, multi-tenancy |
| | [modules.md](architecture/modules.md) | cada bounded context |
| | [events.md](architecture/events.md) | catálogo de eventos de integración |
| | [oop-design.md](architecture/oop-design.md) | patrones y SOLID |
| | [api-contract.md](architecture/api-contract.md) | contrato REST v1 (fuente de verdad) |
| | [adr/](architecture/adr/) | decisiones de arquitectura |
| Proceso | [flujo-de-desarrollo.md](process/flujo-de-desarrollo.md) | ramas, commits, review, DoR/DoD, releases |
| | [pipelines.md](process/pipelines.md) | CI/CD y pipelines de negocio |
| | [testing.md](process/testing.md) | estrategia de pruebas |
| | [seguridad.md](process/seguridad.md) | secretos, RBAC, webhooks, OWASP |
| Diseño | [design-system.md](design/design-system.md) | paleta, tipografía, librerías, accesibilidad |

Regla: si un PR cambia comportamiento, actualiza el documento correspondiente en el mismo PR.
