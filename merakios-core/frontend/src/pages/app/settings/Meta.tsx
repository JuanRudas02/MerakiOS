import { Helmet } from "react-helmet-async";
import { Zap, Facebook, Instagram } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const Meta = () => (
  <>
    <Helmet><title>Meta - MerakiOS</title></Helmet>
    <div className="space-y-6 animate-fade-in-up max-w-2xl">
      <div className="flex items-center gap-4"><Zap className="w-8 h-8 text-primary" /><div><h1 className="font-display text-2xl font-bold">Meta</h1><p className="text-muted-foreground text-sm">Conecta Facebook e Instagram</p></div></div>
      <Card className="bg-gradient-to-r from-blue-500/10 to-pink-500/10 border-blue-500/20">
        <CardHeader><CardTitle>Conectar Meta Business</CardTitle><CardDescription>Vincula tus cuentas para ver métricas en tiempo real</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-lg bg-background/50"><Facebook className="w-8 h-8 text-blue-400" /><div className="flex-1"><p className="font-medium">Facebook</p><p className="text-xs text-muted-foreground">No conectado</p></div><Button variant="outline" size="sm">Conectar</Button></div>
          <div className="flex items-center gap-4 p-4 rounded-lg bg-background/50"><Instagram className="w-8 h-8 text-pink-400" /><div className="flex-1"><p className="font-medium">Instagram</p><p className="text-xs text-muted-foreground">No conectado</p></div><Button variant="outline" size="sm">Conectar</Button></div>
        </CardContent>
      </Card>
    </div>
  </>
);
export default Meta;
