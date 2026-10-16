import { apiClient, ApiError } from './client';

export interface AllergenInsight {
  allergy_id: string;
  allergy_name: string;
  short_insight_text: string;
  is_unlocked: boolean;
  deep_insight_text: string | null;
}

export interface AllergenDeepInsight {
  deep_insight_text: string;
}

// Thrown (in addition to the normal ApiError) when the backend
// returns 403 — Free tier, deep insight needs Plus/Pro. The
// insight detail screen catches this specifically to route to
// the Credits/Upgrade flow instead of showing a generic error.
export class TierUpgradeRequiredError extends Error {}

export const allergenInsightApi = {
  getInsight: (allergyId: string) =>
    apiClient.get<AllergenInsight>(`/api/v1/ai/allergen-insight/${allergyId}`),

  getDeepInsight: async (allergyId: string): Promise<AllergenDeepInsight> => {
    try {
      return await apiClient.post<AllergenDeepInsight>(
        `/api/v1/ai/allergen-insight/${allergyId}/deep`
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        throw new TierUpgradeRequiredError('Deep insights require a Plus or Pro plan.');
      }
      throw err;
    }
  },
};