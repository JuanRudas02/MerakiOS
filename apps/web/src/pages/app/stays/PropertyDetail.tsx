import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Building2, CalendarSync, Check, FileUp, Loader2, Pencil, X } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { EmptyState, ErrorState } from "@/components/common/States";
import { PageSkeleton } from "@/components/common/Loaders";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RequirePermission } from "@/features/auth/permissions";
import { useProperty, useReceipts, useReviewReceipt, useSyncCalendar, useUpdateProperty, useUploadReceipt } from "@/features/stays/hooks";
import { BILLING_SERVICE_LABELS, fileUrl, type BillingService, type ReceiptStatus } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { ROUTES } from "@/lib/routes";
import { PropertyFormDialog } from "./PropertyForm";

const RECEIPT_TONE: Record<ReceiptStatus, "warning" | "success" | "danger"> = { pending: "warning", verified: "success", rejected: "danger" };
const RECEIPT_LABEL: Record<ReceiptStatus, string> = { pending: "Pendiente", verified: "Verificado", rejected: "Rechazado" };

function ReceiptUpload({ propertyId }: { propertyId: string }) {
  const upload = useUploadReceipt(propertyId);
  const [file, setFile] = useState<File | null>(null);
  const [service, setService] = useState<BillingService>("electricity");
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  return (
    <form
      className="grid gap-3 sm:grid-cols-4 sm:items-end"
      onSubmit={(e) => {
        e.preventDefault();
        if (file) upload.mutate({ file, service, period }, { onSuccess: () => setFile(null) });
      }}
    >
      <div className="space-y-1.5">
        <Label>Servicio</Label>
        <Select value={service} onValueChange={(v) => setService(v as BillingService)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(BILLING_SERVICE_LABELS) as BillingService[]).map((k) => (
              <SelectItem key={k} value={k}>
                {BILLING_SERVICE_LABELS[k]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="r-period">Periodo</Label>
        <Input id="r-period" type="month" value={period} onChange={(e) => setPeriod(e.target.value)} required />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="r-file">Comprobante (JPG, PNG, WEBP o PDF · máx. 10 MB)</Label>
        <Input id="r-file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
      </div>
      <Button type="submit" disabled={!file || upload.isPending}>
        {upload.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileUp className="mr-2 h-4 w-4" />} Cargar
      </Button>
    </form>
  );
}

export default function PropertyDetail() {
  const { id = "" } = useParams();
  const property = useProperty(id);
  const receipts = useReceipts(id);
  const update = useUpdateProperty(id);
  const sync = useSyncCalendar(id);
  const review = useReviewReceipt();
  const [editing, setEditing] = useState(false);

  if (property.isLoading) return <PageSkeleton />;
  if (property.error || !property.data) return <ErrorState error={property.error} onRetry={() => property.refetch()} />;
  const p = property.data;
  const cutoffs = (Object.keys(BILLING_SERVICE_LABELS) as BillingService[]).filter((k) => p.billing_cutoffs[k]);

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={ROUTES.APP.STAYS_PROPERTIES}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Propiedades
        </Link>
      </Button>
      <PageHeader
        title={p.name}
        description={`${p.code}${p.address ? ` · ${p.address}` : ""}`}
        icon={Building2}
        accent="mint"
        actions={
          <RequirePermission permission={PERMISSIONS.PROPERTIES_MANAGE}>
            <Button variant="outline" onClick={() => sync.mutate()} disabled={!p.ical_url || sync.isPending} title={p.ical_url ? undefined : "Configura el enlace iCal"}>
              {sync.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CalendarSync className="mr-2 h-4 w-4" />}
              Sincronizar iCal
            </Button>
            <Button onClick={() => setEditing(true)}>
              <Pencil className="mr-2 h-4 w-4" /> Editar
            </Button>
          </RequirePermission>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Section title="Ficha">
          <dl className="space-y-3 text-sm">
            {[
              ["Capacidad", `${p.capacity} huéspedes`],
              ["Propietario", p.owner_name ?? "—"],
              ["WhatsApp propietario", p.owner_phone ?? "—"],
              ["Automatización", p.automation_paused ? "Pausada (comprobante pendiente)" : "Activa"],
              ["Calendario", p.ical_url ? "Conectado" : "Sin iCal"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4">
                <dt className="text-muted-foreground">{k}</dt>
                <dd className="text-right font-medium">{v}</dd>
              </div>
            ))}
          </dl>
        </Section>
        <Section title="Cortes de servicios">
          {cutoffs.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin cortes configurados.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {cutoffs.map((k) => (
                <li key={k} className="flex justify-between">
                  <span>{BILLING_SERVICE_LABELS[k]}</span>
                  <span className="font-medium">Día {p.billing_cutoffs[k]}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="Checklist de limpieza">
          {p.checklist_template.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin ítems.</p>
          ) : (
            <ul className="space-y-1.5 text-sm">
              {p.checklist_template.map((i) => (
                <li key={i} className="flex gap-2">
                  <Check className="mt-0.5 h-4 w-4 text-heavy-mint" /> {i}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Comprobantes de servicios" description="Los propietarios cargan sus soportes y el equipo los verifica.">
        <RequirePermission permission={PERMISSIONS.RECEIPTS_UPLOAD}>
          <div className="mb-6 rounded-lg border bg-elevated/40 p-4">
            <ReceiptUpload propertyId={id} />
          </div>
        </RequirePermission>
        {receipts.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : receipts.error ? (
          <ErrorState error={receipts.error} />
        ) : !receipts.data?.length ? (
          <EmptyState title="Sin comprobantes" description="Aún no se han cargado soportes de pago." />
        ) : (
          <ul className="divide-y">
            {receipts.data.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <a href={fileUrl(r.url)} target="_blank" rel="noreferrer" className="font-medium hover:underline">
                    {BILLING_SERVICE_LABELS[r.service as BillingService] ?? r.service} · {r.period}
                  </a>
                  <p className="text-xs text-muted-foreground">
                    Cargado {fmtDate(r.uploaded_at)}
                    {r.note ? ` · ${r.note}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge tone={RECEIPT_TONE[r.status]}>{RECEIPT_LABEL[r.status]}</StatusBadge>
                  {r.status === "pending" && (
                    <RequirePermission permission={PERMISSIONS.RECEIPTS_VERIFY}>
                      <Button size="sm" variant="outline" onClick={() => review.mutate({ id: r.id, approved: true })} aria-label="Aprobar">
                        <Check className="h-4 w-4 text-heavy-mint" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => review.mutate({ id: r.id, approved: false, note: "Soporte ilegible o incorrecto" })}
                        aria-label="Rechazar"
                      >
                        <X className="h-4 w-4 text-heavy-rose" />
                      </Button>
                    </RequirePermission>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {editing && (
        <PropertyFormDialog
          open={editing}
          onOpenChange={setEditing}
          initial={p}
          pending={update.isPending}
          onSubmit={(v) => update.mutate(v, { onSuccess: () => setEditing(false) })}
        />
      )}
    </div>
  );
}
