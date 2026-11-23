import { useQuery } from "@tanstack/react-query";
import { gamificationApi, type ChallengeInput, type Period, type Team } from "@/lib/api";
import { useApiMutation } from "@/lib/query";

export const gameKeys = {
  all: ["gamification"] as const,
  me: ["gamification", "me"] as const,
  leaderboard: (p: Period, t: Team) => ["gamification", "leaderboard", p, t] as const,
  feed: ["gamification", "feed"] as const,
  badges: ["gamification", "badges"] as const,
  challenges: ["gamification", "challenges"] as const,
  rules: ["gamification", "rules"] as const,
};

export const usePlayer = (enabled = true) => useQuery({ queryKey: gameKeys.me, queryFn: gamificationApi.me, enabled });
export const useLeaderboard = (p: Period, t: Team, enabled = true) =>
  useQuery({ queryKey: gameKeys.leaderboard(p, t), queryFn: () => gamificationApi.leaderboard(p, t), enabled });
export const useFeed = () => useQuery({ queryKey: gameKeys.feed, queryFn: gamificationApi.feed });
export const useBadges = () => useQuery({ queryKey: gameKeys.badges, queryFn: gamificationApi.badges });
export const useChallenges = () => useQuery({ queryKey: gameKeys.challenges, queryFn: gamificationApi.challenges });
export const useRules = () => useQuery({ queryKey: gameKeys.rules, queryFn: gamificationApi.rules });

export const useCreateChallenge = () =>
  useApiMutation((v: ChallengeInput) => gamificationApi.createChallenge(v), { invalidate: [gameKeys.all], success: "Reto creado" });
export const useUpdateRule = () =>
  useApiMutation((v: { key: string; points: number; active: boolean }) => gamificationApi.updateRule(v.key, v), {
    invalidate: [gameKeys.rules],
    success: "Regla actualizada",
  });
