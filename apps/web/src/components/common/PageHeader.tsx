import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  description,
  icon: Icon,
  accent = "primary",
  actions,
}: {
  title: string;
  description?: string;
  icon?: LucideIcon;
  accent?: "primary" | "mint" | "violet" | "meta" | "ember" | "cyan";
  actions?: ReactNode;
}) {
  const tone = {
    primary: "bg-heavy-blue/15 text-heavy-blue",
    mint: "bg-heavy-mint/15 text-heavy-mint",
    violet: "bg-heavy-violet/15 text-heavy-violet",
    meta: "bg-heavy-meta/15 text-heavy-meta",
    ember: "bg-heavy-ember/15 text-heavy-ember",
    cyan: "bg-heavy-cyan/15 text-heavy-cyan",
  }[accent];
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-xl", tone)}>
            <Icon className="h-5 w-5" aria-hidden />
          </div>
        )}
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
          {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
