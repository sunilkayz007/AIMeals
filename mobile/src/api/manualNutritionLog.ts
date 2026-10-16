import { apiClient } from './client';
import type { MealType } from '../types/nutritionLog';

export interface ManualLogPayload {
  logged_at: string; // YYYY-MM-DD
  meal_type: MealType;
  food_name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g?: number;
  water_ml?: number;
  micronutrients?: Record<string, number>;
  notes?: string;
}

/**
 * Logs a meal with manually-typed nutrition values —
 * POST /api/v1/nutrition-logs. Kept as its own small file
 * rather than added to the existing nutritionLog.ts client,
 * matching that file's own `nutritionLogApi` object pattern
 * without needing to touch it.
 */
export const logMealManually = (payload: ManualLogPayload) =>
  apiClient.post('/api/v1/nutrition-logs', payload);

/**
 * Shape returned by POST /api/v1/ai/nutrition/estimate — mirrors
 * app/schemas/ai_meal_estimate.py's MealNutritionEstimateResponse
 * exactly, matching the manual meal-log form's own field set
 * (calories through micronutrients) so it can be used to pre-fill
 * the form with no reshaping.
 */
export interface MealNutritionEstimateResponse {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
  water_ml: number;
  micronutrients: Record<string, number>;
}

/**
 * Powers the manual meal-log form's "Estimate with AI" button —
 * POST /api/v1/ai/nutrition/estimate. Costs 1 AI credit (see
 * SubscriptionService.INTERACTION_CREDIT_COSTS on the backend).
 * quantityDescription is optional free text (e.g. "1 medium bowl",
 * "2 slices", "about 300g") — the backend assumes one typical
 * single-serving portion if omitted.
 *
 * This call does NOT log anything itself — the returned estimate
 * only pre-fills the form; the user still reviews and submits the
 * real entry via logMealManually() above, exactly as if they'd
 * typed the numbers in by hand.
 */
export const estimateMealNutrition = (foodName: string, quantityDescription?: string) =>
  apiClient.post<MealNutritionEstimateResponse>('/api/v1/ai/nutrition/estimate', {
    food_name: foodName,
    quantity_description: quantityDescription,
  });
