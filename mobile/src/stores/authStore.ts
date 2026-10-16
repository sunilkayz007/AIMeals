import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { authApi } from '../api/auth';
import { authOtpApi } from '../api/authOtp';
import { passwordResetApi } from '../api/passwordReset';
import { registerAuthStoreAccessor } from '../api/client';
import type { LoginRequest, RegisterRequest, Tokens, User } from '../types/auth';
const TOKENS_KEY = 'aimeals_auth_tokens';
const USER_KEY = 'aimeals_auth_user';

interface AuthState {
  tokens: Tokens | null;
  user: User | null;
  isLoading: boolean; // true until persisted state has been checked once
  isSubmitting: boolean; // true during an in-flight login/register call
  error: string | null;

  hydrate: () => Promise<void>;
  signIn: (credentials: LoginRequest) => Promise<void>;
  signUp: (data: RegisterRequest) => Promise<void>;
  completeSignupWithOtp: (email: string, otpCode: string, password: string) => Promise<void>;
  completePasswordReset: (email: string, otpCode: string, newPassword: string) => Promise<void>;
  signOut: () => void;
  setTokens: (tokens: Tokens) => void;
  clearError: () => void;
}

/** Shared by signIn, signUp, and completeSignupWithOtp: stores
 * tokens, fetches /me, stores user. */
async function establishSession(tokens: Tokens): Promise<User> {
  await SecureStore.setItemAsync(TOKENS_KEY, JSON.stringify(tokens));
  const user = await authApi.me(tokens.access_token);
  await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
  return user;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  tokens: null,
  user: null,
  isLoading: true,
  isSubmitting: false,
  error: null,

  hydrate: async () => {
    try {
      const [tokensJson, userJson] = await Promise.all([
        SecureStore.getItemAsync(TOKENS_KEY),
        SecureStore.getItemAsync(USER_KEY),
      ]);
      set({
        tokens: tokensJson ? JSON.parse(tokensJson) : null,
        user: userJson ? JSON.parse(userJson) : null,
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  signIn: async (credentials) => {
    set({ isSubmitting: true, error: null });
    try {
      const tokens = await authApi.login(credentials);
      const user = await establishSession(tokens);
      set({ tokens, user, isSubmitting: false });
    } catch (err) {
      set({
        isSubmitting: false,
        error: err instanceof Error ? err.message : 'Sign in failed',
      });
      throw err;
    }
  },

  // Backend register() returns only the created user, not tokens —
  // so sign-up chains register -> login -> /me in one flow.
  signUp: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      await authApi.register(data);
      const tokens = await authApi.login({ email: data.email, password: data.password });
      const user = await establishSession(tokens);
      set({ tokens, user, isSubmitting: false });
    } catch (err) {
      set({
        isSubmitting: false,
        error: err instanceof Error ? err.message : 'Sign up failed',
      });
      throw err;
    }
  },

  // OTP-based signup step 2 (verify code + set password). Unlike
  // signUp() above, the backend endpoint here returns tokens
  // directly (auto-login) — no separate register -> login chain
  // needed, just establishSession() straight away.
  completeSignupWithOtp: async (email, otpCode, password) => {
    set({ isSubmitting: true, error: null });
    try {
      const tokens = await authOtpApi.verifyOtp({ email, otp_code: otpCode, password });
      const user = await establishSession(tokens);
      set({ tokens, user, isSubmitting: false });
    } catch (err) {
      set({
        isSubmitting: false,
        error: err instanceof Error ? err.message : 'Verification failed',
      });
      throw err;
    }
  },

  // Password-reset step 2 (verify code + set new password). Same
  // auto-login precedent as completeSignupWithOtp above -- the
  // backend endpoint returns tokens directly.
  completePasswordReset: async (email, otpCode, newPassword) => {
    set({ isSubmitting: true, error: null });
    try {
      const tokens = await passwordResetApi.confirmReset({
        email,
        otp_code: otpCode,
        new_password: newPassword,
      });
      const user = await establishSession(tokens);
      set({ tokens, user, isSubmitting: false });
    } catch (err) {
      set({
        isSubmitting: false,
        error: err instanceof Error ? err.message : 'Password reset failed',
      });
      throw err;
    }
  },

  signOut: () => {
    const refreshToken = get().tokens?.refresh_token;
    if (refreshToken) {
      // Best-effort server-side revoke; don't block clearing local state on it.
      authApi.logout(refreshToken).catch(() => {});
    }
    SecureStore.deleteItemAsync(TOKENS_KEY).catch(() => {});
    SecureStore.deleteItemAsync(USER_KEY).catch(() => {});
    set({ tokens: null, user: null });
  },

  setTokens: (tokens) => {
    SecureStore.setItemAsync(TOKENS_KEY, JSON.stringify(tokens)).catch(() => {});
    set({ tokens });
  },

  clearError: () => set({ error: null }),
}));

registerAuthStoreAccessor({
  getToken: () => useAuthStore.getState().tokens?.access_token,
  getRefreshToken: () => useAuthStore.getState().tokens?.refresh_token,
  setTokens: (tokens) => useAuthStore.getState().setTokens(tokens),
  signOut: () => useAuthStore.getState().signOut(),
});