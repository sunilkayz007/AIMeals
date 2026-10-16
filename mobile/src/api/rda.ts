import { apiClient } from './client';

export type RDANutrientKind = 'goal' | 'limit';

export interface RDATarget {
  amount: number;
  unit: string;
  kind: RDANutrientKind;
}

export interface RDATargets {
  sodium_mg: RDATarget;
  potassium_mg: RDATarget;
  calcium_mg: RDATarget;
  iron_mg: RDATarget;
  magnesium_mg: RDATarget;
  zinc_mg: RDATarget;
  vitamin_a_mcg: RDATarget;
  vitamin_b12_mcg: RDATarget;
  vitamin_c_mg: RDATarget;
  vitamin_d_mcg: RDATarget;
  disclaimer: string;
}

export const rdaApi = {
  // Throws if the user has no profile yet or hasn't set a date of
  // birth — see backend ProfileController.get_rda_targets()'s
  // docstring. Callers should catch this and treat it the same as
  // any other "complete your profile first" state, not a hard error.
  get: () => apiClient.get<RDATargets>('/api/v1/profile/rda-targets'),
};