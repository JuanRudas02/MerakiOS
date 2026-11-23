# ADR-0002 · Bus de eventos en proceso con publicación tras commit

- **Estado:** Aceptado · 2026-11-22

## Contexto
Gamificación, analítica y CRM necesitan reaccionar a hechos de otros módulos sin acoplarse a ellos.

## Decisión
Puerto `EventBus` con implementación `InMemoryEventBus`. Los agregados registran eventos; la Unit of Work
los publica **después** de `session.commit()`. Cada handler abre su propia UoW. Una excepción en un handler
se registra y no afecta a los demás ni a la transacción original.

## Alternativas
Kafka / RabbitMQ / Redis Streams desde el día uno: infraestructura adicional sin necesidad actual.

## Consecuencias
- ✅ Desacople total entre módulos, pruebas simples (`bus.published`).
- ⚠️ Si el proceso cae entre el commit y el handler, el efecto secundario se pierde (entrega *at-most-once*).
  Mitigación futura: patrón Outbox + relay a Redis Streams manteniendo el puerto.
- ⚠️ Los handlers corren en la misma request: deben ser rápidos; lo lento se delega (tareas en segundo plano).
