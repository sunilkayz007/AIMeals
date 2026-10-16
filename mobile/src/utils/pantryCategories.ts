// Client-side ONLY. `PantryItem` has no `category` field server-side and
// none is being added — this is a display/filter grouping derived from
// `ingredient_name` at render time, never persisted or sent to the API.
// Keyword matching is intentionally simple substring matching against a
// curated list; anything that doesn't match falls into "Other" rather
// than being mis-bucketed or dropped.

export type PantryCategory =
  | 'Produce'
  | 'Dairy & Eggs'
  | 'Protein'
  | 'Grains & Pasta'
  | 'Pantry Staples'
  | 'Other';

export const CATEGORY_ORDER: PantryCategory[] = [
  'Produce',
  'Dairy & Eggs',
  'Protein',
  'Grains & Pasta',
  'Pantry Staples',
  'Other',
];

// Ordered by specificity — first match wins, so put narrower/likelier
// terms before broader ones where overlap could occur.
const CATEGORY_KEYWORDS: Record<Exclude<PantryCategory, 'Other'>, string[]> = {
  Produce: [
    'tomato', 'onion', 'garlic', 'potato', 'carrot', 'pepper', 'chili', 'chilli',
    'spinach', 'lettuce', 'cucumber', 'broccoli', 'cauliflower', 'cabbage',
    'mushroom', 'zucchini', 'courgette', 'eggplant', 'aubergine', 'pumpkin',
    'squash', 'corn', 'peas', 'beans', 'ginger', 'lemon', 'lime', 'apple',
    'banana', 'orange', 'mango', 'berry', 'berries', 'grape', 'avocado',
    'herb', 'basil', 'cilantro', 'coriander', 'parsley', 'mint', 'scallion',
    'green onion', 'leek', 'celery', 'beet', 'radish', 'kale', 'arugula',
  ],
  'Dairy & Eggs': [
    'milk', 'cheese', 'yogurt', 'yoghurt', 'butter', 'cream', 'egg', 'ghee',
    'paneer', 'curd', 'buttermilk',
  ],
  Protein: [
    'chicken', 'beef', 'pork', 'lamb', 'mutton', 'fish', 'salmon', 'tuna',
    'shrimp', 'prawn', 'crab', 'shellfish', 'tofu', 'tempeh', 'sausage',
    'bacon', 'ham', 'turkey', 'mince', 'meat', 'lentil', 'chickpea',
    'kidney bean', 'black bean',
  ],
  'Grains & Pasta': [
    'rice', 'pasta', 'noodle', 'bread', 'flour', 'oat', 'quinoa', 'barley',
    'cereal', 'tortilla', 'bun', 'roti', 'naan', 'couscous', 'spaghetti',
    'macaroni',
  ],
  'Pantry Staples': [
    'oil', 'salt', 'sugar', 'vinegar', 'sauce', 'spice', 'powder', 'stock',
    'broth', 'honey', 'syrup', 'nut', 'almond', 'cashew', 'walnut', 'seed',
    'can', 'canned', 'paste', 'jam', 'baking soda', 'baking powder',
    'yeast', 'coconut milk', 'ketchup', 'mustard', 'mayonnaise', 'mayo',
  ],
};

export function categorizeIngredient(name: string): PantryCategory {
  const lower = name.toLowerCase();
  for (const category of CATEGORY_ORDER) {
    if (category === 'Other') continue;
    const keywords = CATEGORY_KEYWORDS[category];
    if (keywords.some((kw) => lower.includes(kw))) {
      return category;
    }
  }
  return 'Other';
}