import type { Recipe } from './recipe';

// Confirmed exact stage names from app/api/v1/ai_recipes.py's docstring.
export type RecipeGenerationStage =
  | 'checking_credits'
  | 'generating'
  | 'checking_safety'
  | 'verifying_safety'
  | 'saving';

export const STAGE_LABELS: Record<RecipeGenerationStage, string> = {
  checking_credits: 'Checking credits',
  generating: 'Generating recipe',
  checking_safety: 'Checking allergens',
  verifying_safety: 'Verifying safety',
  saving: 'Saving',
};

export const STAGE_ORDER: RecipeGenerationStage[] = [
  'checking_credits',
  'generating',
  'checking_safety',
  'verifying_safety',
  'saving',
];

// closing_note is ephemeral server-side (never persisted to the DB) —
// only present on this one streamed response, not on Recipe/RecipeOut
// normally (e.g. not present when fetching from GET /recipes/mine later).
export interface GeneratedRecipe extends Recipe {
  closing_note: string | null;
}

// Sent on the error/warning event when a generated recipe hits an
// allergen and the client didn't set confirm_allergen_override — a
// preview of the generated (but not yet saved) recipe, plus which
// allergens triggered the warning, so the client can offer "Generate
// Anyway". Implemented for /ai/recipes/generate, /ai/recipes/from-pantry,
// and /ai/ingredient-scan/{scan_id}/generate-recipe (the last of these
// uses its own structurally-similar ScanAllergenWarning in
// aiIngredientScan.ts instead, since GeneratedRecipeFromScan isn't
// identical to GeneratedRecipe).
export interface AllergenWarning {
  recipe_preview: GeneratedRecipe;
  flagged_allergens: string[];
}