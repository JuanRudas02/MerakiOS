import { http } from "./client";

export interface Badge {
  key: string;
  name: string;
  description: string;
  icon: string;
  earned_at?: string;
  criteria?: string;
}

export interface PlayerProfile {
  user_id: string;
  name: string;
  points: number;
  level: { number: number; name: string; min_points: number; next_level_points: number | null; progress: number };
  streak_days: number;
  badges: Badge[];
  rank: number | null;
}

export type Period = "week" | "month" | "all";
export type Team = "all" | "operations" | "sales" | "marketing";

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  name: string;
  role: string;
  points: number;
  level: number;
}

export interface FeedItem {
  id: string;
  user_id: string;
  user_name: string;
  points: number;
  reason: string;
  occurred_at: string;
}

export interface Challenge {
  id: string;
  title: string;
  description: string;
  metric: string;
  target: number;
  progress: number;
  starts_at: string;
  ends_at: string;
  reward_points: number;
  team: Team;
  status: "upcoming" | "active" | "finished";
}

export interface ChallengeInput {
  title: string;
  description: string;
  metric: string;
  target: number;
  starts_at: string;
  ends_at: string;
  reward_points: number;
  team: Team;
}

export interface Rule {
  key: string;
  event: string;
  description: string;
  points: number;
  active: boolean;
}

export const gamificationApi = {
  me: () => http.get<PlayerProfile>("/gamification/me"),
  leaderboard: (period: Period = "week", team: Team = "all") =>
    http.get<LeaderboardEntry[]>("/gamification/leaderboard", { period, team }),
  feed: () => http.get<FeedItem[]>("/gamification/feed"),
  badges: () => http.get<Badge[]>("/gamification/badges"),
  challenges: () => http.get<Challenge[]>("/gamification/challenges"),
  createChallenge: (input: ChallengeInput) => http.post<Challenge>("/gamification/challenges", input),
  rules: () => http.get<Rule[]>("/gamification/rules"),
  updateRule: (key: string, input: { points: number; active: boolean }) =>
    http.put<Rule>(`/gamification/rules/${key}`, input),
};
