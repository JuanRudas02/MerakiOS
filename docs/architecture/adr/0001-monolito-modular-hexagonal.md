# ADR-0001 · Monolito modular con arquitectura hexagonal

- **Estado:** Aceptado · 2026-11-22

## Contexto
Se unifican dos productos (MerakiOS y 1heavy Stays) y se agregan CRM, Mautic, Meta, gamificación y analítica.
El equipo es pequeño; el producto aún busca encaje de mercado; se necesita velocidad sin acumular deuda.

## Decisión
Un único servicio FastAPI (`apps/api`) dividido en *bounded contexts* (`modules/*`), cada uno con capas
`domain / application / infrastructure / api`. Los módulos no se importan entre sí: se comunican por eventos
de integración. Un kernel compartido (`shared/`) aporta bloques DDD, puertos y adaptadores transversales.

## Alternativas
- **Microservicios:** sobrecosto operativo (red, despliegues, observabilidad distribuida) prematuro.
- **Monolito por capas tradicional** (como el MerakiOS original): acoplamiento alto, `main.py` gigante.

## Consecuencias
- ✅ Un despliegue, transacciones locales, refactors baratos, límites claros listos para extraer servicios.
- ⚠️ Requiere disciplina en la regla de dependencias (revisión de PR; candidato a `import-linter` en CI).
