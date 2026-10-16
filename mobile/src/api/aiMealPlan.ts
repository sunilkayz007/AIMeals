import { streamSSE } from './sse';
import { apiClient } from './client';
import type { MealType } from '../types/nutritionLog';
import type { MealPlan, Meal } from './mealPlan';

export type MealPlanChunkStatus = 'pending' | 'completed' | 'failed';

export interface MealPlanChunk {
  id: string;
  chunk_index: number;
  start_date: string;
  end_date: string;
  status: MealPlanChunkStatus;
}

export type MealPlanGenerationStage =
  | 'checking_credits'
  | 'generating'
  | 'checking_safety'
  | 'verifying_safety'
  | 'saving';

export const MEAL_PLAN_STAGE_ORDER: MealPlanGenerationStage[] = [
  'checking_credits',
  'generating',
  'checking_safety',
  'verifying_safety',
  'saving',
];

export const MEAL_PLAN_STAGE_LABELS: Record<MealPlanGenerationStage, string> = {
  checking_credits: 'Checking credits',
  generating: 'Generating your meal plan',
  checking_safety: 'Checking for allergens',
  verifying_safety: 'Verifying safety',
  saving: 'Saving your plan',
};

interface GenerateMealPlanHandlers {
  onStage?: (stage: MealPlanGenerationStage) => void;
  onResult?: (plan: MealPlan) => void;
  onError?: (errorType: string, detail: string) => void;
}

interface GenerateMealPlanRequest {
  title: string;
  start_date: string;
  end_date: string;
  meal_types: MealType[];
  preferences?: string;
}

/**
 * Streams a meal plan generation request. Returns an abort function.
 * The result event is the MealPlan container only — its individual
 * Meal entries (each linked to a real generated Recipe) are fetched
 * separately via mealPlanApi.getMeals(plan.id) once this resolves.
 */
export function generateMealPlan(
  request: GenerateMealPlanRequest,
  handlers: GenerateMealPlanHandlers
): () => void {
  return streamSSE(
    '/api/v1/ai/meal-plans/generate',
    {
      title: request.title,
      start_date: request.start_date,
      end_date: request.end_date,
      meal_types: request.meal_types,
      preferences: request.preferences ?? '',
    },
    {
      onStage: (stage) => handlers.onStage?.(stage as MealPlanGenerationStage),
      onResult: (data) => handlers.onResult?.(data as MealPlan),
      onError: (errorType, detail) => handlers.onError?.(errorType, detail),
    }
  );
}

/**
 * Returns a plan's meals, generating any chunks that are due
 * but haven't generated yet first. This is the AI-aware
 * counterpart to mealPlanApi.getMeals() (plain CRUD, never
 * generates anything) — call this one from the plan detail
 * screen so newly-due days fill in automatically over time.
 */
export const getMealsSyncingDueChunks = (planId: string) =>
  apiClient.get<Meal[]>(`/api/v1/ai/meal-plans/${planId}/meals`);

/**
 * Returns the plan's chunk schedule — which date ranges are
 * pending/completed/failed. Read-only, generates nothing.
 * Used to render "not generated yet" for pending date ranges
 * instead of just silently showing no meals there.
 */
export const getMealPlanChunks = (planId: string) =>
  apiClient.get<MealPlanChunk[]>(`/api/v1/ai/meal-plans/${planId}/chunks`);