import { apiClient } from './client';

export interface Achievement {
  key: string;
  title: string;
  description: string;
  icon: string;
  earned: boolean;
  earned_at: string | null;
  // True only on the fetch immediately after being newly earned —
  // see app/schemas/achievement.py's AchievementOut docstring.
  is_new: boolean;
}

interface AchievementListResponse {
  achievements: Achievement[];
}

// Backs the dedicated Achievements screen. Achievements are AWARDED
// server-side (right after a meal is logged, via
// AchievementService.check_and_award_streaks()) — this client only
// ever reads status, never awards anything itself.
export const achievementsApi = {
  list: () => apiClient.get<AchievementListResponse>('/api/v1/achievements'),
};
