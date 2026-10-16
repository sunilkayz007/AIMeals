// =========================================================
// AIMeals Theme — Layout Constants
// Companion to colors.ts: the brief's non-color specs (card
// radius/shadow, typography) that don't vary between light
// and dark mode, so they don't belong on ThemeColors.
// =========================================================

import { Platform } from 'react-native';

// ---------------------------------------------------
// Card System
// ---------------------------------------------------

export const RADIUS = {
  card: 24,
  button: 24,
  chip: 100, // pill shape, used throughout already
};

// React Native shadows are platform-specific: iOS reads
// shadowColor/Offset/Opacity/Radius, Android reads elevation.
// Spread this object onto a card's style to get the brief's
// "0 8 24 rgba(0,0,0,0.05)" look on both platforms.
export const CARD_SHADOW = Platform.select({
  ios: {
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.05,
    shadowRadius: 24,
  },
  android: {
    elevation: 3,
  },
  default: {},
});

// Same idea, softer — for the primary-button "soft green shadow"
// spec. Pass gradientPrimaryStart (or primary) as shadowColor
// where this is used, since the shadow should tint toward the
// button's own color, not plain black.
export const BUTTON_SHADOW_OPACITY = Platform.select({
  ios: 0.25,
  android: 0, // elevation handles Android; a colored shadow there needs a wrapper View
  default: 0,
});

// ---------------------------------------------------
// Typography
// ---------------------------------------------------
// Brief specifies Poppins (headings/buttons) and Inter (body).
// Both @expo-google-fonts packages and expo-font were already
// present as dependencies but never actually loaded (no useFonts
// call anywhere) — app/_layout.tsx now loads the weights below
// behind a gate before anything renders, so these family name
// strings resolve to the real fonts, not a system-font fallback.
//
// Each key names a SPECIFIC static weight (e.g. "poppinsBold" is
// literally the Poppins_700Bold.ttf face) rather than a generic
// family + a separate numeric fontWeight — React Native does not
// reliably synthesize bold/medium on top of a custom static font
// file the way it does for the platform system font, so callers
// should pick the already-correct-weight key below and leave
// fontWeight unset, rather than setting fontWeight on top of one
// of these (see ThemedText.tsx's VARIANT_STYLES for the pattern).

export const FONTS = {
  // Poppins — headings & buttons per the brand brief.
  poppinsRegular: 'Poppins_400Regular',
  poppinsMedium: 'Poppins_500Medium',
  poppinsSemiBold: 'Poppins_600SemiBold',
  poppinsBold: 'Poppins_700Bold',
  // Inter — body text per the brand brief.
  interRegular: 'Inter_400Regular',
  interMedium: 'Inter_500Medium',
  interSemiBold: 'Inter_600SemiBold',

  // Legacy aliases — only ThemedText.tsx referenced these three
  // names before this file was updated; kept so nothing breaks if
  // anything else starts referencing them the same way.
  headingSemiBold: 'Poppins_600SemiBold',
  bodyRegular: 'Inter_400Regular',
  buttonMedium: 'Poppins_500Medium',
};