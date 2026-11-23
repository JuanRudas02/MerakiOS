import { CreditCard } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { Section } from "@/components/common/Section";
import { StatusBadge } from "@/components/common/StatusBadge";
import { PricingGrid } from "@/components/marketing/PricingGrid";
import { Skeleton } from "@/components/ui/skeleton";
import { useCheckout, useSubscription } from "@/features/billing/hooks";
import type { Checkout } from "@/lib/api";
import { fmtDate } from "@/lib/format";

const STATUS = {
  trialing: { label: "En prueba", tone: "info" },
  active: { label: "Activa", tone: "success" },
  past_due: { label: "Pago pendiente", tone: "warning" },
  canceled: { label: "Cancelada", tone: "danger" },
} as const;

/** Construye la URL del Web Checkout de Wompi con la firma de integridad generada en el backend. */
export function wompiCheckoutUrl(c: Checkout): string {
  const params = new URLSearchParams({
    "public-key": c.public_key,
    currency: c.currency,
    "amount-in-cents": String(c.amount_in_cents),
    reference: c.reference,
    "signature:integrity": c.signature,
    "redirect-url": c.redirect_url,
  });
  return `https://checkout.wompi.co/p/?${params.toString()}`;
}

export default function Billing() {
  const sub = useSubscription();
  const checkout = useCheckout();
  return (
    <div className="space-y-6">
      <PageHeader title="Facturación" description="Plan, estado de la suscripción y pagos con Wompi." icon={CreditCard} />
      <Section title="Suscripción actual">
        {sub.isLoading ? (
          <Skeleton className="h-12" />
        ) : sub.data ? (
          <div className="flex flex-wrap items-center gap-4">
            <p className="font-display text-2xl font-bold capitalize">{sub.data.plan}</p>
            <StatusBadge tone={STATUS[sub.data.status].tone}>{STATUS[sub.data.status].label}</StatusBadge>
            {sub.data.current_period_end && <p className="text-sm text-muted-foreground">Renueva el {fmtDate(sub.data.current_period_end)}</p>}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No pudimos cargar tu suscripción.</p>
        )}
      </Section>
      <PricingGrid
        currentPlan={sub.data?.plan}
        onSelect={(plan) =>
          checkout.mutate(plan, {
            onSuccess: (c) => {
              toast.info("Redirigiendo a Wompi…");
              window.location.assign(wompiCheckoutUrl(c));
            },
          })
        }
      />
    </div>
  );
}
