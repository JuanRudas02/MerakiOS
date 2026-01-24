import { Helmet } from "react-helmet-async";
import { CreditCard, Check } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const Billing = () => (
  <>
    <Helmet><title>Facturación - MerakiOS</title></Helmet>
    <div className="space-y-6 animate-fade-in-up max-w-2xl">
      <div className="flex items-center gap-4"><CreditCard className="w-8 h-8 text-primary" /><div><h1 className="font-display text-2xl font-bold">Facturación</h1><p className="text-muted-foreground text-sm">Plan y pagos</p></div></div>
      <Card className="bg-gradient-to-r from-primary/10 to-secondary/10 border-primary/20">
        <CardHeader><CardTitle>Plan Actual: Starter</CardTitle><CardDescription>Plan gratuito con funciones básicas</CardDescription></CardHeader>
        <CardContent>
          <ul className="space-y-2 mb-4">{["1 usuario", "Métricas básicas", "CRM hasta 100 leads"].map((f,i) => <li key={i} className="flex items-center gap-2 text-sm"><Check className="w-4 h-4 text-accent" />{f}</li>)}</ul>
          <Button className="gradient-primary">Upgrade a Pro</Button>
        </CardContent>
      </Card>
    </div>
  </>
);
export default Billing;
