// Centralized visual identity (emoji + color + one-line benefit) for
// every nutrient tracked across the app — single source of truth,
// used by Home's macro rings, the Health Insights results/color-guide
// screens, and the Goals form, so a color or icon only ever needs
// updating in one place. Replaces two previously-separate, nearly-
// identical hardcoded copies (Home's old NUTRIENT_META and Health
// Insights' old ALL_NUTRIENT_META) — merging them also fixed a real
// bug where Fat and Water both used 💧.
//
// Emoji are a SECONDARY visual accent only — every place this is used
// still shows the nutrient's name and value as text; the emoji never
// replaces that, per the app's accessibility/readability rules.

export interface NutrientVisual {
  icon: string;
  color: string;
  benefit: string;
}

export const NUTRIENT_VISUALS: Record<string, NutrientVisual> = {
  // Macros + hydration
  calories: { icon: '🔥', color: '#F97316', benefit: 'Energy' },
  protein: { icon: '💪', color: '#22C55E', benefit: 'Builds & repairs' },
  carbs: { icon: '🌾', color: '#3B82F6', benefit: 'Primary fuel' },
  fat: { icon: '🥑', color: '#F59E0B', benefit: 'Hormones & absorption' },
  fiber: { icon: '🌿', color: '#A855F7', benefit: 'Digestion & gut health' },
  water: { icon: '💧', color: '#14B8A6', benefit: 'Hydration & balance' },

  // Minerals (keyed to match backend app.core.rda / micronutrients keys)
  sodium_mg: { icon: '🧂', color: '#F97316', benefit: 'Fluid balance (keep under)' },
  potassium_mg: { icon: '🍌', color: '#22C55E', benefit: 'Muscles & nerves' },
  calcium_mg: { icon: '🦴', color: '#3B82F6', benefit: 'Bones & teeth' },
  iron_mg: { icon: '🩸', color: '#EF4444', benefit: 'Oxygen transport' },
  magnesium_mg: { icon: '⚡', color: '#A855F7', benefit: 'Energy & muscles' },
  zinc_mg: { icon: '🛡️', color: '#14B8A6', benefit: 'Immunity & healing' },

  // Vitamins
  vitamin_a_mcg: { icon: '👁️', color: '#F97316', benefit: 'Vision & immunity' },
  vitamin_b12_mcg: { icon: '🧠', color: '#3B82F6', benefit: 'Brain & red blood cells' },
  vitamin_c_mg: { icon: '🍊', color: '#22C55E', benefit: 'Immunity & antioxidant' },
  vitamin_d_mcg: { icon: '☀️', color: '#F59E0B', benefit: 'Bone health & immunity' },
};

// General app-section emoji, used sparingly for headings/nav —
// separate from NUTRIENT_VISUALS since these aren't tied to a
// specific nutrient's color-coding.
export const SECTION_EMOJI = {
  home: '🏠',
  healthInsights: '🩺',
  healthReport: '📄',
  analyzeReport: '🔍',
  recipes: '🍳',
  mealPlan: '📅',
  coach: '💬',
  nutritionTip: '💡',
  goals: '🎯',
  health: '❤️',
  privacy: '🔒',
  important: '⚠️',
  completed: '✅',
  personalized: '✨',
  nutrition: '📊',
} as const;