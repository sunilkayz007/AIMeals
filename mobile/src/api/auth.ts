import { apiClient } from './client';
import type {
  LoginRequest,
  RegisterRequest,
  RefreshRequest,
  Tokens,
  User,
} from '../types/auth';

export const authApi = {
  // Returns the created user — NOT tokens. Sign-up must call login() separately.
  register: (data: RegisterRequest) =>
    apiClient.post<User>('/api/v1/auth/register', data, { skipAuth: true }),

  // Returns only { access_token, refresh_token, token_type } — no user object.
  login: (credentials: LoginRequest) =>
    apiClient.post<Tokens>('/api/v1/auth/login', credentials, { skipAuth: true }),

  refresh: (data: RefreshRequest) =>
    apiClient.post<Tokens>('/api/v1/auth/refresh', data, { skipAuth: true }),

  // Backend requires the refresh_token in the body to revoke it —
  // a bare bearer-token call does nothing server-side.
  logout: (refreshToken: string) =>
    apiClient.post<void>('/api/v1/auth/logout', { refresh_token: refreshToken }),

  // Protected — fetch the current user's profile after obtaining tokens.
  // Accepts an explicit token because this is often called immediately
  // after login/register, before the auth store's state has updated.
  me: (token?: string) => apiClient.get<User>('/api/v1/auth/me', token ? { token } : undefined),
};