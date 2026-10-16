import { apiClient } from './client';
import type { Allergy, AllergySeverity, FullDietaryProfile, Profile } from '../types/profile';

export interface ProfileUpdatePayload {
  date_of_birth?: string;
  gender?: string;
  height_cm?: number;
  weight_kg?: number;
  activity_level?: string;
  goal?: string;
  daily_calorie_target?: number;
  protein_g_target?: number;
  carbs_g_target?: number;
  fat_g_target?: number;
  fiber_g_target?: number;
  daily_water_ml_target?: number;
  typical_wake_time?: string;
  // Two-letter ISO region code (e.g. "IN", "US") read from the
  // device's own configured locale — no location permission, no
  // manual entry. See src/types/profile.ts's Profile.region_code
  // for the full reasoning.
  region_code?: string;
}

export interface AllergyCreatePayload {
  allergy_name: string;
  severity: AllergySeverity;
}

export const profileApi = {
  getFull: () => apiClient.get<FullDietaryProfile>('/api/v1/profile/full'),
  // Genuinely partial — only send the fields you want to change.
  // Also handles first-time profile creation automatically server-side
  // (create_or_update_profile()), so this works even if the user has
  // no profile row yet at all.
  update: (payload: ProfileUpdatePayload) =>
    apiClient.put<Profile>('/api/v1/profile', payload),
  // NOTE: paths inferred from the project's REST convention
  // (ProfileController.add_allergy / remove_allergy already exist in
  // app/controller/profile_controller.py, backed by AllergyCreate /
  // AllergyOut in app/schemas/profile.py) — but the routes file itself
  // wasn't part of this session's export, so these two paths are
  // unverified against app/routes/profile_routes.py. Double-check
  // before relying on this in a build.
  addAllergy: (payload: AllergyCreatePayload) =>
    apiClient.post<void>('/api/v1/profile/allergies', payload),
  // Backend remove_allergy is idempotent (no error if already gone).
  removeAllergy: (allergyId: string) =>
    apiClient.delete<void>(`/api/v1/profile/allergies/${allergyId}`),
  // Resolves the caller's IP to a country code server-side and saves
  // it if changed — REPLACES the earlier device-locale-based signal
  // (see src/types/profile.ts's Profile.region_code comment for why
  // language preference isn't the same as physical location). Call
  // this once, silently, on app launch and ignore the response — it
  // always succeeds with a 200, even when no region could be
  // resolved (e.g. against a local dev backend with no public IP).
  detectRegion: () =>
    apiClient.post<{ region_code: string | null }>('/api/v1/profile/detect-region', {}),
};