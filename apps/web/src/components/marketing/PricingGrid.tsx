import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePlans } from "@/features/billing/hooks";
import { fmtMoney, fmtCompact } from "@/lib/format";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

export function PricingGrid({ onSelect, currentPlan }: { onSelect?: (plan: string) => void; currentPlan?: string }) {
  const { data, isLoading } = usePlans();
  if (isLoading) {
    return (
      <div className="grid gap-6 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-96 rounded-2xl" />
        ))}
      </div>
    );
  }
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {(data ?? []).map((plan) => {
        const featured = plan.key === "growth";
        const current = currentPlan === plan.key;
        return (
          <Card
            key={plan.key}
            className={cn("relative flex flex-col p-7 shadow-card", featured && "border-heavy-blue/60 shadow-glow")}
          >
            {featured && (
              <span className="absolute -top-3 left-7 rounded-full bg-gradient-heavy px-3 py-1 text-xs font-semibold text-white">
                Más elegido
              </span>
            )}
            <h3 className="text-xl font-bold">{plan.name}</h3>
            <p className="mt-4">
              <span className="font-display text-4xl font-bold">{fmtMoney(plan.price_cop)}</span>
              <span className="text-sm text-muted-foreground"> /mes</span>
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {plan.limits.properties} propiedades · {fmtCompact(plan.limits.contacts)} contactos · {plan.limits.seats} usuarios
            </p>
            <ul className="mt-6 flex-1 space-y-3">
              {plan.features.map((f) => (
                <li key={f} className="flex gap-2 text-sm">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-heavy-mint" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
            {onSelect ? (
              <Button className="mt-8" variant={featured ? "default" : "outline"} disabled={current} onClick={() => onSelect(plan.key)}>
                {current ? "Plan actual" : `Elegir ${plan.name}`}
              </Button>
            ) : (
              <Button className="mt-8" variant={featured ? "default" : "outline"} asChild>
                <Link to={`${ROUTES.PUBLIC.ACCESS}?modo=registro&plan=${plan.key}`}>Empezar con {plan.name}</Link>
              </Button>
            )}
          </Card>
        );
      })}
    </div>
  );
}
