import { initializeApp } from 'firebase/app';
import { getAnalytics, logEvent as firebaseLogEvent, setUserId as firebaseSetUserId, setUserProperties } from 'firebase/analytics';

// Firebase configuration (from google-services.json converted to web config)
const firebaseConfig = {
  apiKey: 'AIzaSyD1uc777J4Je2hUHtI2rJlC0Ev7T_11PQY',
  projectId: 'aimeals-73c28',
  appId: '1:19304602866:android:e26472b226b271b9a0846b',
};

let analyticsInstance: ReturnType<typeof getAnalytics> | null = null;

/**
 * Initialize Firebase Analytics.
 * Call this once during app startup before logging any events.
 */
export const initializeAnalytics = async () => {
  try {
    const app = initializeApp(firebaseConfig);
    analyticsInstance = getAnalytics(app);
    console.log('[Analytics] Firebase Analytics initialized');
  } catch (error) {
    console.error('[Analytics] Failed to initialize Firebase Analytics:', error);
  }
};

/**
 * Log a user property (e.g., subscription tier, profile data).
 * These are persistent user attributes used for segmentation.
 */
export const setUserProperty = async (property: string, value: string) => {
  try {
    if (!analyticsInstance) {
      console.warn('[Analytics] Analytics not initialized yet');
      return;
    }
    setUserProperties(analyticsInstance, { [property]: value });
  } catch (error) {
    console.error(`[Analytics] Failed to set user property ${property}:`, error);
  }
};

/**
 * Set the user ID for analytics tracking.
 * Call this after login; call with null on logout.
 */
export const setUserId = async (userId: string | null) => {
  try {
    if (!analyticsInstance) {
      console.warn('[Analytics] Analytics not initialized yet');
      return;
    }
    if (userId) {
      firebaseSetUserId(analyticsInstance, userId);
    } else {
      firebaseSetUserId(analyticsInstance, null);
    }
  } catch (error) {
    console.error('[Analytics] Failed to set user ID:', error);
  }
};

/**
 * Log an analytics event with optional parameters.
 * Firebase limits event names to 40 characters and parameter names to 40 characters.
 */
export const logEvent = async (
  eventName: string,
  params?: Record<string, string | number | boolean>
) => {
  try {
    if (!analyticsInstance) {
      console.warn('[Analytics] Analytics not initialized yet');
      return;
    }

    // Sanitize event name: lowercase, max 40 chars, alphanumeric + underscore
    const cleanName = eventName
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, '_')
      .substring(0, 40);

    // Log to Firebase
    firebaseLogEvent(analyticsInstance, cleanName, params);
  } catch (error) {
    console.error(`[Analytics] Failed to log event ${eventName}:`, error);
  }
};
