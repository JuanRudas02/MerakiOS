import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { ChevronDown, Menu, X } from "lucide-react";
import { HeavyLogo } from "@/components/brand/HeavyLogo";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { PRODUCT_MODULES } from "@/lib/modules";
import { ROUTES } from "@/lib/routes";
import { useAuth } from "@/features/auth/AuthProvider";
import { cn } from "@/lib/utils";

const navClass = ({ isActive }: { isActive: boolean }) =>
  cn("text-sm font-medium transition-colors hover:text-foreground", isActive ? "text-foreground" : "text-muted-foreground");

export function PublicLayout() {
  const [open, setOpen] = useState(false);
  const { status } = useAuth();
  const authed = status === "authenticated";

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50">
        Saltar al contenido
      </a>
      <header className="glass sticky top-0 z-40 border-x-0 border-t-0">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Link to={ROUTES.PUBLIC.HOME} aria-label="1heavy inicio">
            <HeavyLogo size={30} />
          </Link>
          <nav className="hidden items-center gap-7 md:flex" aria-label="Principal">
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground">
                Producto <ChevronDown className="h-3.5 w-3.5" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-72">
                {PRODUCT_MODULES.map((m) => (
                  <DropdownMenuItem key={m.slug} asChild>
                    <Link to={ROUTES.PUBLIC.PRODUCT(m.slug)} className="flex items-start gap-3 py-2">
                      <m.icon className={cn("mt-0.5 h-4 w-4", m.text)} />
                      <span>
                        <span className="block text-sm font-medium">{m.name}</span>
                        <span className="block text-xs text-muted-foreground">{m.tagline}</span>
                      </span>
                    </Link>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <NavLink to={ROUTES.PUBLIC.PRICING} className={navClass}>
              Precios
            </NavLink>
            <NavLink to={ROUTES.PUBLIC.ABOUT} className={navClass}>
              Nosotros
            </NavLink>
          </nav>
          <div className="hidden items-center gap-2 md:flex">
            <ThemeToggle />
            {authed ? (
              <Button asChild>
                <Link to={ROUTES.APP.HOME}>Ir a la app</Link>
              </Button>
            ) : (
              <>
                <Button variant="ghost" asChild>
                  <Link to={ROUTES.PUBLIC.ACCESS}>Iniciar sesión</Link>
                </Button>
                <Button asChild className="shadow-glow">
                  <Link to={`${ROUTES.PUBLIC.ACCESS}?modo=registro`}>Empieza gratis</Link>
                </Button>
              </>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label="Abrir menú"
          >
            {open ? <X /> : <Menu />}
          </Button>
        </div>
        {open && (
          <nav className="container space-y-1 pb-4 md:hidden" aria-label="Móvil">
            {PRODUCT_MODULES.map((m) => (
              <Link
                key={m.slug}
                to={ROUTES.PUBLIC.PRODUCT(m.slug)}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-elevated"
              >
                <m.icon className={cn("h-4 w-4", m.text)} /> {m.name}
              </Link>
            ))}
            <Link to={ROUTES.PUBLIC.PRICING} onClick={() => setOpen(false)} className="block rounded-md px-2 py-2 text-sm hover:bg-elevated">
              Precios
            </Link>
            <Link to={ROUTES.PUBLIC.ABOUT} onClick={() => setOpen(false)} className="block rounded-md px-2 py-2 text-sm hover:bg-elevated">
              Nosotros
            </Link>
            <div className="flex gap-2 pt-2">
              <Button asChild className="flex-1">
                <Link to={authed ? ROUTES.APP.HOME : ROUTES.PUBLIC.ACCESS} onClick={() => setOpen(false)}>
                  {authed ? "Ir a la app" : "Acceder"}
                </Link>
              </Button>
              <ThemeToggle />
            </div>
          </nav>
        )}
      </header>

      <main id="contenido" className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t bg-surface/50">
        <div className="container grid gap-10 py-12 md:grid-cols-4">
          <div className="space-y-3">
            <HeavyLogo size={28} />
            <p className="text-sm text-muted-foreground">
              Growth & Operations OS para empresas que quieren crecer con orden.
            </p>
          </div>
          <div>
            <h3 className="mb-3 text-sm font-semibold">Producto</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {PRODUCT_MODULES.slice(0, 4).map((m) => (
                <li key={m.slug}>
                  <Link className="hover:text-foreground" to={ROUTES.PUBLIC.PRODUCT(m.slug)}>
                    {m.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-3 text-sm font-semibold">Más</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {PRODUCT_MODULES.slice(4).map((m) => (
                <li key={m.slug}>
                  <Link className="hover:text-foreground" to={ROUTES.PUBLIC.PRODUCT(m.slug)}>
                    {m.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-3 text-sm font-semibold">Empresa</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link className="hover:text-foreground" to={ROUTES.PUBLIC.ABOUT}>
                  Nosotros
                </Link>
              </li>
              <li>
                <Link className="hover:text-foreground" to={ROUTES.PUBLIC.PRICING}>
                  Precios
                </Link>
              </li>
              <li>
                <Link className="hover:text-foreground" to={ROUTES.PUBLIC.ACCESS}>
                  Acceso
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t py-6 text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} 1heavy. Todos los derechos reservados.
        </div>
      </footer>
    </div>
  );
}
