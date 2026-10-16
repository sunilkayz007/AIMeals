import { apiClient } from './client';

export interface WaterDaySummary {
  logged_at: string;
  manual_ml: number;
  food_derived_ml: number;
  total_ml: number;
  target_ml: number | null;
  expected_so_far_ml: number | null;
  pace_status: 'ahead' | 'on_track' | 'behind' | null;
}

export interface WaterLogEntry {
  id: string;
  user_id: string;
  logged_at: string;
  amount_ml: number;
  created_at: string;
}

export const waterApi = {
  logWater: (loggedAt: string, amountMl: number) =>
    apiClient.post<WaterLogEntry>('/api/v1/water-logs', {
      logged_at: loggedAt,
      amount_ml: amountMl,
    }),

  deleteLog: (logId: string) => apiClient.delete<void>(`/api/v1/water-logs/${logId}`),

  getDaySummary: (targetDate: string) =>
    apiClient.get<WaterDaySummary>(`/api/v1/water-logs/day/${targetDate}`),
};