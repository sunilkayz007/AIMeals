import { useCallback, useState } from 'react';
import { View, Text, Pressable, ScrollView, Alert, ActivityIndicator } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { useAuthStore } from '../../src/stores/authStore';
import { useTheme, type ThemeMode } from '../../src/theme/ThemeContext';
import MenuListItem from '../../src/components/MenuListItem';
import ModuleNavBar from '../../src/components/ModuleNavBar';
import ThemedCard from '../../src/components/ThemedCard';
import { coachMemoryApi, type CoachMemoryFact } from '../../src/api/coachMemory';

const THEME_OPTIONS: { mode: ThemeMode; label: string }[] = [
  { mode: 'light', label: 'Light' },
  { mode: 'dark', label: 'Dark' },
  { mode: 'system', label: 'System' },
];

export default function Settings() {
  const router = useRouter();
  const { user, signOut } = useAuthStore();
  const { colors, mode, setMode } = useTheme();

  const [memoryFacts, setMemoryFacts] = useState<CoachMemoryFact[]>([]);
  const [isMemoryLoading, setIsMemoryLoading] = useState(true);
  const [isClearingMemory, setIsClearingMemory] = useState(false);

  // Re-fetches every time this screen gains focus (not just on mount) —
  // the Coach can add new facts during a chat session that happened
  // between visits to Settings, and a stale list here would make the
  // "Clear" action look like it did nothing when it actually worked.
  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsMemoryLoading(true);
      coachMemoryApi
        .list()
        .then((res) => {
          if (!cancelled) setMemoryFacts(res.facts);
        })
        .catch(() => {
          // Silent — the Coach memory section just shows as empty rather
          // than surfacing an error for what's a minor, low-stakes screen.
        })
        .finally(() => {
          if (!cancelled) setIsMemoryLoading(false);
        });
      return () => {
        cancelled = true;
      };
    }, [])
  );

  const handleClearMemory = () => {
    Alert.alert(
      'Clear remembered facts?',
      "This removes everything the Coach has remembered about your dietary preferences and goals. It won't affect your chat history.",
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            setIsClearingMemory(true);
            try {
              await coachMemoryApi.clear();
              setMemoryFacts([]);
            } catch (err) {
              Alert.alert('Error', err instanceof Error ? err.message : 'Failed to clear remembered facts');
            } finally {
              setIsClearingMemory(false);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.screenBg }}>
    <ScrollView
      style={{ flex: 1 }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 20 }}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
      </Pressable>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
        Settings ⚙️
      </Text>
      <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 24 }}>
        {user ? `${user.first_name} ${user.last_name} · ${user.email}` : ''}
      </Text>

      {/* Appearance */}
      <Text
        style={{
          fontSize: 11,
          fontWeight: '700',
          color: colors.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: 0.06,
          marginBottom: 10,
        }}
      >
        Appearance
      </Text>
      <View
        style={{
          backgroundColor: colors.surfaceAlt,
          borderRadius: 12,
          padding: 4,
          flexDirection: 'row',
          marginBottom: 28,
        }}
      >
        {THEME_OPTIONS.map((option) => {
          const isActive = mode === option.mode;
          return (
            <Pressable
              key={option.mode}
              onPress={() => setMode(option.mode)}
              style={{
                flex: 1,
                paddingVertical: 8,
                borderRadius: 9,
                alignItems: 'center',
                backgroundColor: isActive ? colors.accentLavender : 'transparent',
              }}
            >
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: '600',
                  color: isActive ? '#fff' : colors.textSecondary,
                }}
              >
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* Preferences — Tails-style icon-badge list */}
      <Text
        style={{
          fontSize: 11,
          fontWeight: '700',
          color: colors.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: 0.06,
          marginBottom: 10,
        }}
      >
        Preferences
      </Text>
      <ThemedCard
        padding={0}
        style={{
          backgroundColor: colors.screenBg,
          borderColor: colors.border,
          borderRadius: 12,
          paddingHorizontal: 14,
          marginBottom: 28,
        }}
      >
        <MenuListItem
          icon="🥗"
          iconBadgeColor={colors.accentSage + '33'}
          title="Daily calorie goal"
          description="Used for your Home progress ring"
          onPress={() => router.push('/(main)/goals')}
          trailing={<Text style={{ color: colors.textMuted }}>›</Text>}
        />
        <MenuListItem
          icon="🏆"
          iconBadgeColor={colors.accentGold + '33'}
          title="Achievements"
          description="Your logging streaks and milestones"
          onPress={() => router.push('/(main)/achievements')}
          trailing={<Text style={{ color: colors.textMuted }}>›</Text>}
        />
        <MenuListItem
          icon="⚠️"
          iconBadgeColor={colors.danger + '33'}
          title="Allergen settings"
          description="Manage your allergy list"
          onPress={() => router.push('/(main)/allergies/manage')}
          trailing={<Text style={{ color: colors.textMuted }}>›</Text>}
        />
        <MenuListItem
          icon="💳"
          iconBadgeColor={colors.accentPeach + '33'}
          title="Manage subscription"
          description="Plan, billing, credits"
          onPress={() => router.push('/(main)/upgrade')}
          trailing={<Text style={{ color: colors.textMuted }}>›</Text>}
          isLast
        />
      </ThemedCard>

      {/* Coach memory — privacy/control surface for the dietary-
          preference/goal facts the Nutrition Coach silently remembers
          across conversations. See backend app/api/v1/coach_memory.py. */}
      <Text
        style={{
          fontSize: 11,
          fontWeight: '700',
          color: colors.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: 0.06,
          marginBottom: 10,
        }}
      >
        Coach memory
      </Text>
      <ThemedCard
        style={{
          backgroundColor: colors.screenBg,
          borderColor: colors.border,
          borderRadius: 12,
          marginBottom: 28,
        }}
      >
        {isMemoryLoading ? (
          <ActivityIndicator size="small" color={colors.accentLavender} />
        ) : memoryFacts.length === 0 ? (
          <Text style={{ fontSize: 12, color: colors.textSecondary }}>
            Nothing remembered yet — as you chat with your Coach, dietary
            preferences and goals it picks up on will show up here.
          </Text>
        ) : (
          <>
            <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 10 }}>
              Your Coach remembers these from past conversations:
            </Text>
            {memoryFacts.map((fact) => (
              <View
                key={fact.id}
                style={{
                  flexDirection: 'row',
                  alignItems: 'flex-start',
                  marginBottom: 6,
                }}
              >
                <Text style={{ fontSize: 13, color: colors.accentLavender, marginRight: 6 }}>•</Text>
                <Text style={{ fontSize: 13, color: colors.textPrimary, flex: 1 }}>{fact.fact}</Text>
              </View>
            ))}
            <Pressable
              onPress={handleClearMemory}
              disabled={isClearingMemory}
              style={{ marginTop: 8, alignSelf: 'flex-start' }}
            >
              <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>
                {isClearingMemory ? 'Clearing…' : 'Clear remembered facts'}
              </Text>
            </Pressable>
          </>
        )}
      </ThemedCard>

      <Pressable onPress={signOut} style={{ marginBottom: 24 }}>
        <Text style={{ color: colors.danger, fontSize: 13, fontWeight: '600' }}>Sign out</Text>
      </Pressable>

      <View
        style={{
          borderTopWidth: 1,
          borderTopColor: colors.border,
          paddingTop: 20,
        }}
      >
        <Pressable onPress={() => router.push('/(main)/delete-account')}>
          <Text style={{ color: colors.textMuted, fontSize: 12 }}>Delete account</Text>
        </Pressable>
      </View>
    </ScrollView>

    <ModuleNavBar currentKey="settings" />
    </View>
  );
}
