import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Check } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";
import { z } from "zod";
import { useNavigate, useLocation } from "react-router-dom";
import { ROUTES } from "@/lib/routes";

const registerSchema = z.object({
  fullName: z.string().trim().min(2, { message: "El nombre debe tener al menos 2 caracteres" }),
  email: z.string().trim().email({ message: "Correo electrónico inválido" }),
  password: z.string().min(8, { message: "La contraseña debe tener al menos 8 caracteres" }),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Las contraseñas no coinciden",
  path: ["confirmPassword"],
});

interface InputWithValidationProps {
  id: string;
  label: string;
  type: string;
  placeholder: string;
  value: string;
  isValid: boolean;
  onChange: (value: string) => void;
}

const InputWithValidation = ({ 
  id, 
  label, 
  type, 
  placeholder, 
  value,
  isValid,
  onChange
}: InputWithValidationProps) => (
  <div className="space-y-2 relative">
    <label htmlFor={id} className="text-sm font-medium text-meraki-black/80">
      {label}
    </label>
    <div className="relative">
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-meraki-white border-meraki-blue/20 text-meraki-black focus:border-meraki-blue focus:ring-meraki-blue/20 pr-10"
        required
      />
      {isValid && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center animate-scale-in">
          <Check className="w-3 h-3 text-primary-foreground" />
        </div>
      )}
    </div>
  </div>
);

const RegisterPanel = () => {
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validFields, setValidFields] = useState({
    fullName: false,
    email: false,
    password: false,
    confirmPassword: false,
  });
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as any)?.from?.pathname || ROUTES.APP.HOME;

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
    
    // Validate fields
    if (field === "fullName") {
      setValidFields((prev) => ({ ...prev, fullName: value.length >= 2 }));
    }
    if (field === "email") {
      setValidFields((prev) => ({ ...prev, email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) }));
    }
    if (field === "password") {
      setValidFields((prev) => ({ 
        ...prev, 
        password: value.length >= 8,
        confirmPassword: formData.confirmPassword === value && value.length >= 8
      }));
    }
    if (field === "confirmPassword") {
      setValidFields((prev) => ({ ...prev, confirmPassword: value === formData.password && value.length >= 8 }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate inputs
    const validation = registerSchema.safeParse(formData);
    if (!validation.success) {
      setError(validation.error.errors[0].message);
      return;
    }

    setIsLoading(true);

    try {
      const redirectUrl = `${window.location.origin}/`;

      const { data, error: authError } = await supabase.auth.signUp({
        email: formData.email.trim(),
        password: formData.password,
        options: {
          emailRedirectTo: redirectUrl,
          data: {
            full_name: formData.fullName.trim(),
          },
        },
      });

      if (authError) {
        let errorMessage = authError.message;
        if (authError.message.includes("User already registered")) {
          errorMessage = "Este correo ya está registrado. Intenta ingresar.";
        } else if (authError.message.includes("Password should be")) {
          errorMessage = "La contraseña debe ser más segura.";
        }
        setError(errorMessage);
        toast.error("Error al registrar", { description: errorMessage });
        return;
      }

      // User created successfully - profile is automatically created via database trigger
      if (data.session) {
        toast.success("¡Cuenta creada!", { description: "Redirigiendo al dashboard..." });
        navigate(redirectTo, { replace: true });
      } else if (data.user) {
        // Auto-confirm enabled - sign in to get session
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email: formData.email.trim(),
          password: formData.password,
        });
        if (!signInError) {
          toast.success("¡Cuenta creada!", { description: "Redirigiendo al dashboard..." });
          navigate(redirectTo, { replace: true });
        } else {
          toast.success("¡Cuenta creada!", { description: "Por favor inicia sesión." });
        }
      }
    } catch (err) {
      setError("Ocurrió un error inesperado. Intenta de nuevo.");
      toast.error("Error inesperado");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen lg:min-h-full p-8 lg:p-12 overflow-hidden light-panel" style={{ background: "linear-gradient(135deg, hsl(213 38% 97%) 0%, hsl(213 30% 95%) 100%)" }}>
      {/* Background pattern */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.07]" viewBox="0 0 400 800" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="hsl(217 82% 50%)" strokeWidth="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
      
      {/* Floating geometric shapes */}
      <div className="absolute top-20 right-20 w-16 h-16 border-2 border-meraki-blue/20 rounded-lg rotate-45 animate-float" />
      <div className="absolute bottom-40 left-16 w-12 h-12 border-2 border-meraki-purple/20 rounded-full animate-float" style={{ animationDelay: "2s" }} />
      <div className="absolute top-1/3 right-10 w-20 h-20 border border-meraki-cyan/15 rotate-12 animate-float" style={{ animationDelay: "4s", clipPath: "polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)" }} />
      
      {/* Content */}
      <div className="relative z-10 w-full max-w-md animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="font-display text-3xl lg:text-4xl font-bold text-meraki-black mb-3">
            Crear tu cuenta
          </h1>
          <p className="text-meraki-black/60 text-lg">
            Activa tu ecosistema digital en minutos.
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
          <InputWithValidation
            id="register-name"
            label="Nombre completo"
            type="text"
            placeholder="Tu nombre"
            value={formData.fullName}
            isValid={validFields.fullName}
            onChange={(value) => handleChange("fullName", value)}
          />
          
          <InputWithValidation
            id="register-email"
            label="Correo electrónico"
            type="email"
            placeholder="tu@email.com"
            value={formData.email}
            isValid={validFields.email}
            onChange={(value) => handleChange("email", value)}
          />
          
          <InputWithValidation
            id="register-password"
            label="Contraseña"
            type="password"
            placeholder="Mínimo 8 caracteres"
            value={formData.password}
            isValid={validFields.password}
            onChange={(value) => handleChange("password", value)}
          />
          
          <InputWithValidation
            id="register-confirm"
            label="Confirmar contraseña"
            type="password"
            placeholder="Repite tu contraseña"
            value={formData.confirmPassword}
            isValid={validFields.confirmPassword}
            onChange={(value) => handleChange("confirmPassword", value)}
          />
          
          <Button
            type="submit"
            variant="merakiLight"
            size="xl"
            className="w-full mt-2"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Creando cuenta...
              </span>
            ) : (
              "Registrar"
            )}
          </Button>
        </form>
        
        {/* Terms */}
        <p className="mt-6 text-center text-sm text-meraki-black/50">
          Al registrarte, aceptas nuestros{" "}
          <a href="#" className="text-meraki-blue hover:underline">Términos de Servicio</a>
          {" "}y{" "}
          <a href="#" className="text-meraki-blue hover:underline">Política de Privacidad</a>
        </p>
        
        {/* Mobile link to login */}
        <div className="lg:hidden mt-6 text-center">
          <p className="text-meraki-black/60">
            ¿Ya tienes cuenta?{" "}
            <a href="#login" className="text-meraki-blue hover:text-meraki-purple transition-colors font-medium">
              Ingresar
            </a>
          </p>
        </div>
      </div>
      
      {/* Decorative glow */}
      <div className="absolute top-1/4 right-0 w-64 h-64 bg-meraki-blue/10 rounded-full blur-[80px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-48 h-48 bg-meraki-purple/10 rounded-full blur-[60px] pointer-events-none" />
    </div>
  );
};

export default RegisterPanel;
