import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Bot, Brain, Loader2, Network, Search, Sparkles, Target, Workflow } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { EmptyState, ErrorState } from "@/components/common/States";
import { PageSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useGenerateAssets, useProject, useRunAudit, useRunFunnel } from "@/features/growth/hooks";
import { AWARENESS_LABELS, type AwarenessLevel, type GeneratedAsset } from "@/lib/api";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";
import { FunnelCanvas } from "./FunnelCanvas";
import { PROJECT_STATUS } from "./Projects";

const AWARENESS_ORDER: AwarenessLevel[] = ["unaware", "problem_aware", "solution_aware", "product_aware", "most_aware"];
const PIPELINE = [
  { icon: Brain, label: "Planner" },
  { icon: Search, label: "Research" },
  { icon: Target, label: "Auditor" },
  { icon: Workflow, label: "Architect" },
];

function List({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (!items?.length) return null;
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <ul className="space-y-1.5 text-sm">
        {items.map((i) => (
          <li key={i} className="flex gap-2">
            <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", tone)} /> {i}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ProjectDetail() {
  const { id = "" } = useParams();
  const { data: p, isLoading, error, refetch } = useProject(id);
  const audit = useRunAudit();
  const funnel = useRunFunnel();
  const assets = useGenerateAssets();
  const [node, setNode] = useState<string | undefined>();
  const [kind, setKind] = useState<GeneratedAsset["kind"]>("ad");

  if (isLoading) return <PageSkeleton />;
  if (error || !p) return <ErrorState error={error} onRetry={() => refetch()} />;

  const busy = p.status === "analyzing" || p.status === "designing";
  // Estado de cada agente: Planner/Research/Auditor (auditoría) y Architect (embudo).
  const stepState = (i: number): "idle" | "running" | "done" => {
    const isAuditStep = i < 3;
    if (p.status === "analyzing") return isAuditStep ? "running" : "idle";
    if (p.status === "designing") return isAuditStep ? "done" : "running";
    if (p.status === "audited") return isAuditStep ? "done" : "idle";
    if (p.status === "completed") return "done";
    return "idle";
  };

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={ROUTES.APP.GROWTH}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Proyectos
        </Link>
      </Button>
      <PageHeader
        title={p.name}
        description={p.niche}
        icon={Sparkles}
        accent="violet"
        actions={
          <>
            <StatusBadge tone={PROJECT_STATUS[p.status].tone}>{PROJECT_STATUS[p.status].label}</StatusBadge>
            <Button variant="outline" onClick={() => audit.mutate(id)} disabled={busy || audit.isPending}>
              <Search className="mr-2 h-4 w-4" /> {p.audit ? "Re-auditar" : "Auditar mercado"}
            </Button>
            <Button
              onClick={() => funnel.mutate(id)}
              disabled={busy || !p.audit || funnel.isPending}
              className="bg-gradient-heavy text-white"
              title={!p.audit ? "Primero audita el mercado" : undefined}
            >
              <Network className="mr-2 h-4 w-4" /> Diseñar embudo
            </Button>
          </>
        }
      />

      <ol className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Pipeline de agentes">
        {PIPELINE.map((s, i) => {
          const state = stepState(i);
          const running = state === "running";
          const done = state === "done";
          return (
            <li
              key={s.label}
              className={cn(
                "flex items-center gap-3 rounded-xl border p-3 text-sm",
                done && "border-heavy-violet/40 bg-heavy-violet/5",
                running && "border-heavy-cyan/60 bg-heavy-cyan/5",
              )}
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin text-heavy-cyan" /> : <s.icon className={cn("h-4 w-4", done ? "text-heavy-violet" : "text-muted-foreground")} />}
              {s.label}
            </li>
          );
        })}
      </ol>

      {p.status === "failed" && p.error && <ErrorState error={new Error(p.error)} />}

      {!p.audit ? (
        <EmptyState
          icon={Bot}
          title={busy ? "Los agentes están investigando…" : "Sin auditoría aún"}
          description={busy ? "Esto suele tardar uno o dos minutos. La página se actualiza sola." : "Ejecuta la auditoría de mercado para obtener avatar, dolores y nivel de conciencia."}
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <Section title="Avatar" className="lg:col-span-2">
            <p className="text-sm leading-relaxed">{p.audit.avatar}</p>
            <div className="mt-6 grid gap-6 sm:grid-cols-2">
              <List title="Dolores" items={p.audit.pain_points} tone="bg-heavy-rose" />
              <List title="Deseos" items={p.audit.desires} tone="bg-heavy-mint" />
              <List title="Jobs To Be Done" items={p.audit.jobs_to_be_done} tone="bg-heavy-cyan" />
              <List title="Competidores" items={p.audit.competitors} tone="bg-heavy-ember" />
            </div>
          </Section>
          <div className="space-y-6">
            <Section title="Nivel de conciencia (Schwartz)">
              <ol className="space-y-1.5">
                {AWARENESS_ORDER.map((a) => (
                  <li
                    key={a}
                    className={cn(
                      "rounded-lg px-3 py-2 text-sm",
                      a === p.audit!.awareness_level ? "bg-gradient-heavy font-semibold text-white" : "text-muted-foreground",
                    )}
                    aria-current={a === p.audit!.awareness_level}
                  >
                    {AWARENESS_LABELS[a]}
                  </li>
                ))}
              </ol>
            </Section>
            <Section title="Oportunidad de mercado">
              <p className="text-sm leading-relaxed">{p.audit.market_opportunity}</p>
            </Section>
          </div>
        </div>
      )}

      {p.funnel && p.funnel.nodes.length > 0 && (
        <Section title="Embudo diseñado" description="Selecciona un nodo para generar activos específicos.">
          <FunnelCanvas funnel={p.funnel} selected={node} onSelect={(n) => setNode(n === node ? undefined : n)} />
        </Section>
      )}

      {p.audit && (
        <Section
          title="Generar activos"
          description={node ? `Para el nodo seleccionado` : "Para el embudo completo"}
          actions={
            <>
              <ToggleGroup type="single" value={kind} onValueChange={(v) => v && setKind(v as GeneratedAsset["kind"])} aria-label="Tipo de activo">
                <ToggleGroupItem value="ad">Anuncio</ToggleGroupItem>
                <ToggleGroupItem value="landing">Landing</ToggleGroupItem>
                <ToggleGroupItem value="email">Email</ToggleGroupItem>
              </ToggleGroup>
              <Button onClick={() => assets.mutate({ id, kind, node_id: node })} disabled={assets.isPending}>
                {assets.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Bot className="mr-2 h-4 w-4" />} Generar
              </Button>
            </>
          }
        >
          {!assets.data ? (
            <p className="text-sm text-muted-foreground">Los copys aparecerán aquí.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {assets.data.assets.map((a, i) => (
                <Card key={i} className="p-4">
                  <p className="text-xs font-semibold uppercase text-heavy-violet">{a.kind}</p>
                  <h3 className="mt-1 font-semibold">{a.title}</h3>
                  <p className="mt-2 whitespace-pre-line text-sm text-muted-foreground">{a.body}</p>
                </Card>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  );
}
