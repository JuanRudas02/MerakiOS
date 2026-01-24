import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import MerakiLogo from "@/components/MerakiLogo";
import AbstractNodes from "@/components/AbstractNodes";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";
import { z } from "zod";
import { useNavigate, useLocation } from "react-router-dom";
import { ROUTES } from "@/lib/routes";

const loginSchema = z.object({
  email: z.string().trim().email({ message: "Correo electrónico inválido" }),
  password: z.string().min(1, { message: "La contraseña es requerida" }),
});

const LoginPanel = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as any)?.from?.pathname || ROUTES.APP.HOME;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate inputs
    const validation = loginSchema.safeParse({ email, password });
    if (!validation.success) {
      setError(validation.error.errors[0].message);
      return;
    }

    setIsLoading(true);

    // BYPASS LOGIN FOR DEMO
    try {
      // Create mock session
      localStorage.setItem("meraki_session", JSON.stringify({
        access_token: "mock_token",
        user: { email: email || "demo@meraki.os", id: "bypass_id" }
      }));
      // Force reload to pick up session in useAuth
      window.location.href = ROUTES.APP.HOME;

    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen lg:min-h-full p-8 lg:p-12 gradient-dark overflow-hidden">
      {/* Background abstract nodes */}
      <AbstractNodes variant="dark" />

      {/* Content */}
      <div className="relative z-10 w-full max-w-md animate-fade-in-up">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <MerakiLogo className="w-24 h-24 lg:w-28 lg:h-28" />
        </div>

        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="font-display text-3xl lg:text-4xl font-bold text-foreground mb-3">
            Bienvenido a{" "}
            <span className="text-gradient inline-block">MerakiOS</span>
          </h1>
          <p className="text-muted-foreground text-lg">
            Tu sistema operativo para negocios en crecimiento.
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label htmlFor="login-email" className="text-sm font-medium text-foreground/80">
              Correo electrónico
            </label>
            <Input
              id="login-email"
              type="email"
              placeholder="tu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              variant="dark"
              required
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="login-password" className="text-sm font-medium text-foreground/80">
              Contraseña
            </label>
            <Input
              id="login-password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              variant="dark"
              required
            />
          </div>

          <div className="flex justify-end">
            <button type="button" className="text-sm text-meraki-cyan hover:text-meraki-blue transition-colors">
              ¿Olvidaste tu contraseña?
            </button>
          </div>

          <Button
            type="submit"
            variant="meraki"
            size="xl"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Ingresando...
              </span>
            ) : (
              "Ingresar"
            )}
          </Button>
        </form>

        {/* Mobile link to register */}
        <div className="lg:hidden mt-8 text-center">
          <p className="text-muted-foreground">
            ¿No tienes cuenta?{" "}
            <a href="#register" className="text-meraki-cyan hover:text-meraki-blue transition-colors font-medium">
              Crear cuenta
            </a>
          </p>
        </div>
      </div>

      {/* Decorative glow */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-meraki-blue/20 rounded-full blur-[100px] pointer-events-none" />
    </div>
  );
};

export default LoginPanel;
