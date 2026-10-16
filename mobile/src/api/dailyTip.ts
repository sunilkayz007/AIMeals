import { apiClient } from './client';

interface DailyTipResponse {
  tip_text: string | null;
}

export const dailyTipApi = {
  // tip_text is null when there's nothing meaningful to show yet (no
  // goals configured, or a same-day generation failure) — not an error,
  // the caller should just render nothing in that case.
  get: () => apiClient.get<DailyTipResponse>('/api/v1/ai/daily-tip'),
};