import { Suspense, useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronsLeft, LogOut, Menu, Search, Settings } from "lucide-react";
import { HeavyLogo, HeavyMark } from "@/components/brand/HeavyLogo";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { PageSkeleton } from "@/components/common/Loaders";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuth } from "@/features/auth/AuthProvider";
import { usePermissions } from "@/features/auth/permissions";
import { ROLE_LABELS } from "@/lib/api";
import { initials } from "@/lib/format";
import { visibleNavigation, type NavGroup } from "@/lib/navigation";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

const COLLAPSE_KEY = "oneheavy.sidebar.collapsed";

function SidebarNav({ groups, collapsed, onNavigate }: { groups: NavGroup[]; collapsed: boolean; onNavigate?: () => void }) {
  return (
    <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Módulos">
      {groups.map((g) => (
        <div key={g.label}>
          {!collapsed && (
            <p className="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{g.label}</p>
          )}
          <ul className="space-y-0.5">
            {g.items.map((item) => {
              const link = (
                <NavLink
                  to={item.to}
                  end={item.end}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      "group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                      isActive ? "bg-elevated text-foreground" : "text-muted-foreground hover:bg-elevated/60 hover:text-foreground",
                      collapsed && "justify-center px-0",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && <span className={cn("absolute left-0 top-1.5 h-[calc(100%-12px)] w-1 rounded-r", g.accent)} />}
                      <item.icon className="h-4 w-4 shrink-0" aria-hidden />
                      {collapsed ? <span className="sr-only">{item.label}</span> : <span className="truncate">{item.label}</span>}
                    </>
                  )}
                </NavLink>
              );
              return (
                <li key={item.to}>
                  {collapsed ? (
                    <Tooltip>
                      <TooltipTrigger asChild>{link}</TooltipTrigger>
                      <TooltipContent side="right">{item.label}</TooltipContent>
                    </Tooltip>
                  ) : (
                    link
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export function AppLayout() {
  const { user, workspace, logout } = useAuth();
  const { canAny } = usePermissions();
  const navigate = useNavigate();
  const location = useLocation();
  const groups = useMemo(() => visibleNavigation(canAny), [canAny]);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => setMobileOpen(false), [location.pathname]);

  const signOut = () => {
    logout();
    navigate(ROUTES.PUBLIC.ACCESS, { replace: true });
  };

  return (
    <div className="flex min-h-screen bg-background">
      <aside
        className={cn(
          "sticky top-0 hidden h-screen shrink-0 flex-col border-r bg-surface transition-[width] duration-200 lg:flex",
          collapsed ? "w-[68px]" : "w-64",
        )}
      >
        <div className={cn("flex h-16 items-center border-b px-4", collapsed && "justify-center px-0")}>
          <Link to={ROUTES.APP.HOME} aria-label="Inicio">
            {collapsed ? <HeavyMark size={30} /> : <HeavyLogo size={28} />}
          </Link>
        </div>
        <SidebarNav groups={groups} collapsed={collapsed} />
        <div className="border-t p-3">
          <Button
            variant="ghost"
            size="sm"
            className={cn("w-full justify-start text-muted-foreground", collapsed && "justify-center")}
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
          >
            <ChevronsLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
            {!collapsed && <span className="ml-2">Colapsar</span>}
          </Button>
        </div>
      </aside>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="flex w-72 flex-col bg-surface p-0">
          <SheetTitle className="flex h-16 items-center border-b px-4">
            <HeavyLogo size={28} />
          </SheetTitle>
          <SidebarNav groups={groups} collapsed={false} onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="glass sticky top-0 z-30 flex h-16 items-center gap-3 border-x-0 border-t-0 px-4 sm:px-6">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Abrir menú">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{workspace?.business_name ?? workspace?.name}</p>
            <p className="text-xs text-muted-foreground">
              Plan <span className="capitalize">{workspace?.plan}</span>
            </p>
          </div>
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              className="hidden gap-2 text-muted-foreground sm:flex"
              onClick={() => setPaletteOpen(true)}
            >
              <Search className="h-3.5 w-3.5" /> Buscar
              <kbd className="rounded border bg-elevated px-1.5 text-[10px]">⌘K</kbd>
            </Button>
            <Button variant="ghost" size="icon" className="sm:hidden" onClick={() => setPaletteOpen(true)} aria-label="Buscar">
              <Search className="h-4 w-4" />
            </Button>
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-9 gap-2 px-1.5" aria-label="Menú de usuario">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-gradient-heavy text-xs font-semibold text-white">
                      {initials(user?.name ?? "1h")}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-60">
                <DropdownMenuLabel>
                  <p className="truncate text-sm">{user?.name}</p>
                  <p className="truncate text-xs font-normal text-muted-foreground">{user?.email ?? user?.username}</p>
                  {user && (
                    <Badge variant="secondary" className="mt-2">
                      {ROLE_LABELS[user.role]}
                    </Badge>
                  )}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => navigate(ROUTES.APP.SETTINGS_PROFILE)}>
                  <Settings className="mr-2 h-4 w-4" /> Ajustes
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={signOut} className="text-heavy-rose focus:text-heavy-rose">
                  <LogOut className="mr-2 h-4 w-4" /> Cerrar sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:py-8">
          <Suspense fallback={<PageSkeleton />}>
            <Outlet />
          </Suspense>
        </main>
      </div>

      <CommandDialog open={paletteOpen} onOpenChange={setPaletteOpen}>
        <CommandInput placeholder="Ir a…" />
        <CommandList>
          <CommandEmpty>Sin resultados.</CommandEmpty>
          {groups.map((g) => (
            <CommandGroup key={g.label} heading={g.label}>
              {g.items.map((i) => (
                <CommandItem
                  key={i.to}
                  value={`${g.label} ${i.label}`}
                  onSelect={() => {
                    setPaletteOpen(false);
                    navigate(i.to);
                  }}
                >
                  <i.icon className="mr-2 h-4 w-4" /> {i.label}
                </CommandItem>
              ))}
            </CommandGroup>
          ))}
          <CommandGroup heading="Sesión">
            <CommandItem onSelect={signOut}>
              <LogOut className="mr-2 h-4 w-4" /> Cerrar sesión
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </div>
  );
}
