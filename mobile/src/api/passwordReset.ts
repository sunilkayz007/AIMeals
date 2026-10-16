import { apiClient } from './client';
import type { Tokens } from '../types/auth';

export interface RequestPasswordResetPayload {
  email: string;
}

export interface ConfirmPasswordResetPayload {
  email: string;
  otp_code: string;
  new_password: string;
}

// Backs the Forgot Password / Reset Password screens. Both endpoints
// work without an access token -- the whole point is the user is
// locked out (mirrors authOtp.ts's register/* endpoints, which are
// also unauthenticated and don't pass any explicit skipAuth flag).
//
// forgot-password always returns 204 whether or not the email is
// registered -- see the backend's AuthService.request_password_reset()
// docstring for the anti-enumeration reasoning. Don't treat success
// here as confirmation the email exists.
export const passwordResetApi = {
  requestReset: (payload: RequestPasswordResetPayload) =>
    apiClient.post<void>('/api/v1/auth/forgot-password', payload),

  confirmReset: (payload: ConfirmPasswordResetPayload) =>
    apiClient.post<Tokens>('/api/v1/auth/reset-password', payload),
};
