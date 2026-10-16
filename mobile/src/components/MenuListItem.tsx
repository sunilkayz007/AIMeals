import { View, Text, Pressable } from 'react-native';
import { useTheme } from '../theme/ThemeContext';

interface MenuListItemProps {
  icon: string; // emoji, matching the rest of the app's icon convention
  iconBadgeColor: string; // background color behind the icon, Tails-style
  title: string;
  description?: string;
  onPress?: () => void;
  trailing?: React.ReactNode; // e.g. a chevron, switch, or value text
  isLast?: boolean; // suppresses the bottom divider when true
}

/**
 * A single row: colored circular icon badge + title (+ optional
 * description) + optional trailing content. Modeled on Tails OS's
 * applications menu — icon badge, generous spacing, subtle divider
 * between rows rather than a bordered card per row.
 */
export default function MenuListItem({
  icon,
  iconBadgeColor,
  title,
  description,
  onPress,
  trailing,
  isLast = false,
}: MenuListItemProps) {
  const { colors } = useTheme();

  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: isLast ? 0 : 1,
        borderBottomColor: colors.border,
      }}
    >
      <View
        style={{
          width: 40,
          height: 40,
          borderRadius: 20,
          backgroundColor: iconBadgeColor,
          alignItems: 'center',
          justifyContent: 'center',
          marginRight: 12,
        }}
      >
        <Text style={{ fontSize: 18 }}>{icon}</Text>
      </View>

      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: 14, fontWeight: '500', color: colors.textPrimary }}>
          {title}
        </Text>
        {description ? (
          <Text style={{ fontSize: 12, color: colors.textSecondary, marginTop: 2 }}>
            {description}
          </Text>
        ) : null}
      </View>

      {trailing}
    </Pressable>
  );
}
