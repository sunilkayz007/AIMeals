import { streamSSEWithFile } from './sse';
import { apiClient } from './client';

export type HealthReportAnalysisStage = 'checking_credits' | 'analyzing_report' | 'saving';

export const HEALTH_REPORT_STAGE_ORDER: HealthReportAnalysisStage[] = [
  'checking_credits',
  'analyzing_report',
  'saving',
];

export const HEALTH_REPORT_STAGE_LABELS: Record<HealthReportAnalysisStage, string> = {
  checking_credits: 'Checking credits',
  analyzing_report: 'Analyzing your report',
  saving: 'Saving results',
};

export type HealthReportStatus = 'awaiting_confirmation' | 'confirmed';
export type RangeStatus = 'below' | 'within' | 'above' | null;
export type PriorityLevel = 'high' | 'medium' | 'low';
export type GuidanceType = 'increase' | 'limit' | 'prioritize';

// Mirrors app/schemas/health_report.py's HealthMarkerOut exactly,
// including range_status — a computed, non-diagnostic field (below/
// within/above the report's own printed reference range), never a
// disease name.
export interface HealthMarker {
  name: string;
  value: number;
  unit: string | null;
  reference_range_text: string | null;
  reference_range_min: number | null;
  reference_range_max: number | null;
  source_page: number | null;
  confidence: number | null;
  range_status: RangeStatus;
}

// Mirrors HealthPriorityOut — strictly non-diagnostic by construction,
// see backend _NUTRITION_FOCUS_SYSTEM_PROMPT's safety rules.
export interface HealthPriority {
  key: string;
  title: string;
  priority: PriorityLevel;
  guidance_type: GuidanceType;
  description: string;
  action_items: string[];
  foods_to_explore: string[];
}

export interface HealthReport {
  id: string;
  user_id: string;
  report_label: string | null;
  status: HealthReportStatus;
  extracted_markers: HealthMarker[];
  confirmed_markers: HealthMarker[] | null;
  nutrition_priorities: HealthPriority[] | null;
  created_at: string;
  updated_at: string;
}

interface AnalyzeHealthReportHandlers {
  // detail carries a live "Extracted <marker name>" line while
  // stage === "analyzing_report" — see sse.ts's SSEHandlers.onStage.
  onStage?: (stage: string, detail?: string) => void;
  onResult?: (report: HealthReport) => void;
  onError?: (errorType: string, detail: string) => void;
}

/**
 * Streams a health report analysis request. Returns an abort function.
 * fileUri is a local file URI from expo-document-picker (PDF) or
 * expo-image-picker (photo of a report) — the file is uploaded, never
 * stored server-side; only the extracted structured markers are kept.
 *
 * mimeType/fileName should reflect the ACTUAL picked file, matching
 * analyzeFoodImage()'s same reasoning in aiFoodImage.ts — a mismatch
 * between declared and real file type can cause Claude to reject the
 * upload.
 */
export function analyzeHealthReport(
  fileUri: string,
  mimeType: string,
  fileName: string,
  handlers: AnalyzeHealthReportHandlers
): () => void {
  return streamSSEWithFile(
    '/api/v1/health-reports/analyze',
    fileUri,
    'report',
    {
      onStage: (stage, detail) => handlers.onStage?.(stage, detail),
      onResult: (data) => handlers.onResult?.(data as HealthReport),
      onError: (errorType, detail) => handlers.onError?.(errorType, detail),
    },
    fileName,
    mimeType
  );
}

/**
 * Confirms a health report's markers (possibly edited by the user
 * during review), triggering the Nutrition Focus Engine. FREE — no
 * credit cost, not streamed (a single request/response, not an SSE
 * call — the backend's own confirm_health_report() runs synchronously
 * within one request, unlike the longer analyze step).
 */
export const confirmHealthReport = (
  reportId: string,
  markers: HealthMarker[]
) => apiClient.post<HealthReport>(`/api/v1/health-reports/${reportId}/confirm`, { markers });

/** Returns the current user's health reports, most recent first. */
export const getHealthReports = () =>
  apiClient.get<HealthReport[]>('/api/v1/health-reports');

/** Returns a single health report. */
export const getHealthReport = (reportId: string) =>
  apiClient.get<HealthReport>(`/api/v1/health-reports/${reportId}`);

/** Deletes a health report permanently. */
export const deleteHealthReport = (reportId: string) =>
  apiClient.delete<void>(`/api/v1/health-reports/${reportId}`);