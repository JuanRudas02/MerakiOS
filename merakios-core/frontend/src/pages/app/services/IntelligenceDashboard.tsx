import { Helmet } from "react-helmet-async";
import { Eye, Activity, AlertTriangle, CheckCircle2, TrendingUp, BarChart3, ArrowRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { ROUTES } from "@/lib/routes";

// Live Audit Canvas
const LiveCanvas = () => {
  return (
    <div className="relative h-72 rounded-xl bg-card/30 border border-border/50 overflow-hidden">
      <div className="absolute inset-0 p-4">
        <svg viewBox="0 0 500 220" className="w-full h-full">
          {/* Connection lines */}
          <path d="M60,110 C120,110 100,50 180,50" stroke="hsl(var(--primary))" strokeWidth="2" fill="none" opacity="0.5" />
          <path d="M180,50 C240,50 220,90 300,80" stroke="hsl(142 76% 36%)" strokeWidth="2" fill="none" opacity="0.5" />
          <path d="M300,80 C360,80 350,50 420,60" stroke="hsl(142 76% 36%)" strokeWidth="2" fill="none" opacity="0.5" />
          <path d="M60,110 C120,110 100,170 180,170" stroke="hsl(var(--primary))" strokeWidth="2" fill="none" opacity="0.5" />
          <path d="M180,170 C240,170 230,130 300,140" stroke="hsl(0 72% 51%)" strokeWidth="2" fill="none" opacity="0.5" />
          <path d="M300,140 C360,140 350,170 420,160" stroke="hsl(0 72% 51%)" strokeWidth="2" fill="none" opacity="0.5" />
          
          {/* Nodes */}
          <g className="animate-pulse">
            <rect x="35" y="90" width="55" height="40" rx="6" fill="hsl(var(--card))" stroke="hsl(var(--primary))" strokeWidth="2" />
            <text x="62" y="115" textAnchor="middle" className="text-[11px] fill-primary font-semibold">INICIO</text>
          </g>
          
          <g>
            <rect x="155" y="30" width="55" height="40" rx="6" fill="hsl(var(--card))" stroke="hsl(142 76% 36%)" strokeWidth="2" />
            <text x="182" y="55" textAnchor="middle" className="text-[11px] font-semibold" fill="hsl(142 76% 36%)">AWARE</text>
            <circle cx="200" cy="40" r="5" fill="hsl(142 76% 36%)" className="animate-pulse" />
          </g>
          
          <g>
            <rect x="155" y="150" width="55" height="40" rx="6" fill="hsl(var(--card))" stroke="hsl(0 72% 51%)" strokeWidth="2" />
            <text x="182" y="175" textAnchor="middle" className="text-[11px] font-semibold" fill="hsl(0 72% 51%)">DROP</text>
            <circle cx="200" cy="160" r="5" fill="hsl(0 72% 51%)" className="animate-pulse" />
          </g>
          
          <g>
            <rect x="275" y="60" width="55" height="40" rx="6" fill="hsl(var(--card))" stroke="hsl(142 76% 36%)" strokeWidth="2" />
            <text x="302" y="85" textAnchor="middle" className="text-[11px] font-semibold" fill="hsl(142 76% 36%)">ENGAGE</text>
          </g>
          
          <g>
            <rect x="275" y="120" width="55" height="40" rx="6" fill="hsl(var(--card))" stroke="hsl(0 72% 51%)" strokeWidth="2" />
            <text x="302" y="145" textAnchor="middle" className="text-[11px] font-semibold" fill="hsl(0 72% 51%)">ALERT</text>
            <circle cx="320" cy="130" r="5" fill="hsl(0 72% 51%)" className="animate-pulse" />
          </g>
          
          <g>
            <rect x="395" y="40" width="55" height="40" rx="6" fill="hsl(var(--card))" stroke="hsl(142 76% 36%)" strokeWidth="2" />
            <text x="422" y="65" textAnchor="middle" className="text-[11px] font-semibold" fill="hsl(142 76% 36%)">CONV</text>
          </g>
          
          <g>
            <rect x="395" y="140" width="55" height="40" rx="6" fill="hsl(var(--card))" stroke="hsl(0 72% 51%)" strokeWidth="2" />
            <text x="422" y="165" textAnchor="middle" className="text-[11px] font-semibold" fill="hsl(0 72% 51%)">EXIT</text>
          </g>
        </svg>
      </div>
      
      {/* Status indicators */}
      <div className="absolute top-3 right-3 flex gap-2">
        <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-green-500/10 border border-green-500/30">
          <CheckCircle2 className="w-3 h-3 text-green-400" />
          <span className="text-[10px] text-green-400 font-medium">3 OK</span>
        </div>
        <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-destructive/10 border border-destructive/30">
          <AlertTriangle className="w-3 h-3 text-destructive" />
          <span className="text-[10px] text-destructive font-medium">3 Alertas</span>
        </div>
      </div>
      
      <div className="absolute bottom-3 left-3 flex items-center gap-2 text-xs text-muted-foreground">
        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        <span className="font-mono">live_audit</span> · Actualizado hace 30s
      </div>
    </div>
  );
};

const IntelligenceDashboard = () => {
  return (
    <>
      <Helmet>
        <title>Dashboard de Inteligencia - MerakiOS</title>
      </Helmet>

      <div className="space-y-8 animate-fade-in-up">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
              <Eye className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-display text-3xl font-bold">Dashboard de Inteligencia</h1>
                <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">The Director</span>
              </div>
              <p className="text-muted-foreground">Supervisión en tiempo real de tu estrategia</p>
            </div>
          </div>
          <Button variant="outline" asChild>
            <Link to={ROUTES.SERVICES.METRICS}>
              <BarChart3 className="w-4 h-4 mr-2" />
              Ver Métricas
            </Link>
          </Button>
        </div>

        {/* Live Canvas */}
        <Card className="bg-card/50 border-border overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-amber-400" />
              Canvas de Auditoría en Vivo
            </CardTitle>
            <CardDescription>Compara tu plan inicial con la realidad</CardDescription>
          </CardHeader>
          <CardContent>
            <LiveCanvas />
          </CardContent>
        </Card>

        {/* Metrics Grid */}
        <div className="grid md:grid-cols-3 gap-6">
          <Card className="bg-card/50 border-border">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">Tasa de Conversión</CardTitle>
                <TrendingUp className="w-4 h-4 text-green-400" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-green-400">+23%</p>
              <p className="text-xs text-muted-foreground">vs. semana anterior</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">Cuellos de Botella</CardTitle>
                <AlertTriangle className="w-4 h-4 text-destructive" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-destructive">2</p>
              <p className="text-xs text-muted-foreground">detectados esta semana</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">Nodos Activos</CardTitle>
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">6/8</p>
              <p className="text-xs text-muted-foreground">funcionando correctamente</p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border-amber-500/20">
          <CardContent className="flex flex-col md:flex-row items-center justify-between gap-4 py-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-amber-500/20 flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-amber-400" />
              </div>
              <div>
                <h3 className="font-display font-semibold">Conecta Meta para métricas reales</h3>
                <p className="text-sm text-muted-foreground">Vincula Facebook e Instagram para datos en vivo</p>
              </div>
            </div>
            <Button className="gradient-primary" asChild>
              <Link to={ROUTES.SETTINGS.META}>
                Conectar Meta
                <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default IntelligenceDashboard;
