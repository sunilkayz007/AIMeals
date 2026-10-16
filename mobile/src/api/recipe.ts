import { apiClient } from './client';
import type { Recipe, RecipeCreate, RecipeUpdate } from '../types/recipe';

export const recipeApi = {
  mine: () => apiClient.get<Recipe[]>('/api/v1/recipes/mine'),

  system: () => apiClient.get<Recipe[]>('/api/v1/recipes/system'),

  get: (id: string) => apiClient.get<Recipe>(`/api/v1/recipes/${id}`),

  create: (payload: RecipeCreate) => apiClient.post<Recipe>('/api/v1/recipes', payload),

  // Genuinely partial — only send fields that actually changed.
  update: (id: string, payload: RecipeUpdate) =>
    apiClient.patch<Recipe>(`/api/v1/recipes/${id}`, payload),

  remove: (id: string) => apiClient.delete<void>(`/api/v1/recipes/${id}`),
};