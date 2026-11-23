import { useQuery } from "@tanstack/react-query";
import { identityApi, type BrandingInput, type InviteInput } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const identityKeys = { members: ["identity", "members"] as const };

export const useMembers = (enabled = true) => useQuery({ queryKey: identityKeys.members, queryFn: identityApi.members, enabled });
export const useInviteMember = () =>
  useApiMutation((input: InviteInput) => identityApi.invite(input), {
    invalidate: [identityKeys.members],
    success: "Miembro invitado",
  });
export const useUpdateBranding = () =>
  useApiMutation((input: BrandingInput) => identityApi.updateBranding(input), { success: "Marca actualizada" });
