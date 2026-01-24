import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { ROUTES } from "@/lib/routes";
import { BarChart3, Facebook, Instagram, ArrowRight, TrendingUp, TrendingDown, Eye, Heart, MessageCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const Metrics = () => {
  return (
    <>
      <Helmet>
        <title>Métricas - MerakiOS</title>
      </Helmet>

      <div className="space-y-8 animate-fade-in-up">
        <div>
          <h1 className="font-display text-3xl font-bold mb-2">Métricas</h1>
          <p className="text-muted-foreground">
            Visualiza el rendimiento de tus campañas en redes sociales.
          </p>
        </div>

        {/* Platform Selection */}
        <div className="grid md:grid-cols-2 gap-6">
          <Link to={ROUTES.SERVICES.METRICS_FB}>
            <Card className="group bg-gradient-to-br from-blue-600/20 to-blue-700/10 border-border hover:border-blue-500/50 transition-all duration-300 cursor-pointer">
              <CardHeader>
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-blue-600/20 flex items-center justify-center">
                    <Facebook className="w-8 h-8 text-blue-400" />
                  </div>
                  <div>
                    <CardTitle>Facebook</CardTitle>
                    <CardDescription>Métricas de páginas y anuncios</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Button variant="ghost" className="w-full group-hover:bg-blue-500/10">
                  Ver métricas
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </CardContent>
            </Card>
          </Link>

          <Link to={ROUTES.SERVICES.METRICS_IG}>
            <Card className="group bg-gradient-to-br from-pink-500/20 to-purple-600/10 border-border hover:border-pink-500/50 transition-all duration-300 cursor-pointer">
              <CardHeader>
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center">
                    <Instagram className="w-8 h-8 text-pink-400" />
                  </div>
                  <div>
                    <CardTitle>Instagram</CardTitle>
                    <CardDescription>Métricas de contenido y engagement</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Button variant="ghost" className="w-full group-hover:bg-pink-500/10">
                  Ver métricas
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <Eye className="w-5 h-5 text-muted-foreground" />
                <span className="flex items-center text-green-400 text-xs">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  12%
                </span>
              </div>
              <p className="text-2xl font-bold mt-2">--</p>
              <p className="text-xs text-muted-foreground">Impresiones</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <Heart className="w-5 h-5 text-muted-foreground" />
                <span className="flex items-center text-green-400 text-xs">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  8%
                </span>
              </div>
              <p className="text-2xl font-bold mt-2">--</p>
              <p className="text-xs text-muted-foreground">Engagement</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <MessageCircle className="w-5 h-5 text-muted-foreground" />
                <span className="flex items-center text-red-400 text-xs">
                  <TrendingDown className="w-3 h-3 mr-1" />
                  3%
                </span>
              </div>
              <p className="text-2xl font-bold mt-2">--</p>
              <p className="text-xs text-muted-foreground">Comentarios</p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <BarChart3 className="w-5 h-5 text-muted-foreground" />
                <span className="flex items-center text-green-400 text-xs">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  15%
                </span>
              </div>
              <p className="text-2xl font-bold mt-2">--</p>
              <p className="text-xs text-muted-foreground">Alcance</p>
            </CardContent>
          </Card>
        </div>

        {/* CTA */}
        <Card className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/20">
          <CardContent className="flex flex-col md:flex-row items-center justify-between gap-4 py-6">
            <div>
              <h3 className="font-display font-semibold">Conecta Meta para ver tus métricas</h3>
              <p className="text-sm text-muted-foreground">Vincula tu cuenta de Facebook e Instagram</p>
            </div>
            <Button className="gradient-primary" asChild>
              <Link to={ROUTES.SETTINGS.META}>
                Conectar Meta
                <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default Metrics;
