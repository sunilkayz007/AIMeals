import { View, type ViewProps, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeContext';
import { RADIUS, CARD_SHADOW } from '../theme/layout';

// Centralized card styling — one place to change the "premium glossy
// feel" (or radius/shadow/border) for every card in the app, instead
// of every screen hand-rolling its own card View style (as every
// screen built so far in this app does today).
//
// The glossy effect is a subtle, semi-transparent white highlight
// along just the TOP edge — reads as light catching the rim of the
// card, without needing a gradient library. Fixed white (not a theme
// color) so it works correctly in both light and dark mode.
//
// Like ThemedText, this wraps rather than replaces View — existing
// hand-styled cards keep working untouched; screens adopt this
// gradually. The `style` prop is applied AFTER the defaults below,
// so a caller can override any individual property (background
// color, border color, etc.) for a colored/variant card — e.g. the
// Health Insights priority cards use `style={{ backgroundColor:
// badge.bg, borderColor: badge.text, borderLeftWidth: 4 }}` to layer
// their own severity coloring on top of this shared base.

interface ThemedCardProps extends ViewProps {
  /** Default true — set false for a flat card with no gloss highlight. */
  glossy?: boolean;
  /** Default 14. */
  padding?: number;
  style?: StyleProp<ViewStyle>;
}

export default function ThemedCard({
  glossy = true,
  padding = 14,
  style,
  children,
  ...rest
}: ThemedCardProps) {
  const { colors } = useTheme();

  return (
    <View
      style={[
        {
          backgroundColor: colors.cardBg,
          borderWidth: 1,
          borderColor: colors.cardBorder,
          borderRadius: RADIUS.card,
          padding,
          ...(glossy ? { borderTopWidth: 1.5, borderTopColor: 'rgba(255,255,255,0.45)' } : {}),
          ...CARD_SHADOW,
        },
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}
