// =========================================================
// REAL implementation (GET /api/v1/ai/allergy-facts, matches
// aimeals_allergy_facts_prompt.md's spec).
//
// Returns {text, category} per fact (not just string[] anymore)
// — category is what lets the Allergies screen show a medical
// disclaimer only when a fact actually touches treatment/
// medication content, rather than guessing from the text.
// =========================================================

import { apiClient } from './client';

export interface AllergyFact {
  text: string;
  category: 'epidemiology' | 'mechanisms' | 'cross_reactivity' | 'prevention' | 'diagnosis' | 'treatment';
}

interface AllergyFactsResponse {
  facts: AllergyFact[];
}

export async function getAllergyFacts(): Promise<AllergyFact[]> {
  const response = await apiClient.get<AllergyFactsResponse>('/api/v1/ai/allergy-facts');
  return response.facts;
}