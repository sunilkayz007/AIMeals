import { apiClient } from './client';

export const deleteAccountApi = {
  requestOtp: (password: string) =>
    apiClient.post<void>('/api/v1/auth/me/request-deletion-otp', { password }),

  confirmDeletion: (otpCode: string) =>
    apiClient.delete<void>('/api/v1/auth/me', { body: { otp_code: otpCode } }),
};