// Mirrors app/schemas/pantry.py exactly.

export interface PantryItem {
  id: string;
  user_id: string;
  ingredient_name: string;
  quantity: number | null;
  unit: string | null;
  expiration_date: string | null; // ISO date (YYYY-MM-DD)
  added_at: string; // ISO datetime
}

export interface PantryItemCreate {
  ingredient_name: string;
  quantity?: number;
  unit?: string;
  expiration_date?: string; // YYYY-MM-DD
}

export interface PantryItemUpdate {
  ingredient_name?: string;
  quantity?: number;
  unit?: string;
  expiration_date?: string;
}

// Not enum-constrained server-side (unit is free text), but a curated
// list keeps entries consistent — used for the chip picker in the UI.
export const COMMON_UNITS = [
  'g',
  'kg',
  'ml',
  'l',
  'pcs',
  'cups',
  'tbsp',
  'tsp',
  'oz',
  'lb',
  'pack',
] as const;
