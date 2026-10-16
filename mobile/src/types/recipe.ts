// Mirrors app/schemas/recipe.py exactly.

export interface Recipe {
  id: string;
  created_by_user_id: string | null; // null = system/curated recipe
  title: string;
  description: string | null;
  instructions: string; // plain text, not structured — one step per line by convention
  ingredients: string; // plain text, not structured — one ingredient per line by convention
  prep_time_minutes: number | null;
  cook_time_minutes: number | null;
  servings: number;
  calories_per_serving: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fiber_g_per_serving: number | null;
  water_ml_per_serving: number | null;
  // Object with sodium_mg/potassium_mg/calcium_mg/iron_mg/magnesium_mg/
  // zinc_mg/vitamin_a_mcg/vitamin_b12_mcg/vitamin_c_mg/vitamin_d_mcg —
  // mirrors app/core/micronutrients.MICRONUTRIENT_KEYS exactly. Only
  // populated for AI-generated recipes (see backend note on
  // recipe_service.create_recipe() not yet wiring this for manually
  // created recipes) — null/undefined otherwise.
  micronutrients: Record<string, number> | null;
  is_ai_generated: boolean;
  created_at: string;
  updated_at: string;
  // NOT YET IMPLEMENTED SERVER-SIDE — backend still fails closed on allergen
  // detection (discards the recipe, never saves it). These fields anticipate
  // the planned fail-open-with-confirmation redesign; they'll always be
  // undefined/false until that backend work is done. See memory note on
  // "Planned AIMeals backend change" for the full spec.
  contains_allergen?: boolean;
  flagged_allergens?: string[];
}

export interface RecipeCreate {
  title: string;
  instructions: string;
  ingredients: string;
  description?: string;
  prep_time_minutes?: number;
  cook_time_minutes?: number;
  servings?: number; // defaults to 1 server-side
  calories_per_serving?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
}

export interface RecipeUpdate {
  title?: string;
  instructions?: string;
  ingredients?: string;
  description?: string;
  prep_time_minutes?: number;
  cook_time_minutes?: number;
  servings?: number;
  calories_per_serving?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
}