// Mirrors app/schemas/profile.py exactly.
export type Gender = 'male' | 'female' | 'other' | 'prefer_not_to_say';
export type ActivityLevel =
  | 'sedentary'
  | 'lightly_active'
  | 'moderately_active'
  | 'very_active'
  | 'extra_active';
export type Goal = 'weight_loss' | 'weight_gain' | 'muscle_gain' | 'maintenance';
export type AllergySeverity = 'mild' | 'moderate' | 'severe';

export interface Profile {
  id: string;
  user_id: string;
  date_of_birth: string | null;
  gender: Gender | null;
  height_cm: number | null;
  weight_kg: number | null;
  activity_level: ActivityLevel | null;
  goal: Goal | null;
  daily_calorie_target: number | null;
  protein_g_target: number | null;
  carbs_g_target: number | null;
  fat_g_target: number | null;
  fiber_g_target: number | null;
  created_at: string;
  updated_at: string;
}

export interface Allergy {
  id: string;
  allergy_id: string;
  allergy_name: string;
  severity: AllergySeverity;
}

export interface DietaryRestriction {
  id: string;
  restriction_id: string;
  restriction_name: string;
}

export interface FullDietaryProfile {
  profile: Profile | null;
  allergies: Allergy[];
  dietary_restrictions: DietaryRestriction[];
}