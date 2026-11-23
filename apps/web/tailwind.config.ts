import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * 1heavy design tokens. Todos los colores son variables HSL definidas en src/index.css
 * (dark por defecto, `.light` en <html> para modo claro).
 */
const token = (name: string) => `hsl(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: ["class", ".dark"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem", screens: { "2xl": "1280px" } },
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "Inter", "sans-serif"],
      },
      colors: {
        border: token("border"),
        input: token("input"),
        ring: token("ring"),
        background: token("background"),
        foreground: token("foreground"),
        surface: token("surface"),
        elevated: token("elevated"),
        primary: { DEFAULT: token("primary"), foreground: token("primary-foreground") },
        secondary: { DEFAULT: token("secondary"), foreground: token("secondary-foreground") },
        destructive: { DEFAULT: token("destructive"), foreground: token("destructive-foreground") },
        muted: { DEFAULT: token("muted"), foreground: token("muted-foreground") },
        accent: { DEFAULT: token("accent"), foreground: token("accent-foreground") },
        popover: { DEFAULT: token("popover"), foreground: token("popover-foreground") },
        card: { DEFAULT: token("card"), foreground: token("card-foreground") },
        heavy: {
          blue: token("heavy-blue"),
          cyan: token("heavy-cyan"),
          ember: token("heavy-ember"),
          violet: token("heavy-violet"),
          mint: token("heavy-mint"),
          rose: token("heavy-rose"),
          meta: token("heavy-meta"),
        },
        module: {
          stays: token("heavy-mint"),
          crm: token("heavy-blue"),
          marketing: token("heavy-violet"),
          meta: token("heavy-meta"),
          gamification: token("heavy-ember"),
          analytics: token("heavy-cyan"),
          growth: token("heavy-violet"),
        },
        sidebar: {
          DEFAULT: token("surface"),
          foreground: token("foreground"),
          primary: token("primary"),
          "primary-foreground": token("primary-foreground"),
          accent: token("elevated"),
          "accent-foreground": token("foreground"),
          border: token("border"),
          ring: token("ring"),
        },
      },
      borderRadius: {
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        glow: "0 0 0 1px hsl(var(--heavy-blue) / 0.25), 0 12px 40px -12px hsl(var(--heavy-blue) / 0.45)",
        card: "0 1px 0 0 hsl(var(--foreground) / 0.04) inset, 0 20px 40px -24px hsl(0 0% 0% / 0.6)",
      },
      backgroundImage: {
        "gradient-heavy": "linear-gradient(135deg, hsl(var(--heavy-blue)) 0%, hsl(var(--heavy-violet)) 100%)",
        "gradient-volt": "linear-gradient(135deg, hsl(var(--heavy-cyan)) 0%, hsl(var(--heavy-blue)) 100%)",
        "gradient-ember": "linear-gradient(135deg, hsl(var(--heavy-ember)) 0%, hsl(var(--heavy-rose)) 100%)",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        shimmer: "shimmer 2s linear infinite",
      },
    },
  },
  plugins: [animate],
} satisfies Config;
