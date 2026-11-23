import { useState } from "react";
import { Link } from "react-router-dom";
import { Building2, MapPin, PauseCircle, Plus, Users } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState } from "@/components/common/States";
import { ListSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { RequirePermission } from "@/features/auth/permissions";
import { useCreateProperty, useProperties } from "@/features/stays/hooks";
import { PERMISSIONS } from "@/lib/permissions";
import { ROUTES } from "@/lib/routes";
import { PropertyFormDialog } from "./PropertyForm";

export default function Properties() {
  const { data, isLoading, error, refetch } = useProperties();
  const create = useCreateProperty();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const items = (data ?? []).filter((p) => `${p.code} ${p.name} ${p.address ?? ""}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Propiedades"
        description="Unidades, propietarios, cortes de servicios y sincronización de calendario."
        icon={Building2}
        accent="mint"
        actions={
          <RequirePermission permission={PERMISSIONS.PROPERTIES_MANAGE}>
            <Button onClick={() => setOpen(true)}>
              <Plus className="mr-1 h-4 w-4" /> Nueva propiedad
            </Button>
          </RequirePermission>
        }
      />
      <Input placeholder="Buscar por código, nombre o dirección…" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-sm" aria-label="Buscar propiedades" />
      {isLoading ? (
        <ListSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Building2}
          title={q ? "Sin resultados" : "Aún no tienes propiedades"}
          description="Registra tu primera unidad para programar limpiezas y controlar servicios."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((p) => (
            <Link key={p.id} to={ROUTES.APP.STAYS_PROPERTY(p.id)} className="group">
              <Card className="h-full p-5 transition-colors group-hover:border-heavy-mint/50">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-heavy-mint">{p.code}</p>
                    <h3 className="truncate text-lg font-semibold">{p.name}</h3>
                  </div>
                  {p.automation_paused && (
                    <StatusBadge tone="warning">
                      <PauseCircle className="mr-1 h-3 w-3" /> Pausada
                    </StatusBadge>
                  )}
                </div>
                {p.address && (
                  <p className="mt-2 flex items-center gap-1.5 text-sm text-muted-foreground">
                    <MapPin className="h-3.5 w-3.5" /> {p.address}
                  </p>
                )}
                <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Users className="h-3.5 w-3.5" /> {p.capacity} huéspedes
                  </span>
                  {p.owner_name && <span className="truncate">Propietario: {p.owner_name}</span>}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
      {open && (
        <PropertyFormDialog
          open={open}
          onOpenChange={setOpen}
          pending={create.isPending}
          onSubmit={(v) => create.mutate(v, { onSuccess: () => setOpen(false) })}
        />
      )}
    </div>
  );
}
