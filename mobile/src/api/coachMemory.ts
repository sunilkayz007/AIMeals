import { apiClient } from './client';

export interface CoachMemoryFact {
  id: string;
  fact: string;
  created_at: string;
}

interface CoachMemoryListResponse {
  facts: CoachMemoryFact[];
}

interface CoachMemoryClearResponse {
  cleared_count: number;
}

// Backs the Settings screen's "Coach memory" section — lets the user
// see and clear the dietary-preference/goal facts the Nutrition Coach
// has silently remembered across conversations. See
// app/api/v1/coach_memory.py's docstring on the backend for the full
// privacy/control reasoning.
export const coachMemoryApi = {
  list: () => apiClient.get<CoachMemoryListResponse>('/api/v1/coach/memory'),
  clear: () => apiClient.delete<CoachMemoryClearResponse>('/api/v1/coach/memory'),
};
