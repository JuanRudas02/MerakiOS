import { Helmet } from "react-helmet-async";
import { PricingGrid } from "@/components/marketing/PricingGrid";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

const FAQ = [
  ["¿Hay periodo de prueba?", "Sí, todos los workspaces nuevos empiezan con 14 días de prueba sin tarjeta."],
  ["¿Cómo se paga?", "Con Wompi: tarjeta, PSE o Nequi, en pesos colombianos."],
  ["¿Mautic tiene costo adicional?", "No. Mautic es open source y corre junto a 1heavy sin licencias por contacto."],
  ["¿Puedo cambiar de plan?", "Sí, en cualquier momento desde Ajustes → Facturación."],
];

export default function Pricing() {
  return (
    <div className="container py-16 sm:py-24">
      <Helmet>
        <title>Precios · 1heavy</title>
      </Helmet>
      <div className="mx-auto mb-14 max-w-2xl text-center">
        <h1 className="text-4xl font-bold sm:text-5xl">Precios simples, valor compuesto</h1>
        <p className="mt-4 text-muted-foreground">Un solo sistema en lugar de CRM + automation + operación + BI por separado.</p>
      </div>
      <PricingGrid />
      <div className="mx-auto mt-20 max-w-3xl">
        <h2 className="text-2xl font-bold">Preguntas frecuentes</h2>
        <Accordion type="single" collapsible className="mt-6">
          {FAQ.map(([q, a], i) => (
            <AccordionItem key={q} value={`p-${i}`}>
              <AccordionTrigger className="text-left">{q}</AccordionTrigger>
              <AccordionContent className="text-muted-foreground">{a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </div>
  );
}
