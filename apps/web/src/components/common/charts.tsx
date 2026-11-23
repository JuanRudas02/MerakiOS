import type { ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

/** Colores de módulos para Recharts (resuelven el token según tema). */
export const CHART_COLORS = {
  blue: "hsl(var(--heavy-blue))",
  cyan: "hsl(var(--heavy-cyan))",
  ember: "hsl(var(--heavy-ember))",
  violet: "hsl(var(--heavy-violet))",
  mint: "hsl(var(--heavy-mint))",
  rose: "hsl(var(--heavy-rose))",
  meta: "hsl(var(--heavy-meta))",
  grid: "hsl(var(--border))",
  axis: "hsl(var(--muted-foreground))",
};

export const SERIES = [CHART_COLORS.blue, CHART_COLORS.cyan, CHART_COLORS.violet, CHART_COLORS.mint, CHART_COLORS.ember, CHART_COLORS.rose];

export const axisProps = {
  stroke: CHART_COLORS.axis,
  fontSize: 11,
  tickLine: false,
  axisLine: false,
} as const;

export const tooltipProps = {
  contentStyle: {
    background: "hsl(var(--popover))",
    border: "1px solid hsl(var(--border))",
    borderRadius: 10,
    fontSize: 12,
    color: "hsl(var(--popover-foreground))",
  },
  labelStyle: { color: "hsl(var(--muted-foreground))" },
  cursor: { fill: "hsl(var(--foreground) / 0.04)" },
} as const;

export function ChartBox({ height = 260, children, label }: { height?: number; children: ReactNode; label: string }) {
  return (
    <div style={{ height }} role="img" aria-label={label} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );
}
