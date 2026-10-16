import { streamSSE } from './sse';
import type { AllergenWarning, GeneratedRecipe, RecipeGenerationStage } from '../types/aiRecipe';

interface GenerateRecipeHandlers {
  onStage?: (stage: RecipeGenerationStage) => void;
  onResult?: (recipe: GeneratedRecipe) => void;
  onError?: (errorType: string, detail: string, allergenWarning?: AllergenWarning) => void;
}

interface GenerateRecipeOverrideOptions {
  confirmAllergenOverride?: boolean;
  warningTextShown?: string;
  // The EXACT recipe content received in the allergen-warning preview.
  // Sending this back means the backend saves THIS content directly
  // instead of calling Claude again — see AIService.generate_recipe()'s
  // docstring on the backend for why this matters: without it, a
  // "Generate Anyway" retry could produce a genuinely different recipe
  // than the one the user actually saw and agreed to, and would double-
  // charge credits for one recipe.
  recipePreviewOverride?: GeneratedRecipe;
  flaggedAllergensOverride?: string[];
}

/**
 * Streams a recipe generation request. Returns an abort function.
 * The generated recipe is auto-saved server-side as part of the flow —
 * it will also appear under My Recipes, not just in this one-off result.
 */
export function generateRecipe(
  requestDescription: string,
  handlers: GenerateRecipeHandlers,
  overrideOptions: GenerateRecipeOverrideOptions = {}
): () => void {
  const {
    confirmAllergenOverride = false,
    warningTextShown,
    recipePreviewOverride,
    flaggedAllergensOverride,
  } = overrideOptions;

  return streamSSE(
    '/api/v1/ai/recipes/generate',
    {
      request_description: requestDescription,
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
      onStage: (stage) => handlers.onStage?.(stage as RecipeGenerationStage),
      onResult: (data) => handlers.onResult?.(data as GeneratedRecipe),
      onError: (errorType, detail, data) => {
        const allergenWarning: AllergenWarning | undefined =
          data?.recipe_preview && data?.flagged_allergens
            ? { recipe_preview: data.recipe_preview, flagged_allergens: data.flagged_allergens }
            : undefined;
        handlers.onError?.(errorType, detail, allergenWarning);
      },
    }
  );
}