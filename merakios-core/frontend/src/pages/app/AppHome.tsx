import { useState } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { ROUTES } from "@/lib/routes";
import { useAuth } from "@/hooks/useAuth";
import { 
  Brain, 
  Network, 
  PenLine,
  Eye,
  Zap,
  ArrowRight,
  TrendingUp,
  Activity,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Target,
  ChevronRight,
  Play
} from "lucide-react";
import { 
  SiFacebook, 
  SiInstagram, 
  SiLinkedin, 
  SiTiktok, 
  SiMeta 
} from "react-icons/si";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import BusinessOnboarding from "@/components/BusinessOnboarding";

// Quick actions - The 4 Pillars with story order
const quickActions = [
  { 
    step: "01",
    title: "Auditoría", 
    subtitle: "The Brain",
    icon: Brain, 
    url: ROUTES.SERVICES.MARKET_AUDIT, 
    color: "text-purple-400", 
    bgColor: "bg-purple-500/10",
    borderColor: "border-purple-500/30",
    description: "Investiga mercado"
  },
  { 
    step: "02",
    title: "Arquitecto", 
    subtitle: "The Mapper",
    icon: Network, 
    url: ROUTES.SERVICES.FUNNEL_ARCHITECT, 
    color: "text-blue-400", 
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
    description: "Diseña embudos"
  },
  { 
    step: "03",
    title: "Construcción", 
    subtitle: "The Blueprints",
    icon: PenLine, 
    url: ROUTES.SERVICES.BLUEPRINTS, 
    color: "text-emerald-400", 
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
    description: "Genera briefs"
  },
  { 
    step: "04",
    title: "Comando", 
    subtitle: "The Director",
    icon: Eye, 
    url: ROUTES.SERVICES.INTELLIGENCE, 
    color: "text-amber-400", 
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
    description: "Supervisa KPIs"
  },
];

// Omnichannel platforms
const platforms = [
  { name: "Meta", icon: SiMeta, connected: true, color: "text-blue-400" },
  { name: "LinkedIn", icon: SiLinkedin, connected: false, color: "text-blue-500" },
  { name: "TikTok", icon: SiTiktok, connected: false, color: "text-pink-400" },
  { name: "Facebook", icon: SiFacebook, connected: true, color: "text-blue-600" },
  { name: "Instagram", icon: SiInstagram, connected: true, color: "text-pink-500" },
];

const suggestedActions = [
  { title: "Iniciar auditoría de mercado", description: "Analiza tu competencia y oportunidades", priority: "high", icon: Brain, url: ROUTES.SERVICES.MARKET_AUDIT },
  { title: "Diseñar primer embudo", description: "Crea tu ruta de conversión visual", priority: "medium", icon: Network, url: ROUTES.SERVICES.FUNNEL_ARCHITECT },
  { title: "Conectar LinkedIn Ads", description: "Amplía tu alcance omnicanal", priority: "low", icon: SiLinkedin, url: ROUTES.SETTINGS.INTEGRATIONS },
];

// Live Audit Canvas with Smart Cards
const LiveAuditCanvas = () => {
  return (
    <div className="relative h-56 rounded-xl bg-gradient-to-br from-card/50 to-card/20 border border-border/50 overflow-hidden">
      {/* Grid background */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: `
            linear-gradient(hsl(var(--border)) 1px, transparent 1px),
            linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px)
          `,
          backgroundSize: '30px 30px'
        }}
      />
      
      <div className="absolute inset-0 p-4">
        <svg viewBox="0 0 500 180" className="w-full h-full">
          {/* Animated connection cables */}
          <defs>
            <linearGradient id="cableGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(var(--primary))">
                <animate attributeName="stop-color" values="hsl(var(--primary));hsl(var(--accent));hsl(var(--primary))" dur="3s" repeatCount="indefinite" />
              </stop>
              <stop offset="100%" stopColor="hsl(var(--accent))">
                <animate attributeName="stop-color" values="hsl(var(--accent));hsl(var(--primary));hsl(var(--accent))" dur="3s" repeatCount="indefinite" />
              </stop>
            </linearGradient>
            <filter id="glowEffect">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          {/* Connection cables with particles */}
          <path d="M90,90 C140,90 120,50 180,50" stroke="url(#cableGradient)" strokeWidth="3" fill="none" filter="url(#glowEffect)" strokeLinecap="round">
            <animate attributeName="stroke-dasharray" values="0,1000;100,1000;0,1000" dur="3s" repeatCount="indefinite" />
          </path>
          <path d="M180,50 C230,50 210,90 280,80" stroke="url(#cableGradient)" strokeWidth="3" fill="none" filter="url(#glowEffect)" strokeLinecap="round">
            <animate attributeName="stroke-dasharray" values="0,1000;100,1000;0,1000" dur="3s" repeatCount="indefinite" begin="0.5s" />
          </path>
          <path d="M280,80 C330,80 310,50 380,60" stroke="hsl(142 76% 36%)" strokeWidth="3" fill="none" filter="url(#glowEffect)" strokeLinecap="round" />
          <path d="M90,90 C140,90 120,130 180,130" stroke="url(#cableGradient)" strokeWidth="3" fill="none" filter="url(#glowEffect)" strokeLinecap="round" />
          <path d="M180,130 C230,130 220,100 280,110" stroke="hsl(0 72% 51%)" strokeWidth="3" fill="none" opacity="0.6" strokeLinecap="round" />
          <path d="M380,60 C420,60 410,90 450,90" stroke="hsl(142 76% 36%)" strokeWidth="3" fill="none" filter="url(#glowEffect)" strokeLinecap="round" />
          
          {/* Smart Card Nodes */}
          {/* Ad Node */}
          <g filter="url(#glowEffect)">
            <rect x="55" y="70" width="70" height="45" rx="8" fill="hsl(var(--card))" stroke="hsl(var(--primary))" strokeWidth="2" />
            <text x="90" y="88" textAnchor="middle" className="text-[9px] fill-primary font-bold">FB AD</text>
            <text x="90" y="102" textAnchor="middle" className="text-[7px] fill-muted-foreground">CTR: 3.2%</text>
            <circle cx="115" cy="92" r="5" fill="hsl(142 76% 36%)" className="animate-pulse" />
          </g>
          
          {/* Landing Node - Good */}
          <g>
            <rect x="145" y="30" width="70" height="45" rx="8" fill="hsl(var(--card))" stroke="hsl(var(--accent))" strokeWidth="2" />
            <text x="180" y="48" textAnchor="middle" className="text-[9px] fill-accent font-bold">LANDING</text>
            <text x="180" y="62" textAnchor="middle" className="text-[7px] fill-muted-foreground">Conv: 12%</text>
            <circle cx="205" cy="52" r="5" fill="hsl(142 76% 36%)" className="animate-pulse" />
          </g>
          
          {/* Email Node - Warning */}
          <g>
            <rect x="145" y="110" width="70" height="45" rx="8" fill="hsl(var(--card))" stroke="hsl(45 93% 47%)" strokeWidth="2" />
            <text x="180" y="128" textAnchor="middle" className="text-[9px] font-bold" fill="hsl(45 93% 47%)">EMAIL</text>
            <text x="180" y="142" textAnchor="middle" className="text-[7px] fill-muted-foreground">Open: 22%</text>
            <circle cx="205" cy="132" r="5" fill="hsl(45 93% 47%)" className="animate-pulse" />
          </g>
          
          {/* Checkout Node */}
          <g>
            <rect x="245" y="60" width="70" height="45" rx="8" fill="hsl(var(--card))" stroke="hsl(var(--primary))" strokeWidth="2" />
            <text x="280" y="78" textAnchor="middle" className="text-[9px] fill-primary font-bold">CHECKOUT</text>
            <text x="280" y="92" textAnchor="middle" className="text-[7px] fill-muted-foreground">$2.4k</text>
          </g>
          
          {/* Drop Node */}
          <g>
            <rect x="245" y="90" width="70" height="35" rx="8" fill="hsl(var(--card))" stroke="hsl(0 72% 51%)" strokeWidth="2" opacity="0.7" />
            <text x="280" y="112" textAnchor="middle" className="text-[9px] font-bold" fill="hsl(0 72% 51%)">DROP</text>
          </g>
          
          {/* Sale Node - Success */}
          <g filter="url(#glowEffect)">
            <rect x="345" y="40" width="70" height="45" rx="8" fill="hsl(var(--card))" stroke="hsl(142 76% 36%)" strokeWidth="2" />
            <text x="380" y="58" textAnchor="middle" className="text-[9px] font-bold" fill="hsl(142 76% 36%)">SALE</text>
            <text x="380" y="72" textAnchor="middle" className="text-[7px] fill-muted-foreground">+23 ventas</text>
            <circle cx="405" cy="62" r="5" fill="hsl(142 76% 36%)" />
          </g>
          
          {/* Goal Node */}
          <g filter="url(#glowEffect)">
            <rect x="415" y="70" width="70" height="45" rx="8" fill="hsl(var(--card))" stroke="hsl(var(--accent))" strokeWidth="2" />
            <text x="450" y="88" textAnchor="middle" className="text-[9px] fill-accent font-bold">GOAL</text>
            <text x="450" y="102" textAnchor="middle" className="text-[7px] fill-muted-foreground">ROI: 340%</text>
          </g>
        </svg>
      </div>
      
      {/* Overlay stats */}
      <div className="absolute top-3 right-3 flex gap-2">
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-green-500/10 border border-green-500/30 backdrop-blur-sm">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
          <span className="text-[11px] text-green-400 font-medium">4 OK</span>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 backdrop-blur-sm">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px] text-amber-400 font-medium">1 Alerta</span>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-destructive/10 border border-destructive/30 backdrop-blur-sm">
          <AlertTriangle className="w-3.5 h-3.5 text-destructive" />
          <span className="text-[11px] text-destructive font-medium">1 Drop</span>
        </div>
      </div>
      
      <div className="absolute bottom-3 left-3 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        <span className="text-xs text-muted-foreground font-mono">live_audit</span>
        <span className="text-[10px] text-muted-foreground">· Actualizado hace 30s</span>
      </div>
    </div>
  );
};

const AppHome = () => {
  const { user } = useAuth();
  const firstName = user?.user_metadata?.full_name?.split(" ")[0] || "Arquitecto";
  const [showOnboarding, setShowOnboarding] = useState(true);
  
  return (
    <>
      <Helmet>
        <title>Dashboard - MerakiOS</title>
      </Helmet>

      <div className="space-y-6 animate-fade-in-up">
        {/* Business Onboarding Banner */}
        {showOnboarding && (
          <BusinessOnboarding 
            onComplete={() => setShowOnboarding(false)}
            onDismiss={() => setShowOnboarding(false)}
          />
        )}

        {/* Welcome Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-primary/20 via-secondary/10 to-accent/10 border border-primary/30 p-8">
          <div className="absolute top-0 right-0 w-72 h-72 bg-accent/10 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-500/10 rounded-full blur-[80px] translate-y-1/2 -translate-x-1/2" />
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                <Brain className="w-5 h-5 text-primary" />
              </div>
              <div>
                <span className="text-sm text-muted-foreground">Centro de Comando</span>
                <Badge variant="outline" className="ml-2 text-[10px] font-mono">IA Activa</Badge>
              </div>
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-bold mb-2">
              ¡Bienvenido, {firstName}!
            </h1>
            <p className="text-muted-foreground max-w-2xl">
              Tu tablero de ajedrez estratégico está listo. Sigue los 4 pasos para arquitectar tu éxito.
            </p>
          </div>
        </div>

        {/* Quick Actions - 4 Pillars in Story Order */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {quickActions.map((action, index) => (
            <Link
              key={index}
              to={action.url}
              className={`group p-5 rounded-2xl ${action.bgColor} border ${action.borderColor} hover:scale-[1.02] transition-all duration-300 relative overflow-hidden`}
            >
              <div className="absolute top-2 right-2 text-[10px] font-mono text-muted-foreground bg-background/50 px-2 py-0.5 rounded-full">
                {action.step}
              </div>
              <div className="flex flex-col gap-3">
                <div className={`w-12 h-12 rounded-xl bg-background/50 flex items-center justify-center group-hover:scale-110 transition-transform`}>
                  <action.icon className={`w-6 h-6 ${action.color}`} />
                </div>
                <div>
                  <span className="font-display font-bold block">{action.title}</span>
                  <span className="text-[10px] text-muted-foreground font-mono">{action.subtitle}</span>
                </div>
                <p className="text-xs text-muted-foreground">{action.description}</p>
              </div>
              <ChevronRight className={`absolute bottom-4 right-4 w-4 h-4 ${action.color} opacity-0 group-hover:opacity-100 transition-opacity`} />
            </Link>
          ))}
        </div>

        {/* Omnichannel Connections Widget */}
        <Card className="bg-card/50 border-border">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-primary" />
                  Conexiones Omnicanal
                </CardTitle>
                <CardDescription>Plataformas integradas con MerakiOS</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link to={ROUTES.SETTINGS.INTEGRATIONS}>
                  Gestionar
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              {platforms.map((platform) => (
                <div 
                  key={platform.name}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                    platform.connected 
                      ? 'bg-primary/10 border border-primary/30' 
                      : 'bg-muted/30 border border-border/50 opacity-50'
                  }`}
                >
                  <platform.icon className={`w-5 h-5 ${platform.connected ? platform.color : 'text-muted-foreground'}`} />
                  <div>
                    <span className="text-sm font-medium">{platform.name}</span>
                    {platform.connected ? (
                      <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                        <span className="text-[10px] text-green-400">Activo</span>
                      </div>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">Conectar</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Live Audit Canvas Preview */}
          <Card className="lg:col-span-2 bg-card/50 border-border overflow-hidden">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Eye className="w-5 h-5 text-amber-400" />
                    Canvas de Auditoría en Vivo
                  </CardTitle>
                  <CardDescription>Tu embudo de ventas en tiempo real</CardDescription>
                </div>
                <Button variant="outline" size="sm" asChild>
                  <Link to={ROUTES.SERVICES.FUNNEL_ARCHITECT}>
                    <Play className="w-4 h-4 mr-2" />
                    Abrir Editor
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <LiveAuditCanvas />
            </CardContent>
          </Card>

          {/* Suggested Actions */}
          <Card className="bg-card/50 border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-accent" />
                Próximos Pasos
              </CardTitle>
              <CardDescription>IA recomendando acciones</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {suggestedActions.map((action, index) => (
                  <Link
                    key={index}
                    to={action.url}
                    className="flex items-start gap-3 p-3 rounded-xl bg-muted/30 hover:bg-muted/50 border-l-2 border-primary transition-colors group"
                  >
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <action.icon className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{action.title}</p>
                      <p className="text-xs text-muted-foreground">{action.description}</p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0 mt-1" />
                  </Link>
                ))}
              </div>
              <Button variant="outline" className="w-full mt-4" size="sm">
                <Sparkles className="w-4 h-4 mr-2" />
                Más recomendaciones
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* CTA to Start Audit */}
        <Card className="bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-cyan-500/10 border-purple-500/20">
          <CardContent className="flex flex-col md:flex-row items-center justify-between gap-6 py-8">
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30 flex items-center justify-center">
                <Brain className="w-7 h-7 text-purple-400" />
              </div>
              <div>
                <h3 className="font-display font-bold text-xl">¿Listo para tu primera auditoría?</h3>
                <p className="text-muted-foreground">La IA analizará tu mercado y diseñará tu estrategia ganadora</p>
              </div>
            </div>
            <Button className="gradient-primary glow-primary px-8" size="lg" asChild>
              <Link to={ROUTES.SERVICES.MARKET_AUDIT}>
                <Target className="w-5 h-5 mr-2" />
                Iniciar Auditoría
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default AppHome;
