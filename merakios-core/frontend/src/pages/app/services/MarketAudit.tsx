// MerakiOS Market Audit Module
import { Helmet } from "react-helmet-async";
import { Brain, Radar, Target, Sparkles, Play, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState, useEffect } from "react";
import { api, Project } from "@/services/api";
import { toast } from "sonner";

const auditSteps = [
  { id: 1, title: "Análisis de Consciencia", description: "Niveles de awareness del mercado", key: "awareness_level" },
  { id: 2, title: "Mapeo de Competencia", description: "Identificación de players clave", key: "market_opportunity" },
  { id: 3, title: "Dolores del Cliente", description: "Pain points y motivaciones", key: "pain_points" },
  { id: 4, title: "Avatar", description: "Perfil del cliente ideal", key: "avatar" },
];

const MarketAudit = () => {
  const [isAuditing, setIsAuditing] = useState(false);
  const [niche, setNiche] = useState("");
  const [project, setProject] = useState<Project | null>(null);

  const handleStartAudit = async () => {
    if (!niche) return toast.error("Por favor ingresa un nicho de mercado");

    setIsAuditing(true);
    try {
      // 1. Create Project
      toast.info("Inicializando proyecto...");
      const newProject = await api.createProject(`Audit: ${niche}`, niche);
      setProject(newProject);

      // 2. Trigger Genesis
      toast.info("Invocando Agente Génesis...");
      await api.triggerGenesis(newProject.id);

      // 3. Poll for results
      pollProjectStatus(newProject.id);

    } catch (error) {
      console.error(error);
      toast.error("Error al iniciar la auditoría");
      setIsAuditing(false);
    }
  };

  const pollProjectStatus = async (projectId: string) => {
    const interval = setInterval(async () => {
      try {
        const p = await api.getProject(projectId);
        setProject(p);

        if (p.status === 'audited' || p.status === 'completed' || p.status === 'designing') {
          clearInterval(interval);
          setIsAuditing(false);
          toast.success("¡Auditoría Completada!");
        }
      } catch (e) {
        clearInterval(interval);
        setIsAuditing(false);
      }
    }, 3000); // Check every 3s
  };

  return (
    <>
      <Helmet>
        <title>Auditoría de Mercado - MerakiOS</title>
      </Helmet>

      <div className="space-y-8 animate-fade-in-up">
        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
            <Brain className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display text-3xl font-bold">Auditoría de Mercado</h1>
              <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">The Brain</span>
            </div>
            <p className="text-muted-foreground">Investigación autónoma antes de escribir una sola palabra</p>
          </div>
        </div>

        {/* Action Card */}
        <Card className="bg-gradient-to-r from-purple-500/10 to-violet-500/10 border-purple-500/20">
          <CardContent className="py-6 space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-purple-500/20 flex items-center justify-center">
                <Radar className={`w-8 h-8 text-purple-400 ${isAuditing ? 'animate-spin' : 'animate-pulse'}`} />
              </div>
              <div className="flex-1 space-y-2">
                <h3 className="font-display font-semibold text-lg">
                  {isAuditing ? "Analizando el mercado..." : "Agente de Auditoría listo"}
                </h3>
                <div className="flex gap-4">
                  <div className="grid w-full max-w-sm items-center gap-1.5">
                    <Label htmlFor="niche">Nicho de Mercado</Label>
                    <Input
                      id="niche"
                      placeholder="Ej: Yoga para ejecutivos estresados"
                      disabled={isAuditing}
                      value={niche}
                      onChange={(e) => setNiche(e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <Button
                className="gradient-primary"
                onClick={handleStartAudit}
                disabled={isAuditing || !niche}
              >
                {isAuditing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                {isAuditing ? "Investigando..." : "Iniciar Auditoría"}
              </Button>
            </div>
            {/* Live Logs (Simulation) */}
            {isAuditing && (
              <div className="text-xs font-mono text-purple-300 bg-black/20 p-2 rounded">
                {project?.status === 'analyzing' ? "> Agente Génesis: Buscando patrones en la web..." : "> Sistema: Esperando agente..."}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Audit Results */}
        <div className="grid md:grid-cols-2 gap-6">
          {auditSteps.map((step) => {
            const isDone = project?.audit_data && project.audit_data[step.key];
            return (
              <Card key={step.id} className={`bg-card/50 border-border transition-all ${isDone ? 'border-green-500/50 bg-green-500/5' : ''}`}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${isDone ? 'bg-green-500/20 text-green-400' : 'bg-primary/10 text-primary'}`}>
                        {step.id}
                      </div>
                      <div>
                        <CardTitle className="text-lg">{step.title}</CardTitle>
                        <CardDescription>{step.description}</CardDescription>
                      </div>
                    </div>
                    {isDone ? (
                      <CheckCircle2 className="w-5 h-5 text-green-400" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-muted-foreground" />
                    )}
                  </div>
                </CardHeader>
                {/* Result Content */}
                {isDone && (
                  <CardContent className="text-sm text-foreground/80 animate-fade-in">
                    {Array.isArray(project?.audit_data[step.key])
                      ? (
                        <ul className="list-disc pl-4 space-y-1">
                          {project?.audit_data[step.key].map((item: string, i: number) => <li key={i}>{item}</li>)}
                        </ul>
                      )
                      : <p>{project?.audit_data[step.key]}</p>
                    }
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>

        {/* Footer Info */}
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              ¿Qué obtendrás?
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Resultados generados en tiempo real por el Agente Génesis (OpenAI + Tavily + LangGraph).</p>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default MarketAudit;
