import { useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { logMealManually, estimateMealNutrition } from '../../../src/api/manualNutritionLog';
import type { MealType } from '../../../src/types/nutritionLog';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import type { ThemeColors } from '../../../src/theme/colors';
import CalendarPickerModal from '../../../src/components/CalendarPickerModal';

const MEAL_TYPES: { value: MealType; label: string }[] = [
  { value: 'breakfast' as MealType, label: 'Breakfast' },
  { value: 'lunch' as MealType, label: 'Lunch' },
  { value: 'dinner' as MealType, label: 'Dinner' },
  { value: 'snack' as MealType, label: 'Snack' },
];

function todayYMD(): string {
  const d = new Date();
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
}

function formatDisplayDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

export default function LogMealForm() {
  const router = useRouter();
  const { colors } = useTheme();
  const inputStyle = getInputStyle(colors);

  const [mealType, setMealType] = useState<MealType>('lunch' as MealType);
  const [loggedAt, setLoggedAt] = useState(todayYMD());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [foodName, setFoodName] = useState('');
  const [calories, setCalories] = useState('');
  const [protein, setProtein] = useState('');
  const [carbs, setCarbs] = useState('');
  const [fat, setFat] = useState('');
  const [fiber, setFiber] = useState('');
  const [water, setWater] = useState('');
  const [notes, setNotes] = useState('');

  // Not shown as its own set of fields — pre-filled silently by
  // "Estimate with AI" (when the user hasn't touched it manually,
  // there's nothing to show 10 separate inputs for) and passed
  // through as-is in the submit payload.
  const [micronutrients, setMicronutrients] = useState<Record<string, number> | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEstimating, setIsEstimating] = useState(false);
  const [estimateError, setEstimateError] = useState<string | null>(null);

  const canSubmit =
    !!foodName.trim() && !!calories.trim() && !!protein.trim() && !!carbs.trim() && !!fat.trim() && !isSubmitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await logMealManually({
        logged_at: loggedAt,
        meal_type: mealType,
        food_name: foodName.trim(),
        calories: parseFloat(calories),
        protein_g: parseFloat(protein),
        carbs_g: parseFloat(carbs),
        fat_g: parseFloat(fat),
        fiber_g: fiber.trim() ? parseFloat(fiber) : 0,
        water_ml: water.trim() ? parseFloat(water) : 0,
        micronutrients: micronutrients ?? undefined,
        notes: notes.trim() || undefined,
      });
      router.back();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log meal — please try again');
    } finally {
      setIsSubmitting(false);
    }
  };

  // "Estimate with AI" — calls the AI nutrition-estimate endpoint
  // (1 credit) and pre-fills every field below from the response.
  // Does NOT log anything itself; the user still reviews and taps
  // "Log Meal" to actually submit, exactly like a manual entry.
  const handleEstimate = async () => {
    if (!foodName.trim() || isEstimating) return;
    setIsEstimating(true);
    setEstimateError(null);
    try {
      const estimate = await estimateMealNutrition(foodName.trim());
      setCalories(String(Math.round(estimate.calories)));
      setProtein(String(Math.round(estimate.protein_g)));
      setCarbs(String(Math.round(estimate.carbs_g)));
      setFat(String(Math.round(estimate.fat_g)));
      setFiber(String(Math.round(estimate.fiber_g)));
      setWater(String(Math.round(estimate.water_ml)));
      setMicronutrients(estimate.micronutrients);
    } catch (err) {
      setEstimateError(
        err instanceof Error ? err.message : 'Could not estimate nutrition — please enter values manually'
      );
    } finally {
      setIsEstimating(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}
      keyboardShouldPersistTaps="handled"
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }} disabled={isSubmitting}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Cancel</Text>
      </Pressable>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 20 }}>
        Log a Meal
      </Text>

      <Field label="Meal type">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {MEAL_TYPES.map((mt) => {
            const isSelected = mealType === mt.value;
            return (
              <Pressable
                key={mt.value}
                onPress={() => setMealType(mt.value)}
                style={{
                  paddingHorizontal: 14,
                  paddingVertical: 8,
                  borderRadius: RADIUS.chip,
                  backgroundColor: isSelected ? colors.primary : colors.cardBg,
                  borderWidth: 1,
                  borderColor: isSelected ? colors.primary : colors.cardBorder,
                }}
              >
                <Text style={{ fontSize: 13, fontWeight: '600', color: isSelected ? '#fff' : colors.textPrimary }}>
                  {mt.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </Field>

      <Field label="Date">
        <Pressable onPress={() => setShowDatePicker(true)} style={inputStyle}>
          <Text style={{ fontSize: 14, color: colors.textPrimary }}>{formatDisplayDate(loggedAt)}</Text>
        </Pressable>
      </Field>

      <CalendarPickerModal
        visible={showDatePicker}
        selectedDate={loggedAt}
        maxDate={todayYMD()}
        onSelect={(date) => {
          setLoggedAt(date);
          setShowDatePicker(false);
        }}
        onClose={() => setShowDatePicker(false)}
      />

      <Field label="Food name">
        <TextInput
          placeholder="e.g. Grilled chicken salad"
          placeholderTextColor={colors.textMuted}
          value={foodName}
          onChangeText={setFoodName}
          style={inputStyle}
        />
      </Field>

      <Pressable
        onPress={handleEstimate}
        disabled={!foodName.trim() || isEstimating}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          alignSelf: 'flex-start',
          gap: 6,
          borderWidth: 1,
          borderColor: colors.accentLavender,
          borderRadius: RADIUS.chip,
          paddingHorizontal: 14,
          paddingVertical: 8,
          marginBottom: 16,
          opacity: foodName.trim() ? 1 : 0.5,
        }}
      >
        {isEstimating ? (
          <ActivityIndicator size="small" color={colors.accentLavender} />
        ) : (
          <Text style={{ fontSize: 13, fontWeight: '600', color: colors.accentLavender }}>
            Estimate with AI
          </Text>
        )}
      </Pressable>

      {estimateError ? (
        <Text style={{ color: colors.danger, fontSize: 12, marginTop: -12, marginBottom: 16 }}>
          {estimateError}
        </Text>
      ) : null}

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 4 }}>
        <View style={{ flex: 1, minWidth: '45%' }}>
          <Field label="Calories">
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

      <Field label="Fiber (g, optional)">
        <TextInput
          placeholder="0"
          placeholderTextColor={colors.textMuted}
          value={fiber}
          onChangeText={setFiber}
          keyboardType="numeric"
          style={inputStyle}
        />
      </Field>

      <Field label="Water (ml, optional)">
        <TextInput
          placeholder="0"
          placeholderTextColor={colors.textMuted}
          value={water}
          onChangeText={setWater}
          keyboardType="numeric"
          style={inputStyle}
        />
      </Field>

      <Field label="Notes (optional)">
        <TextInput
          placeholder="Anything worth remembering about this meal"
          placeholderTextColor={colors.textMuted}
          value={notes}
          onChangeText={setNotes}
          multiline
          numberOfLines={3}
          style={[inputStyle, { minHeight: 70, textAlignVertical: 'top' }]}
        />
      </Field>

      {error ? (
        <Text style={{ color: colors.danger, fontSize: 12, marginTop: 4, marginBottom: 12 }}>{error}</Text>
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
        {isSubmitting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600' }}>Log Meal</Text>
        )}
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
