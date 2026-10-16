import { streamSSE } from './sse';
import type { AllergenWarning, GeneratedRecipe, RecipeGenerationStage } from '../types/aiRecipe';

interface SuggestFromPantryHandlers {
  onStage?: (stage: RecipeGenerationStage) => void;
  onResult?: (recipe: GeneratedRecipe) => void;
  onError?: (errorType: string, detail: string, allergenWarning?: AllergenWarning) => void;
}

interface SuggestFromPantryOverrideOptions {
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
  recipePreviewOverride?: GeneratedRecipe;
  flaggedAllergensOverride?: string[];
}

/**
 * Streams a Pantry Chef suggestion — same SSE shape as regular recipe
 * generation (suggest_recipe_from_pantry() is a thin wrapper around
 * generate_recipe() server-side, inheriting the same stages/safety
 * layers). Now also supports the fail-open-with-confirmation allergen
 * flow: pass confirmAllergenOverride/recipePreviewOverride/
 * flaggedAllergensOverride (mirroring generateRecipe()'s override
 * options) to resend a "Generate Anyway" confirmation instead of
 * always failing closed on an allergen hit.
 */
export function suggestFromPantry(
  selectedIngredients: string[] | undefined,
  additionalPreferences: string,
  handlers: SuggestFromPantryHandlers,
  overrideOptions: SuggestFromPantryOverrideOptions = {}
): () => void {
  const {
    confirmAllergenOverride = false,
    warningTextShown,
    recipePreviewOverride,
    flaggedAllergensOverride,
  } = overrideOptions;

  return streamSSE(
    '/api/v1/ai/recipes/from-pantry',
    {
      selected_ingredients: selectedIngredients,
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
