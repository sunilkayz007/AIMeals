import { apiClient } from './client';
import type { PantryItem, PantryItemCreate, PantryItemUpdate } from '../types/pantry';

export const pantryApi = {
  list: () => apiClient.get<PantryItem[]>('/api/v1/pantry'),

  getExpiringSoon: (withinDays = 3) =>
    apiClient.get<PantryItem[]>(`/api/v1/pantry/expiring-soon?within_days=${withinDays}`),

  // Always creates a new row server-side, even for a duplicate ingredient
  // name — never merges quantities. Don't try to "update instead of add"
  // client-side for an existing item with the same name.
  add: (payload: PantryItemCreate) => apiClient.post<PantryItem>('/api/v1/pantry', payload),

  // Genuinely partial — only send fields that actually changed.
  update: (id: string, payload: PantryItemUpdate) =>
    apiClient.patch<PantryItem>(`/api/v1/pantry/${id}`, payload),

  remove: (id: string) => apiClient.delete<void>(`/api/v1/pantry/${id}`),
};