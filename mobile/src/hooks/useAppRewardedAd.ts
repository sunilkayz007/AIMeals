import { useCallback, useEffect } from 'react';
import { useRewardedAd } from 'react-native-google-mobile-ads';
import { REWARDED_AD_UNIT_ID } from '../config/admob';

/**
 * Thin app-specific wrapper around react-native-google-mobile-ads'
 * own useRewardedAd hook. Handles the load lifecycle so callers don't
 * need to think about it: loads an ad as soon as this hook mounts
 * (so it's likely ready by the time the user actually taps "Watch
 * Ad"), and automatically loads the NEXT ad the moment the current
 * one closes, so a fresh ad is ready for the next watch instead of
 * making the user wait through a cold load every time.
 *
 * IMPORTANT: isEarnedReward firing here means the AdMob SDK confirmed
 * client-side that the user watched to completion — it does NOT mean
 * credits have actually been granted. The real grant happens
 * server-side via AdMob's SSV callback (see
 * app/api/v1/ads.py) once Google's servers independently verify the
 * view and hit that endpoint — which can lag a few seconds behind
 * the client-side event, and requires the backend to be publicly
 * reachable. Callers should treat isEarnedReward as "show a
 * 'reward on its way' message," not "credits are updated now."
 */
export function useAppRewardedAd() {
  const { isLoaded, isClosed, isEarnedReward, load, show, error } = useRewardedAd(REWARDED_AD_UNIT_ID);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (error) {
      // TEMPORARY debug logging while diagnosing why the real ad
      // unit isn't loading — remove once resolved. Check Metro logs
      // for this line.
      console.log('[AdMob] Rewarded ad failed to load:', error);
    }
  }, [error]);

  useEffect(() => {
    if (isClosed) {
      load();
    }
  }, [isClosed, load]);

  const watchAd = useCallback(() => {
    if (isLoaded) {
      show();
      return true;
    }
    return false;
  }, [isLoaded, show]);

  return { isLoaded, isEarnedReward, watchAd, error };
}