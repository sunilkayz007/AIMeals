import { useCallback, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { nutritionLogApi } from '../../../../src/api/nutritionLog';
import { useTheme } from '../../../../src/theme/ThemeContext';
import ThemedCard from '../../../../src/components/ThemedCard';
import type { DailyTotals, NutritionLog, MealType } from '../../../../src/types/nutritionLog';

const MEAL_TYPE_ICON: Record<MealType, string> = {
  breakfast: '🍳',
  lunch: '🍛',
  dinner: '🍽️',
  snack: '🥜',
};

function formatLoggedTime(isoString: string): string {
  const d = new Date(isoString);
  let hours = d.getHours();
  const minutes = d.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12;
  return `${hours}:${minutes} ${ampm}`;
}

// Parses a YYYY-MM-DD date string as a LOCAL date (not UTC) for
// display formatting — same reasoning as home.tsx's todayString():
// new Date("2026-09-01") parses as UTC midnight, which can display as
// the previous day in timezones ahead of UTC. Splitting and
// constructing with the (year, monthIndex, day) constructor avoids
// that, since that overload uses local time.
function formatDateHeading(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}

export default function DayLogs() {
  const router = useRouter();
  const { colors } = useTheme();
  const { date } = useLocalSearchParams<{ date: string }>();

  const [meals, setMeals] = useState<NutritionLog[]>([]);
  const [totals, setTotals] = useState<DailyTotals | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!date) return;
    setIsLoading(true);
    setError(null);
    try {
      const [logs, dayTotals] = await Promise.all([
        nutritionLogApi.getLogsForDay(date),
        nutritionLogApi.getDailyTotals(date),
      ]);
      // Most recently logged first, matching Home's own ordering.
      setMeals([...logs].sort((a, b) => b.created_at.localeCompare(a.created_at)));
      setTotals(dayTotals);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load this day');
    } finally {
      setIsLoading(false);
    }
  }, [date]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.screenBg }}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}>
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        <Text style={{ fontSize: 20, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
          {date ? formatDateHeading(date) : 'Day details'}
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
          Everything you logged this day
        </Text>

        {isLoading ? (
          <View style={{ paddingVertical: 40, alignItems: 'center' }}>
            <ActivityIndicator color={colors.accentPeach} />
          </View>
        ) : error ? (
          <ThemedCard padding={12} style={{ backgroundColor: colors.warningBg, borderColor: 'transparent' }}>
            <Text style={{ color: colors.warningText, fontSize: 12 }}>{error}</Text>
            <Pressable onPress={load} style={{ marginTop: 6 }}>
              <Text style={{ color: colors.warningText, fontSize: 12, fontWeight: '600' }}>Retry</Text>
            </Pressable>
          </ThemedCard>
        ) : (
          <>
            {totals && (
              <ThemedCard
                style={{
                  backgroundColor: colors.surfaceAlt,
                  borderColor: 'transparent',
                  marginBottom: 20,
                  flexDirection: 'row',
                  justifyContent: 'space-around',
                }}
                padding={16}
              >
                <View style={{ alignItems: 'center' }}>
                  <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary }}>
                    {Math.round(totals.calories)}
                  </Text>
                  <Text style={{ fontSize: 10, color: colors.textSecondary }}>kcal</Text>
                </View>
                <View style={{ alignItems: 'center' }}>
                  <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary }}>
                    {Math.round(totals.protein_g)}g
                  </Text>
                  <Text style={{ fontSize: 10, color: colors.textSecondary }}>Protein</Text>
                </View>
                <View style={{ alignItems: 'center' }}>
                  <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary }}>
                    {Math.round(totals.carbs_g)}g
                  </Text>
                  <Text style={{ fontSize: 10, color: colors.textSecondary }}>Carbs</Text>
                </View>
                <View style={{ alignItems: 'center' }}>
                  <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary }}>
                    {Math.round(totals.fat_g)}g
                  </Text>
                  <Text style={{ fontSize: 10, color: colors.textSecondary }}>Fat</Text>
                </View>
              </ThemedCard>
            )}

            {meals.length === 0 ? (
              <Text style={{ fontSize: 12, color: colors.textSecondary, textAlign: 'center', marginTop: 20 }}>
                Nothing logged on this day.
              </Text>
            ) : (
              <View style={{ gap: 10 }}>
                {meals.map((meal) => (
                  <Pressable
                    key={meal.id}
                    onPress={() =>
                      router.push({
                        pathname: '/(main)/meal-detail/[logId]',
                        params: { logId: meal.id, mealData: JSON.stringify(meal) },
                      })
                    }
                  >
                    <ThemedCard
                      style={{
                        flexDirection: 'row',
                        alignItems: 'center',
                        backgroundColor: colors.surfaceAlt,
                        borderColor: 'transparent',
                      }}
                      padding={12}
                    >
                      <View
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 22,
                          backgroundColor: colors.screenBg,
                          alignItems: 'center',
                          justifyContent: 'center',
                          marginRight: 12,
                        }}
                      >
                        <Text style={{ fontSize: 20 }}>{MEAL_TYPE_ICON[meal.meal_type]}</Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }} numberOfLines={1}>
                          {meal.food_name}
                        </Text>
                        <Text style={{ fontSize: 11, color: colors.textMuted, marginTop: 1 }}>
                          {meal.meal_type.charAt(0).toUpperCase() + meal.meal_type.slice(1)} ·{' '}
                          {formatLoggedTime(meal.created_at)}
                        </Text>
                      </View>
                      <Text style={{ fontSize: 12, fontWeight: '700', color: colors.accentSage }}>
                        {Math.round(meal.calories)} kcal
                      </Text>
                    </ThemedCard>
                  </Pressable>
                ))}
              </View>
            )}
          </>
        )}
      </ScrollView>
    </View>
  );
}
