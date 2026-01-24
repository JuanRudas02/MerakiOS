import { Helmet } from "react-helmet-async";
import { Instagram, TrendingUp, Eye, Heart, Users, Image } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const MetricsInstagram = () => {
  return (
    <>
      <Helmet>
        <title>Métricas Instagram - MerakiOS</title>
      </Helmet>

      <div className="space-y-8 animate-fade-in-up">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center">
            <Instagram className="w-6 h-6 text-pink-400" />
          </div>
          <div>
            <h1 className="font-display text-3xl font-bold">Instagram</h1>
            <p className="text-muted-foreground">Métricas de tu perfil y contenido</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <Users className="w-5 h-5 text-pink-400 mb-2" />
              <p className="text-2xl font-bold">--</p>
              <p className="text-xs text-muted-foreground">Seguidores</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <Eye className="w-5 h-5 text-pink-400 mb-2" />
              <p className="text-2xl font-bold">--</p>
              <p className="text-xs text-muted-foreground">Alcance</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <Heart className="w-5 h-5 text-pink-400 mb-2" />
              <p className="text-2xl font-bold">--</p>
              <p className="text-xs text-muted-foreground">Likes</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <Image className="w-5 h-5 text-pink-400 mb-2" />
              <p className="text-2xl font-bold">--</p>
              <p className="text-xs text-muted-foreground">Publicaciones</p>
            </CardContent>
          </Card>
        </div>

        {/* Placeholder Chart */}
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle>Engagement del Perfil</CardTitle>
            <CardDescription>Últimos 30 días</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center border border-dashed border-border rounded-lg">
              <div className="text-center text-muted-foreground">
                <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Conecta tu cuenta de Meta para ver el gráfico</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default MetricsInstagram;
