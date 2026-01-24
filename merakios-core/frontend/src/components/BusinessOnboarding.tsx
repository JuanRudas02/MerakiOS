import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { 
  Building2, 
  Target, 
  MessageCircle, 
  ChevronRight, 
  ChevronLeft,
  Check,
  Sparkles,
  Loader2,
  X
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

const onboardingSchema = z.object({
  // Step 1 - Identidad
  businessName: z.string().min(2, "El nombre debe tener al menos 2 caracteres"),
  marketNiche: z.string().min(2, "El nicho debe tener al menos 2 caracteres"),
  // Step 2 - ADN
  valueProposition: z.string().min(10, "Describe tu propuesta de valor (mín. 10 caracteres)"),
  targetAudience: z.string().min(10, "Describe tu público objetivo (mín. 10 caracteres)"),
  // Step 3 - Voz y Metas
  brandTone: z.string().min(1, "Selecciona un tono de marca"),
  monthlyGoals: z.string().min(10, "Describe tus objetivos (mín. 10 caracteres)"),
});

type OnboardingFormData = z.infer<typeof onboardingSchema>;

const steps = [
  { id: 1, title: "Identidad", icon: Building2, description: "Nombre y nicho" },
  { id: 2, title: "ADN", icon: Target, description: "Propuesta y público" },
  { id: 3, title: "Voz y Metas", icon: MessageCircle, description: "Tono y objetivos" },
];

const brandTones = [
  { value: "formal", label: "Formal y Profesional" },
  { value: "friendly", label: "Amigable y Cercano" },
  { value: "fun", label: "Divertido y Creativo" },
  { value: "inspiring", label: "Inspirador y Motivacional" },
  { value: "technical", label: "Técnico y Especializado" },
  { value: "luxurious", label: "Lujoso y Exclusivo" },
];

interface BusinessOnboardingProps {
  onComplete?: () => void;
  onDismiss?: () => void;
}

const BusinessOnboarding = ({ onComplete, onDismiss }: BusinessOnboardingProps) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
    trigger,
    setValue,
    watch,
  } = useForm<OnboardingFormData>({
    resolver: zodResolver(onboardingSchema),
    mode: "onChange",
  });

  const brandTone = watch("brandTone");

  const validateCurrentStep = async () => {
    let fieldsToValidate: (keyof OnboardingFormData)[] = [];
    
    switch (currentStep) {
      case 1:
        fieldsToValidate = ["businessName", "marketNiche"];
        break;
      case 2:
        fieldsToValidate = ["valueProposition", "targetAudience"];
        break;
      case 3:
        fieldsToValidate = ["brandTone", "monthlyGoals"];
        break;
    }

    const isValid = await trigger(fieldsToValidate);
    return isValid;
  };

  const handleNext = async () => {
    const isValid = await validateCurrentStep();
    if (isValid && currentStep < 3) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const onSubmit = async (data: OnboardingFormData) => {
    setIsSubmitting(true);
    
    try {
      const response = await fetch("http://localhost:8000/api/save-survey", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          identity: {
            businessName: data.businessName,
            marketNiche: data.marketNiche,
          },
          dna: {
            valueProposition: data.valueProposition,
            targetAudience: data.targetAudience,
          },
          voiceAndGoals: {
            brandTone: data.brandTone,
            monthlyGoals: data.monthlyGoals,
          },
        }),
      });

      if (!response.ok) {
        throw new Error("Error al guardar el perfil");
      }

      toast({
        title: "¡Perfil guardado exitosamente!",
        description: "Tu perfil de negocio ha sido configurado correctamente.",
      });

      onComplete?.();
    } catch (error) {
      toast({
        title: "Error al guardar",
        description: "No se pudo conectar con el servidor. Intenta nuevamente.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="relative overflow-hidden bg-gradient-to-br from-card via-card to-primary/5 border-primary/20">
      {/* Dismiss button */}
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="absolute top-4 right-4 z-20 p-1 rounded-full bg-muted/50 hover:bg-muted transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      )}

      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-secondary/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

      <CardContent className="relative z-10 p-6 md:p-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h2 className="font-display text-xl font-bold">Perfil Maestro</h2>
            <p className="text-sm text-muted-foreground">Configura tu negocio para personalizar MerakiOS</p>
          </div>
        </div>

        {/* Stepper */}
        <div className="flex items-center justify-between mb-8">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
                    currentStep > step.id
                      ? "bg-green-500 text-white"
                      : currentStep === step.id
                      ? "gradient-primary text-primary-foreground glow-primary"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {currentStep > step.id ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <step.icon className="w-5 h-5" />
                  )}
                </div>
                <span className={`text-xs mt-2 font-medium ${
                  currentStep >= step.id ? "text-foreground" : "text-muted-foreground"
                }`}>
                  {step.title}
                </span>
                <span className="text-xs text-muted-foreground hidden md:block">
                  {step.description}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 transition-colors duration-300 ${
                    currentStep > step.id ? "bg-green-500" : "bg-muted"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Form Steps */}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="min-h-[200px]">
            {/* Step 1 - Identidad */}
            {currentStep === 1 && (
              <div className="space-y-4 animate-fade-in-up">
                <div className="space-y-2">
                  <Label htmlFor="businessName">Nombre del Negocio *</Label>
                  <Input
                    id="businessName"
                    placeholder="Ej: MerakiOS Studio"
                    className="bg-muted/50 border-border"
                    {...register("businessName")}
                  />
                  {errors.businessName && (
                    <p className="text-xs text-destructive">{errors.businessName.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="marketNiche">Nicho de Mercado *</Label>
                  <Input
                    id="marketNiche"
                    placeholder="Ej: Marketing Digital, E-commerce, Consultoría"
                    className="bg-muted/50 border-border"
                    {...register("marketNiche")}
                  />
                  {errors.marketNiche && (
                    <p className="text-xs text-destructive">{errors.marketNiche.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 2 - ADN */}
            {currentStep === 2 && (
              <div className="space-y-4 animate-fade-in-up">
                <div className="space-y-2">
                  <Label htmlFor="valueProposition">Propuesta de Valor *</Label>
                  <Textarea
                    id="valueProposition"
                    placeholder="¿Qué te hace único? ¿Por qué deberían elegirte?"
                    className="bg-muted/50 border-border min-h-[80px]"
                    {...register("valueProposition")}
                  />
                  {errors.valueProposition && (
                    <p className="text-xs text-destructive">{errors.valueProposition.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="targetAudience">Público Objetivo *</Label>
                  <Textarea
                    id="targetAudience"
                    placeholder="Describe a tu cliente ideal: edad, intereses, problemas que resuelves..."
                    className="bg-muted/50 border-border min-h-[80px]"
                    {...register("targetAudience")}
                  />
                  {errors.targetAudience && (
                    <p className="text-xs text-destructive">{errors.targetAudience.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Step 3 - Voz y Metas */}
            {currentStep === 3 && (
              <div className="space-y-4 animate-fade-in-up">
                <div className="space-y-2">
                  <Label htmlFor="brandTone">Tono de Marca *</Label>
                  <Select
                    value={brandTone}
                    onValueChange={(value) => setValue("brandTone", value, { shouldValidate: true })}
                  >
                    <SelectTrigger className="bg-muted/50 border-border">
                      <SelectValue placeholder="Selecciona el tono de tu marca" />
                    </SelectTrigger>
                    <SelectContent>
                      {brandTones.map((tone) => (
                        <SelectItem key={tone.value} value={tone.value}>
                          {tone.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.brandTone && (
                    <p className="text-xs text-destructive">{errors.brandTone.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="monthlyGoals">Objetivos del Mes *</Label>
                  <Textarea
                    id="monthlyGoals"
                    placeholder="¿Cuáles son tus metas principales este mes? Ej: Conseguir 50 leads, lanzar campaña..."
                    className="bg-muted/50 border-border min-h-[80px]"
                    {...register("monthlyGoals")}
                  />
                  {errors.monthlyGoals && (
                    <p className="text-xs text-destructive">{errors.monthlyGoals.message}</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex justify-between mt-6 pt-4 border-t border-border">
            <Button
              type="button"
              variant="ghost"
              onClick={handlePrev}
              disabled={currentStep === 1}
              className="gap-2"
            >
              <ChevronLeft className="w-4 h-4" />
              Anterior
            </Button>

            {currentStep < 3 ? (
              <Button
                type="button"
                onClick={handleNext}
                className="gradient-primary gap-2"
              >
                Siguiente
                <ChevronRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={isSubmitting}
                className="gradient-primary gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    Guardar Perfil
                  </>
                )}
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default BusinessOnboarding;
