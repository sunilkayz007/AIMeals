import { apiClient } from './client';
import type { MealType } from '../types/nutritionLog';

export interface MealPlan {
  id: string;
  user_id: string;
  title: string;
  start_date: string;
  end_date: string;
  created_at: string;
  updated_at: string;
}

export interface Meal {
  id: string;
  meal_plan_id: string;
  recipe_id: string | null;
  scheduled_date: string;
  meal_type: MealType;
  created_at: string;
}

export const mealPlanApi = {
  list: () => apiClient.get<MealPlan[]>('/api/v1/meal-plans'),

  get: (planId: string) => apiClient.get<MealPlan>(`/api/v1/meal-plans/${planId}`),

  remove: (planId: string) => apiClient.delete<void>(`/api/v1/meal-plans/${planId}`),

  getMeals: (planId: string) => apiClient.get<Meal[]>(`/api/v1/meal-plans/${planId}/meals`),
};