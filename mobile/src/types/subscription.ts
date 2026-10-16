// Mirrors app/schemas/subscription.py and app/models/subscription.py exactly.

export type SubscriptionTier = 'free' | 'plus' | 'pro';

export type SubscriptionStatus = 'active' | 'trialing' | 'cancelled' | 'expired';

export interface Subscription {
  id: string;
  tier: SubscriptionTier;
  status: SubscriptionStatus;
  current_period_start: string | null; // ISO datetime
  current_period_end: string | null; // ISO datetime
  cancel_at_period_end: boolean;
  monthly_credit_allowance: number;
  credits_used_this_period: number;
  // Computed server-side (allowance - used) — don't recompute client-side.
  credits_remaining: number;
}

// Confirmed exact values from app/models/ai_interaction.py's InteractionType enum.
export type InteractionType =
  | 'chat'
  | 'recipe_generation'
  | 'meal_plan_generation'
  | 'food_image_analysis'
  | 'pantry_suggestion'
  | 'ingredient_image_identify'
  | 'ingredient_photo_recipe';

export interface CreditCost {
  interaction_type: InteractionType;
  credit_cost: number;
}