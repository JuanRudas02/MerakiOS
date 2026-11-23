import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Flame,
  LineChart,
  Medal,
  MessageCircle,
  ShieldCheck,
  Sparkles,
  Trophy,
  Workflow,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Reveal } from "@/components/marketing/Reveal";
import { PricingGrid } from "@/components/marketing/PricingGrid";
import { PRODUCT_MODULES } from "@/lib/modules";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

const PIPELINE = [
  { icon: MessageCircle, title: "Captura", text: "Meta Lead Ads, WhatsApp, formularios e iCal alimentan 1heavy.", tone: "text-heavy-meta" },
  { icon: Workflow, title: "Organiza", text: "El CRM deduplica, clasifica por ciclo de vida y asigna.", tone: "text-heavy-blue" },
  { icon: Bot, title: "Activa con IA", text: "Mautic + IA nutre, segmenta y escribe por ti.", tone: "text-heavy-violet" },
  { icon: Zap, title: "Ejecuta", text: "Operación con evidencia, escalamiento y WhatsApp propio.", tone: "text-heavy-mint" },
  { icon: Trophy, title: "Motiva", text: "Cada logro suma puntos, niveles y retos para tu equipo.", tone: "text-heavy-ember" },
  { icon: LineChart, title: "Mide", text: "Analítica unificada y recomendaciones de IA.", tone: "text-heavy-cyan" },
];

function HeroVisual() {
  return (
    <div className="relative mx-auto mt-14 max-w-5xl" aria-hidden>
      <div className="absolute -inset-x-10 -top-10 h-72 rounded-full bg-heavy-blue/20 blur-3xl" />
      <Card className="glass relative overflow-hidden rounded-2xl p-4 shadow-card sm:p-6">
        <div className="mb-4 flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-heavy-rose/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-heavy-ember/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-heavy-mint/70" />
          <span className="ml-3 text-xs text-muted-foreground">app.1heavy.com / inicio</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-4">
          {[
            { k: "Leads (30d)", v: "1.284", c: "text-heavy-meta" },
            { k: "Negocios ganados", v: "86", c: "text-heavy-blue" },
            { k: "Limpiezas a tiempo", v: "97%", c: "text-heavy-mint" },
            { k: "Puntos del equipo", v: "42.9k", c: "text-heavy-ember" },
          ].map((s) => (
            <div key={s.k} className="rounded-xl border bg-elevated/60 p-4">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{s.k}</p>
              <p className={cn("mt-1 font-display text-2xl font-bold", s.c)}>{s.v}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border bg-elevated/60 p-4 sm:col-span-2">
            <svg viewBox="0 0 400 120" className="h-32 w-full">
              <defs>
                <linearGradient id="hero-area" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0" stopColor="hsl(var(--heavy-cyan))" stopOpacity="0.45" />
                  <stop offset="1" stopColor="hsl(var(--heavy-cyan))" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d="M0,95 C40,90 60,70 100,72 C140,74 160,45 200,48 C240,51 260,30 300,26 C340,22 360,12 400,8 L400,120 L0,120Z" fill="url(#hero-area)" />
              <path d="M0,95 C40,90 60,70 100,72 C140,74 160,45 200,48 C240,51 260,30 300,26 C340,22 360,12 400,8" fill="none" stroke="hsl(var(--heavy-cyan))" strokeWidth="2.5" />
            </svg>
          </div>
          <div className="space-y-2 rounded-xl border bg-elevated/60 p-4">
            {["Ana · 2.140 pts", "Luis · 1.980 pts", "Sofía · 1.720 pts"].map((r, i) => (
              <div key={r} className="flex items-center gap-2 text-sm">
                <Medal className={cn("h-4 w-4", ["text-heavy-ember", "text-muted-foreground", "text-heavy-ember/60"][i])} />
                {r}
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}

export default function Landing() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="bg-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" aria-hidden />
        <div className="container relative pb-20 pt-16 text-center sm:pt-24">
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full border bg-surface/70 px-3 py-1 text-xs font-medium text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-heavy-cyan" /> MerakiOS + 1heavy Stays ahora son una sola plataforma
            </span>
          </Reveal>
          <Reveal delay={0.05}>
            <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-bold leading-[1.05] sm:text-6xl">
              El <span className="text-gradient-heavy">Growth & Operations OS</span> para empresas que crecen en serio
            </h1>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mx-auto mt-6 max-w-2xl text-base text-muted-foreground sm:text-lg">
              CRM, Meta Business, Mautic con IA, gamificación, analítica y operación en un solo sistema. Captura, convierte,
              ejecuta y mide sin saltar entre diez herramientas.
            </p>
          </Reveal>
          <Reveal delay={0.15} className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
            <Button size="lg" asChild className="shadow-glow">
              <Link to={`${ROUTES.PUBLIC.ACCESS}?modo=registro`}>
                Crear mi workspace <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to={ROUTES.PUBLIC.PRODUCT("crm")}>Ver el producto</Link>
            </Button>
          </Reveal>
          <p className="mt-4 text-xs text-muted-foreground">14 días de prueba · Sin tarjeta · Tu propio número de WhatsApp</p>
          <HeroVisual />
        </div>
      </section>

      {/* Módulos */}
      <section className="container py-20" aria-labelledby="modulos">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 id="modulos" className="text-3xl font-bold sm:text-4xl">
            Siete módulos. Un solo cerebro.
          </h2>
          <p className="mt-3 text-muted-foreground">
            Cada módulo funciona solo, pero juntos comparten contactos, eventos y métricas en tiempo real.
          </p>
        </Reveal>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {PRODUCT_MODULES.map((m, i) => (
            <Reveal key={m.slug} delay={i * 0.04}>
              <Link to={ROUTES.PUBLIC.PRODUCT(m.slug)} className="group block h-full">
                <Card className="h-full p-6 shadow-card transition-all duration-300 group-hover:-translate-y-1 group-hover:border-foreground/20">
                  <div className={cn("mb-5 grid h-11 w-11 place-items-center rounded-xl text-white", m.bg)}>
                    <m.icon className="h-5 w-5" aria-hidden />
                  </div>
                  <h3 className="text-lg font-semibold">{m.name}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{m.description}</p>
                  <span className={cn("mt-5 inline-flex items-center gap-1 text-sm font-medium", m.text)}>
                    Conocer más <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
                  </span>
                </Card>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Pipeline */}
      <section className="border-y bg-surface/40 py-20" aria-labelledby="como-funciona">
        <div className="container">
          <Reveal className="mx-auto max-w-2xl text-center">
            <h2 id="como-funciona" className="text-3xl font-bold sm:text-4xl">
              Cómo funciona
            </h2>
            <p className="mt-3 text-muted-foreground">Un pipeline continuo, del primer anuncio al cliente que te recomienda.</p>
          </Reveal>
          <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
            {PIPELINE.map((s, i) => (
              <Reveal key={s.title} delay={i * 0.05}>
                <li className="relative h-full rounded-xl border bg-background p-5">
                  <span className="absolute right-4 top-4 font-display text-xs text-muted-foreground">0{i + 1}</span>
                  <s.icon className={cn("h-6 w-6", s.tone)} aria-hidden />
                  <h3 className="mt-4 font-semibold">{s.title}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">{s.text}</p>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* IA + Mautic */}
      <section className="container grid items-center gap-12 py-20 lg:grid-cols-2" aria-labelledby="ia-mautic">
        <Reveal>
          <span className="text-sm font-semibold text-heavy-violet">Mautic open source + IA</span>
          <h2 id="ia-mautic" className="mt-2 text-3xl font-bold sm:text-4xl">
            Marketing automation sin licencias por contacto, con un copiloto que escribe por ti
          </h2>
          <p className="mt-4 text-muted-foreground">
            Mautic corre en tu infraestructura y 1heavy le suma inteligencia: emails generados según tu objetivo, campañas
            planificadas día a día y engagement que vuelve al CRM para priorizar a quién llamar.
          </p>
          <ul className="mt-6 space-y-3">
            {[
              "Emails con asunto, preheader y HTML generados por IA",
              "Campañas multicanal: email, WhatsApp y anuncios",
              "Segmentos por etapa, etiquetas y lead score",
              "Aperturas y clics suben el score del contacto",
            ].map((t) => (
              <li key={t} className="flex gap-2 text-sm">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-heavy-violet" aria-hidden /> {t}
              </li>
            ))}
          </ul>
          <Button variant="outline" className="mt-8" asChild>
            <Link to={ROUTES.PUBLIC.PRODUCT("mautic-ia")}>Explorar Mautic + IA</Link>
          </Button>
        </Reveal>
        <Reveal delay={0.1}>
          <Card className="space-y-4 p-6 shadow-card">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Bot className="h-4 w-4 text-heavy-violet" /> Generador de emails
            </div>
            <div className="rounded-lg border bg-elevated/60 p-4 text-sm">
              <p className="text-xs text-muted-foreground">Objetivo</p>
              <p>Reactivar propietarios que no han renovado su plan de administración</p>
            </div>
            <div className="space-y-2 rounded-lg border border-heavy-violet/40 bg-heavy-violet/5 p-4 text-sm">
              <p className="text-xs text-muted-foreground">Asunto sugerido</p>
              <p className="font-semibold">Tu apartamento ganó 18% más este trimestre — ¿seguimos?</p>
              <p className="text-xs text-muted-foreground">Preheader: resultados, próximos pasos y un beneficio por renovar hoy.</p>
            </div>
            <div className="flex gap-2">
              <span className="rounded-full bg-heavy-violet/15 px-2.5 py-1 text-xs text-heavy-violet">Borrador</span>
              <span className="rounded-full bg-elevated px-2.5 py-1 text-xs text-muted-foreground">Listo para Mautic</span>
            </div>
          </Card>
        </Reveal>
      </section>

      {/* Gamificación */}
      <section className="border-y bg-surface/40 py-20" aria-labelledby="gamificacion">
        <div className="container grid items-center gap-12 lg:grid-cols-2">
          <Reveal className="order-2 lg:order-1">
            <Card className="p-6 shadow-card">
              <div className="flex items-center gap-4">
                <div className="relative grid h-20 w-20 place-items-center rounded-full bg-gradient-ember text-white">
                  <span className="font-display text-2xl font-bold">7</span>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Nivel 7 · Operador élite</p>
                  <p className="font-display text-2xl font-bold">3.420 pts</p>
                  <p className="flex items-center gap-1 text-xs text-heavy-ember">
                    <Flame className="h-3.5 w-3.5" /> Racha de 12 días
                  </p>
                </div>
              </div>
              <div className="mt-6 space-y-2 text-sm">
                {[
                  ["+40", "Limpieza completada a tiempo con fotos"],
                  ["+120", "Negocio ganado: Plan Growth"],
                  ["+25", "Campaña lanzada en Mautic"],
                ].map(([p, t]) => (
                  <div key={t} className="flex items-center justify-between rounded-lg bg-elevated/60 px-3 py-2">
                    <span>{t}</span>
                    <span className="font-semibold text-heavy-ember">{p}</span>
                  </div>
                ))}
              </div>
            </Card>
          </Reveal>
          <Reveal className="order-1 lg:order-2">
            <span className="text-sm font-semibold text-heavy-ember">Gamificación conectada a resultados</span>
            <h2 id="gamificacion" className="mt-2 text-3xl font-bold sm:text-4xl">
              Tu equipo no juega por jugar: juega para mover los indicadores
            </h2>
            <p className="mt-4 text-muted-foreground">
              Las reglas escuchan los eventos reales del negocio. Nadie asigna puntos a mano: llegar a tiempo, cerrar una venta o
              lanzar una campaña se recompensa solo.
            </p>
            <Button variant="outline" className="mt-8" asChild>
              <Link to={ROUTES.PUBLIC.PRODUCT("gamificacion")}>Ver gamificación</Link>
            </Button>
          </Reveal>
        </div>
      </section>

      {/* Confianza */}
      <section className="container py-20" aria-labelledby="confianza">
        <h2 id="confianza" className="sr-only">
          Confianza
        </h2>
        <div className="grid gap-5 md:grid-cols-3">
          {[
            { icon: ShieldCheck, t: "Seguridad por diseño", d: "Multi-tenant aislado, roles y permisos, contraseñas con bcrypt y rate limiting." },
            { icon: MessageCircle, t: "Tu canal, tu marca", d: "WhatsApp con tu número y marca blanca para tu equipo y tus clientes." },
            { icon: Sparkles, t: "IA responsable", d: "Todo lo que genera la IA queda como borrador hasta que tú lo apruebas." },
          ].map((x) => (
            <Card key={x.t} className="p-6">
              <x.icon className="h-6 w-6 text-heavy-blue" aria-hidden />
              <h3 className="mt-4 font-semibold">{x.t}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{x.d}</p>
            </Card>
          ))}
        </div>
        <p className="mt-10 text-center text-sm text-muted-foreground">
          Operadores de alquileres, agencias y equipos comerciales en LATAM ya están construyendo con 1heavy.
        </p>
      </section>

      {/* Precios */}
      <section className="border-t bg-surface/40 py-20" aria-labelledby="precios">
        <div className="container">
          <Reveal className="mx-auto mb-12 max-w-2xl text-center">
            <h2 id="precios" className="text-3xl font-bold sm:text-4xl">
              Planes que crecen contigo
            </h2>
            <p className="mt-3 text-muted-foreground">Precios en pesos colombianos. Cancela cuando quieras.</p>
          </Reveal>
          <PricingGrid />
        </div>
      </section>

      {/* CTA */}
      <section className="container py-20">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-heavy p-10 text-center text-white sm:p-16">
          <div className="bg-grid absolute inset-0 opacity-30" aria-hidden />
          <h2 className="relative text-3xl font-bold sm:text-4xl">Pon a trabajar todo tu negocio en un solo lugar</h2>
          <p className="relative mx-auto mt-3 max-w-xl text-white/85">
            Crea tu workspace en menos de un minuto e invita a tu equipo.
          </p>
          <Button size="lg" variant="secondary" className="relative mt-8 bg-white text-[#0B1020] hover:bg-white/90" asChild>
            <Link to={`${ROUTES.PUBLIC.ACCESS}?modo=registro`}>
              Empezar gratis <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>
    </>
  );
}
