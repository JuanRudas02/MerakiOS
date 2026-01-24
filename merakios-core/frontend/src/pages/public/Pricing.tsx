import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { ROUTES } from "@/lib/routes";
import { Button } from "@/components/ui/button";
import MerakiLogo from "@/components/MerakiLogo";
import { Check, ArrowRight, Zap } from "lucide-react";

const plans = [
  {
    name: "Starter",
    price: "Gratis",
    description: "Perfecto para comenzar",
    features: [
      "1 usuario",
      "Métricas básicas",
      "CRM hasta 100 leads",
      "Soporte por email",
    ],
    cta: "Comenzar Gratis",
    popular: false,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/mes",
    description: "Para negocios en crecimiento",
    features: [
      "5 usuarios",
      "Métricas avanzadas",
      "CRM ilimitado",
      "Informes IA",
      "1 Chatbot",
      "Soporte prioritario",
    ],
    cta: "Comenzar Prueba",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    description: "Para grandes empresas",
    features: [
      "Usuarios ilimitados",
      "Todas las funciones",
      "Chatbots ilimitados",
      "API access",
      "Manager dedicado",
      "SLA garantizado",
    ],
    cta: "Contactar Ventas",
    popular: false,
  },
];

const Pricing = () => {
  return (
    <>
      <Helmet>
        <title>Precios - MerakiOS</title>
        <meta name="description" content="Planes y precios de MerakiOS. Elige el plan perfecto para tu negocio." />
      </Helmet>

      <div className="min-h-screen gradient-dark text-foreground">
        {/* Navigation */}
        <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <Link to={ROUTES.PUBLIC.HOME} className="flex items-center gap-3">
              <MerakiLogo className="w-8 h-8" />
              <span className="font-display font-bold text-xl">MerakiOS</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <Link to={ROUTES.PUBLIC.PRICING} className="text-foreground font-medium">
                Precios
              </Link>
              <Link to={ROUTES.PUBLIC.ABOUT} className="text-muted-foreground hover:text-foreground transition-colors">
                Nosotros
              </Link>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" asChild>
                <Link to={ROUTES.PUBLIC.LOGIN}>Ingresar</Link>
              </Button>
              <Button className="gradient-primary glow-primary" asChild>
                <Link to={ROUTES.PUBLIC.LOGIN}>Comenzar Gratis</Link>
              </Button>
            </div>
          </div>
        </nav>

        {/* Hero */}
        <section className="pt-32 pb-16">
          <div className="container mx-auto px-4 text-center">
            <h1 className="font-display text-4xl md:text-5xl font-bold mb-4">
              Planes simples, <span className="text-gradient">precios justos</span>
            </h1>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Elige el plan que mejor se adapte a tu negocio. Sin sorpresas, sin costos ocultos.
            </p>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="pb-20">
          <div className="container mx-auto px-4">
            <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {plans.map((plan, index) => (
                <div
                  key={index}
                  className={`relative rounded-2xl p-8 ${
                    plan.popular
                      ? "bg-gradient-to-b from-primary/20 to-secondary/10 border-2 border-primary glow-primary"
                      : "bg-card/50 border border-border"
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="px-3 py-1 rounded-full bg-primary text-primary-foreground text-xs font-medium">
                        Más Popular
                      </span>
                    </div>
                  )}

                  <div className="text-center mb-6">
                    <h3 className="font-display text-xl font-bold mb-2">{plan.name}</h3>
                    <p className="text-muted-foreground text-sm mb-4">{plan.description}</p>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="font-display text-4xl font-bold">{plan.price}</span>
                      {plan.period && (
                        <span className="text-muted-foreground">{plan.period}</span>
                      )}
                    </div>
                  </div>

                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-3">
                        <Check className="w-5 h-5 text-accent flex-shrink-0" />
                        <span className="text-sm">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    className={`w-full ${plan.popular ? "gradient-primary glow-primary" : ""}`}
                    variant={plan.popular ? "default" : "outline"}
                    asChild
                  >
                    <Link to={ROUTES.PUBLIC.LOGIN}>
                      {plan.cta}
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 border-t border-border">
          <div className="container mx-auto px-4">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <MerakiLogo className="w-6 h-6" />
                <span className="font-display font-semibold">MerakiOS</span>
              </div>
              <p className="text-muted-foreground text-sm">
                © 2024 MerakiOS. Todos los derechos reservados.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
};

export default Pricing;
