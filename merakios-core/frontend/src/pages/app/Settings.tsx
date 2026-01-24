import { Helmet } from "react-helmet-async";
import { Link, Outlet, useLocation } from "react-router-dom";
import { ROUTES } from "@/lib/routes";
import { User, Link as LinkIcon, Zap, CreditCard, ArrowRight } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const settingsSections = [
  { title: "Perfil", description: "Tu información personal", icon: User, url: ROUTES.SETTINGS.PROFILE },
  { title: "Integraciones", description: "Conecta tus herramientas", icon: LinkIcon, url: ROUTES.SETTINGS.INTEGRATIONS },
  { title: "Meta", description: "Facebook e Instagram", icon: Zap, url: ROUTES.SETTINGS.META },
  { title: "Facturación", description: "Plan y pagos", icon: CreditCard, url: ROUTES.SETTINGS.BILLING },
];

const Settings = () => {
  const location = useLocation();
  const isRoot = location.pathname === ROUTES.SETTINGS.ROOT || location.pathname === ROUTES.APP.SETTINGS;
  if (!isRoot) return <Outlet />;

  return (
    <>
      <Helmet><title>Configuración - MerakiOS</title></Helmet>
      <div className="space-y-8 animate-fade-in-up">
        <div><h1 className="font-display text-3xl font-bold mb-2">Configuración</h1><p className="text-muted-foreground">Administra tu cuenta y preferencias</p></div>
        <div className="grid md:grid-cols-2 gap-6">
          {settingsSections.map((s, i) => (
            <Link key={i} to={s.url}>
              <Card className="group bg-card/50 border-border hover:border-primary/50 transition-all cursor-pointer">
                <CardHeader className="flex flex-row items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center"><s.icon className="w-6 h-6 text-primary" /></div>
                  <div className="flex-1"><CardTitle>{s.title}</CardTitle><CardDescription>{s.description}</CardDescription></div>
                  <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
};
export default Settings;
