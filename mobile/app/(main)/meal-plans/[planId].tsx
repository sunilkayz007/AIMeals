import { useCallback, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { useRouter, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { mealPlanApi } from '../../../src/api/mealPlan';
import type { MealPlan, Meal } from '../../../src/api/mealPlan';
import { getMealsSyncingDueChunks, getMealPlanChunks } from '../../../src/api/aiMealPlan';
import type { MealPlanChunk } from '../../../src/api/aiMealPlan';
import { recipeApi } from '../../../src/api/recipe';
import type { Recipe } from '../../../src/types/recipe';
import { summarizeMicronutrients } from '../../../src/utils/micronutrientSummary';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';

const MEAL_TYPE_ORDER = ['breakfast', 'lunch', 'dinner', 'snack'];
const MEAL_TYPE_LABEL: Record<string, string> = {
  breakfast: 'Breakfast',
  lunch: 'Lunch',
  dinner: 'Dinner',
  snack: 'Snack',
};

function formatDay(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
}

function formatShortDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

// Every calendar date (YYYY-MM-DD) from start to end, inclusive.
function datesInRange(startDate: string, endDate: string): string[] {
  const dates: string[] = [];
  const [sy, sm, sd] = startDate.split('-').map(Number);
  const [ey, em, ed] = endDate.split('-').map(Number);
  let current = new Date(sy, sm - 1, sd);
  const end = new Date(ey, em - 1, ed);
  while (current <= end) {
    dates.push(
      `${current.getFullYear()}-${(current.getMonth() + 1).toString().padStart(2, '0')}-${current.getDate().toString().padStart(2, '0')}`
    );
    current = new Date(current.getFullYear(), current.getMonth(), current.getDate() + 1);
  }
  return dates;
}

export default function MealPlanDetail() {
  const router = useRouter();
  const { colors } = useTheme();
  const { planId } = useLocalSearchParams<{ planId: string }>();

  const [plan, setPlan] = useState<MealPlan | null>(null);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [chunks, setChunks] = useState<MealPlanChunk[]>([]);
  const [recipesById, setRecipesById] = useState<Record<string, Recipe>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!planId) return;
    setIsLoading(true);
    setError(null);
    try {
      // getMealsSyncingDueChunks (not the plain CRUD getMeals)
      // generates any chunks that have become due since the
      // last visit before returning — this is what makes the
      // plan "stay ahead" of the user without any background
      // process running.
      const [planData, mealsData, chunksData] = await Promise.all([
        mealPlanApi.get(planId),
        getMealsSyncingDueChunks(planId),
        getMealPlanChunks(planId),
      ]);
      setPlan(planData);
      setMeals(mealsData);
      setChunks(chunksData);

      const recipeIds = [...new Set(mealsData.map((m) => m.recipe_id).filter((id): id is string => !!id))];
      const recipes = await Promise.all(recipeIds.map((id) => recipeApi.get(id)));
      const byId: Record<string, Recipe> = {};
      recipes.forEach((r) => (byId[r.id] = r));
      setRecipesById(byId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load meal plan');
    } finally {
      setIsLoading(false);
    }
  }, [planId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleDelete = () => {
    if (!plan) return;
    Alert.alert('Delete meal plan?', `Delete "${plan.title}"? This can't be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await mealPlanApi.remove(plan.id);
            router.back();
          } catch (err) {
            Alert.alert('Error', err instanceof Error ? err.message : 'Failed to delete meal plan');
          }
        },
      },
    ]);
  };

  if (isLoading) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  if (error || !plan) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, padding: 20, paddingTop: 60 }}>
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>
        <Text style={{ color: colors.danger, fontSize: 13 }}>{error ?? 'Meal plan not found'}</Text>
      </View>
    );
  }

  const mealsByDate = meals.reduce<Record<string, Meal[]>>((acc, meal) => {
    (acc[meal.scheduled_date] ??= []).push(meal);
    return acc;
  }, {});

  const sortedChunks = [...chunks].sort((a, b) => a.chunk_index - b.chunk_index);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}
    >
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <Pressable onPress={() => router.back()}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>
        <Pressable onPress={handleDelete}>
          <Text style={{ fontSize: 13, color: colors.danger, fontWeight: '600' }}>Delete</Text>
        </Pressable>
      </View>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 20 }}>
        {plan.title}
      </Text>

      {sortedChunks.length === 0 ? (
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>
          No meals in this plan yet.
        </Text>
      ) : (
        sortedChunks.map((chunk) => {
          if (chunk.status === 'pending') {
            return (
              <ThemedCard
                key={chunk.id}
                padding={16}
                style={{ backgroundColor: colors.surfaceAlt, marginBottom: 16, alignItems: 'center' }}
              >
                <ActivityIndicator color={colors.textSecondary} size="small" style={{ marginBottom: 8 }} />
                <Text style={{ fontSize: 13, fontWeight: '600', color: colors.textSecondary, textAlign: 'center' }}>
                  {formatShortDate(chunk.start_date)} – {formatShortDate(chunk.end_date)}: not generated yet
                </Text>
                <Text style={{ fontSize: 11, color: colors.textMuted, textAlign: 'center', marginTop: 2 }}>
                  Check back closer to these dates
                </Text>
              </ThemedCard>
            );
          }

          if (chunk.status === 'failed') {
            return (
              <ThemedCard
                key={chunk.id}
                padding={16}
                style={{ backgroundColor: colors.dangerBg, marginBottom: 16 }}
              >
                <Text style={{ fontSize: 13, fontWeight: '600', color: colors.danger, textAlign: 'center' }}>
                  {formatShortDate(chunk.start_date)} – {formatShortDate(chunk.end_date)}: generation failed
                </Text>
              </ThemedCard>
            );
          }

          // Completed — render each real day within this chunk's range.
          const chunkDates = datesInRange(chunk.start_date, chunk.end_date);
          return chunkDates.map((dateStr) => {
            const dayMeals = [...(mealsByDate[dateStr] ?? [])].sort(
              (a, b) => MEAL_TYPE_ORDER.indexOf(a.meal_type) - MEAL_TYPE_ORDER.indexOf(b.meal_type)
            );
            if (dayMeals.length === 0) return null;

            return (
              <View key={dateStr} style={{ marginBottom: 24 }}>
                <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textSecondary, marginBottom: 10 }}>
                  {formatDay(dateStr)}
                </Text>
                <View style={{ gap: 8 }}>
                  {dayMeals.map((meal) => {
                    const recipe = meal.recipe_id ? recipesById[meal.recipe_id] : undefined;
                    return (
                      <Pressable
                        key={meal.id}
                        onPress={() => recipe && router.push(`/(main)/recipes/${recipe.id}`)}
                        disabled={!recipe}
                      >
                        <ThemedCard padding={14}>
                          <Text style={{ fontSize: 11, fontWeight: '600', color: colors.primaryDark, marginBottom: 4 }}>
                            {MEAL_TYPE_LABEL[meal.meal_type] ?? meal.meal_type}
                          </Text>
                          {recipe ? (
                            <>
                              <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
                                {recipe.title}
                              </Text>
                              <View style={{ flexDirection: 'row', gap: 6 }}>
                                {recipe.calories_per_serving != null && (
                                  <Text style={{ fontSize: 11, color: colors.textSecondary }}>
                                    {Math.round(recipe.calories_per_serving)} kcal
                                  </Text>
                                )}
                              </View>
                              {/* One-line micronutrient callout — see
                                  summarizeMicronutrients()'s "notable
                                  amount" threshold; renders nothing for
                                  a recipe with no standout nutrients or
                                  no micronutrients data at all. */}
                              {summarizeMicronutrients(recipe.micronutrients) && (
                                <Text style={{ fontSize: 11, color: colors.primaryDark, marginTop: 4 }}>
                                  ✨ {summarizeMicronutrients(recipe.micronutrients)}
                                </Text>
                              )}
                            </>
                          ) : (
                            <Text style={{ fontSize: 13, color: colors.textMuted }}>No recipe assigned yet</Text>
                          )}
                        </ThemedCard>
                      </Pressable>
                    );
                  })}
                </View>
              </View>
            );
          });
        })
      )}
    </ScrollView>
  );
}
