import { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, TextInput, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { recipeApi } from '../../../src/api/recipe';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import type { ThemeColors } from '../../../src/theme/colors';

export default function RecipeForm() {
  const router = useRouter();
  const { colors } = useTheme();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const isEditMode = !!id;

  const [isLoadingExisting, setIsLoadingExisting] = useState(isEditMode);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [prepTime, setPrepTime] = useState('');
  const [cookTime, setCookTime] = useState('');
  const [servings, setServings] = useState('1');
  const [ingredients, setIngredients] = useState('');
  const [instructions, setInstructions] = useState('');

  const [showNutrition, setShowNutrition] = useState(false);
  const [calories, setCalories] = useState('');
  const [protein, setProtein] = useState('');
  const [carbs, setCarbs] = useState('');
  const [fat, setFat] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputStyle = getInputStyle(colors);

  // One-time load on mount, NOT useFocusEffect — same fix and same
  // reasoning as the Nutrition Goals screen: useFocusEffect can re-fire
  // while the user is mid-edit (a known keyboard show/hide gotcha in
  // React Navigation-based apps), silently overwriting in-progress
  // typed values with the original server data.
  useEffect(() => {
    if (!isEditMode || !id) return;
    let cancelled = false;
    (async () => {
      setIsLoadingExisting(true);
      try {
        const recipe = await recipeApi.get(id);
        if (cancelled) return;
        setTitle(recipe.title);
        setDescription(recipe.description ?? '');
        setPrepTime(recipe.prep_time_minutes?.toString() ?? '');
        setCookTime(recipe.cook_time_minutes?.toString() ?? '');
        setServings(recipe.servings.toString());
        setIngredients(recipe.ingredients);
        setInstructions(recipe.instructions);
        if (
          recipe.calories_per_serving != null ||
          recipe.protein_g != null ||
          recipe.carbs_g != null ||
          recipe.fat_g != null
        ) {
          setShowNutrition(true);
          setCalories(recipe.calories_per_serving?.toString() ?? '');
          setProtein(recipe.protein_g?.toString() ?? '');
          setCarbs(recipe.carbs_g?.toString() ?? '');
          setFat(recipe.fat_g?.toString() ?? '');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load recipe');
      } finally {
        if (!cancelled) setIsLoadingExisting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, isEditMode]);

  const canSubmit = !!title.trim() && !!ingredients.trim() && !!instructions.trim() && !isSubmitting;

  const handleSubmit = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      const payload = {
        title: title.trim(),
        ingredients: ingredients.trim(),
        instructions: instructions.trim(),
        description: description.trim() || undefined,
        prep_time_minutes: prepTime ? parseInt(prepTime, 10) : undefined,
        cook_time_minutes: cookTime ? parseInt(cookTime, 10) : undefined,
        servings: servings ? parseInt(servings, 10) : undefined,
        calories_per_serving: calories ? parseFloat(calories) : undefined,
        protein_g: protein ? parseFloat(protein) : undefined,
        carbs_g: carbs ? parseFloat(carbs) : undefined,
        fat_g: fat ? parseFloat(fat) : undefined,
      };

      if (isEditMode && id) {
        await recipeApi.update(id, payload);
      } else {
        await recipeApi.create(payload);
      }
      router.back();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save recipe');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoadingExisting) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
      keyboardShouldPersistTaps="handled"
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Cancel</Text>
      </Pressable>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 20 }}>
        {isEditMode ? 'Edit recipe' : 'Add recipe'}
      </Text>

      <Field label="Title">
        <TextInput
          placeholder="e.g. Veggie stir-fry"
          placeholderTextColor={colors.textMuted}
          value={title}
          onChangeText={setTitle}
          style={inputStyle}
        />
      </Field>

      <Field label="Description (optional)">
        <TextInput
          placeholder="A short one-liner about this dish"
          placeholderTextColor={colors.textMuted}
          value={description}
          onChangeText={setDescription}
          style={inputStyle}
        />
      </Field>

      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Field label="Prep time (min)">
            <TextInput
              placeholder="10"
              placeholderTextColor={colors.textMuted}
              value={prepTime}
              onChangeText={setPrepTime}
              keyboardType="numeric"
              style={inputStyle}
            />
          </Field>
        </View>
        <View style={{ flex: 1 }}>
          <Field label="Cook time (min)">
            <TextInput
              placeholder="20"
              placeholderTextColor={colors.textMuted}
              value={cookTime}
              onChangeText={setCookTime}
              keyboardType="numeric"
              style={inputStyle}
            />
          </Field>
        </View>
        <View style={{ flex: 1 }}>
          <Field label="Servings">
            <TextInput
              placeholder="1"
              placeholderTextColor={colors.textMuted}
              value={servings}
              onChangeText={setServings}
              keyboardType="numeric"
              style={inputStyle}
            />
          </Field>
        </View>
      </View>

      <Field label="Ingredients">
        <Text style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 6 }}>One per line</Text>
        <TextInput
          placeholder={'2 tomatoes\n1 onion\n1 tsp cumin'}
          placeholderTextColor={colors.textMuted}
          value={ingredients}
          onChangeText={setIngredients}
          multiline
          numberOfLines={5}
          style={[inputStyle, { minHeight: 100, textAlignVertical: 'top' }]}
        />
      </Field>

      <Field label="Instructions">
        <Text style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 6 }}>One step per line</Text>
        <TextInput
          placeholder={'Chop the vegetables\nHeat oil in a pan\nAdd cumin and let it splutter'}
          placeholderTextColor={colors.textMuted}
          value={instructions}
          onChangeText={setInstructions}
          multiline
          numberOfLines={6}
          style={[inputStyle, { minHeight: 120, textAlignVertical: 'top' }]}
        />
      </Field>

      <Pressable onPress={() => setShowNutrition((v) => !v)} style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 12, color: colors.primaryDark, fontWeight: '600' }}>
          {showNutrition ? '− Hide nutrition info' : '+ Add nutrition info (optional)'}
        </Text>
      </Pressable>

      {showNutrition && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 4 }}>
          <View style={{ flex: 1, minWidth: '45%' }}>
            <Field label="Calories/serving">
              <TextInput
                placeholder="410"
                placeholderTextColor={colors.textMuted}
                value={calories}
                onChangeText={setCalories}
                keyboardType="numeric"
                style={inputStyle}
              />
            </Field>
          </View>
          <View style={{ flex: 1, minWidth: '45%' }}>
            <Field label="Protein (g)">
              <TextInput
                placeholder="18"
                placeholderTextColor={colors.textMuted}
                value={protein}
                onChangeText={setProtein}
                keyboardType="numeric"
                style={inputStyle}
              />
            </Field>
          </View>
          <View style={{ flex: 1, minWidth: '45%' }}>
            <Field label="Carbs (g)">
              <TextInput
                placeholder="44"
                placeholderTextColor={colors.textMuted}
                value={carbs}
                onChangeText={setCarbs}
                keyboardType="numeric"
                style={inputStyle}
              />
            </Field>
          </View>
          <View style={{ flex: 1, minWidth: '45%' }}>
            <Field label="Fat (g)">
              <TextInput
                placeholder="12"
                placeholderTextColor={colors.textMuted}
                value={fat}
                onChangeText={setFat}
                keyboardType="numeric"
                style={inputStyle}
              />
            </Field>
          </View>
        </View>
      )}

      {error ? (
        <Text style={{ color: colors.danger, fontSize: 12, marginTop: 8, marginBottom: 12 }}>{error}</Text>
      ) : (
        <View style={{ marginTop: 8 }} />
      )}

      <Pressable
        onPress={handleSubmit}
        disabled={!canSubmit}
        style={{
          backgroundColor: canSubmit ? colors.primary : colors.border,
          borderRadius: RADIUS.button,
          paddingVertical: 14,
          alignItems: 'center',
          marginTop: 8,
        }}
      >
        <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600' }}>
          {isSubmitting ? 'Saving…' : isEditMode ? 'Save changes' : 'Add recipe'}
        </Text>
      </Pressable>
    </ScrollView>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={{ marginBottom: 16 }}>
      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 }}>
        {label}
      </Text>
      {children}
    </View>
  );
}

function getInputStyle(colors: ThemeColors) {
  return {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    color: colors.textPrimary,
    backgroundColor: colors.cardBg,
  } as const;
}
