import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { ROUTES } from "@/lib/routes";
import { Button } from "@/components/ui/button";
import MerakiLogo from "@/components/MerakiLogo";
import AbstractNodes from "@/components/AbstractNodes";
import { 
  Brain, 
  Network, 
  PenLine, 
  Eye,
  ArrowRight,
  Check,
  X,
  Sparkles,
  Target,
  Radar,
  Zap,
  Crown,
  Building2,
  Rocket,
  Users,
  TrendingUp,
  Shield,
  ChevronRight
} from "lucide-react";
import { 
  SiMeta, 
  SiLinkedin, 
  SiTiktok, 
  SiFacebook, 
  SiInstagram 
} from "react-icons/si";

const pillars = [
  {
    icon: Brain,
    badge: "01 — The Brain",
    title: "Auditoría de Mercado Profunda",
    description: "Investigación autónoma de niveles de consciencia, competencia y dolores del cliente antes de escribir una sola palabra.",
    gradient: "from-purple-500/30 to-violet-600/10",
    iconColor: "text-purple-400",
    borderColor: "border-purple-500/30",
    glowColor: "shadow-purple-500/20",
  },
  {
    icon: Network,
    badge: "02 — The Mapper",
    title: "Arquitecto Visual de Embudos",
    description: "Diseño de embudos visuales interactivos. La IA dibuja la ruta exacta de conversión basada en la auditoría.",
    gradient: "from-blue-500/30 to-cyan-600/10",
    iconColor: "text-blue-400",
    borderColor: "border-blue-500/30",
    glowColor: "shadow-blue-500/20",
    hasPreview: true,
  },
  {
    icon: PenLine,
    badge: "03 — The Blueprints",
    title: "Planos de Construcción",
    description: "Generación de briefs de copy y Prompts de Ingeniería para imagen/video. No te damos el pez, te damos la caña de pescar de alta precisión.",
    gradient: "from-emerald-500/30 to-green-600/10",
    iconColor: "text-emerald-400",
    borderColor: "border-emerald-500/30",
    glowColor: "shadow-emerald-500/20",
  },
  {
    icon: Eye,
    badge: "04 — The Director",
    title: "Dashboard de Inteligencia Viva",
    description: "Supervisión en tiempo real. Compara tu plan inicial con la realidad y detecta cuellos de botella automáticamente.",
    gradient: "from-amber-500/30 to-orange-600/10",
    iconColor: "text-amber-400",
    borderColor: "border-amber-500/30",
    glowColor: "shadow-amber-500/20",
  },
];

// Comparison table data
const comparisonData = [
  { tool: "ClickFunnels", price: "$297/mes", icon: "🔧", included: true },
  { tool: "Agencias Tradicionales", price: "$2,000+/mes", icon: "🏢", included: true },
  { tool: "ChatGPT Plus", price: "$20/mes", icon: "🤖", included: true },
  { tool: "Herramientas SEO", price: "$99/mes", icon: "📊", included: true },
  { tool: "Email Marketing", price: "$50/mes", icon: "📧", included: true },
  { tool: "Analytics Premium", price: "$150/mes", icon: "📈", included: true },
];

// Pricing plans
const pricingPlans = [
  {
    name: "Starter",
    price: "$82",
    period: "/mes",
    description: "Para Solopreneurs",
    features: [
      "Auditoría de mercado básica",
      "1 embudo visual",
      "5 briefs de copy/mes",
      "Dashboard básico",
      "Soporte por email",
    ],
    cta: "Comenzar Ahora",
    popular: false,
    icon: Rocket,
  },
  {
    name: "Growth",
    price: "$252",
    period: "/mes",
    description: "Para Agencias",
    features: [
      "Auditoría ilimitada",
      "Embudos ilimitados",
      "Briefs ilimitados",
      "IA Estratega Completa",
      "Multi-cliente (5 marcas)",
      "API Access básico",
      "Soporte prioritario 24/7",
    ],
    cta: "Escalar Ahora",
    popular: true,
    icon: TrendingUp,
  },
  {
    name: "Empire",
    price: "$422",
    period: "/mes",
    description: "Marca Blanca",
    features: [
      "Todo de Growth",
      "Tu propio SaaS",
      "Clientes ilimitados",
      "API Ilimitada",
      "White-label completo",
      "Manager dedicado",
      "SLA garantizado",
    ],
    cta: "Conquistar",
    popular: false,
    icon: Crown,
  },
];

// Omnichannel platforms
const platforms = [
  { name: "Meta", icon: SiMeta, color: "text-blue-400" },
  { name: "LinkedIn", icon: SiLinkedin, color: "text-blue-500" },
  { name: "TikTok", icon: SiTiktok, color: "text-pink-400" },
  { name: "Facebook", icon: SiFacebook, color: "text-blue-600" },
  { name: "Instagram", icon: SiInstagram, color: "text-pink-500" },
];

// Mini Flow Builder Preview
const FlowBuilderPreview = () => {
  return (
    <div className="absolute -right-2 -bottom-2 w-40 h-32 opacity-70 pointer-events-none">
      <svg viewBox="0 0 160 120" className="w-full h-full">
        {/* Animated connection lines with particles */}
        <defs>
          <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(var(--primary))">
              <animate attributeName="stop-color" values="hsl(var(--primary));hsl(var(--accent));hsl(var(--primary))" dur="3s" repeatCount="indefinite" />
            </stop>
            <stop offset="100%" stopColor="hsl(var(--accent))">
              <animate attributeName="stop-color" values="hsl(var(--accent));hsl(var(--primary));hsl(var(--accent))" dur="3s" repeatCount="indefinite" />
            </stop>
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        {/* Curved connection cables */}
        <path 
          d="M30,40 C60,40 50,20 90,20" 
          stroke="url(#flowGradient)" 
          strokeWidth="2" 
          fill="none"
          filter="url(#glow)"
          strokeDasharray="5,3"
        >
          <animate attributeName="stroke-dashoffset" from="0" to="-16" dur="1s" repeatCount="indefinite" />
        </path>
        <path 
          d="M90,20 C120,20 110,60 140,50" 
          stroke="url(#flowGradient)" 
          strokeWidth="2" 
          fill="none"
          filter="url(#glow)"
          strokeDasharray="5,3"
        >
          <animate attributeName="stroke-dashoffset" from="0" to="-16" dur="1s" repeatCount="indefinite" />
        </path>
        <path 
          d="M30,40 C60,40 50,80 90,80" 
          stroke="url(#flowGradient)" 
          strokeWidth="2" 
          fill="none"
          filter="url(#glow)"
          strokeDasharray="5,3"
        >
          <animate attributeName="stroke-dashoffset" from="0" to="-16" dur="1s" repeatCount="indefinite" />
        </path>
        
        {/* Smart Card nodes with glassmorphism effect */}
        <g filter="url(#glow)">
          <rect x="15" y="30" width="30" height="22" rx="4" fill="hsl(var(--card))" stroke="hsl(var(--primary))" strokeWidth="2" opacity="0.9" />
          <text x="30" y="43" textAnchor="middle" className="text-[6px] fill-primary font-bold">AD</text>
          <circle cx="40" cy="35" r="3" fill="hsl(142 76% 36%)" />
        </g>
        
        <g filter="url(#glow)">
          <rect x="75" y="10" width="30" height="22" rx="4" fill="hsl(var(--card))" stroke="hsl(var(--accent))" strokeWidth="2" opacity="0.9" />
          <text x="90" y="23" textAnchor="middle" className="text-[6px] fill-accent font-bold">LP</text>
          <circle cx="100" cy="15" r="3" fill="hsl(142 76% 36%)" />
        </g>
        
        <g filter="url(#glow)">
          <rect x="75" y="70" width="30" height="22" rx="4" fill="hsl(var(--card))" stroke="hsl(0 72% 51%)" strokeWidth="2" opacity="0.9" />
          <text x="90" y="83" textAnchor="middle" className="text-[6px] fill-destructive font-bold">DROP</text>
          <circle cx="100" cy="75" r="3" fill="hsl(0 72% 51%)" />
        </g>
        
        <g filter="url(#glow)">
          <rect x="125" y="40" width="30" height="22" rx="4" fill="hsl(var(--card))" stroke="hsl(142 76% 36%)" strokeWidth="2" opacity="0.9" />
          <text x="140" y="53" textAnchor="middle" className="text-[6px] font-bold" fill="hsl(142 76% 36%)">SALE</text>
        </g>
      </svg>
    </div>
  );
};

// Dashboard 3D Preview Component
const Dashboard3DPreview = () => {
  return (
    <div className="relative perspective-1000">
      <div className="relative w-full max-w-2xl mx-auto transform rotate-x-12 rotate-y-6 hover:rotate-x-6 hover:rotate-y-3 transition-transform duration-700">
        {/* Dashboard frame */}
        <div className="rounded-2xl bg-gradient-to-br from-card/90 to-card/60 border border-primary/30 p-4 backdrop-blur-xl shadow-2xl shadow-primary/20">
          {/* Window controls */}
          <div className="flex items-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="ml-2 text-xs text-muted-foreground font-mono">merakios.app</span>
          </div>
          
          {/* Dashboard content preview */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 h-32 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/10 border border-purple-500/20 p-3 flex flex-col justify-between">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-400" />
                <span className="text-xs text-purple-400 font-medium">Auditoría Activa</span>
              </div>
              <div className="flex gap-2">
                <div className="flex-1 h-2 rounded-full bg-purple-500/30 overflow-hidden">
                  <div className="h-full w-3/4 bg-purple-400 rounded-full animate-pulse" />
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <div className="h-14 rounded-lg bg-green-500/10 border border-green-500/20 p-2 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-[10px] text-green-400">+23% Conv</span>
              </div>
              <div className="h-14 rounded-lg bg-amber-500/10 border border-amber-500/20 p-2 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-[10px] text-amber-400">2 Alertas</span>
              </div>
            </div>
          </div>
          
          {/* Flow preview */}
          <div className="mt-3 h-16 rounded-lg bg-muted/30 border border-border/50 overflow-hidden flex items-center justify-center gap-4 px-4">
            <div className="w-8 h-8 rounded bg-blue-500/20 border border-blue-500/30 flex items-center justify-center">
              <span className="text-[8px] text-blue-400">AD</span>
            </div>
            <ChevronRight className="w-3 h-3 text-muted-foreground" />
            <div className="w-8 h-8 rounded bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
              <span className="text-[8px] text-purple-400">LP</span>
            </div>
            <ChevronRight className="w-3 h-3 text-muted-foreground" />
            <div className="w-8 h-8 rounded bg-green-500/20 border border-green-500/30 flex items-center justify-center">
              <span className="text-[8px] text-green-400">$</span>
            </div>
          </div>
        </div>
        
        {/* Floating elements */}
        <div className="absolute -top-4 -right-8 px-3 py-2 rounded-lg bg-green-500/20 border border-green-500/40 backdrop-blur-sm animate-float">
          <span className="text-xs text-green-400 font-mono font-bold">ROI +340%</span>
        </div>
        <div className="absolute -bottom-4 -left-8 px-3 py-2 rounded-lg bg-purple-500/20 border border-purple-500/40 backdrop-blur-sm animate-float" style={{ animationDelay: "0.5s" }}>
          <span className="text-xs text-purple-400 font-mono">IA Analizando...</span>
        </div>
      </div>
    </div>
  );
};

const HomePublic = () => {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate(ROUTES.APP.HOME);
    }
  }, [user, loading, navigate]);

  useEffect(() => {
    document.title = "MerakiOS - Tu Agencia Entera en un Solo Tablero de Ajedrez con IA";
  }, []);

  const totalSavings = comparisonData.reduce((acc, item) => {
    const price = parseInt(item.price.replace(/[^0-9]/g, "")) || 0;
    return acc + price;
  }, 0);

  if (loading) return null;

  return (
    <>
      <div className="min-h-screen gradient-dark text-foreground overflow-hidden">
        {/* Navigation */}
        <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <Link to={ROUTES.PUBLIC.HOME} className="flex items-center gap-3">
              <MerakiLogo className="w-8 h-8" />
              <span className="font-display font-bold text-xl">MerakiOS</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-muted-foreground hover:text-foreground transition-colors">
                Características
              </a>
              <a href="#pricing" className="text-muted-foreground hover:text-foreground transition-colors">
                Precios
              </a>
              <Link to={ROUTES.PUBLIC.ABOUT} className="text-muted-foreground hover:text-foreground transition-colors">
                Nosotros
              </Link>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" asChild>
                <Link to={ROUTES.PUBLIC.LOGIN}>Ingresar</Link>
              </Button>
              <Button className="gradient-primary glow-primary" asChild>
                <Link to={ROUTES.PUBLIC.LOGIN}>
                  <Zap className="w-4 h-4 mr-2" />
                  Iniciar Gratis
                </Link>
              </Button>
            </div>
          </div>
        </nav>

        {/* Hero Section - All-in-One */}
        <section className="relative pt-32 pb-24 overflow-hidden">
          <div className="absolute inset-0 opacity-10">
            <AbstractNodes />
          </div>
          
          {/* Gradient orbs */}
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-[120px] animate-pulse" />
          <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: "1s" }} />
          
          <div className="container mx-auto px-4 relative z-10">
            <div className="max-w-5xl mx-auto text-center mb-16">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30 mb-8">
                <Radar className="w-4 h-4 text-accent animate-pulse" />
                <span className="text-sm text-muted-foreground">Potenciado por IA Estratégica</span>
              </div>
              
              <h1 className="font-display text-5xl md:text-7xl lg:text-8xl font-bold mb-6 leading-[0.95]">
                Tu Agencia Entera en un{" "}
                <span className="text-gradient">Solo Tablero de Ajedrez</span>{" "}
                con IA.
              </h1>
              
              <p className="text-xl md:text-2xl text-muted-foreground mb-10 max-w-3xl mx-auto leading-relaxed">
                Audita, Estrategiza, Construye y Optimiza.{" "}
                <span className="text-foreground font-medium">Reemplaza 10 herramientas desconectadas</span>{" "}
                por un Cerebro Central.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
                <Button size="lg" className="gradient-primary glow-primary text-lg px-10 h-14" asChild>
                  <Link to={ROUTES.PUBLIC.LOGIN}>
                    <Target className="w-5 h-5 mr-2" />
                    Iniciar Auditoría Gratis
                  </Link>
                </Button>
                <Button size="lg" variant="outline" className="text-lg px-10 h-14 border-primary/30 hover:bg-primary/10" asChild>
                  <a href="#pricing">
                    Ver Precios
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </a>
                </Button>
              </div>

              {/* Omnichannel platforms bar */}
              <div className="flex items-center justify-center gap-6 py-4">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">Conecta con:</span>
                <div className="flex items-center gap-4">
                  {platforms.map((platform, index) => (
                    <div 
                      key={index}
                      className="w-10 h-10 rounded-lg bg-card/50 border border-border/50 flex items-center justify-center hover:border-primary/50 hover:scale-110 transition-all cursor-pointer"
                      title={platform.name}
                    >
                      <platform.icon className={`w-5 h-5 ${platform.color}`} />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 3D Dashboard Preview */}
            <Dashboard3DPreview />
          </div>
        </section>

        {/* Comparison Table - MerakiOS vs The World */}
        <section className="py-24 relative" id="comparison">
          <div className="container mx-auto px-4">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-destructive/10 border border-destructive/20 mb-4">
                <X className="w-3 h-3 text-destructive" />
                <span className="text-xs text-destructive uppercase tracking-wider font-medium">Deja de pagar de más</span>
              </div>
              <h2 className="font-display text-4xl md:text-5xl font-bold mb-4">
                MerakiOS vs <span className="text-muted-foreground">El Resto del Mundo</span>
              </h2>
              <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
                Mientras otros pagan miles en herramientas fragmentadas, tú tendrás todo en un solo lugar.
              </p>
            </div>

            <div className="max-w-4xl mx-auto">
              <div className="rounded-2xl bg-card/50 border border-border overflow-hidden backdrop-blur-sm">
                {/* Header */}
                <div className="grid grid-cols-3 bg-muted/50 border-b border-border">
                  <div className="p-4 font-medium text-muted-foreground">Herramienta</div>
                  <div className="p-4 font-medium text-muted-foreground text-center">Costo Mensual</div>
                  <div className="p-4 font-medium text-center">
                    <span className="text-gradient font-bold">MerakiOS</span>
                  </div>
                </div>
                
                {/* Rows */}
                {comparisonData.map((item, index) => (
                  <div 
                    key={index}
                    className="grid grid-cols-3 border-b border-border/50 last:border-b-0 hover:bg-muted/20 transition-colors"
                  >
                    <div className="p-4 flex items-center gap-3">
                      <span className="text-2xl">{item.icon}</span>
                      <span className="font-medium">{item.tool}</span>
                    </div>
                    <div className="p-4 flex items-center justify-center">
                      <span className="text-destructive font-mono font-bold">{item.price}</span>
                    </div>
                    <div className="p-4 flex items-center justify-center">
                      <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Check className="w-5 h-5 text-green-400" />
                      </div>
                    </div>
                  </div>
                ))}
                
                {/* Total savings row */}
                <div className="grid grid-cols-3 bg-gradient-to-r from-green-500/10 to-emerald-500/5 border-t-2 border-green-500/30">
                  <div className="p-6 font-bold text-lg">Total sin MerakiOS</div>
                  <div className="p-6 flex items-center justify-center">
                    <span className="text-destructive font-mono font-bold text-2xl line-through decoration-2">${totalSavings}+/mes</span>
                  </div>
                  <div className="p-6 flex items-center justify-center">
                    <div className="text-center">
                      <span className="text-green-400 font-bold text-2xl">Desde $82/mes</span>
                      <p className="text-xs text-green-400/70">Todo incluido</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Savings banner */}
              <div className="mt-8 p-6 rounded-2xl bg-gradient-to-r from-green-500/20 to-emerald-500/10 border border-green-500/30 text-center">
                <p className="text-2xl font-display font-bold text-green-400">
                  💰 Ahorra más de <span className="text-3xl">${totalSavings - 82}/mes</span> en software
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 4 Pillars - Strategic Modules */}
        <section className="py-24 relative" id="features">
          <div className="container mx-auto px-4">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 mb-4">
                <Sparkles className="w-3 h-3 text-accent" />
                <span className="text-xs text-accent uppercase tracking-wider font-medium">Los 4 Módulos</span>
              </div>
              <h2 className="font-display text-4xl md:text-5xl font-bold mb-4">
                Tu Arquitectura de <span className="text-gradient">Inteligencia</span>
              </h2>
              <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
                Cuatro agentes autónomos que trabajan 24/7 para construir tu imperio digital.
              </p>
            </div>

            {/* Bento Grid */}
            <div className="grid md:grid-cols-2 gap-6 max-w-6xl mx-auto">
              {pillars.map((pillar, index) => (
                <div
                  key={index}
                  className={`group relative p-8 rounded-3xl bg-gradient-to-br ${pillar.gradient} border ${pillar.borderColor} hover:shadow-2xl ${pillar.glowColor} transition-all duration-500 backdrop-blur-sm overflow-hidden`}
                >
                  {/* Glassmorphism overlay */}
                  <div className="absolute inset-0 bg-card/20 backdrop-blur-sm" />
                  
                  <div className="relative z-10">
                    <div className="flex items-start justify-between mb-6">
                      <div className="w-16 h-16 rounded-2xl bg-background/50 border border-border/50 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-lg">
                        <pillar.icon className={`w-8 h-8 ${pillar.iconColor}`} />
                      </div>
                      <span className="text-xs font-mono text-muted-foreground bg-background/50 px-3 py-1.5 rounded-lg border border-border/30">
                        {pillar.badge}
                      </span>
                    </div>
                    
                    <h3 className="font-display font-bold text-2xl mb-4 group-hover:text-primary transition-colors">
                      {pillar.title}
                    </h3>
                    <p className="text-muted-foreground leading-relaxed">
                      {pillar.description}
                    </p>

                    {/* Special preview for The Mapper */}
                    {pillar.badge.includes("Mapper") && <FlowBuilderPreview />}
                  </div>

                  {/* Hover glow effect */}
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
                    <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section className="py-24 relative" id="pricing">
          <div className="container mx-auto px-4">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 mb-4">
                <Shield className="w-3 h-3 text-primary" />
                <span className="text-xs text-primary uppercase tracking-wider font-medium">15% menos que la competencia</span>
              </div>
              <h2 className="font-display text-4xl md:text-5xl font-bold mb-4">
                Precios <span className="text-gradient">Brutalmente Honestos</span>
              </h2>
              <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
                Sin trucos. Sin costos ocultos. Sin sorpresas.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
              {pricingPlans.map((plan, index) => (
                <div
                  key={index}
                  className={`relative rounded-3xl p-8 transition-all duration-300 ${
                    plan.popular
                      ? "bg-gradient-to-b from-primary/20 via-secondary/10 to-card/80 border-2 border-primary shadow-2xl shadow-primary/20 scale-105"
                      : "bg-card/50 border border-border hover:border-primary/30"
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <span className="px-4 py-2 rounded-full bg-gradient-to-r from-primary to-secondary text-primary-foreground text-sm font-bold shadow-lg">
                        ⚡ Más Popular
                      </span>
                    </div>
                  )}

                  <div className="text-center mb-8">
                    <div className={`w-14 h-14 mx-auto mb-4 rounded-2xl flex items-center justify-center ${plan.popular ? "bg-primary/20" : "bg-muted"}`}>
                      <plan.icon className={`w-7 h-7 ${plan.popular ? "text-primary" : "text-muted-foreground"}`} />
                    </div>
                    <h3 className="font-display text-2xl font-bold mb-1">{plan.name}</h3>
                    <p className="text-muted-foreground text-sm mb-4">{plan.description}</p>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="font-display text-5xl font-bold">{plan.price}</span>
                      <span className="text-muted-foreground">{plan.period}</span>
                    </div>
                  </div>

                  <ul className="space-y-4 mb-8">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-3">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${plan.popular ? "bg-primary/20" : "bg-accent/20"}`}>
                          <Check className={`w-3 h-3 ${plan.popular ? "text-primary" : "text-accent"}`} />
                        </div>
                        <span className="text-sm">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    className={`w-full h-12 text-base ${plan.popular ? "gradient-primary glow-primary" : ""}`}
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

            {/* Trust badges */}
            <div className="mt-16 flex flex-wrap items-center justify-center gap-8">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Shield className="w-5 h-5 text-green-400" />
                <span className="text-sm">Garantía 30 días</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Users className="w-5 h-5 text-blue-400" />
                <span className="text-sm">+500 negocios activos</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Building2 className="w-5 h-5 text-purple-400" />
                <span className="text-sm">Empresas Fortune 500</span>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 relative">
          <div className="container mx-auto px-4">
            <div className="max-w-4xl mx-auto text-center p-16 rounded-3xl bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/10 border border-primary/30 backdrop-blur-xl relative overflow-hidden">
              {/* Background effects */}
              <div className="absolute inset-0 opacity-30">
                <div className="absolute top-0 left-1/4 w-64 h-64 bg-purple-500/30 rounded-full blur-[100px]" />
                <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-blue-500/30 rounded-full blur-[100px]" />
              </div>
              
              <div className="relative z-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 mb-6">
                  <Brain className="w-3 h-3 text-accent" />
                  <span className="text-xs text-accent uppercase tracking-wider">IA Estratégica</span>
                </div>
                <h2 className="font-display text-4xl md:text-5xl font-bold mb-6">
                  ¿Listo para dominar tu mercado?
                </h2>
                <p className="text-muted-foreground text-xl mb-10 max-w-2xl mx-auto">
                  Deja de adivinar. Deja de pagar de más. Empieza a arquitectar tu éxito con IA.
                </p>
                <Button size="lg" className="gradient-primary glow-primary text-lg px-12 h-16" asChild>
                  <Link to={ROUTES.PUBLIC.LOGIN}>
                    <Target className="w-6 h-6 mr-3" />
                    Comenzar Mi Auditoría Gratis
                    <ArrowRight className="w-6 h-6 ml-3" />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 border-t border-border">
          <div className="container mx-auto px-4">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-3">
                <MerakiLogo className="w-7 h-7" />
                <span className="font-display font-bold text-lg">MerakiOS</span>
                <span className="text-xs text-muted-foreground bg-primary/10 px-2 py-0.5 rounded-full">v3.0</span>
              </div>
              
              <div className="flex items-center gap-6 text-sm text-muted-foreground">
                <Link to={ROUTES.PUBLIC.ABOUT} className="hover:text-foreground transition-colors">Nosotros</Link>
                <a href="#pricing" className="hover:text-foreground transition-colors">Precios</a>
                <a href="#" className="hover:text-foreground transition-colors">Términos</a>
                <a href="#" className="hover:text-foreground transition-colors">Privacidad</a>
              </div>
              
              <p className="text-muted-foreground text-sm">
                © 2024 MerakiOS. Arquitecto de Negocios Digitales.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
};

export default HomePublic;
