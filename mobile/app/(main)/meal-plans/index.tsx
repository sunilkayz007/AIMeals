import { useCallback, useState } from 'react';
import { View, Text, Pressable, FlatList, ActivityIndicator, RefreshControl } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { mealPlanApi } from '../../../src/api/mealPlan';
import type { MealPlan } from '../../../src/api/mealPlan';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';

function formatDateRange(startDate: string, endDate: string): string {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
  return `${start.toLocaleDateString(undefined, opts)} – ${end.toLocaleDateString(undefined, opts)}`;
}

function dayCount(startDate: string, endDate: string): number {
  const start = new Date(startDate);
  const end = new Date(endDate);
  return Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
}

export default function MealPlansList() {
  const router = useRouter();
  const { colors } = useTheme();

  const [plans, setPlans] = useState<MealPlan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    isRefresh ? setIsRefreshing(true) : setIsLoading(true);
    setError(null);
    try {
      const data = await mealPlanApi.list();
      setPlans(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load meal plans');
    } finally {
      isRefresh ? setIsRefreshing(false) : setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const renderItem = ({ item }: { item: MealPlan }) => (
    <Pressable
      onPress={() => router.push(`/(main)/meal-plans/${item.id}`)}
      style={{ marginBottom: 12 }}
    >
      <ThemedCard padding={16}>
        <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
          {item.title}
        </Text>
        <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap' }}>
          <Chip label={formatDateRange(item.start_date, item.end_date)} />
          <Chip label={`${dayCount(item.start_date, item.end_date)} day${dayCount(item.start_date, item.end_date) === 1 ? '' : 's'}`} />
        </View>
      </ThemedCard>
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <View style={{ flex: 1, paddingTop: 60, paddingHorizontal: 20 }}>
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
          <View
            style={{
              width: 40,
              height: 40,
              borderRadius: 20,
              backgroundColor: colors.primaryLight,
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: 10,
            }}
          >
            <Text style={{ fontSize: 18 }}>📅</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary }}>Meal Plans 📅</Text>
            <Text style={{ fontSize: 11, color: colors.textSecondary }}>Let AI plan your week</Text>
          </View>
        </View>
        <Pressable
          onPress={() => router.push('/(main)/meal-plans/new')}
          style={{
            backgroundColor: colors.primary,
            paddingHorizontal: 14,
            paddingVertical: 10,
            borderRadius: RADIUS.button,
          }}
        >
          <Text style={{ color: '#fff', fontSize: 12, fontWeight: '600' }}>+ New Plan</Text>
        </Pressable>
      </View>

      {isLoading ? (
        <View style={{ paddingVertical: 40, alignItems: 'center' }}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : error ? (
        <ThemedCard padding={14} style={{ backgroundColor: colors.dangerBg }}>
          <Text style={{ color: colors.danger, fontSize: 12 }}>{error}</Text>
          <Pressable onPress={() => load()} style={{ marginTop: 6 }}>
            <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
          </Pressable>
        </ThemedCard>
      ) : plans.length === 0 ? (
        <View style={{ paddingVertical: 40, alignItems: 'center' }}>
          <Text style={{ fontSize: 28, marginBottom: 8 }}>📅</Text>
          <Text style={{ fontSize: 13, color: colors.textSecondary, textAlign: 'center' }}>
            No meal plans yet. Tell AI your dates and preferences, and it'll draft your whole week.
          </Text>
        </View>
      ) : (
        <FlatList
          data={plans}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={() => load(true)} />}
        />
      )}
      </View>

      <ModuleNavBar currentKey="meal_plan" />
    </View>
  );
}

function Chip({ label }: { label: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ backgroundColor: colors.surfaceAlt, paddingHorizontal: 9, paddingVertical: 4, borderRadius: RADIUS.chip }}>
      <Text style={{ fontSize: 10, fontWeight: '600', color: colors.textSecondary }}>{label}</Text>
    </View>
  );
}
