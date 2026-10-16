import { TestIds } from 'react-native-google-mobile-ads';

// Dev builds (__DEV__) always use Google's test rewarded ad so local
// testing never consumes real inventory or fires real SSV callbacks.
// Release builds use the REAL ad unit end-to-end, including the SSV
// callback to app/api/v1/ads.py — only real ads trigger that callback,
// so only they actually grant the bonus credits.
const USE_TEST_ADS = __DEV__;

// Real rewarded ad unit for AIMeals — "Bonus Credits Rewarded Ad" in
// the AdMob console. The backend grants a flat +3 credits per
// verified watch (REWARDED_AD_BONUS_CREDITS). SSV callback URL is
// configured directly in the AdMob console against this ad unit, not
// here — see that unit's "Server-side verification" setting.
const REAL_REWARDED_AD_UNIT_ID_ANDROID = 'ca-app-pub-2272440856639213/3903600849';

export const REWARDED_AD_UNIT_ID = USE_TEST_ADS
  ? TestIds.REWARDED
  : REAL_REWARDED_AD_UNIT_ID_ANDROID;