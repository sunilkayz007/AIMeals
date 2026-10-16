import { apiClient } from './client';

export type ReportCategory = 'bug' | 'suggestion' | 'complaint' | 'praise';
export type ReportStatus = 'open' | 'in_progress' | 'resolved';

export interface ReportComment {
  id: string;
  report_id: string;
  author_user_id: string;
  author_email: string;
  is_admin_reply: boolean;
  comment_text: string;
  created_at: string;
}

export interface Report {
  id: string;
  user_id: string;
  user_email: string;
  category: ReportCategory;
  title: string;
  description: string;
  status: ReportStatus;
  created_at: string;
  updated_at: string;
}

export interface ReportDetail extends Report {
  comments: ReportComment[];
}

export const reportsApi = {
  create: (category: ReportCategory, title: string, description: string) =>
    apiClient.post<Report>('/api/v1/reports', { category, title, description }),

  list: () => apiClient.get<Report[]>('/api/v1/reports'),

  getDetail: (reportId: string) =>
    apiClient.get<ReportDetail>(`/api/v1/reports/${reportId}`),

  addComment: (reportId: string, commentText: string) =>
    apiClient.post<ReportComment>(`/api/v1/reports/${reportId}/comments`, {
      comment_text: commentText,
    }),

  closeReport: (reportId: string) =>
    apiClient.post<Report>(`/api/v1/reports/${reportId}/close`, {}),
};