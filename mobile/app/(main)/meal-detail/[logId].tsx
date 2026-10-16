import { View, Text, Pressable, ScrollView } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import type { NutritionLog, MealType } from '../../../src/types/nutritionLog';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS, CARD_SHADOW } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';

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

export default function MealDetail() {
  const router = useRouter();
  const { colors } = useTheme();
  const { mealData } = useLocalSearchParams<{ logId: string; mealData?: string }>();

  let meal: NutritionLog | null = null;
  try {
    meal = mealData ? JSON.parse(mealData) : null;
  } catch {
    meal = null;
  }

  if (!meal) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, padding: 20, paddingTop: 60 }}>
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>
        <Text style={{ color: colors.danger, fontSize: 13 }}>This meal's details couldn't be loaded.</Text>
      </View>
    );
  }

  const source: 'recipe' | 'food_image' | 'manual' = meal.recipe_id
    ? 'recipe'
    : meal.food_image_id
      ? 'food_image'
      : 'manual';

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}>
      <Pressable onPress={() => router.back()} style={{ marginBottom: 20 }}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
      </Pressable>

      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
        <Text style={{ fontSize: 28, marginRight: 10 }}>{MEAL_TYPE_ICON[meal.meal_type]}</Text>
        <View>
          <Text style={{ fontSize: 11, fontWeight: '700', color: colors.primaryDark, textTransform: 'uppercase', letterSpacing: 0.4 }}>
            {meal.meal_type}
          </Text>
          <Text style={{ fontSize: 11, color: colors.textMuted }}>
            Logged at {formatLoggedTime(meal.created_at)}
          </Text>
        </View>
      </View>

      <Text style={{ fontSize: 20, fontWeight: '700', color: colors.textPrimary, marginTop: 16, marginBottom: 20 }}>
        {meal.food_name}
      </Text>

      {/* Nutrition summary card */}
      <ThemedCard style={{ alignItems: 'center', marginBottom: 20 }} padding={20}>
        <Text style={{ fontSize: 34, fontWeight: '800', color: colors.textPrimary, marginBottom: 16 }}>
          {Math.round(meal.calories)}
          <Text style={{ fontSize: 16, fontWeight: '600', color: colors.textSecondary }}> kcal</Text>
        </Text>
        <View style={{ flexDirection: 'row', gap: 28 }}>
          <MacroValue label="Protein" value={`${Math.round(meal.protein_g)}g`} color={colors.ringProtein ?? colors.accentSage} />
          <MacroValue label="Carbs" value={`${Math.round(meal.carbs_g)}g`} color={colors.ringCarbs ?? colors.accentBlue} />
          <MacroValue label="Fat" value={`${Math.round(meal.fat_g)}g`} color={colors.ringFat ?? colors.accentGold} />
        </View>
      </ThemedCard>

      {meal.portion_percentage !== 100 && (
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 }}>
          <Text style={{ fontSize: 12, color: colors.textSecondary }}>Portion logged</Text>
          <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary }}>{meal.portion_percentage}%</Text>
        </View>
      )}

      {meal.notes && (
        <View style={{ marginBottom: 20 }}>
          <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 }}>NOTES</Text>
          <Text style={{ fontSize: 13, color: colors.textPrimary, lineHeight: 19 }}>{meal.notes}</Text>
        </View>
      )}

      <View style={{ marginBottom: 20 }}>
        <Text style={{ fontSize: 11, color: colors.textMuted }}>
          {source === 'recipe' && 'Logged from a recipe'}
          {source === 'food_image' && 'Logged from a food scan'}
          {source === 'manual' && 'Logged manually'}
        </Text>
      </View>

      {source === 'recipe' && meal.recipe_id && (
        <Pressable
          onPress={() => router.push(`/(main)/recipes/${meal!.recipe_id}`)}
          style={{
            backgroundColor: colors.primary,
            borderRadius: RADIUS.button,
            paddingVertical: 14,
            alignItems: 'center',
          }}
        >
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>View Full Recipe</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

function MacroValue({ label, value, color }: { label: string; value: string; color: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ alignItems: 'center' }}>
      <Text style={{ fontSize: 15, fontWeight: '700', color }}>{value}</Text>
      <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 2 }}>{label}</Text>
    </View>
  );
}
