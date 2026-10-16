// =========================================================
// AIMeals Theme — Premium AI Nutrition Brand System
// Rebuilt 2026-08-06 per brand direction: fresh, modern,
// premium, friendly, healthy, AI-powered — think Lifesum /
// Apple Health / Headspace, not washed-out pastel blocks.
//
// BACKWARD COMPATIBILITY: every original key (pageBg, accentSage,
// dangerBg, etc.) is kept and repointed to the new palette, so
// every screen already consuming useTheme() — Home, Pantry,
// Settings, Allergies (index/manage/insight), Credits, Goals,
// ModuleNavBar — gets the new look with ZERO code changes.
// New semantic fields are ADDITIVE, for screens being converted
// next (Recipes, Coach, Pantry add form).
// =========================================================

export interface ThemeColors {
  // ---------------------------------------------------
  // Backgrounds (original keys, repointed)
  // ---------------------------------------------------
  pageBg: string; // outermost background
  screenBg: string; // screen/card surface
  surfaceAlt: string; // secondary surface (list items, subtle fills)
  border: string;

  // ---------------------------------------------------
  // Text (original keys, repointed)
  // ---------------------------------------------------
  textPrimary: string;
  textSecondary: string;
  textMuted: string; // maps to brand "Disabled"

  // ---------------------------------------------------
  // Section accents (original keys — KEPT so every existing
  // colored-icon-badge / section-theming call site still
  // resolves, now pointing at brand-consistent hues instead
  // of the old muted-pastel set)
  // ---------------------------------------------------
  accentSage: string; // -> brand Primary (green)
  accentPeach: string; // -> warm orange accent
  accentLavender: string; // -> brand purple accent (Coach)
  accentBlue: string; // -> brand blue accent (Recipes)
  accentGold: string; // -> brand yellow accent

  // ---------------------------------------------------
  // Semantic (original keys, repointed to brand Success/
  // Warning/Error)
  // ---------------------------------------------------
  danger: string;
  dangerBg: string;
  warningBg: string;
  warningText: string;
  successBg: string;
  successText: string;

  // =====================================================
  // NEW — Brand Primary System
  // =====================================================
  primary: string; // #22C55E
  primaryDark: string; // #16A34A
  primaryLight: string; // #DCFCE7
  mintBg: string; // #F0FDF4

  // Text — brand naming alongside the original keys above
  textDisabled: string; // same value as textMuted, brand-named

  // Card system (brief: white surface, #E8ECEB border, 24dp
  // radius, soft shadow — radius/shadow live in theme.ts
  // alongside this, not here, since they're layout constants
  // not colors)
  cardBg: string;
  cardBorder: string;

  // =====================================================
  // NEW — Progress Ring Colors (brief: distinct per macro,
  // never identical)
  // =====================================================
  ringCalories: string; // #FB923C
  ringProtein: string; // #3B82F6
  ringCarbs: string; // #8B5CF6
  ringFat: string; // #FACC15
  ringWater: string; // brand blue, distinct from ringProtein's blue

  // =====================================================
  // NEW — Home Quick-Action Icon Circles (brief: white card,
  // ONLY the icon circle is colored)
  // =====================================================
  iconCircleScanBg: string;
  iconCircleScanFg: string;
  iconCircleCoachBg: string;
  iconCircleCoachFg: string;
  iconCircleRecipesBg: string;
  iconCircleRecipesFg: string;
  iconCirclePantryBg: string;
  iconCirclePantryFg: string;
  iconCircleMealPlanBg: string;
  iconCircleMealPlanFg: string;
  iconCircleSettingsBg: string;
  iconCircleSettingsFg: string;

  // =====================================================
  // NEW — Pantry Freshness Chips
  // =====================================================
  freshBg: string;
  freshText: string;
  expiringSoonBg: string;
  expiringSoonText: string;
  expiredChipBg: string;
  expiredChipText: string;

  // =====================================================
  // NEW — Allergy Severity Badges (distinct from generic
  // danger/warning — brief specifies exact severity hues)
  // =====================================================
  severitySevereBg: string;
  severitySevereText: string;
  severityModerateBg: string;
  severityModerateText: string;
  severityMildBg: string;
  severityMildText: string;

  // =====================================================
  // NEW — Coach Chat
  // =====================================================
  aiBubbleBg: string;
  aiBubbleText: string;
  userBubbleBg: string;
  userBubbleText: string;
  suggestedChipBg: string;
  suggestedChipText: string;

  // =====================================================
  // NEW — Navigation
  // =====================================================
  navBg: string;
  navSelectedFg: string;
  navSelectedBg: string;
  navUnselectedFg: string;

  // =====================================================
  // NEW — Gradient endpoints (for expo-linear-gradient, once
  // installed — see conversation note on 2026-08-06). Plain
  // color values so screens can use them even before the
  // gradient library lands, as a solid fallback color.
  // =====================================================
  gradientPrimaryStart: string;
  gradientPrimaryEnd: string;

  // =====================================================
  // NEW — Health Insights entry card (Home). Deliberately its
  // own rose/coral family, distinct from every other card's
  // palette, so it stands apart — was hardcoded hex on Home
  // (a real dark-mode bug: stayed bright rose regardless of
  // theme) until these were added.
  // =====================================================
  healthInsightsBg: string;
  healthInsightsBorder: string;
  healthInsightsText: string;
  healthInsightsTextSecondary: string;
}

// =========================================================
// Light Theme
// =========================================================

export const lightColors: ThemeColors = {
  // Backgrounds
  pageBg: '#FAFBF8',
  screenBg: '#FFFFFF',
  surfaceAlt: '#F0FDF4',
  border: '#E8ECEB',

  // Text
  textPrimary: '#1F2937',
  textSecondary: '#6B7280',
  textMuted: '#9CA3AF',

  // Section accents -> brand hues
  accentSage: '#22C55E',
  accentPeach: '#FB923C',
  accentLavender: '#A855F7',
  accentBlue: '#3B82F6',
  accentGold: '#FACC15',

  // Semantic
  danger: '#EF4444',
  dangerBg: '#FEE2E2',
  warningBg: '#FFEDD5',
  warningText: '#C2410C',
  successBg: '#DCFCE7',
  successText: '#16A34A',

  // Brand primary system
  primary: '#22C55E',
  primaryDark: '#16A34A',
  primaryLight: '#DCFCE7',
  mintBg: '#F0FDF4',

  textDisabled: '#9CA3AF',

  cardBg: '#FFFFFF',
  cardBorder: '#E8ECEB',

  // Progress rings — all distinct
  ringCalories: '#FB923C',
  ringProtein: '#3B82F6',
  ringCarbs: '#8B5CF6',
  ringFat: '#FACC15',
  ringWater: '#0EA5E9',

  // Home icon circles
  iconCircleScanBg: '#DCFCE7',
  iconCircleScanFg: '#16A34A',
  iconCircleCoachBg: '#F3E8FF',
  iconCircleCoachFg: '#A855F7',
  iconCircleRecipesBg: '#DBEAFE',
  iconCircleRecipesFg: '#3B82F6',
  iconCirclePantryBg: '#FEF3C7',
  iconCirclePantryFg: '#D97706',
  iconCircleMealPlanBg: '#FCE7F3',
  iconCircleMealPlanFg: '#DB2777',
  iconCircleSettingsBg: '#F3F4F6',
  iconCircleSettingsFg: '#6B7280',

  // Pantry freshness
  freshBg: '#DCFCE7',
  freshText: '#16A34A',
  expiringSoonBg: '#FED7AA',
  expiringSoonText: '#C2410C',
  expiredChipBg: '#FECACA',
  expiredChipText: '#DC2626',

  // Allergy severity
  severitySevereBg: '#FEE2E2',
  severitySevereText: '#EF4444',
  severityModerateBg: '#FFEDD5',
  severityModerateText: '#FB923C',
  severityMildBg: '#FEF9C3',
  severityMildText: '#CA8A04',

  // Coach chat
  aiBubbleBg: '#F3E8FF',
  aiBubbleText: '#1F2937',
  userBubbleBg: '#FFFFFF',
  userBubbleText: '#1F2937',
  suggestedChipBg: '#F3E8FF',
  suggestedChipText: '#7E22CE',

  // Navigation
  navBg: '#FFFFFF',
  navSelectedFg: '#22C55E',
  navSelectedBg: '#DCFCE7',
  navUnselectedFg: '#9CA3AF',

  // Gradient
  gradientPrimaryStart: '#22C55E',
  gradientPrimaryEnd: '#16A34A',

  // Health Insights entry card (rose/coral, distinct family)
  healthInsightsBg: '#FFE4E6',
  healthInsightsBorder: '#FDA4AF',
  healthInsightsText: '#BE123C',
  healthInsightsTextSecondary: '#9F1239',
};

// =========================================================
// Dark Theme
// =========================================================
// Same brand hue family as light mode, brightened where needed
// for legibility on dark surfaces — not a different palette.

export const darkColors: ThemeColors = {
  pageBg: '#14161B',
  screenBg: '#1E212B',
  surfaceAlt: '#1A2E22',
  border: '#2E3239',

  textPrimary: '#F3F4F6',
  textSecondary: '#9CA3AF',
  textMuted: '#6B7280',

  accentSage: '#4ADE80',
  accentPeach: '#FDBA74',
  accentLavender: '#C084FC',
  accentBlue: '#60A5FA',
  accentGold: '#FDE047',

  danger: '#F87171',
  dangerBg: '#3F1D1D',
  warningBg: '#432B12',
  warningText: '#FDBA74',
  successBg: '#14361F',
  successText: '#4ADE80',

  primary: '#4ADE80',
  primaryDark: '#22C55E',
  primaryLight: '#14361F',
  mintBg: '#122016',

  textDisabled: '#6B7280',

  cardBg: '#1E212B',
  cardBorder: '#2E3239',

  ringCalories: '#FDBA74',
  ringProtein: '#60A5FA',
  ringCarbs: '#C084FC',
  ringFat: '#FDE047',
  ringWater: '#38BDF8',

  iconCircleScanBg: '#14361F',
  iconCircleScanFg: '#4ADE80',
  iconCircleCoachBg: '#3B2350',
  iconCircleCoachFg: '#C084FC',
  iconCircleRecipesBg: '#1E3A5F',
  iconCircleRecipesFg: '#60A5FA',
  iconCirclePantryBg: '#3D2E10',
  iconCirclePantryFg: '#FBBF24',
  iconCircleMealPlanBg: '#3D1F30',
  iconCircleMealPlanFg: '#F472B6',
  iconCircleSettingsBg: '#2E313F',
  iconCircleSettingsFg: '#9CA3AF',

  freshBg: '#14361F',
  freshText: '#4ADE80',
  expiringSoonBg: '#432B12',
  expiringSoonText: '#FDBA74',
  expiredChipBg: '#3F1D1D',
  expiredChipText: '#F87171',

  severitySevereBg: '#3F1D1D',
  severitySevereText: '#F87171',
  severityModerateBg: '#432B12',
  severityModerateText: '#FDBA74',
  severityMildBg: '#3D3510',
  severityMildText: '#FDE047',

  aiBubbleBg: '#3B2350',
  aiBubbleText: '#F3F4F6',
  userBubbleBg: '#1E212B',
  userBubbleText: '#F3F4F6',
  suggestedChipBg: '#3B2350',
  suggestedChipText: '#D8B4FE',

  navBg: '#1E212B',
  navSelectedFg: '#4ADE80',
  navSelectedBg: '#14361F',
  navUnselectedFg: '#6B7280',

  gradientPrimaryStart: '#22C55E',
  gradientPrimaryEnd: '#15803D',

  // Health Insights entry card — same rose/coral family,
  // brightened for legibility on a dark surface (same pattern as
  // danger/dangerBg above: a dark-tinted bg, and text bright
  // enough to read clearly against it).
  healthInsightsBg: '#3A1E28',
  healthInsightsBorder: '#6B2E3D',
  healthInsightsText: '#FDA4AF',
  healthInsightsTextSecondary: '#FB7185',
};