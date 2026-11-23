# Seguridad

## 1. Secretos
- Toda credencial llega por variables de entorno `ONEHEAVY_*` (`pydantic-settings`, tipo `SecretStr`: no se imprime en logs ni en `repr`).
- `.env` está en `.gitignore`; sólo se versionan `*.env.example` con placeholders. `pre-commit` ejecuta `detect-private-key`.
- La API **se niega a arrancar** en `production` con el `JWT_SECRET` por defecto.
- Tokens de terceros por workspace (p. ej. token de Meta) se guardan cifrados/opacos y **nunca** se devuelven por la API.
- Incidente heredado: el antiguo `setup_and_run.sh` tenía una contraseña en texto plano; fue eliminado y **debe rotarse** (sigue en el historial de git).

## 2. Autenticación
- Contraseñas con bcrypt (cost 12). Política: ≥ 10 caracteres con letras y números.
- JWT HS256 con `sub` (usuario), `tid` (workspace), `role`, `exp` (12 h por defecto).
- Errores de login genéricos ("Credenciales inválidas") para no revelar si el usuario existe.
- Rate limiting de login/registro por IP: `ONEHEAVY_LOGIN_RATE_LIMIT` (def. `5/minute`). Con varias réplicas, migrar el limitador a Redis.
- Las contraseñas temporales de miembros invitados **no viajan por WhatsApp** (corrige el comportamiento de Stays).

## 3. Autorización (RBAC)
El `Principal` (usuario, workspace, rol, permisos) se reconstruye del JWT en cada request; los casos de uso
llaman `principal.require(Permission.X)` y las rutas usan `Depends(require(...))`. El `tenant_id` **siempre**
sale del token. Reglas extra: nadie asigna `owner`; sólo `owner` crea `admin`; `staff` sólo ve/ejecuta sus tareas; `property_owner` sólo ve sus propiedades.

Matriz generada desde `apps/api/src/oneheavy/shared/domain/access.py`:

| Permiso | owner | admin | manager | coordinator | marketer | sales | staff | property_owner |
|---|---|---|---|---|---|---|---|---|
| `workspace.manage` | ✅ | ✅ | · | · | · | · | · | · |
| `members.manage` | ✅ | ✅ | ✅ | · | · | · | · | · |
| `stays.properties.read` | ✅ | ✅ | ✅ | ✅ | · | · | · | ✅ |
| `stays.properties.manage` | ✅ | ✅ | ✅ | · | · | · | · | · |
| `stays.tasks.read` | ✅ | ✅ | ✅ | ✅ | · | · | ✅ | · |
| `stays.tasks.manage` | ✅ | ✅ | ✅ | ✅ | · | · | · | · |
| `stays.tasks.execute` | ✅ | ✅ | · | · | · | · | ✅ | · |
| `stays.receipts.upload` | ✅ | ✅ | · | · | · | · | · | ✅ |
| `stays.receipts.verify` | ✅ | ✅ | ✅ | · | · | · | · | · |
| `crm.contacts.read` | ✅ | ✅ | ✅ | · | ✅ | ✅ | · | · |
| `crm.contacts.manage` | ✅ | ✅ | · | · | ✅ | ✅ | · | · |
| `crm.deals.manage` | ✅ | ✅ | · | · | · | ✅ | · | · |
| `marketing.manage` | ✅ | ✅ | · | · | ✅ | · | · | · |
| `meta.manage` | ✅ | ✅ | · | · | ✅ | · | · | · |
| `growth.use` | ✅ | ✅ | · | · | ✅ | · | · | · |
| `analytics.read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | · | · |
| `gamification.read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | · |
| `gamification.manage` | ✅ | ✅ | ✅ | · | · | · | · | · |
| `billing.manage` | ✅ | · | · | · | · | · | · | · |

## 4. Webhooks (endpoints públicos)
| Origen | Endpoint | Verificación |
|---|---|---|
| Meta | `GET /meta/webhooks` | `hub.verify_token` == `ONEHEAVY_META_VERIFY_TOKEN` |
| Meta | `POST /meta/webhooks` | HMAC-SHA256 del body con `META_APP_SECRET` vs `X-Hub-Signature-256` (comparación en tiempo constante) |
| Mautic | `POST /marketing/webhooks/mautic` | header `X-Mautic-Secret` == `MAUTIC_WEBHOOK_SECRET` |
| Wompi | `POST /billing/webhooks/wompi` | SHA-256(valores de `signature.properties` + `timestamp` + `WOMPI_EVENTS_SECRET`) == `signature.checksum` |
| Evolution | `POST /stays/webhooks/whatsapp` | token por query string |

Todos: rechazar con 401 si la firma no coincide, procesar de forma **idempotente** (id externo) y responder rápido (< 5 s).

## 5. Archivos subidos
Validación por *magic bytes* (JPG/PNG/WEBP/PDF), límite `ONEHEAVY_MAX_UPLOAD_MB`, nombre aleatorio (UUID), carpeta saneada (sin `..`). En producción usar almacenamiento de objetos (S3/R2) con URLs firmadas.

## 6. Datos personales
- Datos de contactos (Ley 1581 de 2012 en Colombia / GDPR para la UE): registrar origen y consentimiento, permitir exportar y borrar un contacto.
- Conversions API: email/teléfono **hasheados SHA-256** antes de enviarse a Meta.
- No registrar emails, teléfonos ni tokens en logs; los logs usan IDs.
- Prompts a LLM: enviar el mínimo de PII necesario.

## 7. Checklist OWASP (revisión por release)
| OWASP Top 10 | Control en 1heavy |
|---|---|
| A01 Broken Access Control | RBAC por permiso, tenant desde token, pruebas de aislamiento por endpoint |
| A02 Cryptographic Failures | bcrypt, TLS obligatorio en staging/prod, `SecretStr` |
| A03 Injection | SQLAlchemy parametrizado, Pydantic en toda entrada, plantillas sin `eval` |
| A04 Insecure Design | casos de uso con reglas explícitas, human-in-the-loop para envíos IA |
| A05 Security Misconfiguration | CORS por lista, métodos/headers acotados, headers de seguridad en nginx |
| A06 Vulnerable Components | Dependabot + CodeQL |
| A07 Auth Failures | rate limiting, mensajes genéricos, expiración de JWT |
| A08 Integrity Failures | firmas de webhooks, imágenes Docker inmutables por SHA |
| A09 Logging Failures | logs estructurados JSON, sin `except: pass`, handler global sin filtrar detalles |
| A10 SSRF | URLs iCal validadas (http/https, sin IPs privadas) antes de descargar |
