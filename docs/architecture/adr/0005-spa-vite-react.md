# ADR-0005 · Frontend SPA con React + Vite + shadcn/ui

- **Estado:** Aceptado · 2026-11-22

## Contexto
Existían dos frontends: MerakiOS (Vite + React 18 + shadcn/ui + Tailwind 3) y Stays (Next.js 16 + Tailwind 4 + PWA).

## Decisión
Se conserva el frontend de MerakiOS como base (`apps/web`) y se migran a él las vistas de Stays.
Stack: React 18, Vite, TypeScript, Tailwind + tokens CSS, shadcn/ui (Radix), TanStack Query, Recharts,
framer-motion, lucide. Rutas con *code splitting* (`React.lazy`). Se sirve estático con nginx.

## Alternativas
Next.js: SSR innecesario para una app autenticada; la landing pública puede prerenderizarse luego si SEO lo exige.

## Consecuencias
- ✅ Un solo design system, build rápido, despliegue estático barato, componentes accesibles (Radix).
- ⚠️ La PWA offline del personal de limpieza debe re-implementarse (vite-plugin-pwa) en una fase siguiente.
