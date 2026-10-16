import { useCallback, useEffect, useState } from 'react';
import { View, Text, Pressable, ActivityIndicator, ScrollView, LogBox } from 'react-native';

// WheelPickerExpo renders its own internal, fixed-height FlatList
// (a vertical VirtualizedList) inside this screen's outer vertical
// ScrollView. React Native flags this structurally regardless of
// the nestedScrollEnabled prop already passed below (that prop only
// fixes Android's actual nested-scroll gesture handling — it doesn't
// suppress this console warning). Each wheel here only ever holds a
// small, bounded list (at most ~121 items — see AGE_ITEMS/HEIGHT_ITEMS/
// WEIGHT_ITEMS), nowhere near the scale where virtualization/windowing
// actually matters for performance, so this specific warning is a
// known false alarm for this exact bounded-picker-in-a-form-screen
// pattern — safe to suppress rather than restructure the whole
// screen around it.
LogBox.ignoreLogs([
  'VirtualizedLists should never be nested inside plain ScrollViews',
]);
import { useRouter } from 'expo-router';
import WheelPickerExpo from 'react-native-wheel-picker-expo';
import { profileApi } from '../../../src/api/profile';
import { rdaApi, type RDATargets } from '../../../src/api/rda';
import { nutritionLogApi } from '../../../src/api/nutritionLog';
import { waterApi, type WaterDaySummary } from '../../../src/api/water';
import { getHealthReports } from '../../../src/api/healthReport';
import type { HealthReport, HealthMarker } from '../../../src/api/healthReport';
import { useTheme } from '../../../src/theme/ThemeContext';
import ProgressRing from '../../../src/components/ProgressRing';
import ThemedText from '../../../src/components/ThemedText';
import ThemedCard from '../../../src/components/ThemedCard';
import type { Gender } from '../../../src/types/profile';
import type { DailyTotals } from '../../../src/types/nutritionLog';
import { getMarkerSeverity, type MarkerSeverity } from '../../../src/utils/healthMarkerSeverity';
import { formatLitersFromMl } from '../../../src/utils/recipeText';

// Ranges chosen to cover the practical adult range without an
// unnecessarily long wheel to scroll through.
const MIN_AGE = 10;
const MAX_AGE = 120;
const MIN_HEIGHT_CM = 100;
const MAX_HEIGHT_CM = 220;
const MIN_WEIGHT_KG = 30;
const MAX_WEIGHT_KG = 200;

function range(min: number, max: number): number[] {
  return Array.from({ length: max - min + 1 }, (_, i) => min + i);
}

const AGE_ITEMS = range(MIN_AGE, MAX_AGE).map((n) => ({ label: String(n), value: n }));
const HEIGHT_ITEMS = range(MIN_HEIGHT_CM, MAX_HEIGHT_CM).map((n) => ({ label: `${n} cm`, value: n }));
const WEIGHT_ITEMS = range(MIN_WEIGHT_KG, MAX_WEIGHT_KG).map((n) => ({ label: `${n} kg`, value: n }));

const DEFAULT_AGE = 30;
const DEFAULT_HEIGHT_CM = 170;
const DEFAULT_WEIGHT_KG = 70;

// Gender is needed alongside age/weight because the RDA (Recommended
// Dietary Allowance) targets computed by the backend for several
// minerals — Iron most notably — differ meaningfully by sex. See
// backend app/core/rda.py's module docstring for exactly how each
// option maps to a reference table (male vs. everything else).
const GENDER_OPTIONS: { label: string; value: Gender }[] = [
  { label: 'Male', value: 'male' },
  { label: 'Female', value: 'female' },
  { label: 'Other', value: 'other' },
  { label: 'Prefer not to say', value: 'prefer_not_to_say' },
];

// Display order and short labels for the 10 auto-computed RDA
// nutrients — see backend app/core/rda.py for the underlying
// calculation.
const RDA_NUTRIENT_DISPLAY: {
  key: keyof Omit<RDATargets, 'disclaimer'>;
  label: string;
}[] = [
  { key: 'sodium_mg', label: 'Sodium' },
  { key: 'potassium_mg', label: 'Potassium' },
  { key: 'calcium_mg', label: 'Calcium' },
  { key: 'iron_mg', label: 'Iron' },
  { key: 'magnesium_mg', label: 'Magnesium' },
  { key: 'zinc_mg', label: 'Zinc' },
  { key: 'vitamin_a_mcg', label: 'Vitamin A' },
  { key: 'vitamin_b12_mcg', label: 'Vitamin B12' },
  { key: 'vitamin_c_mg', label: 'Vitamin C' },
  { key: 'vitamin_d_mcg', label: 'Vitamin D' },
];

function formatRdaAmount(amount: number): string {
  return Number.isInteger(amount) ? String(amount) : amount.toFixed(1);
}

// Fixed color + icon + one-line benefit per nutrient, mirrored from
// app/(main)/home.tsx's NUTRIENT_META for the 6 macros, extended here
// with the 10 RDA nutrients — matching the reference design's repeating
// orange/green/blue/red/purple/teal pattern across the mineral row and
// orange/blue/green/gold across the vitamin row. Used for the rings'
// colors, and (best-effort, by name match) for the "Nutrients to
// Watch" card below.
//
// Intentionally fixed hex, NOT theme tokens — these are per-nutrient
// IDENTITY colors (same reasoning as a dataviz category palette: a
// nutrient's color should stay recognizable across light/dark mode,
// not shift with the theme). Not a dark-mode bug — left untouched
// during the Sep 4 2026 design-system hex sweep for exactly this
// reason.
const ALL_NUTRIENT_META: Record<string, { color: string; icon: string; benefit: string }> = {
  calories: { color: '#F97316', icon: '🔥', benefit: 'Energy' },
  protein: { color: '#22C55E', icon: '💪', benefit: 'Builds & repairs' },
  carbs: { color: '#3B82F6', icon: '🌾', benefit: 'Primary fuel' },
  fat: { color: '#F59E0B', icon: '💧', benefit: 'Hormones & absorption' },
  fiber: { color: '#A855F7', icon: '🌿', benefit: 'Digestion & gut health' },
  water: { color: '#14B8A6', icon: '💧', benefit: 'Hydration & balance' },
  sodium_mg: { color: '#F97316', icon: '🧂', benefit: 'Fluid balance (keep under)' },
  potassium_mg: { color: '#22C55E', icon: '🍌', benefit: 'Muscles & nerves' },
  calcium_mg: { color: '#3B82F6', icon: '🦴', benefit: 'Bones & teeth' },
  iron_mg: { color: '#EF4444', icon: '🩸', benefit: 'Oxygen transport' },
  magnesium_mg: { color: '#A855F7', icon: '⚡', benefit: 'Energy & muscles' },
  zinc_mg: { color: '#14B8A6', icon: '🛡️', benefit: 'Immunity & healing' },
  vitamin_a_mcg: { color: '#F97316', icon: '👁️', benefit: 'Vision & immunity' },
  vitamin_b12_mcg: { color: '#3B82F6', icon: '🧠', benefit: 'Brain & red blood cells' },
  vitamin_c_mg: { color: '#22C55E', icon: '🍊', benefit: 'Immunity & antioxidant' },
  vitamin_d_mcg: { color: '#F59E0B', icon: '☀️', benefit: 'Bone health & immunity' },
};

// Label used for name-matching against arbitrary health-report marker
// names below (e.g. a report marker literally named "Iron" or
// "Serum Iron" should match the 'iron_mg' entry above). Kept separate
// from RDA_NUTRIENT_DISPLAY since this list also includes the 6
// macros, which RDA_NUTRIENT_DISPLAY deliberately excludes.
const NUTRIENT_NAME_LOOKUP: { key: keyof typeof ALL_NUTRIENT_META; label: string }[] = [
  { key: 'calories', label: 'Calories' },
  { key: 'protein', label: 'Protein' },
  { key: 'carbs', label: 'Carbs' },
  { key: 'fat', label: 'Fat' },
  { key: 'fiber', label: 'Fiber' },
  { key: 'water', label: 'Water' },
  { key: 'sodium_mg', label: 'Sodium' },
  { key: 'potassium_mg', label: 'Potassium' },
  { key: 'calcium_mg', label: 'Calcium' },
  { key: 'iron_mg', label: 'Iron' },
  { key: 'magnesium_mg', label: 'Magnesium' },
  { key: 'zinc_mg', label: 'Zinc' },
  { key: 'vitamin_a_mcg', label: 'Vitamin A' },
  { key: 'vitamin_b12_mcg', label: 'Vitamin B12' },
  { key: 'vitamin_c_mg', label: 'Vitamin C' },
  { key: 'vitamin_d_mcg', label: 'Vitamin D' },
];

// Best-effort match of an arbitrary health-report marker name (e.g.
// "Serum Iron", "Hemoglobin A1c") against the app's fixed nutrient
// icon/color set. Health report markers come from AI extraction of a
// real lab report and are NOT limited to this app's 16 tracked
// nutrients — most won't match at all, which is expected and fine
// (see FALLBACK_ICON_META below for the unmatched case).
function findNutrientMeta(markerName: string): { color: string; icon: string } | null {
  const normalized = markerName.toLowerCase();
  const match = NUTRIENT_NAME_LOOKUP.find(
    ({ label }) => normalized.includes(label.toLowerCase()) || label.toLowerCase().includes(normalized)
  );
  return match ? ALL_NUTRIENT_META[match.key] : null;
}

const FALLBACK_ICON = '🔬';

// ---------------------------------------------------------------
// Severity classification (getMarkerSeverity/MarkerSeverity) now
// lives in src/utils/healthMarkerSeverity.ts, shared with
// app/(main)/health-insights/index.tsx — previously duplicated
// identically in both files.
// ---------------------------------------------------------------

// Combines severity ('high'/'medium') + direction ('above'/'below')
// into the 4-level label shown on each flagged marker's pill —
// "Very High" / "High" / "Very Low" / "Low".
function flaggedMarkerDisplay(
  marker: HealthMarker,
  colors: any
): { label: string; textColor: string; bgColor: string; arrow: '↑' | '↓' } {
  const severity = getMarkerSeverity(marker);
  const isAbove = marker.range_status === 'above';
  const isHigh = severity === 'high';

  const label = isAbove ? (isHigh ? 'Very High' : 'High') : isHigh ? 'Very Low' : 'Low';
  const textColor = isHigh ? colors.danger : colors.warningText;
  const bgColor = isHigh ? colors.dangerBg : colors.warningBg;
  const arrow = isAbove ? '↑' : '↓';

  return { label, textColor, bgColor, arrow };
}

// Water is tracked in ml on the backend but shown in liters here,
// matching Home's own formatting — see home.tsx's formatLiters for
// the identical reasoning (whole liters show with no decimal).
function formatLiters(ml: number): string {
  return `${formatLitersFromMl(ml)}L`;
}

function safePercent(consumed: number, target: number | null): number {
  if (!target || target <= 0) return 0;
  return (consumed / target) * 100;
}

function todayString(): string {
  const d = new Date();
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
}

// The backend only stores a real date_of_birth, not a plain age number —
// there's no separate "age" column on Profile. A roller that lets someone
// pick "34" rather than an exact birthdate is a deliberately simpler
// input, so the picked age is converted to an approximate date of birth
// (Jan 1 of the corresponding birth year) on save. This is an
// approximation, not the user's real birthdate — acceptable here since
// age is only used for calorie/nutrient estimation, not anything
// date-of-birth-precise like a legal age check.
function approximateDateOfBirthFromAge(age: number): string {
  const birthYear = new Date().getFullYear() - age;
  return `${birthYear}-01-01`;
}

function approximateAgeFromDateOfBirth(dateOfBirth: string): number {
  const birthYear = new Date(dateOfBirth).getFullYear();
  return new Date().getFullYear() - birthYear;
}

interface MacroTargets {
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  water_ml: number | null;
}

export default function BodyDetails() {
  const router = useRouter();
  const { colors } = useTheme();

  const [age, setAge] = useState(DEFAULT_AGE);
  const [heightCm, setHeightCm] = useState(DEFAULT_HEIGHT_CM);
  const [weightKg, setWeightKg] = useState(DEFAULT_WEIGHT_KG);
  const [gender, setGender] = useState<Gender | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Once true, the input form is replaced entirely by the full rings
  // view below — this happens automatically the moment the profile
  // already has body details saved (from any previous visit), or
  // right after this screen's own Save succeeds.
  const [isComplete, setIsComplete] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);

  const [rdaTargets, setRdaTargets] = useState<RDATargets | null>(null);
  const [dailyTotals, setDailyTotals] = useState<DailyTotals | null>(null);
  const [macroTargets, setMacroTargets] = useState<MacroTargets | null>(null);
  const [waterSummary, setWaterSummary] = useState<WaterDaySummary | null>(null);
  const [latestHealthReport, setLatestHealthReport] = useState<HealthReport | null>(null);
  const [showAllFlaggedMarkers, setShowAllFlaggedMarkers] = useState(false);
  const [showAllRdaNutrients, setShowAllRdaNutrients] = useState(false);

  // Loads everything needed for the rings view: the 10 RDA targets,
  // today's macro totals/targets, today's water, and the latest
  // CONFIRMED health report (for the "Nutrients to Watch" card) —
  // same reports call Health Insights itself makes, just reading the
  // first confirmed one.
  const loadRingsData = useCallback(async () => {
    try {
      const [rda, totals, profileFull, water, reports] = await Promise.all([
        rdaApi.get(),
        nutritionLogApi.getDailyTotals(todayString()),
        profileApi.getFull(),
        waterApi.getDaySummary(todayString()),
        getHealthReports().catch(() => []), // non-fatal — this card is a nice-to-have, not core to the rings view
      ]);
      setRdaTargets(rda);
      setDailyTotals(totals);
      setMacroTargets({
        calories: profileFull.profile?.daily_calorie_target ?? null,
        protein_g: profileFull.profile?.protein_g_target ?? null,
        carbs_g: profileFull.profile?.carbs_g_target ?? null,
        fat_g: profileFull.profile?.fat_g_target ?? null,
        fiber_g: profileFull.profile?.fiber_g_target ?? null,
        water_ml: profileFull.profile?.daily_water_ml_target ?? null,
      });
      setWaterSummary(water);
      setLatestHealthReport(reports.find((r) => r.status === 'confirmed') ?? null);
      return true;
    } catch {
      // RDA targets require date_of_birth on the backend — a failure
      // here means the profile isn't actually complete yet, so the
      // form stays showing rather than the rings view.
      return false;
    }
  }, []);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const full = await profileApi.getFull();
      const p = full.profile;
      if (p?.date_of_birth) {
        const derivedAge = approximateAgeFromDateOfBirth(p.date_of_birth);
        if (derivedAge >= MIN_AGE && derivedAge <= MAX_AGE) setAge(derivedAge);
      }
      if (p?.height_cm && p.height_cm >= MIN_HEIGHT_CM && p.height_cm <= MAX_HEIGHT_CM) {
        setHeightCm(Math.round(p.height_cm));
      }
      if (p?.weight_kg && p.weight_kg >= MIN_WEIGHT_KG && p.weight_kg <= MAX_WEIGHT_KG) {
        setWeightKg(Math.round(p.weight_kg));
      }
      if (p?.gender) {
        setGender(p.gender);
      }

      const bodyDetailsSaved = Boolean(p?.date_of_birth && p?.height_cm && p?.weight_kg);
      if (bodyDetailsSaved) {
        const ringsLoaded = await loadRingsData();
        setIsComplete(ringsLoaded);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setIsLoading(false);
    }
  }, [loadRingsData]);

  // One-time load on mount, not useFocusEffect — same reasoning as the
  // Goals screen: this is a single-purpose edit form, and re-fetching on
  // focus can clobber an in-progress selection with stale server data.
  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      await profileApi.update({
        date_of_birth: approximateDateOfBirthFromAge(age),
        height_cm: heightCm,
        weight_kg: weightKg,
        ...(gender ? { gender } : {}),
      });
      const ringsLoaded = await loadRingsData();
      if (ringsLoaded) {
        setIsComplete(true);
        setShowEditForm(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  const initialAgeIndex = Math.max(0, Math.min(AGE_ITEMS.length - 1, age - MIN_AGE));
  const initialHeightIndex = Math.max(0, Math.min(HEIGHT_ITEMS.length - 1, heightCm - MIN_HEIGHT_CM));
  const initialWeightIndex = Math.max(0, Math.min(WEIGHT_ITEMS.length - 1, weightKg - MIN_WEIGHT_KG));

  const showForm = !isComplete || showEditForm;

  // Combined macro rings (Calories through Water) — same shape and
  // rendering logic as Home's own macroRings, duplicated here rather
  // than imported since Home doesn't export it. Kept deliberately
  // identical so both screens read the same at a glance.
  const macroRings = macroTargets
    ? [
        {
          key: 'calories',
          label: 'Calories',
          consumed: dailyTotals?.calories ?? 0,
          target: macroTargets.calories,
          unit: 'kcal',
          color: ALL_NUTRIENT_META.calories.color,
        },
        {
          key: 'protein',
          label: 'Protein',
          consumed: dailyTotals?.protein_g ?? 0,
          target: macroTargets.protein_g,
          unit: 'g',
          color: ALL_NUTRIENT_META.protein.color,
        },
        {
          key: 'carbs',
          label: 'Carbs',
          consumed: dailyTotals?.carbs_g ?? 0,
          target: macroTargets.carbs_g,
          unit: 'g',
          color: ALL_NUTRIENT_META.carbs.color,
        },
        {
          key: 'fat',
          label: 'Fat',
          consumed: dailyTotals?.fat_g ?? 0,
          target: macroTargets.fat_g,
          unit: 'g',
          color: ALL_NUTRIENT_META.fat.color,
        },
        {
          key: 'fiber',
          label: 'Fiber',
          consumed: dailyTotals?.fiber_g ?? 0,
          target: macroTargets.fiber_g,
          unit: 'g',
          color: ALL_NUTRIENT_META.fiber.color,
        },
        {
          key: 'water',
          label: 'Water',
          consumed: waterSummary?.total_ml ?? 0,
          target: macroTargets.water_ml,
          unit: 'L',
          color: ALL_NUTRIENT_META.water.color,
        },
      ]
    : [];

  const flaggedMarkers = (latestHealthReport?.confirmed_markers ?? []).filter(
    (m) => m.range_status === 'above' || m.range_status === 'below'
  );

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.screenBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
        <ThemedText variant="body" color="textSecondary">‹ Back</ThemedText>
      </Pressable>

      {isLoading ? (
        <ActivityIndicator color={colors.accentPeach} />
      ) : showForm ? (
        <>
          <ThemedText variant="h1" style={{ marginBottom: 4 }}>
            Your body details
          </ThemedText>
          <ThemedText variant="body" color="textSecondary" style={{ marginBottom: 20 }}>
            Scroll each wheel to set your age, height, and weight, and select your gender below.
          </ThemedText>

          <ThemedCard
            padding={12}
            style={{ backgroundColor: colors.accentSage + '30', borderColor: 'transparent', marginBottom: 24 }}
          >
            <ThemedText variant="bodySmall" color="textSecondary" style={{ lineHeight: 17 }}>
              Once saved, this form will be replaced by your full nutrient breakdown — every
              target from Calories to Vitamin D.
            </ThemedText>
          </ThemedCard>

          <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginBottom: 24 }}>
            <View style={{ width: 100, alignItems: 'center' }}>
              <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 8 }}>
                Age
              </ThemedText>
              <WheelPickerExpo
                height={180}
                width={100}
                initialSelectedIndex={initialAgeIndex}
                items={AGE_ITEMS}
                onChange={({ item }) => setAge(item.value)}
                backgroundColor={colors.screenBg}
                flatListProps={{ nestedScrollEnabled: true }}
              />
            </View>

            <View style={{ width: 100, alignItems: 'center' }}>
              <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 8 }}>
                Height
              </ThemedText>
              <WheelPickerExpo
                height={180}
                width={100}
                initialSelectedIndex={initialHeightIndex}
                items={HEIGHT_ITEMS}
                onChange={({ item }) => setHeightCm(item.value)}
                backgroundColor={colors.screenBg}
                flatListProps={{ nestedScrollEnabled: true }}
              />
            </View>

            <View style={{ width: 100, alignItems: 'center' }}>
              <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 8 }}>
                Weight
              </ThemedText>
              <WheelPickerExpo
                height={180}
                width={100}
                initialSelectedIndex={initialWeightIndex}
                items={WEIGHT_ITEMS}
                onChange={({ item }) => setWeightKg(item.value)}
                backgroundColor={colors.screenBg}
                flatListProps={{ nestedScrollEnabled: true }}
              />
            </View>
          </View>

          <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 10 }}>
            Gender
          </ThemedText>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 24 }}>
            {GENDER_OPTIONS.map((option) => {
              const selected = gender === option.value;
              return (
                <Pressable
                  key={option.value}
                  onPress={() => setGender(option.value)}
                  style={{
                    borderWidth: 1,
                    borderColor: selected ? colors.accentPeach : colors.border,
                    backgroundColor: selected ? colors.accentPeach + '20' : colors.screenBg,
                    borderRadius: 100,
                    paddingHorizontal: 14,
                    paddingVertical: 8,
                  }}
                >
                  <ThemedText
                    variant="label"
                    style={{ color: selected ? colors.accentPeach : colors.textSecondary }}
                  >
                    {option.label}
                  </ThemedText>
                </Pressable>
              );
            })}
          </View>

          {error ? (
            <ThemedText variant="bodySmall" color="danger" style={{ marginBottom: 12 }}>{error}</ThemedText>
          ) : null}

          <Pressable
            onPress={handleSave}
            disabled={isSaving}
            style={{
              backgroundColor: colors.accentPeach,
              borderRadius: 8,
              paddingVertical: 12,
              alignItems: 'center',
              marginTop: 8,
              opacity: isSaving ? 0.6 : 1,
            }}
          >
            <ThemedText variant="button" style={{ color: '#fff' }}>
              {isSaving ? 'Saving…' : 'Save details'}
            </ThemedText>
          </Pressable>

          {isComplete && (
            <Pressable onPress={() => setShowEditForm(false)} style={{ marginTop: 14, alignItems: 'center' }}>
              <ThemedText variant="caption" color="textSecondary">‹ Back to your breakdown</ThemedText>
            </Pressable>
          )}
        </>
      ) : (
        <>
          <View
            style={{
              flexDirection: 'row',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 4,
            }}
          >
            <ThemedText variant="h1">Your full breakdown</ThemedText>
            <Pressable onPress={() => setShowEditForm(true)}>
              <ThemedText variant="label" style={{ color: colors.accentPeach }}>Edit ›</ThemedText>
            </Pressable>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', marginBottom: 20 }}>
            <ThemedText variant="body" color="textSecondary" style={{ flex: 1 }}>
              Every target, from Calories to Vitamin D, based on today's progress and your Health
              Insights.
            </ThemedText>
            <Pressable onPress={() => router.push('/(main)/history')} style={{ marginLeft: 10 }}>
              <ThemedText variant="label" style={{ color: colors.accentPeach }}>History ›</ThemedText>
            </Pressable>
          </View>

          <ThemedCard
            style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', borderRadius: 12, padding: 16, marginBottom: 20 }}
          >
            <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 14 }}>
              Calories & Fats Today
            </ThemedText>
            <View
              style={{
                flexDirection: 'row',
                flexWrap: 'wrap',
                justifyContent: 'space-between',
                rowGap: 16,
              }}
            >
              {macroRings.map((ring) => {
                const percent = safePercent(ring.consumed, ring.target);
                const isOver = percent > 100;
                const ringColor = !ring.target
                  ? colors.border
                  : ring.key === 'water'
                    ? ring.color
                    : isOver
                      ? colors.danger
                      : ring.color;
                return (
                  <View key={ring.key} style={{ alignItems: 'center', width: '31%' }}>
                    <ProgressRing
                      percent={percent}
                      size={60}
                      strokeWidth={6}
                      color={ringColor}
                      trackColor={colors.border}
                      centerLabel={ring.target ? `${Math.round(percent)}%` : '--'}
                    />
                    <Text style={{ fontSize: 10, color: colors.textSecondary, marginTop: 6 }}>
                      {ring.label}
                    </Text>
                    <Text
                      style={{
                        fontSize: 10,
                        color: ring.target ? colors.textPrimary : colors.textMuted,
                        fontWeight: '600',
                        marginTop: 1,
                        textAlign: 'center',
                      }}
                    >
                      {ring.target
                        ? ring.unit === 'L'
                          ? `${formatLiters(ring.consumed)}/${formatLiters(ring.target)}`
                          : `${Math.round(ring.consumed)}/${Math.round(ring.target)}${ring.unit === 'kcal' ? '' : 'g'}`
                        : 'Not set'}
                    </Text>
                  </View>
                );
              })}
            </View>
          </ThemedCard>

          {rdaTargets && (
            <ThemedCard
              style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', borderRadius: 12, padding: 16, marginBottom: 20 }}
            >
              <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 14 }}>
                Vitamins & Minerals Today
              </ThemedText>

              <View
                style={{
                  flexDirection: 'row',
                  flexWrap: 'wrap',
                  justifyContent: 'space-between',
                  rowGap: 16,
                }}
              >
                {(showAllRdaNutrients ? RDA_NUTRIENT_DISPLAY : RDA_NUTRIENT_DISPLAY.slice(0, 6)).map(({ key, label }) => {
                  const target = rdaTargets[key];
                  // Real consumption, summed server-side across
                  // today's logged meals (scaled by portion_percentage
                  // for partially-eaten meals) — see backend
                  // NutritionLogService.get_daily_totals() and
                  // app.core.micronutrients. Not-yet-logged
                  // nutrients default to 0 via the same ?? fallback
                  // as every other ring on this screen.
                  const consumed = dailyTotals?.micronutrients?.[key] ?? 0;
                  const percent = safePercent(consumed, target.amount);
                  const ringColor = ALL_NUTRIENT_META[key].color;
                  return (
                    <View key={key} style={{ alignItems: 'center', width: '31%' }}>
                      <ProgressRing
                        percent={percent}
                        size={60}
                        strokeWidth={6}
                        color={ringColor}
                        trackColor={colors.border}
                        centerLabel={`${Math.round(percent)}%`}
                      />
                      <Text style={{ fontSize: 10, color: colors.textSecondary, marginTop: 6 }}>
                        {label}
                      </Text>
                      <Text
                        style={{
                          fontSize: 10,
                          color: colors.textPrimary,
                          fontWeight: '600',
                          marginTop: 1,
                          textAlign: 'center',
                        }}
                      >
                        {formatRdaAmount(consumed)}/{formatRdaAmount(target.amount)} {target.unit}
                      </Text>
                      <Text style={{ fontSize: 9, color: colors.textMuted, marginTop: 1 }}>
                        {target.kind === 'limit' ? 'keep under' : 'daily goal'}
                      </Text>
                    </View>
                  );
                })}
              </View>

              {RDA_NUTRIENT_DISPLAY.length > 6 && (
                <Pressable
                  onPress={() => setShowAllRdaNutrients((prev) => !prev)}
                  style={{ marginTop: 12 }}
                >
                  <ThemedText variant="label" style={{ color: colors.accentPeach }}>
                    {showAllRdaNutrients ? '‹ Show less' : `Know more (${RDA_NUTRIENT_DISPLAY.length}) ›`}
                  </ThemedText>
                </Pressable>
              )}

              <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 14, textAlign: 'center' }}>
                {rdaTargets.disclaimer}
              </Text>
            </ThemedCard>
          )}

          {/* Nutrients to Watch — replaces the old static "Color guide"
              legend. Shows ONLY markers flagged above/below range in
              the user's last CONFIRMED health report, not a generic
              legend of every tracked nutrient. Icon/color is a
              best-effort match against this app's own nutrient set
              (findNutrientMeta) — most lab markers won't match, and
              fall back to a generic icon rather than a fabricated one.
              Severity pill (Very High/High/Low/Very Low) reuses the
              same >15%-deviation threshold as the Health Insights
              screen — see getMarkerSeverity() in
              src/utils/healthMarkerSeverity.ts. */}
          <ThemedCard
            style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', borderRadius: 12, padding: 16, marginBottom: 20 }}
          >
            <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 2 }}>
              Health Insights
            </ThemedText>
            <ThemedText variant="caption" color="textMuted" style={{ marginBottom: 14 }}>
              As per your last uploaded Health Report
            </ThemedText>

            {!latestHealthReport ? (
              <ThemedText variant="bodySmall" color="textSecondary" style={{ lineHeight: 16 }}>
                Upload and confirm a health report to see which nutrients need attention.
              </ThemedText>
            ) : flaggedMarkers.length === 0 ? (
              <ThemedText variant="bodySmall" color="textSecondary" style={{ lineHeight: 16 }}>
                Nothing flagged — every marker in your last report was within its reference range.
              </ThemedText>
            ) : (
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
                {(showAllFlaggedMarkers ? flaggedMarkers : flaggedMarkers.slice(0, 6)).map((marker, i) => {
                  const meta = findNutrientMeta(marker.name);
                  const display = flaggedMarkerDisplay(marker, colors);
                  return (
                    <View
                      key={`${marker.name}-${i}`}
                      style={{
                        width: '47%',
                        backgroundColor: colors.screenBg,
                        borderWidth: 1,
                        borderColor: colors.border,
                        borderRadius: 10,
                        padding: 10,
                      }}
                    >
                      <View
                        style={{
                          flexDirection: 'row',
                          justifyContent: 'space-between',
                          alignItems: 'flex-start',
                          marginBottom: 8,
                        }}
                      >
                        <View
                          style={{
                            width: 34,
                            height: 34,
                            borderRadius: 17,
                            backgroundColor: meta ? meta.color + '33' : colors.border + '55',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Text style={{ fontSize: 15 }}>{meta ? meta.icon : FALLBACK_ICON}</Text>
                        </View>

                        <View
                          style={{
                            backgroundColor: display.bgColor,
                            borderRadius: 100,
                            paddingHorizontal: 8,
                            paddingVertical: 3,
                            flexDirection: 'row',
                            alignItems: 'center',
                            gap: 2,
                          }}
                        >
                          <Text style={{ fontSize: 10, fontWeight: '700', color: display.textColor }}>
                            {display.label}
                          </Text>
                          <Text style={{ fontSize: 10, fontWeight: '700', color: display.textColor }}>
                            {display.arrow}
                          </Text>
                        </View>
                      </View>

                      <ThemedText variant="label" color="textPrimary" numberOfLines={1}>
                        {marker.name}
                      </ThemedText>
                      {marker.reference_range_text ? (
                        <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 1 }} numberOfLines={2}>
                          Reference: {marker.reference_range_text}
                        </Text>
                      ) : marker.unit ? (
                        <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 1 }}>
                          {marker.value} {marker.unit}
                        </Text>
                      ) : null}
                    </View>
                  );
                })}
              </View>
            )}
            {flaggedMarkers.length > 6 && (
              <Pressable
                onPress={() => setShowAllFlaggedMarkers((prev) => !prev)}
                style={{ marginTop: 12 }}
              >
                <ThemedText variant="label" style={{ color: colors.accentPeach }}>
                  {showAllFlaggedMarkers ? '‹ Show less' : `Know more (${flaggedMarkers.length}) ›`}
                </ThemedText>
              </Pressable>
            )}
          </ThemedCard>
        </>
      )}
    </ScrollView>
  );
}
