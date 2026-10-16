import { apiClient } from './client';
import type { Tokens } from '../types/auth';

export interface RequestSignupOtpPayload {
  email: string;
  first_name: string;
  last_name: string;
}

export interface VerifySignupOtpPayload {
  email: string;
  otp_code: string;
  password: string;
}

export const authOtpApi = {
  requestOtp: (payload: RequestSignupOtpPayload) =>
    apiClient.post<void>('/api/v1/auth/register/request-otp', payload),

  verifyOtp: (payload: VerifySignupOtpPayload) =>
    apiClient.post<Tokens>('/api/v1/auth/register/verify-otp', payload),
};