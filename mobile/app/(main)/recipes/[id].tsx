import { useCallback, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { useRouter, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { recipeApi } from '../../../src/api/recipe';
import { useAuthStore } from '../../../src/stores/authStore';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';
import type { Recipe } from '../../../src/types/recipe';
import { stripLeadingStepNumber } from '../../../src/utils/recipeText';

export default function RecipeDetail() {
  const router = useRouter();
  const { colors } = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuthStore();

  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await recipeApi.get(id);
      setRecipe(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recipe');
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const isOwner = !!recipe && !!user && recipe.created_by_user_id === user.id;

  const handleDelete = () => {
    if (!recipe) return;
    Alert.alert('Delete recipe?', `Delete "${recipe.title}"? This can't be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await recipeApi.remove(recipe.id);
            router.back();
          } catch (err) {
            Alert.alert('Error', err instanceof Error ? err.message : 'Failed to delete recipe');
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

  if (error || !recipe) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, padding: 20, paddingTop: 60 }}>
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>
        <Text style={{ color: colors.danger, fontSize: 13 }}>{error ?? 'Recipe not found'}</Text>
      </View>
    );
  }

  const ingredientLines = recipe.ingredients.split('\n').filter((l) => l.trim());
  const instructionLines = recipe.instructions.split('\n').filter((l) => l.trim());
  const totalTime = (recipe.prep_time_minutes ?? 0) + (recipe.cook_time_minutes ?? 0);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
    >
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 12,
        }}
      >
        <Pressable onPress={() => router.back()}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>
        {isOwner && (
          <View style={{ flexDirection: 'row', gap: 16 }}>
            <Pressable onPress={() => router.push(`/(main)/recipes/form?id=${recipe.id}`)}>
              <Text style={{ fontSize: 13, color: colors.primaryDark, fontWeight: '600' }}>Edit</Text>
            </Pressable>
            <Pressable onPress={handleDelete}>
              <Text style={{ fontSize: 13, color: colors.danger, fontWeight: '600' }}>Delete</Text>
            </Pressable>
          </View>
        )}
      </View>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
        {recipe.title}
      </Text>
      {recipe.description ? (
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 14 }}>
          {recipe.description}
        </Text>
      ) : (
        <View style={{ marginBottom: 10 }} />
      )}

      {recipe.contains_allergen ? (
        <ThemedCard
          padding={12}
          style={{ backgroundColor: colors.dangerBg, borderColor: colors.danger, marginBottom: 16 }}
        >
          <Text style={{ color: colors.danger, fontSize: 13, fontWeight: '700' }}>
            ⚠ Contains allergens
          </Text>
        </ThemedCard>
      ) : null}

      <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
        {totalTime > 0 && <Badge label={`${totalTime} min`} />}
        <Badge label={`${recipe.servings} serving${recipe.servings === 1 ? '' : 's'}`} />
        {recipe.is_ai_generated && <Badge label="AI generated" tone="ai" />}
      </View>

      {(recipe.calories_per_serving != null ||
        recipe.protein_g != null ||
        recipe.carbs_g != null ||
        recipe.fat_g != null) && (
        <ThemedCard
          padding={16}
          style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 }}
        >
          {recipe.calories_per_serving != null && (
            <Macro label="Calories" value={`${Math.round(recipe.calories_per_serving)}`} color={colors.ringCalories} />
          )}
          {recipe.protein_g != null && <Macro label="Protein" value={`${recipe.protein_g}g`} color={colors.ringProtein} />}
          {recipe.carbs_g != null && <Macro label="Carbs" value={`${recipe.carbs_g}g`} color={colors.ringCarbs} />}
          {recipe.fat_g != null && <Macro label="Fat" value={`${recipe.fat_g}g`} color={colors.ringFat} />}
        </ThemedCard>
      )}

      <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary, marginBottom: 8 }}>
        Ingredients
      </Text>
      <View style={{ marginBottom: 20 }}>
        {ingredientLines.map((line, i) => (
          <Text key={i} style={{ fontSize: 13, color: colors.textPrimary, marginBottom: 4 }}>
            •  {line.trim()}
          </Text>
        ))}
      </View>

      <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary, marginBottom: 8 }}>
        Instructions
      </Text>
      <View>
        {instructionLines.map((line, i) => (
          <Text key={i} style={{ fontSize: 13, color: colors.textPrimary, marginBottom: 8, lineHeight: 19 }}>
            {i + 1}.  {stripLeadingStepNumber(line)}
          </Text>
        ))}
      </View>
    </ScrollView>
  );
}

function Badge({ label, tone }: { label: string; tone?: 'ai' }) {
  const { colors } = useTheme();
  const bg = tone === 'ai' ? colors.primaryLight : colors.surfaceAlt;
  const text = tone === 'ai' ? colors.primaryDark : colors.textSecondary;
  return (
    <View style={{ backgroundColor: bg, paddingHorizontal: 10, paddingVertical: 5, borderRadius: RADIUS.chip }}>
      <Text style={{ fontSize: 11, fontWeight: '600', color: text }}>{label}</Text>
    </View>
  );
}

function Macro({ label, value, color }: { label: string; value: string; color: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ alignItems: 'center' }}>
      <Text style={{ fontSize: 15, fontWeight: '700', color }}>{value}</Text>
      <Text style={{ fontSize: 10, color: colors.textSecondary }}>{label}</Text>
    </View>
  );
}
