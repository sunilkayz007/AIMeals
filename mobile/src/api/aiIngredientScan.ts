import { streamSSE, streamSSEWithImage } from './sse';
import { apiClient } from './client';

export type IngredientScanStage = 'checking_credits' | 'analyzing_image' | 'saving';

export const INGREDIENT_SCAN_STAGE_ORDER: IngredientScanStage[] = [
  'checking_credits',
  'analyzing_image',
  'saving',
];

export const INGREDIENT_SCAN_STAGE_LABELS: Record<IngredientScanStage, string> = {
  checking_credits: 'Checking credits',
  analyzing_image: 'Identifying ingredients',
  saving: 'Saving results',
};

export type RecipeFromScanStage =
  | 'checking_credits'
  | 'generating'
  | 'checking_safety'
  | 'verifying_safety'
  | 'saving';

export const RECIPE_FROM_SCAN_STAGE_ORDER: RecipeFromScanStage[] = [
  'checking_credits',
  'generating',
  'checking_safety',
  'verifying_safety',
  'saving',
];

export const RECIPE_FROM_SCAN_STAGE_LABELS: Record<RecipeFromScanStage, string> = {
  checking_credits: 'Checking credits',
  generating: 'Generating your recipe',
  checking_safety: 'Checking for allergens',
  verifying_safety: 'Verifying safety',
  saving: 'Saving your recipe',
};

export interface IdentifiedIngredient {
  name: string;
  confidence_score: number | null;
  confidence_note: string | null;
  alternatives: string[];
  quantity: number | null;
  unit: string | null;
}

export interface IngredientScan {
  id: string;
  user_id: string;
  ingredients: IdentifiedIngredient[];
  status: string;
  ai_interaction_id: string | null;
  created_at: string;
}

export interface GeneratedRecipeFromScan {
  id: string;
  title: string;
  description: string | null;
  instructions: string;
  ingredients: string;
  servings: number;
  prep_time_minutes: number | null;
  cook_time_minutes: number | null;
  calories_per_serving: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  contains_allergen: boolean;
  flagged_allergens: string[] | null;
  is_ai_generated: boolean;
  closing_note?: string | null;
  [key: string]: unknown;
}

// Same fail-open-with-confirmation shape as AllergenWarning in
// types/aiRecipe.ts, just typed against GeneratedRecipeFromScan
// instead of GeneratedRecipe — the two recipe-preview shapes are
// structurally close but not identical (this one has no user_id/
// created_at/etc.), so this stays a local type rather than forcing
// an awkward cross-import.
export interface ScanAllergenWarning {
  recipe_preview: GeneratedRecipeFromScan;
  flagged_allergens: string[];
}

interface IdentifyIngredientsHandlers {
  // detail carries a live "Found <ingredient name>" line while
  // stage === "analyzing_image" — see sse.ts's SSEHandlers.onStage
  // and backend app/core/sse_streaming.py's live-detail feature.
  onStage?: (stage: IngredientScanStage, detail?: string) => void;
  onResult?: (scan: IngredientScan) => void;
  onError?: (errorType: string, detail: string) => void;
  onUploadProgress?: (percent: number) => void;
}

/**
 * Step 1: streams an ingredient-identification request from an
 * uploaded photo. Returns an abort function. imageUri is a local
 * file URI from expo-image-picker — never stored server-side.
 */
export function identifyIngredients(
  imageUri: string,
  mimeType: string,
  fileName: string,
  handlers: IdentifyIngredientsHandlers
): () => void {
  return streamSSEWithImage(
    '/api/v1/ai/ingredient-scan/identify',
    imageUri,
    {
      onStage: (stage, detail) => handlers.onStage?.(stage as IngredientScanStage, detail),
      onResult: (data) => handlers.onResult?.(data as IngredientScan),
      onError: (errorType, detail) => handlers.onError?.(errorType, detail),
      onUploadProgress: (percent) => handlers.onUploadProgress?.(percent),
    },
    fileName,
    mimeType
  );
}

interface GenerateRecipeFromScanHandlers {
  onStage?: (stage: RecipeFromScanStage) => void;
  onResult?: (recipe: GeneratedRecipeFromScan) => void;
  onError?: (errorType: string, detail: string, allergenWarning?: ScanAllergenWarning) => void;
}

interface GenerateRecipeFromScanOverrideOptions {
  confirmAllergenOverride?: boolean;
  warningTextShown?: string;
  // The EXACT recipe content received in the allergen-warning preview.
  // Sending this back means the backend saves THIS content directly
  // instead of calling Claude again — see AIService.generate_recipe()'s
  // docstring on the backend for why this matters: without it, a
  // "Generate Anyway" retry could produce a genuinely different recipe
  // than the one the user actually saw and agreed to, and would double-
  // charge credits for one recipe. Same shape as generateRecipe()'s
  // override options in aiRecipe.ts.
  recipePreviewOverride?: GeneratedRecipeFromScan;
  flaggedAllergensOverride?: string[];
}

/**
 * Step 2: streams a recipe-generation request from a previously
 * identified (and possibly user-corrected) ingredient scan.
 * correctedNames, if provided, REPLACES the scan's identified
 * ingredients entirely — pass the full current list, not just
 * the changed items. Pass undefined to use the originally
 * identified ingredients as-is.
 *
 * Now also supports the fail-open-with-confirmation allergen flow:
 * pass confirmAllergenOverride/recipePreviewOverride/
 * flaggedAllergensOverride (mirroring generateRecipe()'s override
 * options in aiRecipe.ts) to resend a "Generate Anyway" confirmation
 * instead of always failing closed on an allergen hit. On a first
 * attempt that gets flagged, onError's allergenWarning carries the
 * preview + flagged allergens the client needs in order to offer that
 * choice.
 */
export function generateRecipeFromScan(
  scanId: string,
  correctedNames: string[] | undefined,
  additionalPreferences: string,
  handlers: GenerateRecipeFromScanHandlers,
  overrideOptions: GenerateRecipeFromScanOverrideOptions = {}
): () => void {
  const {
    confirmAllergenOverride = false,
    warningTextShown,
    recipePreviewOverride,
    flaggedAllergensOverride,
  } = overrideOptions;

  return streamSSE(
    `/api/v1/ai/ingredient-scan/${scanId}/generate-recipe`,
    {
      corrected_ingredient_names: correctedNames ?? null,
      additional_preferences: additionalPreferences,
      confirm_allergen_override: confirmAllergenOverride,
      ...(confirmAllergenOverride && warningTextShown
        ? { warning_text_shown: warningTextShown }
        : {}),
      ...(confirmAllergenOverride && recipePreviewOverride
        ? { recipe_preview_override: recipePreviewOverride }
        : {}),
      ...(confirmAllergenOverride && flaggedAllergensOverride
        ? { flagged_allergens_override: flaggedAllergensOverride }
        : {}),
    },
    {
      onStage: (stage) => handlers.onStage?.(stage as RecipeFromScanStage),
      onResult: (data) => handlers.onResult?.(data as GeneratedRecipeFromScan),
      onError: (errorType, detail, data) => {
        const allergenWarning: ScanAllergenWarning | undefined =
          data?.recipe_preview && data?.flagged_allergens
            ? { recipe_preview: data.recipe_preview, flagged_allergens: data.flagged_allergens }
            : undefined;
        handlers.onError?.(errorType, detail, allergenWarning);
      },
    }
  );
}

/**
 * Fetches the current user's most recent ingredient scans (any
 * status), most recent first. Free, plain GET — no credit cost,
 * no Claude call. Backs the "Recent scans" section on the
 * Ingredient Scan screen's initial (pre-photo) state. Note:
 * scans are swept ~24h after creation server-side, so this
 * naturally only ever shows same-day activity.
 */
export const getRecentIngredientScans = (limit: number = 5) =>
  apiClient.get<IngredientScan[]>(`/api/v1/ai/ingredient-scan/recent?limit=${limit}`);
