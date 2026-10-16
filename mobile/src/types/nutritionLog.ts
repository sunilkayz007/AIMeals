// Mirrors app/schemas/nutrition_log.py exactly.
export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

export interface NutritionLog {
  id: string;
  user_id: string;
  recipe_id: string | null;
  food_image_id: string | null;
  logged_at: string; // YYYY-MM-DD
  meal_type: MealType;
  food_name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  portion_percentage: number;
  notes: string | null;
  created_at: string;
}

export interface DailyTotals {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
  micronutrients: Record<string, number>;
  entry_count: number;
}

export interface PendingConfirmation {
  source_type: 'recipe' | 'food_image';
  source_id: string;
  title: string;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  created_at: string;
}