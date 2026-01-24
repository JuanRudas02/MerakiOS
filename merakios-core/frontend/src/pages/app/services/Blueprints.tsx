import { Helmet } from "react-helmet-async";
import { PenLine, Zap, FileCode, Copy, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

// Animated Prompt Display
const AnimatedPrompt = () => {
  const [displayText, setDisplayText] = useState("");
  const fullPrompt = `"Hero shot, visionary CEO architect reviewing holographic blueprint of digital ecosystem, 
  dramatic rim lighting, deep blue and violet color palette, cinematic composition, 
  floating data nodes in background, ultra-detailed, professional photography style 
  --ar 16:9 --style raw --v 6.1"`;
  
  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      if (index <= fullPrompt.length) {
        setDisplayText(fullPrompt.slice(0, index));
        index++;
      } else {
        setTimeout(() => { index = 0; }, 2000);
      }
    }, 30);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-4 rounded-lg bg-background/50 border border-border font-mono text-sm">
      <div className="flex items-center gap-2 mb-3 text-muted-foreground">
        <FileCode className="w-4 h-4 text-emerald-400" />
        <span>midjourney_hero.prompt</span>
        <Button variant="ghost" size="sm" className="ml-auto h-6 px-2">
          <Copy className="w-3 h-3" />
        </Button>
      </div>
      <p className="text-emerald-400/80 leading-relaxed break-words">
        {displayText}
        <span className="animate-pulse">|</span>
      </p>
    </div>
  );
};

const Blueprints = () => {
  return (
    <>
      <Helmet>
        <title>Planos de Construcción - MerakiOS</title>
      </Helmet>

      <div className="space-y-8 animate-fade-in-up">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
            <PenLine className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display text-3xl font-bold">Planos de Construcción</h1>
              <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">The Blueprints</span>
            </div>
            <p className="text-muted-foreground">Briefs de copy y Prompts de Ingeniería de alta precisión</p>
          </div>
        </div>

        {/* Coming Soon Status */}
        <Card className="bg-gradient-to-r from-emerald-500/10 to-green-500/10 border-emerald-500/20">
          <CardContent className="py-8">
            <div className="flex flex-col items-center text-center gap-4">
              <div className="w-20 h-20 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <PenLine className="w-10 h-10 text-emerald-400" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-xl mb-2">Próximamente disponible</h3>
                <p className="text-muted-foreground max-w-lg">
                  No te damos el pez, te damos la caña de pescar de alta precisión. 
                  Genera briefs de copywriting y prompts de ingeniería para imagen/video 
                  basados en tu auditoría y embudo.
                </p>
              </div>
              <Button variant="outline" disabled>
                <Zap className="w-4 h-4 mr-2" />
                En desarrollo
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Preview - Animated Prompt */}
        <Card className="bg-card/50 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              Vista previa: Generador de Prompts
            </CardTitle>
            <CardDescription>Prompts profesionales listos para Midjourney, DALL-E y más</CardDescription>
          </CardHeader>
          <CardContent>
            <AnimatedPrompt />
          </CardContent>
        </Card>

        {/* Types of Blueprints */}
        <div className="grid md:grid-cols-3 gap-6">
          <Card className="bg-card/50 border-border">
            <CardHeader>
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center mb-2">
                <FileCode className="w-5 h-5 text-purple-400" />
              </div>
              <CardTitle className="text-lg">Prompts de Imagen</CardTitle>
              <CardDescription>Midjourney, DALL-E, Stable Diffusion</CardDescription>
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
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center mb-2">
                <FileCode className="w-5 h-5 text-blue-400" />
              </div>
              <CardTitle className="text-lg">Prompts de Video</CardTitle>
              <CardDescription>Runway, Pika, Sora</CardDescription>
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
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center mb-2">
                <FileCode className="w-5 h-5 text-amber-400" />
              </div>
              <CardTitle className="text-lg">Briefs de Copy</CardTitle>
              <CardDescription>Headlines, CTAs, Scripts</CardDescription>
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

export default Blueprints;
