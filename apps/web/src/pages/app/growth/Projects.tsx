import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, Plus, Rocket } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateProject, useProjects } from "@/features/growth/hooks";
import type { ProjectStatus } from "@/lib/api";
import { fmtRelative } from "@/lib/format";
import { ROUTES } from "@/lib/routes";

export const PROJECT_STATUS: Record<ProjectStatus, { label: string; tone: "neutral" | "info" | "violet" | "warning" | "success" | "danger" }> = {
  draft: { label: "Borrador", tone: "neutral" },
  analyzing: { label: "Investigando", tone: "info" },
  audited: { label: "Auditado", tone: "violet" },
  designing: { label: "Diseñando embudo", tone: "warning" },
  completed: { label: "Completo", tone: "success" },
  failed: { label: "Falló", tone: "danger" },
};

export default function Projects() {
  const { data, isLoading, error, refetch } = useProjects();
  const create = useCreateProject();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", niche: "", url: "" });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Growth IA"
        description="Agentes que investigan tu mercado, auditan la oportunidad y diseñan tu embudo."
        icon={Rocket}
        accent="violet"
        actions={
          <Button onClick={() => setOpen(true)} className="bg-gradient-heavy text-white">
            <Plus className="mr-1 h-4 w-4" /> Nuevo proyecto
          </Button>
        }
      />
      {isLoading ? (
        <ListSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState icon={Rocket} title="Sin proyectos" description="Crea un proyecto con tu nicho y deja que la IA haga la investigación." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.map((p) => (
            <Link key={p.id} to={ROUTES.APP.GROWTH_PROJECT(p.id)} className="group">
              <Card className="h-full p-5 transition-colors group-hover:border-heavy-violet/50">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold">{p.name}</h3>
                  <StatusBadge tone={PROJECT_STATUS[p.status].tone}>{PROJECT_STATUS[p.status].label}</StatusBadge>
                </div>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{p.niche}</p>
                <p className="mt-4 text-xs text-muted-foreground">Actualizado {fmtRelative(p.updated_at)}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo proyecto de growth</DialogTitle>
            <DialogDescription>Mientras más específico el nicho, mejor la auditoría.</DialogDescription>
          </DialogHeader>
          <form
            id="project-form"
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate(
                { name: form.name, niche: form.niche, url: form.url || undefined },
                { onSuccess: (p) => navigate(ROUTES.APP.GROWTH_PROJECT(p.id)) },
              );
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="g-name">Nombre</Label>
              <Input id="g-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="g-niche">Nicho / oferta</Label>
              <Input id="g-niche" required placeholder="Administración de Airbnb para inversionistas en Medellín" value={form.niche} onChange={(e) => setForm({ ...form, niche: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="g-url">Sitio web (opcional)</Label>
              <Input id="g-url" type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="project-form" disabled={create.isPending}>
              {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Crear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
