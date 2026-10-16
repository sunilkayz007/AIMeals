// Single source of truth for every top-level module — used by Home's
// module grid, ModuleNavBar's cross-navigation strip on every
// sub-screen, and the quick-actions cards. Keeping this in one place
// means adding/renaming a module only requires editing it here.

export type BadgeColorKey = 'accentSage' | 'accentPeach' | 'accentLavender' | 'accentBlue' | 'danger';

export interface ModuleDef {
  key: string;
  icon: string;
  label: string;
  subtitle: string;
  badgeColorKey: BadgeColorKey;
  route: string | null;
  showInQuickActions?: boolean;
}

export const MODULES: ModuleDef[] = [
  { key: 'scan', icon: '📷', label: 'Scan food', subtitle: 'AI food analysis', badgeColorKey: 'accentLavender', route: '/(main)/scan' },
  { key: 'ingredient_scan', icon: '🥕', label: 'Ingredient Scan', subtitle: 'Ingredients → recipe', badgeColorKey: 'accentSage', route: '/(main)/ingredient-scan' },
  { key: 'pantry', icon: '🍳', label: 'Pantry', subtitle: 'What you have on hand', badgeColorKey: 'accentSage', route: '/(main)/pantry' },
  { key: 'discover', icon: '🧭', label: 'Discover Recipes', subtitle: 'Healthy & tasty', badgeColorKey: 'accentSage', route: '/(main)/recipes' },
  { key: 'coach', icon: '💬', label: 'Coach chat', subtitle: 'Ask anything', badgeColorKey: 'accentLavender', route: '/(main)/coach' },
  { key: 'meal_plan', icon: '📅', label: 'Meal plan', subtitle: 'Plan your meals', badgeColorKey: 'accentBlue', route: '/(main)/meal-plans' },
  { key: 'health_insights', icon: '🩺', label: 'Health Insights', subtitle: 'From report to plate', badgeColorKey: 'danger', route: '/(main)/health-insights', showInQuickActions: false },
  { key: 'credits', icon: '💳', label: 'Credits', subtitle: 'Plan & usage', badgeColorKey: 'accentPeach', route: '/(main)/credits' },
  { key: 'allergies', icon: '⚠️', label: 'Allergies', subtitle: 'Your allergy list', badgeColorKey: 'danger', route: '/(main)/allergies' },
  { key: 'settings', icon: '⚙️', label: 'Settings', subtitle: 'App preferences', badgeColorKey: 'accentBlue', route: '/(main)/settings' },
  { key: 'reports', icon: '📝', label: 'Feedback', subtitle: "Tell us what's working", badgeColorKey: 'accentPeach', route: '/(main)/reports' },
];
