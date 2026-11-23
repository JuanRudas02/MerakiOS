# ADR-0003 · Mautic como motor de ejecución de marketing; 1heavy como cerebro

- **Estado:** Aceptado · 2026-11-22

## Contexto
Se requiere email marketing, segmentación, tracking y campañas automatizadas. Construirlo es costoso
(entregabilidad, editores, tracking de aperturas). Mautic es open source, auto-hospedable y tiene API REST y webhooks.

## Decisión
- El **CRM de 1heavy es la fuente de verdad** de contactos; Mautic recibe una copia sincronizada (`mautic_id`).
- 1heavy decide *qué* comunicar (segmentos, planes de campaña, copy generado por IA) y **Mautic ejecuta** (envío, tracking).
- Integración por el puerto `MauticGateway` (adaptador HTTP + fake) y webhooks entrantes con secreto.
- La IA propone y una persona aprueba antes de enviar (human-in-the-loop).

## Alternativas
HubSpot/ActiveCampaign (costo por contacto, lock-in) · motor propio (meses de trabajo, entregabilidad).

## Consecuencias
- ✅ Costo marginal bajo, control de datos, diferenciador "IA + open source".
- ⚠️ Operar Mautic (MariaDB, cron, SMTP/SES). Mautic se habilita por flag (`ONEHEAVY_MAUTIC_ENABLED`); sin él, el módulo funciona en modo local.
