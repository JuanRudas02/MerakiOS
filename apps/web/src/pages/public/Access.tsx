import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { HeavyLogo } from "@/components/brand/HeavyLogo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/features/auth/AuthProvider";
import { errorMessage } from "@/lib/query";
import { ROUTES } from "@/lib/routes";
import { PRODUCT_MODULES } from "@/lib/modules";
import { cn } from "@/lib/utils";

const loginSchema = z.object({
  identifier: z.string().min(3, "Ingresa tu email o usuario"),
  password: z.string().min(1, "Ingresa tu contraseña"),
});

const registerSchema = z.object({
  workspace_name: z.string().min(2, "Mínimo 2 caracteres").max(120),
  owner_name: z.string().min(2, "Mínimo 2 caracteres").max(120),
  email: z.string().email("Email inválido"),
  phone: z.string().optional(),
  password: z
    .string()
    .min(10, "Mínimo 10 caracteres")
    .regex(/[A-Za-z]/, "Debe incluir letras")
    .regex(/\d/, "Debe incluir números"),
});

type LoginValues = z.infer<typeof loginSchema>;
type RegisterValues = z.infer<typeof registerSchema>;

function FieldError({ message, id }: { message?: string; id: string }) {
  return message ? (
    <p id={id} className="text-xs text-heavy-rose">
      {message}
    </p>
  ) : null;
}

function LoginForm({ onDone }: { onDone: () => void }) {
  const { login } = useAuth();
  const { register, handleSubmit, formState } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });
  const [error, setError] = useState<string | null>(null);
  const submit = handleSubmit(async (v) => {
    setError(null);
    try {
      await login(v.identifier, v.password);
      onDone();
    } catch (e) {
      setError(errorMessage(e));
    }
  });
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <div className="space-y-1.5">
        <Label htmlFor="identifier">Email o usuario</Label>
        <Input id="identifier" autoComplete="username" aria-invalid={!!formState.errors.identifier} {...register("identifier")} />
        <FieldError id="identifier-error" message={formState.errors.identifier?.message} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="password">Contraseña</Label>
        <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
        <FieldError id="password-error" message={formState.errors.password?.message} />
      </div>
      {error && (
        <p role="alert" className="rounded-md border border-heavy-rose/40 bg-heavy-rose/10 px-3 py-2 text-sm">
          {error}
        </p>
      )}
      <Button type="submit" className="w-full" disabled={formState.isSubmitting}>
        {formState.isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Iniciar sesión
      </Button>
    </form>
  );
}

function RegisterForm({ onDone }: { onDone: () => void }) {
  const { register: signUp } = useAuth();
  const { register, handleSubmit, formState } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });
  const [error, setError] = useState<string | null>(null);
  const submit = handleSubmit(async (v) => {
    setError(null);
    try {
      await signUp({ ...v, phone: v.phone || undefined });
      toast.success("¡Workspace creado! Bienvenido a 1heavy");
      onDone();
    } catch (e) {
      setError(errorMessage(e));
    }
  });
  const e = formState.errors;
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="workspace_name">Empresa</Label>
          <Input id="workspace_name" autoComplete="organization" {...register("workspace_name")} />
          <FieldError id="ws-error" message={e.workspace_name?.message} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="owner_name">Tu nombre</Label>
          <Input id="owner_name" autoComplete="name" {...register("owner_name")} />
          <FieldError id="owner-error" message={e.owner_name?.message} />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="email">Email de trabajo</Label>
        <Input id="email" type="email" autoComplete="email" {...register("email")} />
        <FieldError id="email-error" message={e.email?.message} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="phone">WhatsApp (opcional)</Label>
        <Input id="phone" type="tel" autoComplete="tel" placeholder="300 123 4567" {...register("phone")} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="reg-password">Contraseña</Label>
        <Input id="reg-password" type="password" autoComplete="new-password" {...register("password")} />
        <FieldError id="pwd-error" message={e.password?.message} />
        {!e.password && <p className="text-xs text-muted-foreground">Mínimo 10 caracteres con letras y números.</p>}
      </div>
      {error && (
        <p role="alert" className="rounded-md border border-heavy-rose/40 bg-heavy-rose/10 px-3 py-2 text-sm">
          {error}
        </p>
      )}
      <Button type="submit" className="w-full" disabled={formState.isSubmitting}>
        {formState.isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Crear workspace
      </Button>
      <p className="text-center text-xs text-muted-foreground">14 días de prueba. Sin tarjeta.</p>
    </form>
  );
}

export default function Access() {
  const { status } = useAuth();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const tab = params.get("modo") === "registro" ? "registro" : "ingreso";
  const from = (location.state as { from?: string } | null)?.from ?? ROUTES.APP.HOME;

  if (status === "authenticated") return <Navigate to={from} replace />;
  const done = () => navigate(from, { replace: true });

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <Helmet>
        <title>Acceso · 1heavy</title>
      </Helmet>
      <aside className="relative hidden overflow-hidden bg-gradient-heavy p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="bg-grid absolute inset-0 opacity-30" aria-hidden />
        <Link to={ROUTES.PUBLIC.HOME} className="relative">
          <span className="font-display text-2xl font-bold">1heavy</span>
        </Link>
        <div className="relative">
          <h2 className="text-4xl font-bold leading-tight">Todo tu crecimiento y tu operación, en un solo lugar.</h2>
          <ul className="mt-8 grid grid-cols-2 gap-3">
            {PRODUCT_MODULES.map((m) => (
              <li key={m.slug} className="flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm backdrop-blur">
                <m.icon className="h-4 w-4" aria-hidden /> {m.name}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative flex items-center gap-2 text-sm text-white/80">
          <ShieldCheck className="h-4 w-4" /> Datos aislados por workspace · Acceso por roles
        </p>
      </aside>

      <main className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-md">
          <Link to={ROUTES.PUBLIC.HOME} className="mb-10 inline-block">
            <HeavyLogo />
          </Link>
          <h1 className="text-2xl font-bold">{tab === "registro" ? "Crea tu workspace" : "Bienvenido de nuevo"}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {tab === "registro" ? "Empieza a operar y crecer con 1heavy." : "Ingresa para continuar en tu workspace."}
          </p>
          <Tabs value={tab} onValueChange={(v) => setParams(v === "registro" ? { modo: "registro" } : {})} className="mt-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="ingreso">Iniciar sesión</TabsTrigger>
              <TabsTrigger value="registro">Registrarme</TabsTrigger>
            </TabsList>
            <TabsContent value="ingreso" className={cn("mt-6")}>
              <LoginForm onDone={done} />
            </TabsContent>
            <TabsContent value="registro" className="mt-6">
              <RegisterForm onDone={done} />
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}
