// Builds a single, short "Good source of X, Y & Z" line from a
// recipe's micronutrients object — shown below a fully generated
// recipe or a meal-plan meal card, so the user sees a tangible
// connection between what they're eating and their confirmed health
// priorities, without needing to open the full nutrient breakdown.
//
// This is a lightweight DISPLAY heuristic, not a personalized or
// medical claim: it compares each value against a fixed, general
// adult reference amount (roughly the same shape as backend
// app/core/rda.py's reference table, not imported directly since
// this is just a "is this a meaningfully high amount" yardstick, not
// a personalized target) and highlights whichever nutrients clear a
// noticeable threshold — never all 10, and never implying the user's
// own personalized targets.

const NUTRIENT_LABELS: Record<string, string> = {
  sodium_mg: 'Sodium',
  potassium_mg: 'Potassium',
  calcium_mg: 'Calcium',
  iron_mg: 'Iron',
  magnesium_mg: 'Magnesium',
  zinc_mg: 'Zinc',
  vitamin_a_mcg: 'Vitamin A',
  vitamin_b12_mcg: 'Vitamin B12',
  vitamin_c_mg: 'Vitamin C',
  vitamin_d_mcg: 'Vitamin D',
};

// General adult reference amounts, used ONLY to judge which
// nutrients are worth mentioning — not a personalized target (those
// come from GET /api/v1/profile/rda-targets elsewhere in the app).
const REFERENCE_DAILY_VALUE: Record<string, number> = {
  sodium_mg: 1500,
  potassium_mg: 3400,
  calcium_mg: 1000,
  iron_mg: 8,
  magnesium_mg: 400,
  zinc_mg: 11,
  vitamin_a_mcg: 900,
  vitamin_b12_mcg: 2.4,
  vitamin_c_mg: 90,
  vitamin_d_mcg: 15,
};

// Below this percentage of the reference amount, a nutrient isn't
// worth calling out — avoids a misleading "Good source of Sodium"
// for a trace amount.
const NOTABLE_THRESHOLD_PERCENT = 15;
const MAX_NUTRIENTS_SHOWN = 3;

function joinWithAmpersand(names: string[]): string {
  if (names.length === 0) return '';
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} & ${names[1]}`;
  return `${names.slice(0, -1).join(', ')} & ${names[names.length - 1]}`;
}

/**
 * Returns a one-line summary like "Good source of Vitamin D, Iron &
 * Potassium", or null if nothing in the recipe clears the notability
 * threshold (or micronutrients data isn't available at all) — callers
 * should render nothing in that case, not a placeholder line.
 */
export function summarizeMicronutrients(
  micronutrients: Record<string, number> | null | undefined
): string | null {
  if (!micronutrients) return null;

  const notable = Object.entries(micronutrients)
    .map(([key, value]) => {
      const reference = REFERENCE_DAILY_VALUE[key];
      const label = NUTRIENT_LABELS[key];
      const percent = reference ? (value / reference) * 100 : 0;
      return { label, percent };
    })
    .filter((n) => n.label && n.percent >= NOTABLE_THRESHOLD_PERCENT)
    .sort((a, b) => b.percent - a.percent)
    .slice(0, MAX_NUTRIENTS_SHOWN);

  if (notable.length === 0) return null;

  return `Good source of ${joinWithAmpersand(notable.map((n) => n.label))}`;
}