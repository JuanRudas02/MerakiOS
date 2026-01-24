import { Helmet } from "react-helmet-async";
import { useAuth } from "@/hooks/useAuth";
import { User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

const Profile = () => {
  const { user } = useAuth();
  return (
    <>
      <Helmet><title>Perfil - MerakiOS</title></Helmet>
      <div className="space-y-6 animate-fade-in-up max-w-2xl">
        <div className="flex items-center gap-4"><User className="w-8 h-8 text-primary" /><div><h1 className="font-display text-2xl font-bold">Perfil</h1><p className="text-muted-foreground text-sm">Tu información personal</p></div></div>
        <Card className="bg-card/50 border-border">
          <CardHeader><CardTitle>Información básica</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div><Label>Nombre</Label><Input defaultValue={user?.user_metadata?.full_name || ""} /></div>
            <div><Label>Email</Label><Input defaultValue={user?.email || ""} disabled /></div>
            <Button>Guardar cambios</Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
};
export default Profile;
