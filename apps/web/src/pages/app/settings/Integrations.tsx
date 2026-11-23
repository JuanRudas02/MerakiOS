import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, CircleDashed, Loader2, Megaphone, MessageCircle, Plug, Target } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/AuthProvider";
import { usePermissions } from "@/features/auth/permissions";
import { useUpdateBranding } from "@/features/identity/hooks";
import { useMarketingStatus } from "@/features/marketing/hooks";
import { useMetaConnection } from "@/features/meta/hooks";
import { fmtRelative } from "@/lib/format";
import { PERMISSIONS } from "@/lib/permissions";
import { ROUTES } from "@/lib/routes";

function State({ ok, label }: { ok: boolean; label?: string }) {
  return ok ? (
    <StatusBadge tone="success">
      <CheckCircle2 className="mr-1 h-3 w-3" /> {label ?? "Conectado"}
    </StatusBadge>
  ) : (
    <StatusBadge tone="warning">
      <CircleDashed className="mr-1 h-3 w-3" /> {label ?? "Pendiente"}
    </StatusBadge>
  );
}

export default function Integrations() {
  const { can } = usePermissions();
  const { workspace, setWorkspace } = useAuth();
  const mautic = useMarketingStatus(can(PERMISSIONS.MARKETING_MANAGE));
  const meta = useMetaConnection(can(PERMISSIONS.META_MANAGE));
  const update = useUpdateBranding();
  const [instance, setInstance] = useState(workspace?.whatsapp_instance ?? "");

  return (
    <div className="space-y-6">
      <PageHeader title="Integraciones" description="Canales y plataformas conectadas a tu workspace." icon={Plug} />
      <div className="grid gap-6 lg:grid-cols-3">
        <Section title="WhatsApp" actions={<State ok={!!workspace?.whatsapp_instance} />}>
          <div className="space-y-3 text-sm">
            <p className="flex gap-2 text-muted-foreground">
              <MessageCircle className="h-4 w-4 shrink-0 text-heavy-mint" /> Cada empresa conecta su propio número escaneando un QR en Evolution API. Indica aquí el nombre de tu instancia.
            </p>
            {can(PERMISSIONS.WORKSPACE_MANAGE) && workspace && (
              <form
                className="space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  update.mutate(
                    { business_name: workspace.business_name, logo_url: workspace.logo_url, primary_color: workspace.primary_color, whatsapp_instance: instance },
                    { onSuccess: (ws) => setWorkspace(ws) },
                  );
                }}
              >
                <Label htmlFor="wa-instance">Instancia</Label>
                <div className="flex gap-2">
                  <Input id="wa-instance" value={instance} onChange={(e) => setInstance(e.target.value)} placeholder="mi-empresa-01" />
                  <Button type="submit" disabled={update.isPending}>
                    {update.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Guardar"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </Section>

        {can(PERMISSIONS.MARKETING_MANAGE) && (
          <Section title="Mautic" actions={mautic.data && <State ok={mautic.data.connected} label={mautic.data.mautic_enabled ? undefined : "Desactivado"} />}>
            {mautic.isLoading ? (
              <Skeleton className="h-20" />
            ) : (
              <div className="space-y-3 text-sm">
                <p className="flex gap-2 text-muted-foreground">
                  <Megaphone className="h-4 w-4 shrink-0 text-heavy-violet" /> Marketing automation open source. Se configura en el servidor (variables ONEHEAVY_MAUTIC_*).
                </p>
                {mautic.data?.last_sync_at && <p>Última sincronización {fmtRelative(mautic.data.last_sync_at)}</p>}
                <Button variant="outline" size="sm" asChild>
                  <Link to={ROUTES.APP.MARKETING}>Abrir Marketing</Link>
                </Button>
              </div>
            )}
          </Section>
        )}

        {can(PERMISSIONS.META_MANAGE) && (
          <Section title="Meta Business" actions={meta.data && <State ok={meta.data.connected} />}>
            {meta.isLoading ? (
              <Skeleton className="h-20" />
            ) : (
              <div className="space-y-3 text-sm">
                <p className="flex gap-2 text-muted-foreground">
                  <Target className="h-4 w-4 shrink-0 text-heavy-meta" /> Cuenta publicitaria, Lead Ads y Conversions API.
                </p>
                {meta.data?.ad_account_id && <p className="font-mono text-xs">{meta.data.ad_account_id}</p>}
                <Button variant="outline" size="sm" asChild>
                  <Link to={ROUTES.APP.META}>{meta.data?.connected ? "Ver campañas" : "Conectar"}</Link>
                </Button>
              </div>
            )}
          </Section>
        )}
      </div>
    </div>
  );
}
