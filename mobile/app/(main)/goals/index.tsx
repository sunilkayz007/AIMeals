import { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { profileApi } from '../../../src/api/profile';
import { useTheme } from '../../../src/theme/ThemeContext';
import ThemedText from '../../../src/components/ThemedText';

interface Field {
  key:
    | 'daily_calorie_target'
    | 'protein_g_target'
    | 'carbs_g_target'
    | 'fat_g_target'
    | 'fiber_g_target'
    | 'daily_water_ml_target';
  label: string;
  unit: string;
  placeholder: string;
  /** Sanity ceiling; mirrors ProfileUpdate's `le=` bounds in the backend. */
  max: number;
}

const FIELDS: Field[] = [
  { key: 'daily_calorie_target', label: 'Calories', unit: 'kcal/day', placeholder: 'e.g. 2200', max: 10000 },
  { key: 'protein_g_target', label: 'Protein', unit: 'g/day', placeholder: 'e.g. 120', max: 1000 },
  { key: 'carbs_g_target', label: 'Carbs', unit: 'g/day', placeholder: 'e.g. 250', max: 2000 },
  { key: 'fat_g_target', label: 'Fat', unit: 'g/day', placeholder: 'e.g. 70', max: 1000 },
  { key: 'fiber_g_target', label: 'Fiber', unit: 'g/day', placeholder: 'e.g. 30', max: 500 },
  { key: 'daily_water_ml_target', label: 'Water', unit: 'ml/day', placeholder: 'e.g. 2000', max: 20000 },
];

/** Returns a user-facing problem with a field's text, or null if it's fine (or empty). */
function fieldProblem(field: Field, raw: string | undefined): string | null {
  const text = (raw ?? '').trim();
  if (text === '') return null;
  const parsed = Number(text);
  if (!Number.isFinite(parsed) || parsed <= 0) return 'Enter a number greater than 0.';
  if (parsed > field.max) return `That's too high — the maximum is ${field.max} ${field.unit}.`;
  return null;
}

// HH:MM, 24-hour. Kept as a plain string (not a picker) to avoid
// pulling in a HeroUI Native component whose exact API hasn't been
// verified — same reasoning as this project's other custom-built
// inputs (see standing rule on avoiding unverified prebuilt components).
function isValidWakeTime(value: string): boolean {
  return /^([01]\d|2[0-3]):([0-5]\d)$/.test(value.trim());
}

export default function NutritionGoals() {
  const router = useRouter();
  const { colors } = useTheme();

  const [values, setValues] = useState<Record<string, string>>({});
  const [wakeTime, setWakeTime] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const full = await profileApi.getFull();
      const p = full.profile;
      setValues({
        daily_calorie_target: p?.daily_calorie_target ? String(Math.round(p.daily_calorie_target)) : '',
        protein_g_target: p?.protein_g_target ? String(Math.round(p.protein_g_target)) : '',
        carbs_g_target: p?.carbs_g_target ? String(Math.round(p.carbs_g_target)) : '',
        fat_g_target: p?.fat_g_target ? String(Math.round(p.fat_g_target)) : '',
        fiber_g_target: p?.fiber_g_target ? String(Math.round(p.fiber_g_target)) : '',
        daily_water_ml_target: p?.daily_water_ml_target ? String(Math.round(p.daily_water_ml_target)) : '',
      });
      setWakeTime(p?.typical_wake_time ?? '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Deliberately a one-time load on mount, NOT useFocusEffect. This is a
  // single-purpose edit form, not a list screen that needs refreshing
  // every time it regains focus — useFocusEffect can re-fire while the
  // user is still typing (a known gotcha with keyboard show/hide in
  // React Navigation-based apps), silently overwriting in-progress
  // field values with stale server data. A plain one-time load avoids
  // that entire class of bug.
  useEffect(() => {
    load();
  }, [load]);

  // At least the calorie field must be a valid positive number to save —
  // the others are optional (a user might only care about tracking
  // calories, not full macros).
  const calorieValue = parseInt(values.daily_calorie_target ?? '', 10);
  const wakeTimeTrimmed = wakeTime.trim();
  const wakeTimeValid = wakeTimeTrimmed === '' || isValidWakeTime(wakeTimeTrimmed);
  const fieldProblems = FIELDS.map((f) => fieldProblem(f, values[f.key]));
  const hasFieldProblem = fieldProblems.some((p) => p !== null);
  const canSave =
    !isNaN(calorieValue) && calorieValue > 0 && !hasFieldProblem && wakeTimeValid && !isSaving;

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const payload: Record<string, number | string> = {};
      for (const field of FIELDS) {
        const raw = values[field.key];
        const parsed = raw ? parseInt(raw, 10) : NaN;
        if (!isNaN(parsed) && parsed > 0) {
          payload[field.key] = parsed;
        }
      }
      if (wakeTimeTrimmed) {
        payload.typical_wake_time = wakeTimeTrimmed;
      }
      await profileApi.update(payload);
      router.back();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.screenBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
        <ThemedText variant="body" color="textSecondary">‹ Back</ThemedText>
      </Pressable>

      <ThemedText variant="h1" style={{ marginBottom: 4 }}>
        Nutrition goals
      </ThemedText>
      <ThemedText variant="body" color="textSecondary" style={{ marginBottom: 24 }}>
        Used to track your progress on Home. Calories is required; protein, carbs, fat, fiber, and
        water are optional.
      </ThemedText>

      {isLoading ? (
        <ActivityIndicator color={colors.accentPeach} />
      ) : (
        <>
          {FIELDS.map((field, index) => (
            <View key={field.key} style={{ marginBottom: 18 }}>
              <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 6 }}>
                {field.label} <Text style={{ color: colors.textMuted, fontWeight: '400' }}>({field.unit})</Text>
              </Text>
              <TextInput
                placeholder={field.placeholder}
                value={values[field.key] ?? ''}
                onChangeText={(text) => setValues((prev) => ({ ...prev, [field.key]: text }))}
                keyboardType="numeric"
                style={{
                  borderWidth: 1,
                  borderColor: fieldProblems[index] ? colors.danger : colors.border,
                  borderRadius: 8,
                  paddingHorizontal: 14,
                  paddingVertical: 12,
                  fontSize: 16,
                  color: colors.textPrimary,
                }}
              />
              {fieldProblems[index] ? (
                <ThemedText variant="caption" color="danger" style={{ marginTop: 4 }}>
                  {fieldProblems[index]}
                </ThemedText>
              ) : field.key === 'daily_calorie_target' && !(values[field.key] ?? '').trim() ? (
                <ThemedText variant="caption" color="textMuted" style={{ marginTop: 4 }}>
                  Calories is required to save your goals.
                </ThemedText>
              ) : null}
            </View>
          ))}

          <View style={{ marginBottom: 18 }}>
            <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 6 }}>
              Typical wake time
            </Text>
            <Text style={{ fontSize: 11, color: colors.textMuted, marginBottom: 6 }}>
              Used to pace your water reminder through the day — only needed if you set a water
              target above.
            </Text>
            <TextInput
              placeholder="e.g. 07:00"
              value={wakeTime}
              onChangeText={setWakeTime}
              autoCapitalize="none"
              style={{
                borderWidth: 1,
                borderColor: !wakeTimeValid ? colors.danger : colors.border,
                borderRadius: 8,
                paddingHorizontal: 14,
                paddingVertical: 12,
                fontSize: 16,
                color: colors.textPrimary,
              }}
            />
            {!wakeTimeValid && (
              <ThemedText variant="caption" color="danger" style={{ marginTop: 4 }}>
                Use 24-hour HH:MM format, e.g. 07:00 or 18:30.
              </ThemedText>
            )}
          </View>

          {error ? (
            <ThemedText variant="bodySmall" color="danger" style={{ marginBottom: 12 }}>{error}</ThemedText>
          ) : null}

          <Pressable
            onPress={handleSave}
            disabled={!canSave}
            style={{
              backgroundColor: canSave ? colors.accentPeach : colors.border,
              borderRadius: 8,
              paddingVertical: 12,
              alignItems: 'center',
              marginTop: 8,
            }}
          >
            <ThemedText variant="button" style={{ color: '#fff' }}>
              {isSaving ? 'Saving…' : 'Save goals'}
            </ThemedText>
          </Pressable>
        </>
      )}
    </ScrollView>
  );
}
