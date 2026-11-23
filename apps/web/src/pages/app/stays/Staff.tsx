import { useState } from "react";
import { Loader2, Phone, Plus, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RequirePermission } from "@/features/auth/permissions";
import { useCreateStaff, useStaff } from "@/features/stays/hooks";
import type { StaffCategory } from "@/lib/api";
import { initials } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";

const CATEGORY: Record<StaffCategory, string> = { cleaning: "Limpieza", maintenance: "Mantenimiento" };

export default function Staff() {
  const { data, isLoading, error, refetch } = useStaff();
  const create = useCreateStaff();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "", category: "cleaning" as StaffCategory });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Personal operativo"
        description="Equipo de limpieza y mantenimiento. Reciben sus asignaciones por WhatsApp."
        icon={UsersRound}
        accent="mint"
        actions={
          <RequirePermission permission={PERMISSIONS.TASKS_MANAGE}>
            <Button onClick={() => setOpen(true)}>
              <Plus className="mr-1 h-4 w-4" /> Agregar colaborador
            </Button>
          </RequirePermission>
        }
      />
      {isLoading ? (
        <ListSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data?.length ? (
        <EmptyState icon={UsersRound} title="Sin personal registrado" description="Agrega colaboradores o invítalos desde Ajustes → Equipo para darles acceso." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.map((s) => (
            <Card key={s.id} className="flex items-center gap-4 p-5">
              <Avatar className="h-11 w-11">
                <AvatarFallback className="bg-heavy-mint/15 font-semibold text-heavy-mint">{initials(s.name)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{s.name}</p>
                <p className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Phone className="h-3 w-3" /> {s.phone}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <StatusBadge tone="success">{CATEGORY[s.category]}</StatusBadge>
                  {s.has_login && <StatusBadge tone="info">Con acceso</StatusBadge>}
                  {!s.active && <StatusBadge tone="danger">Inactivo</StatusBadge>}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo colaborador</DialogTitle>
          </DialogHeader>
          <form
            id="staff-form"
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate(form, {
                onSuccess: () => {
                  setOpen(false);
                  setForm({ name: "", phone: "", category: "cleaning" });
                },
              });
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="s-name">Nombre</Label>
              <Input id="s-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="s-phone">WhatsApp</Label>
              <Input id="s-phone" required type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="300 123 4567" />
            </div>
            <div className="space-y-1.5">
              <Label>Categoría</Label>
              <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v as StaffCategory })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cleaning">Limpieza</SelectItem>
                  <SelectItem value="maintenance">Mantenimiento</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" form="staff-form" disabled={create.isPending}>
              {create.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
