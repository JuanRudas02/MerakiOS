import { useMemo } from "react";
import { FileText, Gift, Mail, Megaphone, MousePointerClick, PlayCircle, ShoppingCart, ThumbsUp, type LucideIcon } from "lucide-react";
import type { Funnel, FunnelNodeType } from "@/lib/api";
import { cn } from "@/lib/utils";

const NODE_META: Record<FunnelNodeType, { icon: LucideIcon; label: string; cls: string }> = {
  ad: { icon: Megaphone, label: "Anuncio", cls: "border-heavy-meta/50 text-heavy-meta" },
  landing: { icon: FileText, label: "Landing", cls: "border-heavy-blue/50 text-heavy-blue" },
  optin: { icon: MousePointerClick, label: "Opt-in", cls: "border-heavy-cyan/50 text-heavy-cyan" },
  vsl: { icon: PlayCircle, label: "VSL", cls: "border-heavy-violet/50 text-heavy-violet" },
  email: { icon: Mail, label: "Email", cls: "border-heavy-violet/50 text-heavy-violet" },
  checkout: { icon: ShoppingCart, label: "Checkout", cls: "border-heavy-mint/50 text-heavy-mint" },
  upsell: { icon: Gift, label: "Upsell", cls: "border-heavy-ember/50 text-heavy-ember" },
  thankyou: { icon: ThumbsUp, label: "Gracias", cls: "border-heavy-mint/50 text-heavy-mint" },
};

const NODE_W = 168;
const NODE_H = 64;
const PAD = 24;

/**
 * Visualiza el embudo devuelto por el agente Blueprint. Usa las posiciones del
 * backend; si vienen vacías/colapsadas, distribuye los nodos por niveles (BFS).
 */
export function FunnelCanvas({ funnel, selected, onSelect }: { funnel: Funnel; selected?: string; onSelect?: (id: string) => void }) {
  const layout = useMemo(() => {
    const positions = new Map(funnel.nodes.map((n) => [n.id, { x: n.position?.x ?? 0, y: n.position?.y ?? 0 }]));
    const distinct = new Set(funnel.nodes.map((n) => `${n.position?.x},${n.position?.y}`)).size;
    if (distinct < funnel.nodes.length) {
      const incoming = new Map(funnel.nodes.map((n) => [n.id, 0]));
      funnel.edges.forEach((e) => incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1));
      const level = new Map<string, number>();
      const queue = funnel.nodes.filter((n) => !incoming.get(n.id)).map((n) => n.id);
      queue.forEach((id) => level.set(id, 0));
      while (queue.length) {
        const id = queue.shift()!;
        funnel.edges
          .filter((e) => e.source === id && !level.has(e.target))
          .forEach((e) => {
            level.set(e.target, (level.get(id) ?? 0) + 1);
            queue.push(e.target);
          });
      }
      const rows = new Map<number, number>();
      funnel.nodes.forEach((n, i) => {
        const l = level.get(n.id) ?? i;
        const r = rows.get(l) ?? 0;
        rows.set(l, r + 1);
        positions.set(n.id, { x: l * (NODE_W + 56), y: r * (NODE_H + 32) });
      });
    }
    const xs = [...positions.values()].map((p) => p.x);
    const ys = [...positions.values()].map((p) => p.y);
    const minX = Math.min(...xs, 0);
    const minY = Math.min(...ys, 0);
    positions.forEach((p, k) => positions.set(k, { x: p.x - minX + PAD, y: p.y - minY + PAD }));
    const width = Math.max(...[...positions.values()].map((p) => p.x)) + NODE_W + PAD;
    const height = Math.max(...[...positions.values()].map((p) => p.y)) + NODE_H + PAD;
    return { positions, width, height };
  }, [funnel]);

  return (
    <div className="overflow-auto rounded-xl border bg-grid bg-background" role="region" aria-label="Diagrama del embudo">
      <div className="relative" style={{ width: layout.width, height: layout.height, minWidth: "100%" }}>
        <svg className="absolute inset-0" width={layout.width} height={layout.height} aria-hidden>
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="hsl(var(--muted-foreground))" />
            </marker>
          </defs>
          {funnel.edges.map((e) => {
            const a = layout.positions.get(e.source);
            const b = layout.positions.get(e.target);
            if (!a || !b) return null;
            const x1 = a.x + NODE_W;
            const y1 = a.y + NODE_H / 2;
            const x2 = b.x;
            const y2 = b.y + NODE_H / 2;
            const mx = (x1 + x2) / 2;
            return (
              <path
                key={e.id}
                d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                fill="none"
                stroke="hsl(var(--muted-foreground) / 0.6)"
                strokeWidth={1.5}
                strokeDasharray="5 4"
                markerEnd="url(#arrow)"
              />
            );
          })}
        </svg>
        {funnel.nodes.map((n) => {
          const p = layout.positions.get(n.id)!;
          const meta = NODE_META[n.type] ?? NODE_META.landing;
          return (
            <button
              key={n.id}
              type="button"
              onClick={() => onSelect?.(n.id)}
              className={cn(
                "absolute flex items-center gap-2 rounded-xl border-2 bg-surface px-3 text-left shadow-card transition-transform hover:-translate-y-0.5",
                meta.cls,
                selected === n.id && "ring-2 ring-ring ring-offset-2 ring-offset-background",
              )}
              style={{ left: p.x, top: p.y, width: NODE_W, height: NODE_H }}
              aria-pressed={selected === n.id}
            >
              <meta.icon className="h-5 w-5 shrink-0" aria-hidden />
              <span className="min-w-0">
                <span className="block text-[10px] font-semibold uppercase tracking-wide">{meta.label}</span>
                <span className="block truncate text-sm text-foreground">{n.label}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
