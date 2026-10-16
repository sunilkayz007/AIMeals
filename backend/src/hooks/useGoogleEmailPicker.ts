import { useEffect } from 'react';
import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';

WebBrowser.maybeCompleteAuthSession();

// Real Client ID, created in Google Cloud Console (Web application type).
const GOOGLE_CLIENT_ID = '597507276599-6p0pnads1eviqjrgn359jip237sbsufk.apps.googleusercontent.com';

const discovery = {
  authorizationEndpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
};

export interface GooglePickedIdentity {
  email: string;
  firstName: string;
  lastName: string;
}

/**
 * Opens Google's own account picker purely as a convenience for
 * selecting an email address — this is NOT authentication. The
 * resulting ID token is decoded client-side ONLY to read the
 * email/name claims for pre-filling the signup form; it is never
 * sent to the backend, never used to verify identity, and never
 * trusted as proof of anything. Real verification still happens
 * entirely through the existing OTP flow, completely unchanged.
 *
 * Uses ResponseType.IdToken (implicit flow) deliberately — this
 * returns the ID token directly with no token-exchange step,
 * meaning no client secret is ever needed here. A client secret
 * should never be embedded in a mobile app (it's extractable),
 * so this is the correct flow shape for a public mobile client,
 * not a shortcut.
 *
 * IMPORTANT: uses the app's custom URL scheme ("aimeals://",
 * already configured in app.json) for the OAuth redirect, which
 * requires a real development build — this will NOT work in
 * plain Expo Go. Same requirement RevenueCat's native SDK
 * already needs.
 */
export function useGoogleEmailPicker(onPicked: (identity: GooglePickedIdentity) => void) {
  const redirectUri = AuthSession.makeRedirectUri({ scheme: 'aimeals' });

  // Logged so you can copy the EXACT value into Google Cloud
  // Console's "Authorized redirect URIs" field — the precise
  // trailing-slash format Expo generates should be copied
  // verbatim rather than guessed, since it must match exactly.
  useEffect(() => {
    console.log('[Google email picker] Redirect URI to add in Google Cloud Console:', redirectUri);
  }, [redirectUri]);

  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: GOOGLE_CLIENT_ID,
      scopes: ['openid', 'email', 'profile'],
      redirectUri,
      responseType: AuthSession.ResponseType.IdToken,
      extraParams: {
        nonce: Math.random().toString(36).substring(2),
      },
    },
    discovery
  );

  useEffect(() => {
    if (response?.type === 'success' && response.params.id_token) {
      const identity = decodeGoogleIdToken(response.params.id_token);
      if (identity) onPicked(identity);
    }
  }, [response]);

  return { promptAsync, isReady: !!request };
}

/**
 * Dependency-free base64url decode — deliberately avoids atob()
 * (inconsistent availability across React Native/Hermes versions)
 * and Buffer (not guaranteed globally available either), for
 * maximum compatibility without adding a new package.
 *
 * NOTE: this simple byte-to-char mapping handles standard ASCII
 * names/emails correctly but does not do full UTF-8 multi-byte
 * decoding — a name with non-Latin characters (e.g. Cyrillic,
 * CJK) could come through slightly mangled. Acceptable here since
 * this only pre-fills a form field the user can freely edit
 * before submitting, not something silently trusted.
 */
function base64UrlDecode(input: string): string {
  const base64 = input.replace(/-/g, '+').replace(/_/g, '/');
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  let output = '';
  let buffer = 0;
  let bits = 0;

  for (const char of base64) {
    if (char === '=') break;
    const index = chars.indexOf(char);
    if (index === -1) continue;
    buffer = (buffer << 6) | index;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      output += String.fromCharCode((buffer >> bits) & 0xff);
    }
  }

  return output;
}

function decodeGoogleIdToken(idToken: string): GooglePickedIdentity | null {
  try {
    const payloadSegment = idToken.split('.')[1];
    const payload = JSON.parse(base64UrlDecode(payloadSegment));

    const fullName: string = payload.name || '';
    const [firstName, ...rest] = fullName.split(' ');

    return {
      email: payload.email || '',
      firstName: firstName || payload.given_name || '',
      lastName: rest.join(' ') || payload.family_name || '',
    };
  } catch {
    return null;
  }
}