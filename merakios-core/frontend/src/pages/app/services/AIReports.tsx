import { Helmet } from "react-helmet-async";
import { Brain, Sparkles, FileText, TrendingUp, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const AIReports = () => {
  return (
    <>
      <Helmet>
        <title>Informes IA - MerakiOS</title>
      </Helmet>

      <div className="space-y-8 animate-fade-in-up">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
            <Brain className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h1 className="font-display text-3xl font-bold">Informes IA</h1>
            <p className="text-muted-foreground">Análisis inteligentes para tu negocio</p>
          </div>
        </div>

        {/* AI Status */}
        <Card className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border-purple-500/20">
          <CardContent className="py-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-purple-500/20 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-purple-400 animate-pulse" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-lg">IA preparando recomendaciones</h3>
                <p className="text-sm text-muted-foreground">
                  Conecta tus cuentas de Meta para que la IA analice tus datos y genere reportes personalizados.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Report Types */}
        <div className="grid md:grid-cols-3 gap-6">
          <Card className="bg-card/50 border-border">
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
                <TrendingUp className="w-5 h-5 text-primary" />
              </div>
              <CardTitle className="text-lg">Análisis de Rendimiento</CardTitle>
              <CardDescription>Resumen semanal de tus métricas más importantes</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full" disabled>
                <Zap className="w-4 h-4 mr-2" />
                Próximamente
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
                <FileText className="w-5 h-5 text-primary" />
              </div>
              <CardTitle className="text-lg">Reporte de Contenido</CardTitle>
              <CardDescription>Análisis de qué tipo de contenido funciona mejor</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full" disabled>
                <Zap className="w-4 h-4 mr-2" />
                Próximamente
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border">
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
                <Brain className="w-5 h-5 text-primary" />
              </div>
              <CardTitle className="text-lg">Recomendaciones IA</CardTitle>
              <CardDescription>Sugerencias personalizadas basadas en tus datos</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full" disabled>
                <Zap className="w-4 h-4 mr-2" />
                Próximamente
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
};

export default AIReports;
