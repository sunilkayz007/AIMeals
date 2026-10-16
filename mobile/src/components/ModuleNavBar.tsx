import { View, Text, Pressable, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '../theme/ThemeContext';
import { MODULES, type ModuleDef } from '../config/modules';

interface ModuleNavBarProps {
  // The module this screen represents — excluded from the row, since
  // there's no point showing a link to the screen you're already on.
  currentKey: string;
}

// Home isn't in MODULES (it's the screen the modules are shown FROM,
// not a module itself), which meant there was previously no way to
// jump straight back to Home from this bar — only router.back(),
// which doesn't always land on Home. Pinned to the front of the row
// on every screen except Home itself.
const HOME_MODULE: ModuleDef = {
  key: 'home',
  icon: '🏠',
  label: 'Home',
  subtitle: 'Your daily overview',
  badgeColorKey: 'accentSage',
  route: '/(main)/home',
};

/**
 * Horizontally scrollable strip of every OTHER module, placed at the
 * bottom of each module's own screen — lets the user jump directly
 * from e.g. Pantry to Coach without backing out to Home first.
 *
 * Theme-aware (uses useTheme) even though not every screen this gets
 * placed on is themed yet (Coach/Pantry/Recipes/Allergies still use
 * hardcoded light colors as of this writing) — this way the component
 * itself is already correct for when those screens get themed later,
 * rather than needing rework then.
 */
export default function ModuleNavBar({ currentKey }: ModuleNavBarProps) {
  const router = useRouter();
  const { colors } = useTheme();
  const otherModules = MODULES.filter((m) => m.key !== currentKey);
  const rowModules = currentKey === 'home' ? otherModules : [HOME_MODULE, ...otherModules];

  return (
    <View
      style={{
        borderTopWidth: 1,
        borderTopColor: colors.border,
        backgroundColor: colors.screenBg,
      }}
    >
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 16, paddingVertical: 10, gap: 14 }}
      >
        {rowModules.map((mod) => {
          const isBuilt = !!mod.route;
          return (
            <Pressable
              key={mod.key}
              onPress={() => {
                if (mod.route) router.push(mod.route as any);
              }}
              disabled={!isBuilt}
              style={{ alignItems: 'center', width: 60, opacity: isBuilt ? 1 : 0.4 }}
            >
              <View
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 18,
                  backgroundColor: colors[mod.badgeColorKey] + '33',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 3,
                }}
              >
                <Text style={{ fontSize: 16 }}>{mod.icon}</Text>
              </View>
              <Text
                style={{
                  fontSize: 9,
                  fontWeight: '500',
                  color: colors.textPrimary,
                  textAlign: 'center',
                }}
                numberOfLines={2}
              >
                {mod.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}
