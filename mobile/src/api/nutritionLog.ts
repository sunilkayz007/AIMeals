import { apiClient } from './client';
import type { DailyTotals, MealType, NutritionLog, PendingConfirmation } from '../types/nutritionLog';

function todayString(): string {
  return new Date().toISOString().split('T')[0];
}

export const nutritionLogApi = {
  getPendingConfirmations: () =>
    apiClient.get<PendingConfirmation[]>('/api/v1/nutrition-logs/pending-confirmations'),

  dismissConfirmation: (sourceType: 'recipe' | 'food_image', sourceId: string) =>
    apiClient.post<void>(
      `/api/v1/nutrition-logs/pending-confirmations/${sourceType}/${sourceId}/dismiss`
    ),

  logFromRecipe: (recipeId: string, mealType: MealType, portionPercentage: number) =>
    apiClient.post<NutritionLog>('/api/v1/nutrition-logs/from-recipe', {
      recipe_id: recipeId,
      meal_type: mealType,
      portion_percentage: portionPercentage,
      logged_at: todayString(),
    }),

  logFromFoodImage: (foodImageId: string, mealType: MealType, portionPercentage: number) =>
    apiClient.post<NutritionLog>('/api/v1/nutrition-logs/from-food-image', {
      food_image_id: foodImageId,
      meal_type: mealType,
      portion_percentage: portionPercentage,
      logged_at: todayString(),
    }),

  getDailyTotals: (targetDate: string) =>
    apiClient.get<DailyTotals>(`/api/v1/nutrition-logs/day/${targetDate}/totals`),

  getLogsForDay: (targetDate: string) =>
    apiClient.get<NutritionLog[]>(`/api/v1/nutrition-logs/day/${targetDate}`),

  // Backs the History calendar — one call per visible month instead of
  // a separate request per day. Mirrors backend GET /range exactly
  // (inclusive start/end, both YYYY-MM-DD).
  getLogsForRange: (startDate: string, endDate: string) =>
    apiClient.get<NutritionLog[]>(
      `/api/v1/nutrition-logs/range?start_date=${startDate}&end_date=${endDate}`
    ),
};