import { useLocation } from "react-router-dom";
import {
  Home,
  Brain,
  Network,
  PenLine,
  Eye,
  Zap,
  BarChart3,
  Link as LinkIcon,
  CreditCard,
  User,
  ChevronDown,
  Sparkles,
  Command,
  Layers,
} from "lucide-react";
import { 
  SiFacebook, 
  SiInstagram, 
  SiLinkedin, 
  SiTiktok, 
  SiMeta 
} from "react-icons/si";
import { NavLink } from "@/components/NavLink";
import { ROUTES } from "@/lib/routes";
import MerakiLogo from "@/components/MerakiLogo";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// Strategic Navigation with Story-telling order
const strategicModules = [
  { 
    title: "Auditoría", 
    url: ROUTES.SERVICES.MARKET_AUDIT, 
    icon: Brain,
    subtitle: "The Brain",
    description: "Investiga tu mercado",
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
  },
  { 
    title: "Arquitecto", 
    url: ROUTES.SERVICES.FUNNEL_ARCHITECT, 
    icon: Network,
    subtitle: "The Mapper",
    description: "Diseña tus embudos",
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
  },
  { 
    title: "Construcción", 
    url: ROUTES.SERVICES.BLUEPRINTS, 
    icon: PenLine,
    subtitle: "The Blueprints",
    description: "Genera tus briefs",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
  },
  { 
    title: "Comando Central", 
    url: ROUTES.SERVICES.INTELLIGENCE, 
    icon: Command,
    subtitle: "The Director",
    description: "Supervisa todo",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
    children: [
      { title: "Dashboard", url: ROUTES.SERVICES.INTELLIGENCE, icon: Eye },
      { title: "Métricas", url: ROUTES.SERVICES.METRICS, icon: BarChart3 },
      { title: "Facebook", url: ROUTES.SERVICES.METRICS_FB, icon: SiFacebook },
      { title: "Instagram", url: ROUTES.SERVICES.METRICS_IG, icon: SiInstagram },
    ]
  },
  { 
    title: "Informes IA", 
    url: ROUTES.SERVICES.AI_REPORTS, 
    icon: Sparkles,
    subtitle: "AI Reports",
    description: "Análisis inteligentes",
    color: "text-cyan-400",
    bgColor: "bg-cyan-500/10",
  },
];

const settingsItems = [
  { title: "Perfil", url: ROUTES.SETTINGS.PROFILE, icon: User },
  { title: "Integraciones", url: ROUTES.SETTINGS.INTEGRATIONS, icon: LinkIcon },
  { title: "Meta", url: ROUTES.SETTINGS.META, icon: Zap },
  { title: "Facturación", url: ROUTES.SETTINGS.BILLING, icon: CreditCard },
];

// Omnichannel connections
const connectedPlatforms = [
  { name: "Meta", icon: SiMeta, connected: true, color: "text-blue-400" },
  { name: "LinkedIn", icon: SiLinkedin, connected: false, color: "text-blue-500" },
  { name: "TikTok", icon: SiTiktok, connected: false, color: "text-pink-400" },
];

const AppSidebar = () => {
  const location = useLocation();
  const { state } = useSidebar();
  const collapsed = state === "collapsed";

  const isActive = (path: string) => location.pathname === path;
  const isParentActive = (children: { url: string }[]) => 
    children.some(child => location.pathname === child.url);

  return (
    <Sidebar className="border-r border-sidebar-border">
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <NavLink to={ROUTES.APP.HOME} className="flex items-center gap-3">
          <MerakiLogo className="w-9 h-9" />
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-display font-bold text-lg text-sidebar-foreground">
                MerakiOS
              </span>
              <span className="text-[10px] text-primary font-medium -mt-0.5">Strategic AI v3.0</span>
            </div>
          )}
        </NavLink>
      </SidebarHeader>

      <SidebarContent className="px-2">
        {/* Home */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={isActive(ROUTES.APP.HOME)}>
                  <NavLink to={ROUTES.APP.HOME}>
                    <Home className="w-4 h-4" />
                    <span>Dashboard</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Strategic Modules - Story Order */}
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-3 h-3" />
            Tu Historia de Éxito
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {strategicModules.map((item, index) => (
                <SidebarMenuItem key={item.title}>
                  {item.children ? (
                    <Collapsible defaultOpen={isParentActive(item.children)}>
                      <CollapsibleTrigger asChild>
                        <SidebarMenuButton 
                          isActive={isActive(item.url) || isParentActive(item.children)}
                          className="group"
                        >
                          <div className={`w-6 h-6 rounded-md ${item.bgColor} flex items-center justify-center`}>
                            <item.icon className={`w-3.5 h-3.5 ${item.color}`} />
                          </div>
                          <div className="flex-1 flex items-center gap-2">
                            <span className="font-medium">{item.title}</span>
                            {!collapsed && (
                              <span className="text-[9px] text-muted-foreground font-mono bg-muted px-1.5 py-0.5 rounded hidden group-hover:inline">
                                {index + 1}
                              </span>
                            )}
                          </div>
                          <ChevronDown className="w-4 h-4 transition-transform group-data-[state=open]:rotate-180" />
                        </SidebarMenuButton>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <SidebarMenuSub>
                          {item.children.map((child) => (
                            <SidebarMenuSubItem key={child.title}>
                              <SidebarMenuSubButton asChild isActive={isActive(child.url)}>
                                <NavLink to={child.url}>
                                  <child.icon className="w-4 h-4" />
                                  <span>{child.title}</span>
                                </NavLink>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          ))}
                        </SidebarMenuSub>
                      </CollapsibleContent>
                    </Collapsible>
                  ) : (
                    <SidebarMenuButton asChild isActive={isActive(item.url)} className="group">
                      <NavLink to={item.url}>
                        <div className={`w-6 h-6 rounded-md ${item.bgColor} flex items-center justify-center`}>
                          <item.icon className={`w-3.5 h-3.5 ${item.color}`} />
                        </div>
                        <div className="flex-1 flex items-center gap-2">
                          <span className="font-medium">{item.title}</span>
                          {!collapsed && (
                            <span className="text-[9px] text-muted-foreground font-mono bg-muted px-1.5 py-0.5 rounded hidden group-hover:inline">
                              {index + 1}
                            </span>
                          )}
                        </div>
                      </NavLink>
                    </SidebarMenuButton>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Omnichannel Connections */}
        {!collapsed && (
          <SidebarGroup>
            <SidebarGroupLabel className="text-xs text-muted-foreground uppercase tracking-wider">
              Conexiones Activas
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 border border-border/50">
                {connectedPlatforms.map((platform) => (
                  <div 
                    key={platform.name}
                    className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                      platform.connected 
                        ? 'bg-primary/10 border border-primary/30 shadow-sm shadow-primary/20' 
                        : 'bg-muted/50 border border-border/30 opacity-40'
                    }`}
                    title={`${platform.name} ${platform.connected ? '(Conectado)' : '(Desconectado)'}`}
                  >
                    <platform.icon className={`w-4 h-4 ${platform.connected ? platform.color : 'text-muted-foreground'}`} />
                  </div>
                ))}
                <NavLink 
                  to={ROUTES.SETTINGS.INTEGRATIONS}
                  className="flex-1 text-center text-xs text-primary hover:underline"
                >
                  + Conectar más
                </NavLink>
              </div>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Settings */}
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs text-muted-foreground uppercase tracking-wider">
            Configuración
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {settingsItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)}>
                    <NavLink to={item.url}>
                      <item.icon className="w-4 h-4" />
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span>IA Activa</span>
          <span className="text-primary font-mono ml-auto">v3.0</span>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
};

export default AppSidebar;
