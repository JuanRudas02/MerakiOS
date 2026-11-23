import { Link, Navigate, useParams } from "react-router-dom";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Helmet } from "react-helmet-async";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Reveal } from "@/components/marketing/Reveal";
import { moduleBySlug, PRODUCT_MODULES } from "@/lib/modules";
import { PRODUCT_CONTENT } from "@/lib/product-content";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

export default function ProductPage() {
  const { slug = "" } = useParams();
  const mod = moduleBySlug(slug);
  const content = PRODUCT_CONTENT[slug];
  if (!mod || !content) return <Navigate to="/404" replace />;
  const Icon = mod.icon;
  const others = PRODUCT_MODULES.filter((m) => m.slug !== slug).slice(0, 3);

  return (
    <>
      <Helmet>
        <title>{`${mod.name} · 1heavy`}</title>
        <meta name="description" content={content.subheadline} />
      </Helmet>

      <section className="relative overflow-hidden">
        <div className="bg-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" aria-hidden />
        <div className="container relative py-16 sm:py-24">
          <Reveal>
            <span className={cn("inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold", mod.text)}>
              <Icon className="h-3.5 w-3.5" aria-hidden /> {mod.name}
            </span>
            <h1 className="mt-6 max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">{content.headline}</h1>
            <p className="mt-5 max-w-2xl text-lg text-muted-foreground">{content.subheadline}</p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" asChild>
                <Link to={`${ROUTES.PUBLIC.ACCESS}?modo=registro`}>
                  Probar {mod.name} <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link to={ROUTES.PUBLIC.PRICING}>Ver precios</Link>
              </Button>
            </div>
          </Reveal>
          <dl className="mt-14 grid max-w-3xl grid-cols-3 gap-6">
            {content.metrics.map((m) => (
              <div key={m.label}>
                <dt className="sr-only">{m.label}</dt>
                <dd className={cn("font-display text-3xl font-bold sm:text-4xl", mod.text)}>{m.value}</dd>
                <dd className="mt-1 text-xs text-muted-foreground sm:text-sm">{m.label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="container py-16" aria-labelledby="funcionalidades">
        <h2 id="funcionalidades" className="text-2xl font-bold sm:text-3xl">
          Funcionalidades
        </h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {content.features.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.04}>
              <Card className="h-full p-6">
                <CheckCircle2 className={cn("h-5 w-5", mod.text)} aria-hidden />
                <h3 className="mt-4 font-semibold">{f.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{f.description}</p>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="border-y bg-surface/40 py-16" aria-labelledby="flujo">
        <div className="container">
          <h2 id="flujo" className="text-2xl font-bold sm:text-3xl">
            Flujo de trabajo
          </h2>
          <ol className="mt-8 grid gap-4 md:grid-cols-4">
            {content.workflow.map((w, i) => (
              <li key={w.step} className="relative rounded-xl border bg-background p-5">
                <span className={cn("grid h-8 w-8 place-items-center rounded-full text-sm font-bold text-white", mod.bg)}>
                  {i + 1}
                </span>
                <h3 className="mt-4 font-semibold">{w.step}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{w.detail}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="container py-16" aria-labelledby="casos">
        <h2 id="casos" className="text-2xl font-bold sm:text-3xl">
          Casos de uso
        </h2>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {content.useCases.map((u) => (
            <Card key={u.title} className="p-6">
              <p className={cn("text-xs font-semibold uppercase tracking-wide", mod.text)}>{u.actor}</p>
              <h3 className="mt-2 font-semibold">{u.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{u.outcome}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="container max-w-3xl py-16" aria-labelledby="faq">
        <h2 id="faq" className="text-2xl font-bold sm:text-3xl">
          Preguntas frecuentes
        </h2>
        <Accordion type="single" collapsible className="mt-6">
          {content.faqs.map((f, i) => (
            <AccordionItem key={f.q} value={`faq-${i}`}>
              <AccordionTrigger className="text-left">{f.q}</AccordionTrigger>
              <AccordionContent className="text-muted-foreground">{f.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </section>

      <section className="container pb-20">
        <h2 className="mb-6 text-xl font-bold">Funciona mejor junto a</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {others.map((m) => (
            <Link key={m.slug} to={ROUTES.PUBLIC.PRODUCT(m.slug)} className="group">
              <Card className="flex items-center gap-4 p-5 transition-colors group-hover:border-foreground/20">
                <m.icon className={cn("h-6 w-6", m.text)} aria-hidden />
                <div>
                  <p className="font-semibold">{m.name}</p>
                  <p className="text-xs text-muted-foreground">{m.tagline}</p>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
