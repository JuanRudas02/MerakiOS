import { Helmet } from "react-helmet-async";
import { Link, Outlet, useLocation } from "react-router-dom";
import { ROUTES } from "@/lib/routes";
import { Brain, Network, PenLine, Eye, BarChart3, ArrowRight, Zap, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const servicesData = [
  { 
    title: "Auditoría de Mercado", 
    description: "Investigación autónoma de niveles de consciencia, competencia y dolores del cliente.", 
    icon: Brain, 
    status: "active",
    badge: "The Brain",
    url: ROUTES.SERVICES.MARKET_AUDIT,
    gradient: "from-purple-500/20 to-violet-600/10"
  },
  { 
    title: "Arquitecto de Embudos", 
    description: "Diseño de embudos visuales interactivos. La IA dibuja la ruta de conversión.", 
    icon: Network, 
    status: "coming",
    badge: "The Mapper",
    url: ROUTES.SERVICES.FUNNEL_ARCHITECT,
    gradient: "from-blue-500/20 to-cyan-600/10"
  },
  { 
    title: "Planos de Construcción", 
    description: "Briefs de copy y Prompts de Ingeniería para imagen/video de alta precisión.", 
    icon: PenLine, 
    status: "coming",
    badge: "The Blueprints",
    url: ROUTES.SERVICES.BLUEPRINTS,
    gradient: "from-emerald-500/20 to-green-600/10"
  },
  { 
    title: "Dashboard de Inteligencia", 
    description: "Supervisión en tiempo real. Compara plan vs realidad y detecta cuellos de botella.", 
    icon: Eye, 
    status: "active",
    badge: "The Director",
    url: ROUTES.SERVICES.INTELLIGENCE,
    gradient: "from-amber-500/20 to-orange-600/10"
  },
  { 
    title: "Métricas", 
    description: "Analiza el rendimiento de tus campañas de Facebook e Instagram.", 
    icon: BarChart3, 
    status: "active",
    url: ROUTES.SERVICES.METRICS,
    gradient: "from-blue-500/20 to-blue-600/10"
  },
  { 
    title: "Informes IA", 
    description: "Análisis inteligentes y recomendaciones automatizadas.", 
    icon: Sparkles, 
    status: "active",
    url: ROUTES.SERVICES.AI_REPORTS,
    gradient: "from-pink-500/20 to-purple-600/10"
  },
];

const Services = () => {
  const location = useLocation();
  const isRootServices = location.pathname === ROUTES.SERVICES.ROOT || location.pathname === ROUTES.APP.SERVICES;

  if (!isRootServices) {
    return <Outlet />;
  }

  return (
    <>
      <Helmet>
        <title>Módulos Estratégicos - MerakiOS</title>
      </Helmet>

      <div className="space-y-8 animate-fade-in-up">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-5 h-5 text-primary" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-medium">Los 4 Pilares</span>
          </div>
          <h1 className="font-display text-3xl font-bold mb-2">Módulos Estratégicos</h1>
          <p className="text-muted-foreground">
            Agentes autónomos de IA para arquitectar tu estrategia digital.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {servicesData.map((service, index) => (
            <Card 
              key={index} 
              className={`group bg-gradient-to-br ${service.gradient} border-border hover:border-primary/50 transition-all duration-300 backdrop-blur-sm`}
            >
              <CardHeader>
                <div className="flex items-center justify-between mb-2">
                  <div className="w-12 h-12 rounded-lg bg-background/50 flex items-center justify-center">
                    <service.icon className="w-6 h-6 text-primary" />
                  </div>
                  <div className="flex items-center gap-2">
                    {service.badge && (
                      <span className="text-[9px] font-mono text-muted-foreground bg-background/50 px-2 py-0.5 rounded border border-border/30">
                        {service.badge}
                      </span>
                    )}
                    {service.status === "active" ? (
                      <span className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full">
                        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                        Activo
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-1 rounded-full">
                        <Zap className="w-3 h-3" />
                        Próximamente
                      </span>
                    )}
                  </div>
                </div>
                <CardTitle>{service.title}</CardTitle>
                <CardDescription>{service.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  variant={service.status === "active" ? "default" : "outline"} 
                  className="w-full" 
                  asChild
                  disabled={service.status === "coming"}
                >
                  <Link to={service.url}>
                    {service.status === "active" ? "Acceder" : "Próximamente"}
                    {service.status === "active" && <ArrowRight className="ml-2 w-4 h-4" />}
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </>
  );
};

export default Services;
