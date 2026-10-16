import { useCallback, useState } from 'react';
import { View, Text, ScrollView, ActivityIndicator, RefreshControl, Pressable } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { achievementsApi, type Achievement } from '../../../src/api/achievements';
import { useTheme } from '../../../src/theme/ThemeContext';
import ThemedCard from '../../../src/components/ThemedCard';

function formatEarnedDate(isoString: string | null): string {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function Achievements() {
  const router = useRouter();
  const { colors } = useTheme();

  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    isRefresh ? setIsRefreshing(true) : setIsLoading(true);
    setError(null);
    try {
      const res = await achievementsApi.list();
      setAchievements(res.achievements);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load achievements');
    } finally {
      isRefresh ? setIsRefreshing(false) : setIsLoading(false);
    }
  }, []);

  // Re-fetch on every focus, not just mount — a streak achievement can
  // be newly earned from logging a meal on another screen, and coming
  // back here should reflect that without a manual pull-to-refresh.
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const earnedCount = achievements.filter((a) => a.earned).length;

  return (
    <View style={{ flex: 1, backgroundColor: colors.screenBg }}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={() => load(true)} tintColor={colors.accentGold} />
        }
      >
        <Pressable onPress={() => router.back()} style={{ marginBottom: 20 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
          Achievements 🏆
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 24 }}>
          {isLoading
            ? 'Loading your progress…'
            : `You've earned ${earnedCount} of ${achievements.length} so far — keep it up!`}
        </Text>

        {isLoading ? (
          <ActivityIndicator size="large" color={colors.accentGold} style={{ marginTop: 40 }} />
        ) : error ? (
          <Text style={{ fontSize: 13, color: colors.danger }}>{error}</Text>
        ) : achievements.length === 0 ? (
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>
            No achievements available yet — check back soon!
          </Text>
        ) : (
          achievements.map((achievement) => (
            <ThemedCard
              key={achievement.key}
              style={{
                backgroundColor: achievement.earned ? colors.successBg : colors.surfaceAlt,
                borderColor: achievement.earned ? colors.successText : colors.border,
                borderRadius: 14,
                marginBottom: 12,
                opacity: achievement.earned ? 1 : 0.75,
              }}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <View
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 24,
                    backgroundColor: achievement.earned ? colors.accentGold + '33' : colors.border,
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: 14,
                  }}
                >
                  <Text style={{ fontSize: 22 }}>{achievement.earned ? achievement.icon : '🔒'}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    <Text style={{ fontSize: 15, fontWeight: '600', color: colors.textPrimary }}>
                      {achievement.title}
                    </Text>
                    {achievement.is_new ? (
                      <View
                        style={{
                          marginLeft: 8,
                          paddingHorizontal: 8,
                          paddingVertical: 2,
                          borderRadius: 100,
                          backgroundColor: colors.accentGold,
                        }}
                      >
                        <Text style={{ fontSize: 9, fontWeight: '700', color: '#fff' }}>NEW</Text>
                      </View>
                    ) : null}
                  </View>
                  <Text style={{ fontSize: 12, color: colors.textSecondary, marginTop: 2 }}>
                    {achievement.description}
                  </Text>
                  {achievement.earned && achievement.earned_at ? (
                    <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 4 }}>
                      Earned {formatEarnedDate(achievement.earned_at)}
                    </Text>
                  ) : null}
                </View>
              </View>
            </ThemedCard>
          ))
        )}
      </ScrollView>
    </View>
  );
}
