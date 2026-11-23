import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { AppRoutes } from "./AppRoutes";
import { makeUser, renderWith } from "@/test/utils";
import { PERMISSIONS } from "@/lib/permissions";

// Sin backend en tests: cualquier llamada falla y las vistas muestran su estado de error/fallback.
vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 503 }));

describe("rutas", () => {
  it("renderiza la landing pública", async () => {
    renderWith(<AppRoutes />, { route: "/" });
    expect(await screen.findByRole("heading", { level: 1, name: /Growth & Operations OS/i })).toBeInTheDocument();
  });

  it("renderiza una subpágina de producto", async () => {
    renderWith(<AppRoutes />, { route: "/producto/mautic-ia" });
    expect(await screen.findByRole("heading", { level: 1, name: /Marketing automation open source/i })).toBeInTheDocument();
  });

  it("muestra la página de acceso con pestañas de login y registro", async () => {
    renderWith(<AppRoutes />, { route: "/acceso" });
    expect(await screen.findByRole("tab", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Registrarme" })).toBeInTheDocument();
  });

  it("redirige /app a /acceso si no hay sesión", async () => {
    renderWith(<AppRoutes />, { route: "/app" });
    expect(await screen.findByRole("heading", { name: /Bienvenido de nuevo/i })).toBeInTheDocument();
  });

  it("bloquea módulos sin permiso dentro de la app", async () => {
    renderWith(<AppRoutes />, { route: "/app/marketing", user: makeUser([PERMISSIONS.TASKS_READ]) });
    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });

  it("filtra la navegación según permisos", async () => {
    renderWith(<AppRoutes />, { route: "/app/ajustes/perfil", user: makeUser([PERMISSIONS.TASKS_READ, PERMISSIONS.TASKS_EXECUTE]) });
    expect(await screen.findByRole("heading", { name: "Mi perfil" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Módulos" });
    expect(nav).toHaveTextContent("Tareas");
    expect(nav).not.toHaveTextContent("Contactos");
    expect(nav).not.toHaveTextContent("Facturación");
  });

  it("muestra 404 para rutas desconocidas", async () => {
    renderWith(<AppRoutes />, { route: "/no-existe" });
    expect(await screen.findByText("Esta página no existe")).toBeInTheDocument();
  });
});
