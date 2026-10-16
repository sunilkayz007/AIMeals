const BASE_URL = process.env.EXPO_PUBLIC_API_URL;

if (!BASE_URL) {
  // Fails loudly at startup rather than silently hitting undefined/undefined.
  throw new Error(
    'EXPO_PUBLIC_API_URL is not set. Copy .env.example to .env and set it — see SETUP.md.'
  );
}

// client.ts is used by auth.ts, which is used by authStore.ts — so client.ts
// can't import authStore.ts directly without creating a require cycle
// (authStore -> auth -> client -> authStore). Instead, authStore registers
// itself here once, after it's fully created. See the bottom of authStore.ts.
interface AuthStoreAccessor {
  getToken: () => string | undefined;
  getRefreshToken: () => string | undefined;
  setTokens: (tokens: { access_token: string; refresh_token: string; token_type: string }) => void;
  signOut: () => void;
}

let authStoreAccessor: AuthStoreAccessor | null = null;

export function registerAuthStoreAccessor(accessor: AuthStoreAccessor) {
  authStoreAccessor = accessor;
}

function requireAuthStoreAccessor(): AuthStoreAccessor {
  if (!authStoreAccessor) {
    throw new Error(
      'authStoreAccessor not registered yet — registerAuthStoreAccessor() must run before any API calls. Check authStore.ts.'
    );
  }
  return authStoreAccessor;
}

class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

/**
 * Extracts a real, human-readable message from a FastAPI error
 * response body, falling back to a generic status-code message
 * only when the body doesn't have anything usable.
 *
 * FastAPI's `detail` field comes in two shapes depending on the
 * error:
 *   - A plain string, for custom HTTPExceptions raised directly
 *     (e.g. `raise HTTPException(status_code=409, detail=str(e))`)
 *     — the common case throughout this backend's controllers.
 *   - An array of {msg, loc, type} objects, for Pydantic
 *     validation errors (422s) — FastAPI's own automatic format,
 *     not something any controller constructs by hand.
 * Previously this function's result was computed but never used —
 * every ApiError's .message was hardcoded to the generic string
 * regardless of what the backend actually said, even though the
 * real detail was already being captured on .body. This was the
 * root cause of every screen in the app showing "Request to ...
 * failed with status ..." instead of the actual backend message.
 */
function extractErrorMessage(path: string, status: number, parsedBody: unknown): string {
  if (parsedBody && typeof parsedBody === 'object' && 'detail' in parsedBody) {
    const detail = (parsedBody as { detail: unknown }).detail;

    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          item && typeof item === 'object' && 'msg' in item
            ? String((item as { msg: unknown }).msg)
            : null
        )
        .filter((msg): msg is string => !!msg);
      if (messages.length > 0) return messages.join(' ');
    }
  }

  if (status >= 500) {
    return 'Something went wrong on our side. Please try again in a moment.';
  }

  return `Request to ${path} failed with status ${status}`;
}

const OFFLINE_MESSAGE = "You're offline or we can't reach the server. Check your connection and try again.";

/**
 * Thrown when a request never got an HTTP response (offline, DNS
 * failure, timeout). React Native's own message for this includes the
 * Java exception and the backend hostname ("fetch failed:
 * java.net.UnknownHostException: Unable to resolve host ..."), which
 * every screen renders as-is via `err.message` — so the friendly text
 * is applied here, once, instead of in each screen.
 */
class NetworkError extends Error {
  constructor() {
    super(OFFLINE_MESSAGE);
  }
}

/** fetch() that turns a transport failure into a NetworkError. */
async function safeFetch(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new NetworkError();
  }
}

let refreshPromise: Promise<string | null> | null = null;

/**
 * Attempts to refresh the access token using the stored refresh token.
 * De-duplicated: if multiple requests 401 at the same time, only one
 * refresh call is made and all callers await the same promise.
 *
 * Calls POST /api/v1/auth/refresh directly (not via authApi, to avoid
 * a circular import with auth.ts) with body { refresh_token }, matching
 * app/schemas/auth.py's RefreshTokenRequest exactly.
 */
async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  const promise = (async () => {
    const accessor = requireAuthStoreAccessor();
    const refreshToken = accessor.getRefreshToken();
    if (!refreshToken) {
      accessor.signOut();
      return null;
    }

    try {
      const res = await safeFetch(`${BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) {
        // Only end the session when the server says the refresh token
        // itself is no good. A 5xx/429 (server hiccup) must not log the
        // user out — the stored token may still be perfectly valid.
        if (res.status >= 400 && res.status < 500 && res.status !== 429) {
          accessor.signOut();
        }
        return null;
      }

      // Response is a Token: { access_token, refresh_token, token_type }.
      // Refresh rotation means a NEW refresh_token comes back each time —
      // must be stored, or the next refresh will fail with a revoked-token error.
      const data = await res.json();
      accessor.setTokens(data);
      return data.access_token as string;
    } catch {
      // Network failure or an unreadable body: we don't know the token
      // is invalid, so keep the session and let the caller's request
      // fail with the original 401 / a network error. (Signing out
      // here used to drop users to the sign-in screen on a flaky
      // connection.)
      return null;
    }
  })();

  // Cleared from outside the IIFE so EVERY exit path resets it — the
  // early "no refresh token" return used to leave a settled promise
  // cached forever, silently disabling refresh for the rest of the
  // app session (even after the user signed back in).
  refreshPromise = promise;
  promise
    .finally(() => {
      if (refreshPromise === promise) refreshPromise = null;
    })
    .catch(() => {});

  return promise;
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** Set true for endpoints that don't require auth (login/register). */
  skipAuth?: boolean;
  /**
   * Explicit token to use instead of reading from the auth store.
   * Needed right after login/register, before the store's `tokens`
   * state has been set — see authStore.ts's establishSession().
   */
  token?: string;
}

/**
 * Core request function. JSON in, JSON out. Attaches the bearer token,
 * retries once on 401 after a token refresh, throws ApiError on any
 * non-2xx response (including the retry).
 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, skipAuth, token: explicitToken, headers, ...rest } = options;

  const doFetch = async (): Promise<Response> => {
    const token = explicitToken ?? requireAuthStoreAccessor().getToken();
    const authHeader = !skipAuth && token ? { Authorization: `Bearer ${token}` } : {};

    return safeFetch(`${BASE_URL}${path}`, {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch();

  if (res.status === 401 && !skipAuth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      res = await doFetch();
    }
  }

  if (!res.ok) {
    let parsedBody: unknown = null;
    try {
      parsedBody = await res.json();
    } catch {
      // response wasn't JSON (e.g. 500 HTML error page) — leave body null
    }
    throw new ApiError(
      res.status,
      parsedBody,
      extractErrorMessage(path, res.status, parsedBody)
    );
  }

  // 204 No Content — several endpoints return this (e.g. profile
  // allergy add/remove, per the backend handoff doc).
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'GET' }),

  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),

  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PUT', body }),

  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PATCH', body }),

  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'DELETE' }),

  /** Base URL exposed for cases that need it directly (e.g. building an SSE URL in Phase 4). */
  baseUrl: BASE_URL,
};

export { ApiError, NetworkError };