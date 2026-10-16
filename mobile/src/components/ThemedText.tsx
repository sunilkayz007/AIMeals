import { Text, type TextProps, type TextStyle } from 'react-native';
import { useTheme } from '../theme/ThemeContext';
import { FONTS } from '../theme/layout';

// Centralized typography — one place to change font family/size/weight
// for a given semantic role, instead of every screen hand-rolling its
// own fontSize/fontWeight/color combination (as every screen built so
// far in this app does today). Matches the design system's typography
// hierarchy: Screen title / Section heading / Card title / Body /
// Secondary / Buttons / Small labels.
//
// This does NOT replace React Native's own Text — it wraps it. Any
// existing <Text style={{...}}> usage keeps working untouched; this
// is for NEW/updated screens to adopt gradually (per the "don't
// rewrite everything at once" migration rule), not a forced rewrite.

export type TextVariant =
  | 'display'    // rare — hero numbers, big stat callouts
  | 'h1'         // screen title
  | 'h2'         // section heading
  | 'h3'         // card title
  | 'body'       // default body text
  | 'bodySmall'  // secondary/supporting text
  | 'caption'    // small labels, timestamps, muted notes
  | 'label'      // form field labels, small emphasis text
  | 'button';    // button text

type VariantStyle = Pick<TextStyle, 'fontSize' | 'fontFamily'>;

// Each variant now points at the SPECIFIC static font weight it always
// meant (Poppins for headings, Inter for body) instead of pairing a
// single "SemiBold"/"Regular" family constant with a separate numeric
// fontWeight — that combination only worked by accident while FONTS
// fell back to the platform system font (which freely synthesizes any
// weight); now that real Poppins/Inter .ttf files are loaded, a static
// font file IS a specific weight, so fontWeight is dropped here rather
// than risking inconsistent synthetic-bold rendering on top of it. The
// numeric weight every variant used to declare is preserved below only
// in the choice of WHICH static weight file it now points to (e.g. h1
// was fontWeight: '700' + the SemiBold family — now it's simply the
// Bold family, matching what was actually intended).
const VARIANT_STYLES: Record<TextVariant, VariantStyle> = {
  display: { fontSize: 28, fontFamily: FONTS.poppinsBold },
  h1: { fontSize: 22, fontFamily: FONTS.poppinsBold },
  h2: { fontSize: 17, fontFamily: FONTS.poppinsBold },
  h3: { fontSize: 14, fontFamily: FONTS.poppinsSemiBold },
  body: { fontSize: 13, fontFamily: FONTS.interRegular },
  bodySmall: { fontSize: 12, fontFamily: FONTS.interRegular },
  caption: { fontSize: 11, fontFamily: FONTS.interRegular },
  label: { fontSize: 12, fontFamily: FONTS.interMedium },
  button: { fontSize: 14, fontFamily: FONTS.poppinsSemiBold },
};

// Which theme color a variant uses BY DEFAULT — always overridable via
// the `color` prop (either a semantic key below, or the caller can
// just pass a raw hex through `style` for a one-off case, same as
// always).
const DEFAULT_COLOR_KEY: Record<TextVariant, 'textPrimary' | 'textSecondary' | 'textMuted'> = {
  display: 'textPrimary',
  h1: 'textPrimary',
  h2: 'textPrimary',
  h3: 'textPrimary',
  body: 'textPrimary',
  bodySmall: 'textSecondary',
  caption: 'textMuted',
  label: 'textSecondary',
  button: 'textPrimary',
};

export type SemanticColorKey =
  | 'textPrimary'
  | 'textSecondary'
  | 'textMuted'
  | 'primary'
  | 'danger'
  | 'warningText'
  | 'successText';

interface ThemedTextProps extends TextProps {
  variant?: TextVariant;
  // A semantic theme color key (e.g. "danger" for an error message),
  // OR omit entirely to use the variant's sensible default above. For
  // a genuine one-off color not in this list, pass it via `style`
  // exactly as before — this prop is a convenience, not a restriction.
  color?: SemanticColorKey;
}

export default function ThemedText({ variant = 'body', color, style, children, ...rest }: ThemedTextProps) {
  const { colors } = useTheme();
  const variantStyle = VARIANT_STYLES[variant];
  const resolvedColor = colors[color ?? DEFAULT_COLOR_KEY[variant]];

  return (
    <Text style={[variantStyle, { color: resolvedColor }, style]} {...rest}>
      {children}
    </Text>
  );
}
