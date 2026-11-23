import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { HeavyMark } from "@/components/brand/HeavyLogo";
import { ROUTES } from "@/lib/routes";

export default function NotFound() {
  return (
    <div className="grid min-h-[70vh] place-items-center px-4 text-center">
      <div>
        <HeavyMark size={56} className="mx-auto" />
        <p className="mt-6 font-display text-6xl font-bold text-gradient-heavy">404</p>
        <h1 className="mt-2 text-xl font-semibold">Esta página no existe</h1>
        <p className="mt-2 text-sm text-muted-foreground">Puede que el enlace esté roto o que la página se haya movido.</p>
        <Button className="mt-6" asChild>
          <Link to={ROUTES.PUBLIC.HOME}>Volver al inicio</Link>
        </Button>
      </div>
    </div>
  );
}
