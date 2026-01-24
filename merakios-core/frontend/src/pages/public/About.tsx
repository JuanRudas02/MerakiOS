import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { ROUTES } from "@/lib/routes";
import { Button } from "@/components/ui/button";
import MerakiLogo from "@/components/MerakiLogo";
import { Target, Heart, Rocket, Users, ArrowRight } from "lucide-react";

const values = [
  {
    icon: Target,
    title: "Enfoque",
    description: "Nos enfocamos en lo que realmente importa para tu negocio.",
  },
  {
    icon: Heart,
    title: "Pasión",
    description: "Amamos lo que hacemos y eso se refleja en cada detalle.",
  },
  {
    icon: Rocket,
    title: "Innovación",
    description: "Constantemente mejoramos para mantenerte a la vanguardia.",
  },
  {
    icon: Users,
    title: "Comunidad",
    description: "Crecemos junto a nuestros usuarios, escuchando sus necesidades.",
  },
];

const About = () => {
  return (
    <>
      <Helmet>
        <title>Nosotros - MerakiOS</title>
        <meta name="description" content="Conoce la historia detrás de MerakiOS y nuestra misión de empoderar negocios." />
      </Helmet>

      <div className="min-h-screen gradient-dark text-foreground">
        {/* Navigation */}
        <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <Link to={ROUTES.PUBLIC.HOME} className="flex items-center gap-3">
              <MerakiLogo className="w-8 h-8" />
              <span className="font-display font-bold text-xl">MerakiOS</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <Link to={ROUTES.PUBLIC.PRICING} className="text-muted-foreground hover:text-foreground transition-colors">
                Precios
              </Link>
              <Link to={ROUTES.PUBLIC.ABOUT} className="text-foreground font-medium">
                Nosotros
              </Link>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" asChild>
                <Link to={ROUTES.PUBLIC.LOGIN}>Ingresar</Link>
              </Button>
              <Button className="gradient-primary glow-primary" asChild>
                <Link to={ROUTES.PUBLIC.LOGIN}>Comenzar Gratis</Link>
              </Button>
            </div>
          </div>
        </nav>

        {/* Hero */}
        <section className="pt-32 pb-16">
          <div className="container mx-auto px-4 text-center">
            <h1 className="font-display text-4xl md:text-5xl font-bold mb-4">
              Creemos en el poder de la <span className="text-gradient">automatización</span>
            </h1>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              MerakiOS nació de una idea simple: hacer que la tecnología trabaje para ti, no al revés.
            </p>
          </div>
        </section>

        {/* Story */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <div className="max-w-3xl mx-auto">
              <div className="prose prose-invert mx-auto">
                <p className="text-lg text-muted-foreground leading-relaxed mb-6">
                  <strong className="text-foreground">Meraki</strong> es una palabra griega que significa 
                  "hacer algo con pasión, con alma, dejando una parte de ti en tu trabajo". 
                  Eso es exactamente lo que buscamos inspirar en cada emprendedor.
                </p>
                <p className="text-lg text-muted-foreground leading-relaxed mb-6">
                  Creamos MerakiOS porque entendemos los desafíos de gestionar un negocio digital. 
                  La fragmentación de herramientas, la complejidad técnica, y la falta de tiempo 
                  son obstáculos reales que enfrentan miles de emprendedores cada día.
                </p>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Nuestra misión es simple: darte el sistema operativo que tu negocio necesita 
                  para crecer, automatizar y prosperar.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Values */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <h2 className="font-display text-3xl font-bold text-center mb-12">
              Nuestros Valores
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
              {values.map((value, index) => (
                <div
                  key={index}
                  className="p-6 rounded-xl bg-card/50 border border-border text-center"
                >
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <value.icon className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="font-display font-semibold text-lg mb-2">{value.title}</h3>
                  <p className="text-muted-foreground text-sm">{value.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <div className="max-w-2xl mx-auto text-center p-12 rounded-2xl bg-gradient-to-br from-primary/10 to-secondary/10 border border-primary/20">
              <h2 className="font-display text-2xl font-bold mb-4">
                Únete a la comunidad MerakiOS
              </h2>
              <p className="text-muted-foreground mb-6">
                Sé parte de los emprendedores que están transformando sus negocios.
              </p>
              <Button size="lg" className="gradient-primary glow-primary" asChild>
                <Link to={ROUTES.PUBLIC.LOGIN}>
                  Comenzar Ahora
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Link>
              </Button>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 border-t border-border">
          <div className="container mx-auto px-4">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <MerakiLogo className="w-6 h-6" />
                <span className="font-display font-semibold">MerakiOS</span>
              </div>
              <p className="text-muted-foreground text-sm">
                © 2024 MerakiOS. Todos los derechos reservados.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
};

export default About;
