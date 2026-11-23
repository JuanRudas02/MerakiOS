import { useState } from "react";
import { Brush, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/features/auth/AuthProvider";
import { useUpdateBranding } from "@/features/identity/hooks";

export default function Brand() {
  const { workspace, setWorkspace } = useAuth();
  const update = useUpdateBranding();
  const [form, setForm] = useState({
    business_name: workspace?.business_name ?? "",
    logo_url: workspace?.logo_url ?? "",
    primary_color: workspace?.primary_color ?? "#3B5BFD",
  });
  return (
    <div className="space-y-6">
      <PageHeader title="Marca blanca" description="Tu equipo, propietarios y clientes ven tu marca, no la nuestra." icon={Brush} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Identidad">
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              update.mutate(
                { business_name: form.business_name, logo_url: form.logo_url || null, primary_color: form.primary_color },
                { onSuccess: (ws) => setWorkspace(ws) },
              );
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="b-name">Nombre comercial</Label>
              <Input id="b-name" required minLength={2} value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="b-logo">URL del logo</Label>
              <Input id="b-logo" type="url" value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="b-color">Color primario</Label>
              <div className="flex gap-2">
                <input
                  type="color"
                  aria-label="Selector de color"
                  value={form.primary_color}
                  onChange={(e) => setForm({ ...form, primary_color: e.target.value.toUpperCase() })}
                  className="h-10 w-14 cursor-pointer rounded-md border bg-transparent"
                />
                <Input id="b-color" pattern="^#[0-9A-Fa-f]{6}$" value={form.primary_color} onChange={(e) => setForm({ ...form, primary_color: e.target.value })} />
              </div>
            </div>
            <Button type="submit" disabled={update.isPending}>
              {update.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Guardar
            </Button>
          </form>
        </Section>
        <Section title="Vista previa del mensaje de WhatsApp">
          <div className="rounded-xl bg-[#0B141A] p-4">
            <div className="max-w-xs rounded-lg rounded-tl-none bg-[#202C33] p-3 text-sm text-[#E9EDEF]">
              <p>
                👋 Hola <strong>Luz</strong>, <strong>{form.business_name || "Tu empresa"}</strong> te asignó una limpieza mañana a las 11:00 en{" "}
                <strong>SKY-05</strong>.
              </p>
              <p className="mt-2 text-right text-[10px] text-[#8696A0]">10:42</p>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            {form.logo_url ? (
              <img src={form.logo_url} alt="Logo" className="h-10 w-10 rounded-lg object-cover" />
            ) : (
              <div className="h-10 w-10 rounded-lg" style={{ background: form.primary_color }} aria-hidden />
            )}
            <span className="font-semibold" style={{ color: form.primary_color }}>
              {form.business_name}
            </span>
          </div>
        </Section>
      </div>
    </div>
  );
}
