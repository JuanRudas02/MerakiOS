import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useStaff } from "@/features/stays/hooks";
import { BILLING_SERVICE_LABELS, type BillingService, type Property, type PropertyInput } from "@/lib/api";

const EMPTY: PropertyInput = {
  code: "",
  name: "",
  address: "",
  capacity: 2,
  owner_name: "",
  owner_phone: "",
  default_staff_id: null,
  billing_cutoffs: {},
  checklist_template: ["Tender camas", "Baño desinfectado", "Cocina limpia", "Reponer amenities"],
  visual_inventory: [],
  ical_url: "",
};

const lines = (v: string) => v.split("\n").map((s) => s.trim()).filter(Boolean);

export function PropertyFormDialog({
  open,
  onOpenChange,
  initial,
  onSubmit,
  pending,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  initial?: Property;
  onSubmit: (v: PropertyInput) => void;
  pending?: boolean;
}) {
  const [form, setForm] = useState<PropertyInput>(initial ?? EMPTY);
  const staff = useStaff();
  const set = <K extends keyof PropertyInput>(k: K, v: PropertyInput[K]) => setForm((f) => ({ ...f, [k]: v }));
  const nullable = (v: string | null | undefined) => (v ? v : null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{initial ? "Editar propiedad" : "Nueva propiedad"}</DialogTitle>
          <DialogDescription>Datos de la unidad, propietario, cortes de servicios y checklist.</DialogDescription>
        </DialogHeader>
        <form
          id="property-form"
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({
              ...form,
              address: nullable(form.address),
              owner_name: nullable(form.owner_name),
              owner_phone: nullable(form.owner_phone),
              ical_url: nullable(form.ical_url),
            });
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="p-code">Código</Label>
            <Input id="p-code" required value={form.code} onChange={(e) => set("code", e.target.value)} placeholder="SKY-05" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-name">Nombre</Label>
            <Input id="p-name" required value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="p-address">Dirección</Label>
            <Input id="p-address" value={form.address ?? ""} onChange={(e) => set("address", e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-capacity">Capacidad</Label>
            <Input id="p-capacity" type="number" min={1} value={form.capacity} onChange={(e) => set("capacity", Number(e.target.value))} />
          </div>
          <div className="space-y-1.5">
            <Label>Personal por defecto</Label>
            <Select value={form.default_staff_id ?? "none"} onValueChange={(v) => set("default_staff_id", v === "none" ? null : v)}>
              <SelectTrigger>
                <SelectValue placeholder="Sin asignar" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sin asignar</SelectItem>
                {staff.data?.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-owner">Propietario</Label>
            <Input id="p-owner" value={form.owner_name ?? ""} onChange={(e) => set("owner_name", e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-owner-phone">WhatsApp del propietario</Label>
            <Input id="p-owner-phone" type="tel" value={form.owner_phone ?? ""} onChange={(e) => set("owner_phone", e.target.value)} />
          </div>
          <fieldset className="sm:col-span-2">
            <legend className="mb-2 text-sm font-medium">Día de corte de servicios (1–31)</legend>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {(Object.keys(BILLING_SERVICE_LABELS) as BillingService[]).map((k) => (
                <div key={k} className="space-y-1">
                  <Label htmlFor={`cut-${k}`} className="text-xs text-muted-foreground">
                    {BILLING_SERVICE_LABELS[k]}
                  </Label>
                  <Input
                    id={`cut-${k}`}
                    type="number"
                    min={1}
                    max={31}
                    value={form.billing_cutoffs[k] ?? ""}
                    onChange={(e) =>
                      set("billing_cutoffs", { ...form.billing_cutoffs, [k]: e.target.value ? Number(e.target.value) : null })
                    }
                  />
                </div>
              ))}
            </div>
          </fieldset>
          <div className="space-y-1.5">
            <Label htmlFor="p-checklist">Checklist (uno por línea)</Label>
            <Textarea
              id="p-checklist"
              rows={5}
              value={form.checklist_template.join("\n")}
              onChange={(e) => set("checklist_template", lines(e.target.value))}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-inventory">Inventario visual (uno por línea)</Label>
            <Textarea
              id="p-inventory"
              rows={5}
              value={form.visual_inventory.join("\n")}
              onChange={(e) => set("visual_inventory", lines(e.target.value))}
            />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="p-ical">Enlace iCal (Airbnb / Booking)</Label>
            <Input id="p-ical" type="url" value={form.ical_url ?? ""} onChange={(e) => set("ical_url", e.target.value)} placeholder="https://www.airbnb.com/calendar/ical/…" />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button type="submit" form="property-form" disabled={pending}>
            {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
