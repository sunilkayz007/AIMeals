import { streamSSEWithImage } from './sse';
import { apiClient } from './client';

export type FoodImageAnalysisStage = 'checking_credits' | 'analyzing_image' | 'saving';

export const FOOD_IMAGE_STAGE_ORDER: FoodImageAnalysisStage[] = [
  'checking_credits',
  'analyzing_image',
  'saving',
];

export const FOOD_IMAGE_STAGE_LABELS: Record<FoodImageAnalysisStage, string> = {
  checking_credits: 'Checking credits',
  analyzing_image: 'Analyzing your photo',
  saving: 'Saving results',
};

export type FoodImageStatus = 'pending' | 'confirmed';

export interface FoodItemAlternative {
  name: string;
  confidence: number | null;
  reason: string | null;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
}

export interface FoodItem {
  name: string;
  region: string | null;
  confidence: number | null;
  reason: string | null;
  estimated_weight_g: number | null;
  visible_percentage: number | null;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  alternatives: FoodItemAlternative[];
}

export interface FoodImage {
  id: string;
  user_id: string;
  ai_interaction_id: string | null;
  image_url: string | null;
  status: FoodImageStatus;
  meal_type: string | null;
  detected_foods: FoodItem[];
  total_calories: number | null;
  total_protein_g: number | null;
  total_carbs_g: number | null;
  total_fat_g: number | null;
  uploaded_at: string;
}

interface AnalyzeFoodImageHandlers {
  // detail carries a live "Found <food name>" line while
  // stage === "analyzing_image" — see sse.ts's SSEHandlers.onStage
  // and backend app/core/sse_streaming.py's live-detail feature.
  onStage?: (stage: string, detail?: string) => void;
  onResult?: (image: FoodImage) => void;
  onError?: (errorType: string, detail: string) => void;
  onUploadProgress?: (percent: number) => void;
}

/**
 * Streams a food photo analysis request. Returns an abort function.
 * imageUri is a local file URI from expo-image-picker (camera or
 * gallery) — the image is uploaded, never stored server-side.
 *
 * mimeType/fileName should reflect the ACTUAL picked file (not a
 * hardcoded guess) — Claude's API rejects a mismatch between the
 * declared media type and the real image bytes (e.g. a PNG declared
 * as image/jpeg), so this matters for real, not just for correctness
 * of the multipart request.
 */
export function analyzeFoodImage(
  imageUri: string,
  mimeType: string,
  fileName: string,
  handlers: AnalyzeFoodImageHandlers
): () => void {
  return streamSSEWithImage('/api/v1/ai/food-image/analyze', imageUri, {
    onStage: (stage, detail) => handlers.onStage?.(stage, detail),
    onResult: (data) => handlers.onResult?.(data as FoodImage),
    onError: (errorType, detail) => handlers.onError?.(errorType, detail),
    onUploadProgress: (percent) => handlers.onUploadProgress?.(percent),
  }, fileName, mimeType);
}

/**
 * Resolves one or more ambiguous items in a PENDING analysis in a
 * single call. Free — no credit cost, not streamed (no Claude call
 * happens here, every alternative was already computed up front).
 */
export const resolveFoodImageAmbiguity = (
  imageId: string,
  resolutions: { item_index: number; chosen_label: string }[]
) => apiClient.post<FoodImage>(`/api/v1/ai/food-image/${imageId}/resolve`, { resolutions });

/**
 * Logs a confirmed food-image scan as a meal, macros auto-filled and
 * scaled by portionPercentage.
 *
 * ASSUMPTION, flagged clearly: exact field names for this request
 * weren't independently confirmed against the real
 * NutritionLogFromFoodImageCreate schema — inferred from
 * NutritionLogService.log_meal_from_food_image()'s real parameters
 * (seen directly, earlier this session, during the water-tracking
 * fix), which this schema almost certainly mirrors closely.
 *
 * CONFIRMED VIA REAL 422 ERROR (2026-08-11): logged_at is required
 * and was missing from the original version of this function.
 *
 * CORRECTED (2026-08-11, second pass): defaults to LOCAL date
 * components, not toISOString()-based UTC conversion. An earlier
 * version of this fix matched home.tsx's todayString(), which was
 * itself found to be the actual bug — toISOString() disagrees with
 * the backend's own local-timezone date.today() for part of every
 * day in any timezone ahead of UTC (confirmed directly via backend
 * logs: /ai/daily-tip, server-computed, showed a different date
 * than the frontend's UTC-based calculation at the same moment).
 * home.tsx's todayString() was fixed the same way, for the same
 * reason — see that function's own comment.
 */
export const logFoodImageAsMeal = (
  foodImageId: string,
  mealType: string,
  portionPercentage: number = 100,
  notes?: string,
  loggedAt?: string
) => {
  const now = new Date();
  const defaultLoggedAt = `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')}`;

  return apiClient.post('/api/v1/nutrition-logs/from-food-image', {
    food_image_id: foodImageId,
    meal_type: mealType,
    portion_percentage: portionPercentage,
    logged_at: loggedAt ?? defaultLoggedAt,
    ...(notes ? { notes } : {}),
  });
};

/**
 * Fetches the current user's most recent food-image scans (any
 * status), most recent first. Free, plain GET — no credit cost,
 * no Claude call. Backs the "Recent scans" section on the Food
 * Scan screen's initial (pre-photo) state.
 */
export const getRecentFoodImages = (limit: number = 5) =>
  apiClient.get<FoodImage[]>(`/api/v1/ai/food-image/recent?limit=${limit}`);
