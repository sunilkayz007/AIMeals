// Mirrors app/schemas/auth.py and app/schemas/user.py exactly,
// confirmed against the real backend source.

export type UserRole = string; // backend has a UserRole enum; treat as string
                                 // until we need to branch on specific roles

export interface User {
  id: string; // uuid
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string; // ISO datetime
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string; // "bearer"
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface RefreshRequest {
  refresh_token: string;
}
