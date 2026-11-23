import { useState } from "react";
import { KanbanSquare, Loader2, MoreHorizontal, Plus } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState } from "@/components/common/States";
import { PageSkeleton } from "@/components/common/Loaders";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RequirePermission, usePermissions } from "@/features/auth/permissions";
import { useCreateDeal, useMoveDeal, usePipeline } from "@/features/crm/hooks";
import type { Deal, DealStage } from "@/lib/api";
import { fmtDate, fmtMoney } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { cn } from "@/lib/utils";

const STAGE_ACCENT: Record<DealStage, string> = {
  new: "bg-muted-foreground",
  qualified: "bg-heavy-cyan",
  proposal: "bg-heavy-blue",
  negotiation: "bg-heavy-violet",
  won: "bg-heavy-mint",
  lost: "bg-heavy-rose",
};

function NewDealDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const create = useCreateDeal();
  const [form, setForm] = useState({ title: "", amount: "", currency: "COP", expected_close: "" });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nuevo negocio</DialogTitle>
        </DialogHeader>
        <form
          id="deal-form"
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate(
              { title: form.title, amount: Number(form.amount), currency: form.currency, expected_close: form.expected_close || null },
              { onSuccess: () => onOpenChange(false) },
            );
          }}
        >
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="d-title">Título</Label>
            <Input id="d-title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="d-amount">Valor</Label>
            <Input id="d-amount" type="number" min={0} required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="d-currency">Moneda</Label>
            <Input id="d-currency" maxLength={3} value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="d-close">Cierre esperado</Label>
            <Input id="d-close" type="date" value={form.expected_close} onChange={(e) => setForm({ ...form, expected_close: e.target.value })} />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button type="submit" form="deal-form" disabled={create.isPending}>
            {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Crear
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Pipeline() {
  const { data, isLoading, error, refetch } = usePipeline();
  const move = useMoveDeal();
  const { can } = usePermissions();
  const canMove = can(PERMISSIONS.DEALS_MANAGE);
  const [creating, setCreating] = useState(false);
  const [dragging, setDragging] = useState<string | null>(null);
  const [over, setOver] = useState<DealStage | null>(null);

  if (isLoading) return <PageSkeleton />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;

  const stages = [...data.stages].sort((a, b) => a.order - b.order);
  const byStage = (s: DealStage) => data.deals.filter((d) => d.stage === s);
  const total = (deals: Deal[]) => deals.reduce((acc, d) => acc + Number(d.amount), 0);
  const weighted = stages.reduce((acc, s) => acc + total(byStage(s.key)) * s.probability, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline de negocios"
        description={`Valor ponderado: ${fmtMoney(weighted)}`}
        icon={KanbanSquare}
        accent="primary"
        actions={
          <RequirePermission permission={PERMISSIONS.DEALS_MANAGE}>
            <Button onClick={() => setCreating(true)}>
              <Plus className="mr-1 h-4 w-4" /> Nuevo negocio
            </Button>
          </RequirePermission>
        }
      />
      {data.deals.length === 0 && <EmptyState icon={KanbanSquare} title="Sin negocios" description="Crea tu primer negocio para empezar a pronosticar." />}
      <div className="-mx-4 flex snap-x gap-4 overflow-x-auto px-4 pb-4 sm:mx-0 sm:px-0">
        {stages.map((s) => {
          const deals = byStage(s.key);
          return (
            <section
              key={s.key}
              aria-label={s.name}
              className={cn("w-72 shrink-0 snap-start rounded-xl border bg-surface p-3 transition-colors", over === s.key && "border-heavy-blue bg-heavy-blue/5")}
              onDragOver={(e) => {
                if (!canMove) return;
                e.preventDefault();
                setOver(s.key);
              }}
              onDragLeave={() => setOver(null)}
              onDrop={() => {
                if (dragging) move.mutate({ id: dragging, stage: s.key });
                setDragging(null);
                setOver(null);
              }}
            >
              <header className="mb-3 flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <span className={cn("h-2 w-2 rounded-full", STAGE_ACCENT[s.key])} />
                  <h2 className="text-sm font-semibold">{s.name}</h2>
                  <span className="text-xs text-muted-foreground">{deals.length}</span>
                </div>
                <span className="text-xs text-muted-foreground">{Math.round(s.probability * 100)}%</span>
              </header>
              <p className="mb-3 px-1 text-xs text-muted-foreground">{fmtMoney(total(deals))}</p>
              <div className="space-y-2">
                {deals.map((d) => (
                  <Card
                    key={d.id}
                    draggable={canMove}
                    onDragStart={() => setDragging(d.id)}
                    className={cn("p-3 shadow-sm", canMove && "cursor-grab active:cursor-grabbing", dragging === d.id && "opacity-50")}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium">{d.title}</p>
                      {canMove && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="-mr-1 -mt-1 h-7 w-7" aria-label={`Mover ${d.title}`}>
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Mover a</DropdownMenuLabel>
                            {stages
                              .filter((x) => x.key !== d.stage)
                              .map((x) => (
                                <DropdownMenuItem key={x.key} onSelect={() => move.mutate({ id: d.id, stage: x.key })}>
                                  {x.name}
                                </DropdownMenuItem>
                              ))}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                    {d.contact_name && <p className="text-xs text-muted-foreground">{d.contact_name}</p>}
                    <div className="mt-2 flex items-center justify-between text-xs">
                      <span className="font-semibold">{fmtMoney(d.amount, d.currency)}</span>
                      {d.expected_close && <span className="text-muted-foreground">{fmtDate(d.expected_close, "d MMM")}</span>}
                    </div>
                  </Card>
                ))}
              </div>
            </section>
          );
        })}
      </div>
      {creating && <NewDealDialog open onOpenChange={setCreating} />}
    </div>
  );
}
