// Curated static list for the ingredient-name autocomplete on the Add
// Pantry Item screen. No backend ingredient lookup exists yet (only
// AI-based photo/scan detection), so this is a client-side suggestion
// source — not authoritative, just a typing shortcut. The user can
// always type a name that isn't in this list; nothing is enforced.

export const COMMON_INGREDIENTS = [
  // Vegetables
  'Onion', 'Garlic', 'Ginger', 'Tomato', 'Potato', 'Carrot', 'Cucumber',
  'Bell Pepper', 'Spinach', 'Cabbage', 'Cauliflower', 'Broccoli', 'Green Beans',
  'Peas', 'Eggplant', 'Zucchini', 'Sweet Potato', 'Beetroot', 'Radish',
  'Lettuce', 'Kale', 'Mushroom', 'Corn', 'Pumpkin', 'Okra', 'Bottle Gourd',
  'Bitter Gourd', 'Green Chili', 'Coriander Leaves', 'Mint Leaves', 'Curry Leaves',

  // Fruits
  'Apple', 'Banana', 'Orange', 'Lemon', 'Lime', 'Mango', 'Grapes', 'Strawberry',
  'Blueberry', 'Pineapple', 'Watermelon', 'Papaya', 'Pomegranate', 'Guava',
  'Avocado', 'Pear', 'Peach', 'Kiwi', 'Plum',

  // Proteins
  'Chicken Breast', 'Chicken Thigh', 'Eggs', 'Paneer', 'Tofu', 'Salmon',
  'Shrimp', 'Ground Beef', 'Ground Turkey', 'Pork', 'Fish Fillet', 'Lentils',
  'Chickpeas', 'Kidney Beans', 'Black Beans', 'Soybeans', 'Moong Dal',
  'Toor Dal', 'Chana Dal', 'Masoor Dal',

  // Dairy
  'Milk', 'Butter', 'Ghee', 'Yogurt', 'Curd', 'Cheese', 'Cream', 'Cottage Cheese',

  // Grains & Staples
  'Rice', 'Basmati Rice', 'Brown Rice', 'Wheat Flour', 'Atta', 'Maida',
  'Bread', 'Pasta', 'Noodles', 'Oats', 'Quinoa', 'Semolina', 'Poha',
  'Vermicelli', 'Besan',

  // Spices & Condiments
  'Salt', 'Black Pepper', 'Turmeric', 'Cumin', 'Coriander Powder',
  'Red Chili Powder', 'Garam Masala', 'Mustard Seeds', 'Cardamom',
  'Cinnamon', 'Cloves', 'Bay Leaf', 'Asafoetida', 'Fenugreek Seeds',
  'Sugar', 'Honey', 'Soy Sauce', 'Vinegar', 'Ketchup', 'Mayonnaise',
  'Mustard', 'Olive Oil', 'Cooking Oil', 'Sesame Oil', 'Vanilla Extract',

  // Nuts & Seeds
  'Almonds', 'Cashews', 'Walnuts', 'Peanuts', 'Pistachios', 'Sesame Seeds',
  'Chia Seeds', 'Flax Seeds', 'Sunflower Seeds', 'Raisins',

  // Bakery / Other
  'Baking Powder', 'Baking Soda', 'Yeast', 'Cocoa Powder', 'Chocolate Chips',
] as const;

export function getIngredientSuggestions(query: string, limit = 5): string[] {
  const trimmed = query.trim().toLowerCase();
  if (!trimmed) return [];

  const startsWith = COMMON_INGREDIENTS.filter((i) =>
    i.toLowerCase().startsWith(trimmed)
  );
  const includes = COMMON_INGREDIENTS.filter(
    (i) => !i.toLowerCase().startsWith(trimmed) && i.toLowerCase().includes(trimmed)
  );

  // "Starts with" matches rank above "contains" matches (typing "oni"
  // should surface "Onion" before something like "Coconut Oil").
  return [...startsWith, ...includes].slice(0, limit);
}