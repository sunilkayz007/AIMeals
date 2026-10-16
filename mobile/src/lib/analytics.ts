import { logEvent, setUserId, setUserProperty } from './firebase';

/**
 * High-level analytics wrapper for AIMeals.
 * All events are logged with Firebase Analytics.
 * Centralizes event naming and parameter tracking.
 */

// ============================================================================
// AUTHENTICATION & USER EVENTS
// ============================================================================

export const analytics_signup = async (method: 'email' | 'otp') => {
  await logEvent('signup', { method });
};

export const analytics_signup_complete = async (method: string) => {
  await logEvent('signup_complete', { method });
};

export const analytics_login = async (method: 'email' | 'password') => {
  await logEvent('login', { method });
};

export const analytics_logout = async () => {
  await logEvent('logout');
  await setUserId(null);
};

export const analytics_password_reset = async () => {
  await logEvent('password_reset');
};

export const analytics_otp_requested = async () => {
  await logEvent('otp_requested');
};

export const analytics_otp_verified = async (success: boolean) => {
  await logEvent('otp_verified', { success });
};

export const analytics_user_identified = async (userId: string, tier: string) => {
  await setUserId(userId);
  await setUserProperty('subscription_tier', tier);
};

// ============================================================================
// FOOD SCANNING & ANALYSIS
// ============================================================================

export const analytics_food_scan_opened = async () => {
  await logEvent('food_scan_opened');
};

export const analytics_food_photo_captured = async () => {
  await logEvent('food_photo_captured');
};

export const analytics_food_scan_started = async () => {
  await logEvent('food_scan_started');
};

export const analytics_food_scan_completed = async (
  success: boolean,
  calories?: number,
  timeMs?: number
) => {
  await logEvent('food_scan_completed', {
    success,
    ...(calories && { calories }),
    ...(timeMs && { time_ms: timeMs }),
  });
};

export const analytics_food_scan_failed = async (error: string) => {
  await logEvent('food_scan_failed', { error: error.substring(0, 50) });
};

// ============================================================================
// INGREDIENT SCANNING
// ============================================================================

export const analytics_ingredient_scan_opened = async () => {
  await logEvent('ingredient_scan_opened');
};

export const analytics_ingredient_scan_started = async () => {
  await logEvent('ingredient_scan_started');
};

export const analytics_ingredient_scan_completed = async (
  success: boolean,
  ingredientCount?: number
) => {
  await logEvent('ingredient_scan_completed', {
    success,
    ...(ingredientCount && { ingredient_count: ingredientCount }),
  });
};

export const analytics_ingredient_scan_failed = async (error: string) => {
  await logEvent('ingredient_scan_failed', { error: error.substring(0, 50) });
};

// ============================================================================
// MEAL LOGGING
// ============================================================================

export const analytics_meal_log_opened = async () => {
  await logEvent('meal_log_opened');
};

export const analytics_meal_logged = async (
  method: 'manual' | 'scan' | 'recipe',
  calories: number
) => {
  await logEvent('meal_logged', { method, calories });
};

export const analytics_meal_log_deleted = async () => {
  await logEvent('meal_log_deleted');
};

export const analytics_estimate_nutrition_started = async () => {
  await logEvent('estimate_nutrition_started');
};

export const analytics_estimate_nutrition_completed = async (success: boolean) => {
  await logEvent('estimate_nutrition_completed', { success });
};

// ============================================================================
// WATER LOGGING
// ============================================================================

export const analytics_water_logged = async (amountMl: number) => {
  await logEvent('water_logged', { amount_ml: amountMl });
};

export const analytics_water_log_deleted = async () => {
  await logEvent('water_log_deleted');
};

// ============================================================================
// RECIPES & MEAL PLANNING
// ============================================================================

export const analytics_recipe_generator_opened = async () => {
  await logEvent('recipe_generator_opened');
};

export const analytics_recipe_generated = async (
  source: 'pantry' | 'manual',
  recipeCount?: number
) => {
  await logEvent('recipe_generated', {
    source,
    ...(recipeCount && { recipe_count: recipeCount }),
  });
};

export const analytics_recipe_generated_failed = async (error: string) => {
  await logEvent('recipe_generated_failed', { error: error.substring(0, 50) });
};

export const analytics_recipe_saved = async () => {
  await logEvent('recipe_saved');
};

export const analytics_recipe_viewed = async (recipeId: string) => {
  await logEvent('recipe_viewed', { recipe_id: recipeId });
};

export const analytics_meal_plan_generated = async (
  duration: 'daily' | 'weekly' | 'monthly',
  success: boolean
) => {
  await logEvent('meal_plan_generated', { duration, success });
};

export const analytics_meal_plan_generated_failed = async (error: string) => {
  await logEvent('meal_plan_generated_failed', { error: error.substring(0, 50) });
};

// ============================================================================
// PANTRY MANAGEMENT
// ============================================================================

export const analytics_pantry_opened = async () => {
  await logEvent('pantry_opened');
};

export const analytics_pantry_item_added = async (itemName: string) => {
  await logEvent('pantry_item_added', { item_name: itemName.substring(0, 50) });
};

export const analytics_pantry_item_removed = async () => {
  await logEvent('pantry_item_removed');
};

export const analytics_pantry_chef_opened = async () => {
  await logEvent('pantry_chef_opened');
};

// ============================================================================
// COACH & CHAT
// ============================================================================

export const analytics_coach_opened = async () => {
  await logEvent('coach_opened');
};

export const analytics_coach_message_sent = async (messageLength: number) => {
  await logEvent('coach_message_sent', { message_length: messageLength });
};

export const analytics_coach_message_received = async (responseLength: number) => {
  await logEvent('coach_message_received', { response_length: responseLength });
};

export const analytics_coach_chat_cleared = async () => {
  await logEvent('coach_chat_cleared');
};

export const analytics_coach_daily_tip_viewed = async () => {
  await logEvent('coach_daily_tip_viewed');
};

// ============================================================================
// SUBSCRIPTIONS & MONETIZATION
// ============================================================================

export const analytics_subscription_paywall_shown = async (tier: 'plus' | 'pro') => {
  await logEvent('subscription_paywall_shown', { tier });
};

export const analytics_subscription_purchase_initiated = async (tier: string) => {
  await logEvent('subscription_purchase_initiated', { tier });
};

export const analytics_subscription_purchase_completed = async (
  tier: string,
  price: number,
  currency: string
) => {
  await logEvent('subscription_purchase_completed', { tier, price, currency });
};

export const analytics_subscription_purchase_failed = async (
  tier: string,
  error: string
) => {
  await logEvent('subscription_purchase_failed', {
    tier,
    error: error.substring(0, 50),
  });
};

export const analytics_subscription_restored = async (tier: string) => {
  await logEvent('subscription_restored', { tier });
};

export const analytics_credits_display_viewed = async (creditsRemaining: number) => {
  await logEvent('credits_display_viewed', { credits_remaining: creditsRemaining });
};

export const analytics_rewarded_ad_shown = async () => {
  await logEvent('rewarded_ad_shown');
};

export const analytics_rewarded_ad_completed = async (creditsEarned: number) => {
  await logEvent('rewarded_ad_completed', { credits_earned: creditsEarned });
};

export const analytics_rewarded_ad_failed = async (error: string) => {
  await logEvent('rewarded_ad_failed', { error: error.substring(0, 50) });
};

// ============================================================================
// HEALTH DATA & ALLERGIES
// ============================================================================

export const analytics_health_report_upload_started = async () => {
  await logEvent('health_report_upload_started');
};

export const analytics_health_report_uploaded = async (success: boolean) => {
  await logEvent('health_report_uploaded', { success });
};

export const analytics_health_report_upload_failed = async (error: string) => {
  await logEvent('health_report_upload_failed', { error: error.substring(0, 50) });
};

export const analytics_allergy_added = async (allergyName: string) => {
  await logEvent('allergy_added', { allergy: allergyName.substring(0, 50) });
};

export const analytics_allergy_removed = async () => {
  await logEvent('allergy_removed');
};

export const analytics_allergen_insight_viewed = async (
  allergenName: string,
  isDeep: boolean
) => {
  await logEvent('allergen_insight_viewed', {
    allergen: allergenName.substring(0, 50),
    is_deep: isDeep,
  });
};

// ============================================================================
// ACHIEVEMENTS
// ============================================================================

export const analytics_achievement_earned = async (achievementId: string) => {
  await logEvent('achievement_earned', { achievement_id: achievementId });
};

export const analytics_achievement_viewed = async (achievementId: string) => {
  await logEvent('achievement_viewed', { achievement_id: achievementId });
};

// ============================================================================
// SETTINGS & PREFERENCES
// ============================================================================

export const analytics_profile_updated = async () => {
  await logEvent('profile_updated');
};

export const analytics_goals_updated = async () => {
  await logEvent('goals_updated');
};

export const analytics_theme_changed = async (theme: 'light' | 'dark' | 'auto') => {
  await logEvent('theme_changed', { theme });
};

export const analytics_settings_opened = async () => {
  await logEvent('settings_opened');
};

export const analytics_delete_account_initiated = async () => {
  await logEvent('delete_account_initiated');
};

export const analytics_delete_account_completed = async (success: boolean) => {
  await logEvent('delete_account_completed', { success });
};

// ============================================================================
// NAVIGATION & UI
// ============================================================================

export const analytics_screen_viewed = async (screenName: string) => {
  await logEvent('screen_viewed', {
    screen_name: screenName.substring(0, 50),
  });
};

export const analytics_feature_accessed = async (featureName: string) => {
  await logEvent('feature_accessed', {
    feature_name: featureName.substring(0, 50),
  });
};

// ============================================================================
// FEEDBACK & SUPPORT
// ============================================================================

export const analytics_feedback_submitted = async (category: string) => {
  await logEvent('feedback_submitted', {
    category: category.substring(0, 50),
  });
};

export const analytics_support_contacted = async () => {
  await logEvent('support_contacted');
};

// ============================================================================
// ERROR TRACKING
// ============================================================================

export const analytics_error_occurred = async (errorType: string, message: string) => {
  await logEvent('error_occurred', {
    error_type: errorType.substring(0, 50),
    error_message: message.substring(0, 50),
  });
};

export const analytics_app_crash = async (crashMessage: string) => {
  await logEvent('app_crash', { crash_message: crashMessage.substring(0, 100) });
};

// ============================================================================
// SESSION TRACKING
// ============================================================================

export const analytics_session_started = async () => {
  await logEvent('session_started');
};

export const analytics_session_ended = async (durationMs: number) => {
  await logEvent('session_ended', { duration_ms: durationMs });
};
