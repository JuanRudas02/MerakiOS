/** Contenido de las subpáginas de producto (/producto/:slug). */

export interface ProductContent {
  headline: string;
  subheadline: string;
  features: { title: string; description: string }[];
  useCases: { actor: string; title: string; outcome: string }[];
  workflow: { step: string; detail: string }[];
  metrics: { value: string; label: string }[];
  faqs: { q: string; a: string }[];
}

export const PRODUCT_CONTENT: Record<string, ProductContent> = {
  crm: {
    headline: "Un CRM que entiende el ciclo de vida completo de tu cliente",
    subheadline:
      "Desde el primer clic en un anuncio hasta el cliente que te recomienda: contactos sin duplicados, pipeline visual y scoring explicado por IA.",
    features: [
      { title: "Contactos sin duplicados", description: "Deduplicación automática por email y teléfono (E.164) en cada fuente de captura." },
      { title: "Ciclo de vida", description: "Suscriptor → Lead → MQL → SQL → Oportunidad → Cliente → Evangelizador, con historial de cambios." },
      { title: "Pipeline visual", description: "Tablero kanban de negocios con probabilidad por etapa y valor ponderado." },
      { title: "Timeline 360°", description: "Notas, llamadas, WhatsApp, emails de Mautic y leads de Meta en una sola línea de tiempo." },
      { title: "Lead scoring con IA", description: "Puntaje 0–100 por perfil y engagement, con explicación en lenguaje natural y siguiente mejor acción." },
      { title: "Importación masiva", description: "Carga contactos existentes y 1heavy los fusiona con los que ya tienes." },
    ],
    useCases: [
      { actor: "Ventas", title: "Priorizar leads calientes", outcome: "El equipo llama primero a quien tiene más probabilidad de cerrar." },
      { actor: "Marketing", title: "Medir el aporte de cada canal", outcome: "Cada contacto conserva su fuente: Meta, WhatsApp, formulario o Mautic." },
      { actor: "Gerencia", title: "Pronosticar ingresos", outcome: "Pipeline ponderado por etapa para proyectar el mes." },
    ],
    workflow: [
      { step: "Captura", detail: "Lead Ads, formularios, WhatsApp o importación." },
      { step: "Enriquecimiento", detail: "Deduplicación, fuente y etiquetas automáticas." },
      { step: "Scoring", detail: "Engagement de Mautic + perfil = puntaje con IA." },
      { step: "Cierre", detail: "Negocio ganado → puntos de gamificación y evento de conversión a Meta." },
    ],
    metrics: [
      { value: "360°", label: "vista del contacto" },
      { value: "0–100", label: "lead score explicable" },
      { value: "8", label: "etapas de ciclo de vida" },
    ],
    faqs: [
      { q: "¿Puedo importar mis contactos actuales?", a: "Sí. La importación fusiona por email o teléfono y te reporta creados, fusionados y omitidos." },
      { q: "¿El CRM se sincroniza con Mautic?", a: "Sí. Cada contacto nuevo se sincroniza con Mautic y el engagement de vuelta alimenta el scoring." },
      { q: "¿Quién ve qué?", a: "El acceso es por roles: ventas, marketing, gerencia y administradores tienen permisos distintos." },
    ],
  },
  "meta-business": {
    headline: "Tu pauta en Meta, conectada a resultados de negocio",
    subheadline:
      "Conecta tu cuenta publicitaria, lleva cada Lead Ad directo al CRM y recibe alertas cuando una campaña se sale del benchmark.",
    features: [
      { title: "Insights diarios", description: "Inversión, impresiones, clics, CTR, CPC, CPM, leads, CPL y ROAS por campaña." },
      { title: "Lead Ads → CRM", description: "Webhook con firma verificada: el lead aparece en el CRM en segundos, sin exportar CSV." },
      { title: "Alertas de rendimiento", description: "Detección de fatiga creativa, CTR bajo o CPL disparado con severidad." },
      { title: "Conversions API", description: "Los negocios ganados regresan a Meta como conversiones con datos hasheados." },
      { title: "Token seguro", description: "El token se almacena cifrado y nunca vuelve al navegador." },
      { title: "Multi-cuenta", description: "Cada workspace conecta su propia cuenta publicitaria, página y píxel." },
    ],
    useCases: [
      { actor: "Media buyer", title: "Detectar fatiga creativa", outcome: "Alerta temprana antes de quemar presupuesto." },
      { actor: "Ventas", title: "Responder leads en minutos", outcome: "El lead llega al CRM con sus respuestas del formulario." },
      { actor: "Dirección", title: "Ver CPL real vs. ventas", outcome: "Inversión y negocios ganados en el mismo tablero." },
    ],
    workflow: [
      { step: "Conecta", detail: "ID de cuenta publicitaria, página y píxel." },
      { step: "Sincroniza", detail: "Insights diarios automáticos." },
      { step: "Captura", detail: "Lead Ads entran al CRM como contactos." },
      { step: "Optimiza", detail: "Alertas + conversiones de vuelta a Meta." },
    ],
    metrics: [
      { value: "9", label: "métricas por campaña" },
      { value: "<1 min", label: "del lead al CRM" },
      { value: "24/7", label: "monitoreo de anomalías" },
    ],
    faqs: [
      { q: "¿Necesito ser socio de Meta?", a: "No. Basta con un token de usuario del sistema con permisos de lectura de anuncios y leads." },
      { q: "¿Es una integración oficial?", a: "Usa la Graph API y la Marketing API públicas. 1heavy no está afiliado a Meta Platforms." },
      { q: "¿Puedo probar sin pauta activa?", a: "Sí, puedes enviar un lead de prueba desde el panel y verlo llegar al CRM." },
    ],
  },
  "mautic-ia": {
    headline: "Marketing automation open source, con un copiloto de IA",
    subheadline:
      "Mautic te da el motor sin licencias por contacto; 1heavy le suma IA para escribir emails, planear campañas y segmentar mejor.",
    features: [
      { title: "Sin costo por contacto", description: "Mautic es open source: tu base crece sin que crezca la factura." },
      { title: "Emails con IA", description: "Asunto, preheader y cuerpo HTML generados según objetivo, audiencia y tono de tu marca." },
      { title: "Planificador de campañas", description: "La IA propone la secuencia día a día por email, WhatsApp y anuncios." },
      { title: "Segmentos inteligentes", description: "Filtros por etapa, etiquetas y puntaje, sincronizados con Mautic." },
      { title: "Engagement al CRM", description: "Aperturas, clics y formularios vuelven como actividad y suben el score." },
      { title: "Tus datos, tu servidor", description: "Mautic corre en tu infraestructura; los datos no salen de tu control." },
    ],
    useCases: [
      { actor: "Marketing", title: "Nutrir leads fríos", outcome: "Secuencias automáticas hasta que el lead esté listo para ventas." },
      { actor: "Fundador", title: "Lanzar una campaña en una tarde", outcome: "La IA redacta, tú apruebas y Mautic envía." },
      { actor: "Ventas", title: "Saber quién abrió la propuesta", outcome: "El engagement aparece en el timeline del contacto." },
    ],
    workflow: [
      { step: "Segmenta", detail: "Define la audiencia con datos del CRM." },
      { step: "Genera", detail: "La IA escribe el email o la campaña." },
      { step: "Publica", detail: "Se envía a Mautic con un clic." },
      { step: "Aprende", detail: "El engagement retroalimenta el scoring." },
    ],
    metrics: [
      { value: "$0", label: "licencia por contacto" },
      { value: "3", label: "canales por campaña" },
      { value: "IA", label: "en cada borrador" },
    ],
    faqs: [
      { q: "¿Tengo que instalar Mautic?", a: "1heavy incluye la configuración Docker de Mautic. También puedes conectar una instancia existente." },
      { q: "¿Qué proveedor de IA usan?", a: "La arquitectura es agnóstica: el puerto de IA admite distintos proveedores y un modo local para pruebas." },
      { q: "¿La IA envía sin mi aprobación?", a: "No. Todo lo generado queda como borrador hasta que lo publicas." },
    ],
  },
  gamificacion: {
    headline: "Convierte los resultados del negocio en un juego que tu equipo quiere ganar",
    subheadline:
      "Puntos, niveles, insignias y retos que se otorgan solos a partir de lo que pasa en operación, ventas y marketing.",
    features: [
      { title: "Reglas por evento", description: "Limpieza a tiempo, negocio ganado, campaña lanzada: cada logro suma puntos automáticamente." },
      { title: "Niveles e insignias", description: "Progresión visible con insignias por hitos, rachas y excelencia." },
      { title: "Retos por equipo", description: "Metas con fecha y recompensa para operaciones, ventas o marketing." },
      { title: "Leaderboards", description: "Ranking semanal, mensual e histórico, filtrado por equipo." },
      { title: "Feed de logros", description: "Reconocimiento público en tiempo real." },
      { title: "Configurable", description: "Ajusta puntos y activa o desactiva reglas sin tocar código." },
    ],
    useCases: [
      { actor: "Operaciones", title: "Puntualidad del personal", outcome: "Llegar a tiempo y con fotos completas da puntos y rachas." },
      { actor: "Ventas", title: "Competencia sana", outcome: "Ranking de negocios ganados con retos mensuales." },
      { actor: "RR. HH.", title: "Reconocimiento objetivo", outcome: "Datos reales para bonos e incentivos." },
    ],
    workflow: [
      { step: "Evento", detail: "Algo pasa en el negocio (tarea, venta, campaña)." },
      { step: "Regla", detail: "El motor evalúa las reglas activas." },
      { step: "Recompensa", detail: "Puntos, nivel e insignias al instante." },
      { step: "Reconocimiento", detail: "Feed, ranking y retos." },
    ],
    metrics: [
      { value: "+12", label: "reglas listas para usar" },
      { value: "3", label: "equipos con ranking propio" },
      { value: "0", label: "puntos manuales" },
    ],
    faqs: [
      { q: "¿Los puntos se pueden manipular?", a: "No. Sólo se otorgan a partir de eventos reales del sistema y quedan en un libro inmutable." },
      { q: "¿Funciona para personal operativo?", a: "Sí, el personal de limpieza ve su progreso desde el celular." },
      { q: "¿Puedo crear mis propios retos?", a: "Sí, con métrica, meta, fechas, equipo y recompensa." },
    ],
  },
  analitica: {
    headline: "Una sola fuente de verdad para operación, ventas y marketing",
    subheadline:
      "KPIs unificados de todos los módulos y un analista de IA que resume lo importante y recomienda qué hacer.",
    features: [
      { title: "Overview unificado", description: "Operación, ventas, marketing, growth y gamificación en un tablero." },
      { title: "Series de tiempo", description: "Evolución diaria de cualquier métrica clave." },
      { title: "Embudo de ciclo de vida", description: "Cuántos contactos hay en cada etapa y dónde se pierden." },
      { title: "Insights con IA", description: "Resumen ejecutivo, highlights, riesgos y recomendaciones accionables." },
      { title: "Basado en eventos", description: "Cada métrica se construye desde eventos de dominio auditables." },
      { title: "Por workspace", description: "Aislamiento total de datos entre clientes." },
    ],
    useCases: [
      { actor: "Dirección", title: "Reunión semanal en 5 minutos", outcome: "El resumen IA llega listo para discutir." },
      { actor: "Marketing", title: "CPL vs. conversión", outcome: "Ver si más leads significan más ventas." },
      { actor: "Operaciones", title: "Calidad del servicio", outcome: "Puntualidad, duración e incidencias por periodo." },
    ],
    workflow: [
      { step: "Eventos", detail: "Todos los módulos publican hechos de negocio." },
      { step: "Proyección", detail: "Se consolidan en métricas diarias." },
      { step: "Visualización", detail: "Tableros y series de tiempo." },
      { step: "Recomendación", detail: "La IA interpreta y sugiere acciones." },
    ],
    metrics: [
      { value: "5", label: "áreas del negocio" },
      { value: "8", label: "series de tiempo" },
      { value: "1", label: "clic para el resumen IA" },
    ],
    faqs: [
      { q: "¿Puedo exportar los datos?", a: "Los endpoints son públicos para tu workspace vía API con tu token." },
      { q: "¿Cada cuánto se actualiza?", a: "En tiempo real: cada evento actualiza las métricas al instante." },
      { q: "¿La IA ve datos de otros clientes?", a: "No. El contexto que recibe es sólo el de tu workspace." },
    ],
  },
  "growth-ia": {
    headline: "Agentes de IA que investigan tu mercado y diseñan tu embudo",
    subheadline:
      "El motor de estrategia (antes MerakiOS) investiga, audita con frameworks probados y arma el embudo listo para ejecutar.",
    features: [
      { title: "Auditoría de mercado", description: "Avatar, dolores, deseos y competidores con investigación web." },
      { title: "Niveles de conciencia", description: "Clasificación según Eugene Schwartz para elegir el mensaje correcto." },
      { title: "Jobs To Be Done", description: "Qué intenta lograr realmente tu cliente." },
      { title: "Arquitecto de embudos", description: "Anuncio → landing → email → checkout según el nivel de conciencia." },
      { title: "Activos generados", description: "Copys de anuncios, landings y emails por nodo del embudo." },
      { title: "Pipeline iterativo", description: "Si falta información, el agente vuelve a investigar (hasta 2 ciclos)." },
    ],
    useCases: [
      { actor: "Fundador", title: "Validar un nicho", outcome: "Auditoría completa antes de invertir en pauta." },
      { actor: "Agencia", title: "Onboarding de clientes", outcome: "Estrategia inicial en minutos, no semanas." },
      { actor: "Marketing", title: "Lanzar un producto", outcome: "Embudo y copys coherentes con el avatar." },
    ],
    workflow: [
      { step: "Planner", detail: "Define qué investigar." },
      { step: "Research", detail: "Busca señales del mercado." },
      { step: "Auditor", detail: "Aplica Schwartz + JTBD." },
      { step: "Architect", detail: "Diseña el embudo y sus activos." },
    ],
    metrics: [
      { value: "4", label: "agentes encadenados" },
      { value: "5", label: "niveles de conciencia" },
      { value: "8", label: "tipos de nodo de embudo" },
    ],
    faqs: [
      { q: "¿Qué pasa con MerakiOS?", a: "MerakiOS ahora es el módulo Growth IA de 1heavy, con todo su motor de estrategia." },
      { q: "¿Puedo editar el embudo?", a: "Sí, el embudo es un punto de partida y los activos se regeneran por nodo." },
      { q: "¿Cuánto tarda una auditoría?", a: "Normalmente uno o dos minutos; la pantalla se actualiza sola." },
    ],
  },
  stays: {
    headline: "Operación impecable para alquileres de corta estadía",
    subheadline:
      "Coordina limpiezas por WhatsApp con tu propio número, con evidencia fotográfica, checklists, escalamiento automático y control de servicios.",
    features: [
      { title: "Tareas con evidencia", description: "Fotos de llegada y salida obligatorias, checklist por propiedad y timestamps." },
      { title: "WhatsApp con tu número", description: "Conecta por QR; tu personal y propietarios hablan con tu marca." },
      { title: "Escalamiento automático", description: "Si nadie confirma llegada, el supervisor recibe una alerta." },
      { title: "Sincronización iCal", description: "Airbnb y Booking crean las limpiezas de check-out automáticamente." },
      { title: "Cortes de servicios", description: "Recordatorios a propietarios y verificación de comprobantes." },
      { title: "Ranking del personal", description: "Puntualidad y duración promedio, conectados a la gamificación." },
    ],
    useCases: [
      { actor: "Administrador", title: "Programar limpiezas", outcome: "El limpiador recibe la asignación por WhatsApp al instante." },
      { actor: "Personal", title: "Confirmar y completar", outcome: "Llegada, checklist y fotos desde el celular." },
      { actor: "Propietario", title: "Pagar servicios a tiempo", outcome: "Recordatorios y carga de comprobantes." },
    ],
    workflow: [
      { step: "Reserva", detail: "iCal o creación manual." },
      { step: "Asignación", detail: "WhatsApp al personal." },
      { step: "Ejecución", detail: "Llegada → checklist → fotos." },
      { step: "Control", detail: "Dashboard, escalamiento y ranking." },
    ],
    metrics: [
      { value: "100%", label: "tareas con evidencia" },
      { value: "10 min", label: "para escalar un retraso" },
      { value: "6", label: "servicios con corte controlado" },
    ],
    faqs: [
      { q: "¿El personal necesita instalar una app?", a: "No. Usa WhatsApp y una web app que se instala desde el navegador." },
      { q: "¿Qué pasa si mi número de WhatsApp se bloquea?", a: "Cada empresa usa su propio número, así que un bloqueo no afecta a nadie más." },
      { q: "¿Funciona con Airbnb y Booking?", a: "Sí, mediante el enlace iCal de cada anuncio." },
    ],
  },
};
