import { apiClient } from './client';
import type { CreditCost, InteractionType, Subscription } from '../types/subscription';

export const subscriptionApi = {
  // Can return null — a user without a subscription row yet is a valid
  // (if rare, since register() auto-provisions Free tier) state, not an error.
  get: () => apiClient.get<Subscription | null>('/api/v1/subscription'),

  getCreditCost: (interactionType: InteractionType) =>
    apiClient.get<CreditCost>(`/api/v1/subscription/credit-cost/${interactionType}`),
};