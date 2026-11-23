import { Helmet } from "react-helmet-async";
import { Compass, Layers, Rocket, Users } from "lucide-react";
import { Card } from "@/components/ui/card";

const VALUES = [
  { icon: Layers, t: "Un sistema, no un collage", d: "Contactos, operación y métricas comparten el mismo modelo de datos y eventos." },
  { icon: Compass, t: "IA con criterio", d: "Frameworks probados (Schwartz, JTBD) y aprobación humana antes de publicar." },
  { icon: Users, t: "Hecho para LATAM", d: "WhatsApp como canal principal, pesos colombianos y soporte en español." },
  { icon: Rocket, t: "Open source donde importa", d: "Mautic para marketing automation: sin licencias por contacto." },
];

export default function About() {
  return (
    <div className="container py-16 sm:py-24">
      <Helmet>
        <title>Nosotros · 1heavy</title>
      </Helmet>
      <div className="max-w-3xl">
        <h1 className="text-4xl font-bold sm:text-5xl">
          Construimos el sistema operativo para equipos que <span className="text-gradient-heavy">cargan con el crecimiento</span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground">
          1heavy nace de unir dos productos: <strong className="text-foreground">MerakiOS</strong>, un motor de estrategia con
          agentes de IA, y <strong className="text-foreground">1heavy Stays</strong>, la plataforma de operación para alquileres de
          corta estadía. Descubrimos que las empresas que crecen necesitan ambas cosas a la vez: atraer y convertir clientes, y
          ejecutar la operación sin fricción.
        </p>
      </div>
      <div className="mt-14 grid gap-5 sm:grid-cols-2">
        {VALUES.map((v) => (
          <Card key={v.t} className="p-6">
            <v.icon className="h-6 w-6 text-heavy-blue" aria-hidden />
            <h2 className="mt-4 text-lg font-semibold">{v.t}</h2>
            <p className="mt-1.5 text-sm text-muted-foreground">{v.d}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
