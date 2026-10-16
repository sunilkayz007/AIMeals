import { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { generateMealPlan, MEAL_PLAN_STAGE_ORDER, MEAL_PLAN_STAGE_LABELS } from '../../../src/api/aiMealPlan';
import type { MealPlanGenerationStage } from '../../../src/api/aiMealPlan';
import type { MealPlan } from '../../../src/api/mealPlan';
import type { MealType } from '../../../src/types/nutritionLog';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';
import type { ThemeColors } from '../../../src/theme/colors';
import CalendarPickerModal from '../../../src/components/CalendarPickerModal';

// ASSUMPTION, flagged clearly: these are the standard four meal
// types (matching every mockup/design doc referenced throughout
// this project), but the exact MealType enum values were never
// independently confirmed against the real backend enum. If
// generation fails with a validation error mentioning meal_type,
// this is the one place to check/fix.
const MEAL_TYPES: { value: MealType; label: string }[] = [
  { value: 'breakfast' as MealType, label: 'Breakfast' },
  { value: 'lunch' as MealType, label: 'Lunch' },
  { value: 'dinner' as MealType, label: 'Dinner' },
  { value: 'snack' as MealType, label: 'Snack' },
];

const ERROR_MESSAGES: Record<string, string> = {};

function todayYMD(): string {
  const d = new Date();
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
}

function formatDisplayDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

export default function NewMealPlan() {
  const router = useRouter();
  const { colors } = useTheme();
  const inputStyle = getInputStyle(colors);
  // prefill comes from the Health Insights results screen's "Meal
  // Plan" card — a suggested starting point built from the user's
  // confirmed nutrition priorities (e.g. "Focus on: Increase Dietary
  // Fiber and Improve Vitamin D"). Purely a convenience the user can
  // freely edit — the backend already applies the full confirmed
  // priority list (and day-by-day targeting) to every meal plan
  // generation automatically, regardless of what's typed here.
  const { prefill } = useLocalSearchParams<{ prefill?: string }>();

  const [title, setTitle] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [showStartPicker, setShowStartPicker] = useState(false);
  const [showEndPicker, setShowEndPicker] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<MealType[]>(['breakfast', 'lunch', 'dinner'] as MealType[]);
  const [preferences, setPreferences] = useState(prefill ?? '');

  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStage, setCurrentStage] = useState<MealPlanGenerationStage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  const toggleType = (type: MealType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSelectStart = (dateStr: string) => {
    setStartDate(dateStr);
    setShowStartPicker(false);
    // If the current end date is now before the newly-picked start
    // date, clear it rather than leave an invalid range sitting there
    // silently — the end-date picker's minDate will also stop it from
    // happening again going forward.
    if (endDate && endDate < dateStr) {
      setEndDate('');
    }
  };

  const handleSelectEnd = (dateStr: string) => {
    setEndDate(dateStr);
    setShowEndPicker(false);
  };

  const canGenerate = !!title.trim() && !!startDate && !!endDate && selectedTypes.length > 0 && !isGenerating;

  const handleGenerate = () => {
    if (!canGenerate) return;
    setIsGenerating(true);
    setCurrentStage(null);
    setError(null);
    setErrorType(null);

    abortRef.current = generateMealPlan(
      {
        title: title.trim(),
        start_date: startDate,
        end_date: endDate,
        meal_types: selectedTypes,
        preferences: preferences.trim(),
      },
      {
        onStage: (stage) => setCurrentStage(stage),
        onResult: (plan: MealPlan) => {
          setIsGenerating(false);
          setCurrentStage(null);
          router.replace(`/(main)/meal-plans/${plan.id}`);
        },
        onError: (errorType, detail) => {
          setIsGenerating(false);
          setCurrentStage(null);
          setError(ERROR_MESSAGES[errorType] ?? detail);
          setErrorType(errorType);
        },
      }
    );
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}
      keyboardShouldPersistTaps="handled"
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }} disabled={isGenerating}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Cancel</Text>
      </Pressable>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
        New Meal Plan
      </Text>
      <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
        Tell AI your dates and preferences — it'll generate real, complete recipes for every meal.
      </Text>

      <Field label="Title">
        <TextInput
          placeholder="e.g. This week's meals"
          placeholderTextColor={colors.textMuted}
          value={title}
          onChangeText={setTitle}
          editable={!isGenerating}
          style={inputStyle}
        />
      </Field>

      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Field label="Start date">
            <Pressable onPress={() => !isGenerating && setShowStartPicker(true)} style={inputStyle}>
              <Text style={{ fontSize: 14, color: startDate ? colors.textPrimary : colors.textMuted }}>
                {startDate ? formatDisplayDate(startDate) : 'Select date'}
              </Text>
            </Pressable>
          </Field>
        </View>
        <View style={{ flex: 1 }}>
          <Field label="End date">
            <Pressable
              onPress={() => !isGenerating && startDate && setShowEndPicker(true)}
              style={[inputStyle, { opacity: startDate ? 1 : 0.5 }]}
            >
              <Text style={{ fontSize: 14, color: endDate ? colors.textPrimary : colors.textMuted }}>
                {endDate ? formatDisplayDate(endDate) : 'Select date'}
              </Text>
            </Pressable>
          </Field>
        </View>
      </View>

      <CalendarPickerModal
        visible={showStartPicker}
        selectedDate={startDate || undefined}
        minDate={todayYMD()}
        onSelect={handleSelectStart}
        onClose={() => setShowStartPicker(false)}
      />
      <CalendarPickerModal
        visible={showEndPicker}
        selectedDate={endDate || undefined}
        minDate={startDate || todayYMD()}
        onSelect={handleSelectEnd}
        onClose={() => setShowEndPicker(false)}
      />

      <Field label="Meal types to include">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {MEAL_TYPES.map((mt) => {
            const isSelected = selectedTypes.includes(mt.value);
            return (
              <Pressable
                key={mt.value}
                onPress={() => toggleType(mt.value)}
                disabled={isGenerating}
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

      <Field label="Preferences (optional)">
        <TextInput
          placeholder="e.g. high protein, no dairy, quick weeknight dinners"
          placeholderTextColor={colors.textMuted}
          value={preferences}
          onChangeText={setPreferences}
          editable={!isGenerating}
          multiline
          numberOfLines={3}
          style={[inputStyle, { minHeight: 70, textAlignVertical: 'top' }]}
        />
      </Field>

      {isGenerating && (
        <ThemedCard padding={14} style={{ backgroundColor: colors.surfaceAlt, marginBottom: 16 }}>
          {MEAL_PLAN_STAGE_ORDER.map((stage) => {
            const currentIndex = currentStage ? MEAL_PLAN_STAGE_ORDER.indexOf(currentStage) : -1;
            const thisIndex = MEAL_PLAN_STAGE_ORDER.indexOf(stage);
            const isDone = thisIndex < currentIndex;
            const isActive = stage === currentStage;
            return (
              <View key={stage} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
                <Text style={{ width: 18, fontSize: 12 }}>{isDone ? '✓' : isActive ? '' : '○'}</Text>
                {isActive && <ActivityIndicator size="small" color={colors.primary} style={{ marginRight: 6 }} />}
                <Text
                  style={{
                    fontSize: 12,
                    color: isDone || isActive ? colors.textPrimary : colors.textMuted,
                    fontWeight: isActive ? '600' : '400',
                  }}
                >
                  {MEAL_PLAN_STAGE_LABELS[stage]}
                </Text>
              </View>
            );
          })}
        </ThemedCard>
      )}

      {error && (
        <ThemedCard padding={12} style={{ backgroundColor: colors.dangerBg, marginBottom: 16 }}>
          <Text style={{ color: colors.danger, fontSize: 12, marginBottom: errorType === 'InsufficientCreditsError' ? 10 : 0 }}>
            {error}
          </Text>
          {errorType === 'InsufficientCreditsError' && (
            <Pressable
              onPress={() => router.push('/(main)/credits')}
              style={{
                backgroundColor: colors.danger,
                borderRadius: RADIUS.button,
                paddingVertical: 10,
                alignItems: 'center',
              }}
            >
              <Text style={{ color: '#fff', fontWeight: '700', fontSize: 13 }}>Upgrade to Plus or Pro</Text>
            </Pressable>
          )}
        </ThemedCard>
      )}

      <Pressable
        onPress={handleGenerate}
        disabled={!canGenerate}
        style={{
          backgroundColor: canGenerate ? colors.primary : colors.border,
          borderRadius: RADIUS.button,
          paddingVertical: 14,
          alignItems: 'center',
        }}
      >
        <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>
          {isGenerating ? 'Generating…' : 'Generate meal plan'}
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
