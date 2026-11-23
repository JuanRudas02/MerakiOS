import { useQuery } from "@tanstack/react-query";
import { billingApi, FALLBACK_PLANS } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

/** Planes desde el API; si no responde, catálogo estático (landing pública). */
export const usePlans = () =>
  useQuery({
    queryKey: ["billing", "plans"],
    queryFn: async () => {
      try {
        const plans = await billingApi.plans();
        return plans.length ? plans : FALLBACK_PLANS;
      } catch {
        return FALLBACK_PLANS;
      }
    },
    staleTime: 5 * 60_000,
  });
export const useSubscription = (enabled = true) =>
  useQuery({ queryKey: ["billing", "subscription"], queryFn: billingApi.subscription, enabled });
export const useCheckout = () => useApiMutation((plan: string) => billingApi.checkout(plan));
