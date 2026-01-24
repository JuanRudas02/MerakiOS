import { Helmet } from "react-helmet-async";
import { Link as LinkIcon, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const Integrations = () => (
  <>
    <Helmet><title>Integraciones - MerakiOS</title></Helmet>
    <div className="space-y-6 animate-fade-in-up max-w-2xl">
      <div className="flex items-center gap-4"><LinkIcon className="w-8 h-8 text-primary" /><div><h1 className="font-display text-2xl font-bold">Integraciones</h1><p className="text-muted-foreground text-sm">Conecta tus herramientas</p></div></div>
      <Card className="bg-card/50 border-border"><CardHeader><CardTitle>Meta (Facebook & Instagram)</CardTitle><CardDescription>Conecta para ver métricas</CardDescription></CardHeader><CardContent><Button><Zap className="w-4 h-4 mr-2" />Conectar Meta</Button></CardContent></Card>
    </div>
  </>
);
export default Integrations;
