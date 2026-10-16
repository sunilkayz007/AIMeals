import { useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView, Modal, Image } from 'react-native';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import {
  analyzeFoodImage,
  resolveFoodImageAmbiguity,
  logFoodImageAsMeal,
  FOOD_IMAGE_STAGE_ORDER,
  FOOD_IMAGE_STAGE_LABELS,
  getRecentFoodImages,
} from '../../../src/api/aiFoodImage';
import type { FoodImage, FoodImageAnalysisStage, FoodItem } from '../../../src/api/aiFoodImage';
import type { MealType } from '../../../src/types/nutritionLog';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS, CARD_SHADOW } from '../../../src/theme/layout';
import { formatLitersFromMl } from '../../../src/utils/recipeText';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import ProgressRing from '../../../src/components/ProgressRing';
import ThemedCard from '../../../src/components/ThemedCard';
import { nutritionLogApi } from '../../../src/api/nutritionLog';
import { profileApi } from '../../../src/api/profile';
import { waterApi } from '../../../src/api/water';
import type { WaterDaySummary } from '../../../src/api/water';
import { dailyTipApi } from '../../../src/api/dailyTip';

const ERROR_MESSAGES: Record<string, string> = {
  InsufficientCreditsError:
    "You're out of credits for this billing period. Upgrade your plan to keep scanning.",
  InappropriateImageError:
    "This doesn't look like a food photo — try again with a clear picture of your meal.",
  UnsupportedImageFormatError:
    "This photo format isn't supported (this usually happens with HEIC photos on iPhone). Try retaking the photo, or turn off \"High Efficiency\" in Settings > Camera > Formats.",
};

const MEAL_TYPES: { value: MealType; label: string }[] = [
  { value: 'breakfast' as MealType, label: 'Breakfast' },
  { value: 'lunch' as MealType, label: 'Lunch' },
  { value: 'dinner' as MealType, label: 'Dinner' },
  { value: 'snack' as MealType, label: 'Snack' },
];

// Lightweight keyword heuristic for a per-food icon — purely
// cosmetic, never affects data. Falls back to a generic plate
// for anything unmatched rather than guessing wrong.
// Local calendar date (YYYY-MM-DD), NOT toISOString()-based — matches
// home.tsx's own todayString() and the same reasoning documented
// there (toISOString() disagrees with the backend's local-timezone
// date.today() for part of every day in any timezone ahead of UTC).
function todayString(): string {
  const d = new Date();
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
}

// "Scanned today, 1:15 PM" / "Scanned Sep 3, 1:15 PM" — absolute,
// matching the reference design, rather than a relative "2h ago".
function formatScanTimestamp(isoString: string): string {
  const d = new Date(isoString);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const hours24 = d.getHours();
  const minutes = d.getMinutes().toString().padStart(2, '0');
  const period = hours24 >= 12 ? 'PM' : 'AM';
  const hours12 = hours24 % 12 === 0 ? 12 : hours24 % 12;
  const time = `${hours12}:${minutes} ${period}`;
  const day = isToday ? 'today' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `Scanned ${day}, ${time}`;
}

function getFoodEmoji(name: string): string {
  const n = name.toLowerCase();
  if (/paneer|tofu|cheese/.test(n)) return '🥘';
  if (/chicken|meat|mutton|fish|egg/.test(n)) return '🍗';
  if (/broccoli|spinach|salad|greens|vegetable/.test(n)) return '🥦';
  if (/pepper|capsicum/.test(n)) return '🫑';
  if (/rice|biryani/.test(n)) return '🍚';
  if (/bread|roti|naan|chapati/.test(n)) return '🫓';
  if (/dal|lentil|curry|gravy/.test(n)) return '🍛';
  if (/fruit|apple|banana|orange/.test(n)) return '🍎';
  return '🍽️';
}

type ScreenState = 'picking' | 'analyzing' | 'reviewing' | 'error' | 'empty' | 'logged';
type LogSheetState = 'idle' | 'logging' | 'error';

export default function ScanFood() {
  const router = useRouter();
  const { colors } = useTheme();

  const [state, setState] = useState<ScreenState>('picking');
  const [showPickerSheet, setShowPickerSheet] = useState(false);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<FoodImageAnalysisStage | null>(null);
  // Live "Found <food name>" text while stage === 'analyzing_image' —
  // same live-detail pattern as health-insights/index.tsx's currentDetail.
  const [currentDetail, setCurrentDetail] = useState<string | null>(null);
  const [uploadPercent, setUploadPercent] = useState<number | null>(null);
  const [hasRealUploadProgress, setHasRealUploadProgress] = useState(false);
  const [result, setResult] = useState<FoodImage | null>(null);
  const [error, setError] = useState<string | null>(null);

  // item_index -> chosen label, for items with alternatives
  const [selectedLabels, setSelectedLabels] = useState<Record<number, string>>({});

  // Log sheet
  const [showLogSheet, setShowLogSheet] = useState(false);
  const [mealType, setMealType] = useState<MealType>('lunch' as MealType);
  const [portionPercent, setPortionPercent] = useState(100);
  const [notes, setNotes] = useState('');
  const [logSheetState, setLogSheetState] = useState<LogSheetState>('idle');
  const [logSheetError, setLogSheetError] = useState<string | null>(null);

  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  // Dashboard section shown on the initial (pre-photo) screen, so
  // that space isn't empty while waiting for a tap: today's ring
  // progress (meals/water/protein), the same daily tip Home shows,
  // the most recent scan, and a "meals remaining" nudge. Every piece
  // loads independently (Promise.allSettled, not .all) and fails
  // silently — this is a secondary dashboard, not core scan
  // functionality, so one failed fetch should never block the rest
  // or show an error state.
  const DAILY_MEAL_TARGET = 3; // no such setting exists yet server-side; a fixed default, easy to make configurable later

  const [dailyTotals, setDailyTotals] = useState<{ entry_count: number; protein_g: number } | null>(null);
  const [proteinTarget, setProteinTarget] = useState<number | null>(null);
  const [waterSummary, setWaterSummary] = useState<WaterDaySummary | null>(null);
  const [dailyTip, setDailyTip] = useState<string | null>(null);
  const [lastScan, setLastScan] = useState<FoodImage | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.allSettled([
      nutritionLogApi.getDailyTotals(todayString()),
      profileApi.getFull(),
      waterApi.getDaySummary(todayString()),
      dailyTipApi.get(),
      getRecentFoodImages(1),
    ]).then(([totalsR, profileR, waterR, tipR, scansR]) => {
      if (cancelled) return;
      if (totalsR.status === 'fulfilled') setDailyTotals(totalsR.value);
      if (profileR.status === 'fulfilled') setProteinTarget(profileR.value.profile?.protein_g_target ?? null);
      if (waterR.status === 'fulfilled') setWaterSummary(waterR.value);
      if (tipR.status === 'fulfilled') setDailyTip(tipR.value.tip_text);
      if (scansR.status === 'fulfilled' && scansR.value.length > 0) setLastScan(scansR.value[0]);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const requestAndPick = async (source: 'camera' | 'gallery') => {
    setShowPickerSheet(false);

    if (source === 'camera') {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        setError('Camera permission is needed to take a photo.');
        return;
      }
      const pickResult = await ImagePicker.launchCameraAsync({ quality: 0.7 });
      if (!pickResult.canceled && pickResult.assets[0]) {
        const asset = pickResult.assets[0];
        const mimeType = resolveImageMimeType(asset.uri, asset.mimeType);
        startAnalysis(asset.uri, mimeType, fileNameForMimeType(mimeType));
      }
    } else {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        setError('Photo library permission is needed to choose an image.');
        return;
      }
      const pickResult = await ImagePicker.launchImageLibraryAsync({
        quality: 0.7,
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
      });
      if (!pickResult.canceled && pickResult.assets[0]) {
        const asset = pickResult.assets[0];
        const mimeType = resolveImageMimeType(asset.uri, asset.mimeType);
        startAnalysis(asset.uri, mimeType, fileNameForMimeType(mimeType));
      }
    }
  };

  const startAnalysis = (uri: string, mimeType: string, fileName: string) => {
    setImageUri(uri);
    setState('analyzing');
    setCurrentStage(null);
    setCurrentDetail(null);
    setUploadPercent(0);
    setHasRealUploadProgress(false);
    setError(null);
    setResult(null);
    setSelectedLabels({});
    setPortionPercent(100);

    abortRef.current = analyzeFoodImage(uri, mimeType, fileName, {
      onUploadProgress: (percent) => {
        setHasRealUploadProgress(true);
        setUploadPercent(percent);
      },
      onStage: (stage, detail) => {
        setUploadPercent(100);
        setCurrentStage(stage as FoodImageAnalysisStage);
        setCurrentDetail(detail ?? null);
      },
      onResult: (image) => {
        setResult(image);
        setCurrentStage(null);
        setCurrentDetail(null);

        if (image.detected_foods.length === 0) {
          setState('empty');
          return;
        }

        const initialSelections: Record<number, string> = {};
        image.detected_foods.forEach((item, i) => {
          if (item.alternatives.length > 0) initialSelections[i] = item.name;
        });
        setSelectedLabels(initialSelections);
        setState('reviewing');
      },
      onError: (errorType, detail) => {
        setCurrentStage(null);
        setCurrentDetail(null);
        setError(ERROR_MESSAGES[errorType] ?? detail);
        setState('error');
      },
    });
  };

  const handleOpenLogSheet = () => {
    setLogSheetError(null);
    setLogSheetState('idle');
    setShowLogSheet(true);
  };

  const handleConfirmAndLog = async () => {
    if (!result) return;
    setLogSheetState('logging');
    setLogSheetError(null);

    try {
      let finalResult = result;

      const ambiguousIndices = result.detected_foods
        .map((item, i) => (item.alternatives.length > 0 ? i : -1))
        .filter((i) => i !== -1);

      if (ambiguousIndices.length > 0) {
        finalResult = await resolveFoodImageAmbiguity(
          result.id,
          ambiguousIndices.map((i) => ({ item_index: i, chosen_label: selectedLabels[i] }))
        );
        setResult(finalResult);
      }

      await logFoodImageAsMeal(finalResult.id, mealType, portionPercent, notes.trim() || undefined);

      setShowLogSheet(false);
      setState('logged');
    } catch (err) {
      setLogSheetError(err instanceof Error ? err.message : 'Failed to log — please try again');
      setLogSheetState('error');
    }
  };

  const handleStartOver = () => {
    setState('picking');
    setImageUri(null);
    setResult(null);
    setError(null);
    setSelectedLabels({});
    setNotes('');
    setPortionPercent(100);
  };

  // ---------------------------------------------------
  // Picking / Analyzing
  // ---------------------------------------------------

  if (state === 'picking' || state === 'analyzing') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
        <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, flexGrow: 1 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 20 }}>
            <Pressable onPress={() => router.back()}>
              <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
            </Pressable>
          </View>

          <Text style={{ fontSize: 22, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
            Food Scan 📷
          </Text>
          <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 24 }}>
            Take or choose a photo of your meal — AIMeals will identify what's on your plate.
          </Text>

          {imageUri && (
            <Image
              source={{ uri: imageUri }}
              style={{ width: '100%', height: 240, borderRadius: RADIUS.card, marginBottom: 20 }}
              resizeMode="cover"
            />
          )}

          {state === 'analyzing' ? (
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent' }} padding={18}>
              <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: currentDetail ? 4 : 14 }}>
                ✨ Analyzing your meal…
              </Text>
              {currentDetail && (
                <Text
                  style={{ fontSize: 12, color: colors.primary, marginBottom: 10, fontStyle: 'italic' }}
                  numberOfLines={1}
                >
                  {currentDetail}
                </Text>
              )}
              {uploadPercent !== null && uploadPercent < 100 ? (
                hasRealUploadProgress ? (
                  <View>
                    <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 8 }}>
                      Uploading photo… {uploadPercent}%
                    </Text>
                    <View style={{ height: 6, borderRadius: 3, backgroundColor: colors.border, overflow: 'hidden' }}>
                      <View style={{ height: '100%', width: `${uploadPercent}%`, backgroundColor: colors.primary, borderRadius: 3 }} />
                    </View>
                  </View>
                ) : (
                  <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    <ActivityIndicator size="small" color={colors.primary} style={{ marginRight: 8 }} />
                    <Text style={{ fontSize: 13, color: colors.textSecondary }}>Uploading photo…</Text>
                  </View>
                )
              ) : (
                FOOD_IMAGE_STAGE_ORDER.map((stage) => {
                  const currentIndex = currentStage ? FOOD_IMAGE_STAGE_ORDER.indexOf(currentStage) : -1;
                  const thisIndex = FOOD_IMAGE_STAGE_ORDER.indexOf(stage);
                  const isDone = thisIndex < currentIndex;
                  const isActive = stage === currentStage;
                  return (
                    <View key={stage} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                      <Text style={{ width: 18, fontSize: 12 }}>{isDone ? '✓' : isActive ? '' : '○'}</Text>
                      {isActive && <ActivityIndicator size="small" color={colors.primary} style={{ marginRight: 6 }} />}
                      <Text
                        style={{
                          fontSize: 13,
                          color: isDone || isActive ? colors.textPrimary : colors.textMuted,
                          fontWeight: isActive ? '600' : '400',
                        }}
                      >
                        {FOOD_IMAGE_STAGE_LABELS[stage]}
                      </Text>
                    </View>
                  );
                })
              )}
            </ThemedCard>
          ) : (
            <Pressable
              onPress={() => setShowPickerSheet(true)}
              style={{
                backgroundColor: colors.primary,
                borderRadius: RADIUS.button,
                paddingVertical: 16,
                alignItems: 'center',
                ...CARD_SHADOW,
              }}
            >
              <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>📷 Scan a meal</Text>
            </Pressable>
          )}

          {state === 'picking' && (dailyTotals || waterSummary) && (
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', marginTop: 28, marginBottom: 16 }} padding={16}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary }}>Today's progress</Text>
                <Pressable onPress={() => router.push('/(main)/home')}>
                  <Text style={{ fontSize: 12, color: colors.primary, fontWeight: '600' }}>View all ›</Text>
                </Pressable>
              </View>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <View style={{ alignItems: 'center', width: '31%' }}>
                  <ProgressRing
                    percent={Math.min(100, ((dailyTotals?.entry_count ?? 0) / DAILY_MEAL_TARGET) * 100)}
                    size={64}
                    strokeWidth={6}
                    color={colors.primary}
                    trackColor={colors.border}
                    centerLabel={`${dailyTotals?.entry_count ?? 0}/${DAILY_MEAL_TARGET}`}
                  />
                  <Text style={{ fontSize: 11, fontWeight: '600', color: colors.textPrimary, marginTop: 6 }}>Meals</Text>
                  <Text style={{ fontSize: 10, color: colors.textSecondary }}>logged</Text>
                </View>
                <View style={{ alignItems: 'center', width: '31%' }}>
                  <ProgressRing
                    percent={waterSummary?.target_ml ? Math.min(100, (waterSummary.total_ml / waterSummary.target_ml) * 100) : 0}
                    size={64}
                    strokeWidth={6}
                    color={colors.accentPeach}
                    trackColor={colors.border}
                    centerLabel={
                      waterSummary?.target_ml
                        ? `${formatLitersFromMl(waterSummary.total_ml)}/${formatLitersFromMl(waterSummary.target_ml)}L`
                        : '--'
                    }
                  />
                  <Text style={{ fontSize: 11, fontWeight: '600', color: colors.textPrimary, marginTop: 6 }}>Water</Text>
                  <Text style={{ fontSize: 10, color: colors.textSecondary }}>today</Text>
                </View>
                <View style={{ alignItems: 'center', width: '31%' }}>
                  <ProgressRing
                    percent={proteinTarget ? Math.min(100, ((dailyTotals?.protein_g ?? 0) / proteinTarget) * 100) : 0}
                    size={64}
                    strokeWidth={6}
                    color={colors.accentLavender}
                    trackColor={colors.border}
                    centerLabel={proteinTarget ? `${Math.round(((dailyTotals?.protein_g ?? 0) / proteinTarget) * 100)}%` : '--'}
                  />
                  <Text style={{ fontSize: 11, fontWeight: '600', color: colors.textPrimary, marginTop: 6 }}>Protein</Text>
                  <Text style={{ fontSize: 10, color: colors.textSecondary }}>of daily target</Text>
                </View>
              </View>
            </ThemedCard>
          )}

          {state === 'picking' && dailyTip && (
            <ThemedCard style={{ flexDirection: 'row', backgroundColor: colors.surfaceAlt, borderColor: 'transparent', marginBottom: 16 }} padding={16}>
              <Text style={{ fontSize: 18, marginRight: 10 }}>💡</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>AIMeals insight</Text>
                <Text style={{ fontSize: 12, color: colors.textSecondary, lineHeight: 17, marginBottom: 8 }}>{dailyTip}</Text>
                <Pressable onPress={() => router.push('/(main)/health-insights')}>
                  <Text style={{ fontSize: 12, color: colors.primary, fontWeight: '600' }}>View nutrition insights →</Text>
                </Pressable>
              </View>
            </ThemedCard>
          )}

          {state === 'picking' && lastScan && (() => {
            const names = lastScan.detected_foods.map((f) => f.name);
            const label =
              names.length > 2
                ? `${names.slice(0, 2).join(', ')} +${names.length - 2} more`
                : names.join(', ') || 'Scan';
            const emoji = getFoodEmoji(names[0] ?? '');
            return (
              <ThemedCard style={{ borderColor: colors.border, marginBottom: 16 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    <Text style={{ fontSize: 14, marginRight: 6 }}>🕛</Text>
                    <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }}>Last scanned meal</Text>
                  </View>
                  <Pressable onPress={() => router.push('/(main)/history')}>
                    <Text style={{ fontSize: 12, color: colors.primary, fontWeight: '600' }}>View history</Text>
                  </Pressable>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <View
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 10,
                      backgroundColor: colors.surfaceAlt,
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginRight: 12,
                    }}
                  >
                    <Text style={{ fontSize: 22 }}>{emoji}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }} numberOfLines={1}>
                      {label}
                    </Text>
                    <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>
                      {lastScan.total_calories != null ? `${Math.round(lastScan.total_calories)} kcal` : ''}
                      {lastScan.total_protein_g != null ? ` · ${Math.round(lastScan.total_protein_g)}g protein` : ''}
                    </Text>
                    <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 2 }}>
                      {formatScanTimestamp(lastScan.uploaded_at)}
                    </Text>
                  </View>
                </View>
              </ThemedCard>
            );
          })()}

          {state === 'picking' && dailyTotals && dailyTotals.entry_count < DAILY_MEAL_TARGET && (
            <ThemedCard style={{ backgroundColor: colors.accentPeach + '22', borderColor: 'transparent', marginBottom: 12 }} padding={16}>
              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                <Text style={{ fontSize: 16, marginRight: 8 }}>🎯</Text>
                <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }}>Today's goal</Text>
              </View>
              <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 12 }}>
                Scan {DAILY_MEAL_TARGET - dailyTotals.entry_count} more meal
                {DAILY_MEAL_TARGET - dailyTotals.entry_count === 1 ? '' : 's'} to complete your daily food diary.
              </Text>
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <View style={{ flex: 1, height: 6, borderRadius: 3, backgroundColor: colors.border, overflow: 'hidden', marginRight: 10 }}>
                  <View
                    style={{
                      height: '100%',
                      width: `${Math.min(100, (dailyTotals.entry_count / DAILY_MEAL_TARGET) * 100)}%`,
                      backgroundColor: colors.primary,
                      borderRadius: 3,
                    }}
                  />
                </View>
                <Text style={{ fontSize: 11, fontWeight: '700', color: colors.textPrimary }}>
                  {dailyTotals.entry_count} / {DAILY_MEAL_TARGET}
                </Text>
              </View>
            </ThemedCard>
          )}
        </ScrollView>

        <Modal visible={showPickerSheet} transparent animationType="fade" onRequestClose={() => setShowPickerSheet(false)}>
          <Pressable
            onPress={() => setShowPickerSheet(false)}
            style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' }}
          >
            <Pressable
              onPress={(e) => e.stopPropagation()}
              style={{
                backgroundColor: colors.cardBg,
                borderTopLeftRadius: RADIUS.card,
                borderTopRightRadius: RADIUS.card,
                padding: 20,
                paddingBottom: 36,
              }}
            >
              <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 16, textAlign: 'center' }}>
                Scan a meal
              </Text>
              <Pressable
                onPress={() => requestAndPick('camera')}
                style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 14, alignItems: 'center', marginBottom: 10 }}
              >
                <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Take Photo</Text>
              </Pressable>
              <Pressable
                onPress={() => requestAndPick('gallery')}
                style={{ borderWidth: 1, borderColor: colors.cardBorder, borderRadius: RADIUS.button, paddingVertical: 14, alignItems: 'center' }}
              >
                <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: 14 }}>Choose from Gallery</Text>
              </Pressable>
            </Pressable>
          </Pressable>
        </Modal>

        <ModuleNavBar currentKey="scan" />
      </View>
    );
  }

  // ---------------------------------------------------
  // Error state (analysis itself failed)
  // ---------------------------------------------------

  if (state === 'error') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Text style={{ fontSize: 36, marginBottom: 12 }}>😕</Text>
        <Text style={{ fontSize: 17, fontWeight: '700', color: colors.textPrimary, marginBottom: 6, textAlign: 'center' }}>
          Couldn't analyze this meal
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 24, textAlign: 'center' }}>
          {error ?? 'Something went wrong while analyzing your photo.'}
        </Text>
        <Pressable
          onPress={handleStartOver}
          style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 12, paddingHorizontal: 28 }}
        >
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Try Again</Text>
        </Pressable>
      </View>
    );
  }

  // ---------------------------------------------------
  // Empty state (zero foods detected)
  // ---------------------------------------------------

  if (state === 'empty') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Text style={{ fontSize: 36, marginBottom: 12 }}>🔍</Text>
        <Text style={{ fontSize: 17, fontWeight: '700', color: colors.textPrimary, marginBottom: 24, textAlign: 'center' }}>
          Couldn't confidently identify any food.
        </Text>
        <Pressable
          onPress={handleStartOver}
          style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 12, paddingHorizontal: 24 }}
        >
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Try Another Photo</Text>
        </Pressable>
      </View>
    );
  }

  // ---------------------------------------------------
  // Logged success state
  // ---------------------------------------------------

  if (state === 'logged') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center', padding: 20 }}>
        <Text style={{ fontSize: 40, marginBottom: 12 }}>✅</Text>
        <Text style={{ fontSize: 17, fontWeight: '700', color: colors.textPrimary, marginBottom: 4, textAlign: 'center' }}>
          Meal Logged
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 24, textAlign: 'center' }}>
          Your Home totals — and water, if this meal contributed any — have already been updated.
        </Text>
        <Pressable
          // dismissTo pops back to the Home already on the stack instead of
          // pushing a second Home on top of this finished flow (which made
          // Back on Home re-open this "Meal Logged" screen).
          onPress={() => router.dismissTo('/(main)/home')}
          style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 12, paddingHorizontal: 24 }}
        >
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Back to Home</Text>
        </Pressable>
      </View>
    );
  }

  // ---------------------------------------------------
  // Reviewing — the main redesigned screen
  // ---------------------------------------------------

  if (!result) return null;

  const portionScale = portionPercent / 100;
  const scaledCalories = (result.total_calories ?? 0) * portionScale;
  const scaledProtein = (result.total_protein_g ?? 0) * portionScale;
  const scaledCarbs = (result.total_carbs_g ?? 0) * portionScale;
  const scaledFat = (result.total_fat_g ?? 0) * portionScale;
  const foodCount = result.detected_foods.length;
  const hasAmbiguous = result.detected_foods.some((item) => item.alternatives.length > 0);

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 110 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Pressable onPress={handleStartOver}>
            <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
          </Pressable>
          <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary }}>Food Scan</Text>
          <Pressable onPress={handleStartOver}>
            <Text style={{ fontSize: 16, color: colors.textSecondary }}>⋮</Text>
          </Pressable>
        </View>

        {/* Hero image */}
        {imageUri && (
          <Image
            source={{ uri: imageUri }}
            style={{ width: '100%', height: 240, borderRadius: RADIUS.card, marginBottom: 10 }}
            resizeMode="cover"
          />
        )}
        <Text style={{ fontSize: 13, fontWeight: '600', color: colors.primaryDark, marginBottom: 20 }}>
          ✨ {foodCount} food{foodCount === 1 ? '' : 's'} detected
        </Text>

        {/* AI result header */}
        <Text style={{ fontSize: 19, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
          Your meal is ready to review
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
          AIMeals found {foodCount} food{foodCount === 1 ? '' : 's'} in your photo.
        </Text>

        {/* Meal estimate card */}
        <ThemedCard style={{ alignItems: 'center', marginBottom: 24 }} padding={20}>
          <Text style={{ fontSize: 11, fontWeight: '700', color: colors.textSecondary, letterSpacing: 0.6, marginBottom: 6 }}>
            MEAL ESTIMATE
          </Text>
          <Text style={{ fontSize: 34, fontWeight: '800', color: colors.textPrimary, marginBottom: 16 }}>
            {Math.round(scaledCalories)}
            <Text style={{ fontSize: 16, fontWeight: '600', color: colors.textSecondary }}> kcal</Text>
          </Text>
          <View style={{ flexDirection: 'row', gap: 28 }}>
            <MacroValue label="Protein" value={`${Math.round(scaledProtein)}g`} color={colors.ringProtein ?? colors.accentSage} />
            <MacroValue label="Carbs" value={`${Math.round(scaledCarbs)}g`} color={colors.ringCarbs ?? colors.accentBlue} />
            <MacroValue label="Fat" value={`${Math.round(scaledFat)}g`} color={colors.ringFat ?? colors.accentGold} />
          </View>
        </ThemedCard>

        {/* Portion control — real backend-supported whole-meal scaling */}
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary }}>PORTION</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
            <Pressable
              onPress={() => setPortionPercent((p) => Math.max(25, p - 25))}
              style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}
            >
              <Text style={{ fontSize: 16, fontWeight: '700', color: colors.textPrimary }}>−</Text>
            </Pressable>
            <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, minWidth: 46, textAlign: 'center' }}>
              {portionPercent}%
            </Text>
            <Pressable
              onPress={() => setPortionPercent((p) => Math.min(200, p + 25))}
              style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}
            >
              <Text style={{ fontSize: 16, fontWeight: '700', color: colors.textPrimary }}>+</Text>
            </Pressable>
          </View>
        </View>

        {/* Detected foods */}
        <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 2 }}>
          What AIMeals found
        </Text>
        <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 14 }}>
          {foodCount} food{foodCount === 1 ? '' : 's'} detected
        </Text>

        <View style={{ gap: 10 }}>
          {result.detected_foods.map((item, i) => (
            <FoodCard
              key={i}
              item={item}
              displayName={item.alternatives.length > 0 ? selectedLabels[i] ?? item.name : item.name}
              isAmbiguous={item.alternatives.length > 0}
              selectedLabel={selectedLabels[i] ?? item.name}
              onSelect={(label) => setSelectedLabels((prev) => ({ ...prev, [i]: label }))}
              colors={colors}
            />
          ))}
        </View>
      </ScrollView>

      {/* Sticky bottom action */}
      <View
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: colors.pageBg,
          borderTopWidth: 1,
          borderTopColor: colors.border,
          padding: 16,
          paddingBottom: 24,
        }}
      >
        <Text style={{ fontSize: 11, color: colors.textSecondary, textAlign: 'center', marginBottom: 8 }}>
          {foodCount} food{foodCount === 1 ? '' : 's'} • {Math.round(scaledCalories)} kcal
        </Text>
        <Pressable
          onPress={handleOpenLogSheet}
          style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 15, alignItems: 'center', ...CARD_SHADOW }}
        >
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>Log This Meal</Text>
        </Pressable>
      </View>

      {/* Log sheet */}
      <Modal visible={showLogSheet} transparent animationType="fade" onRequestClose={() => setShowLogSheet(false)}>
        <Pressable
          onPress={() => logSheetState !== 'logging' && setShowLogSheet(false)}
          style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' }}
        >
          <Pressable
            onPress={(e) => e.stopPropagation()}
            style={{ backgroundColor: colors.cardBg, borderTopLeftRadius: RADIUS.card, borderTopRightRadius: RADIUS.card, padding: 20, paddingBottom: 36 }}
          >
            <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 16 }}>
              Log this meal as
            </Text>

            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
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
                      backgroundColor: isSelected ? colors.primary : colors.surfaceAlt,
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

            <TextInput
              placeholder="Notes (optional)"
              placeholderTextColor={colors.textMuted}
              value={notes}
              onChangeText={setNotes}
              editable={logSheetState !== 'logging'}
              style={{
                borderWidth: 1,
                borderColor: colors.border,
                borderRadius: 12,
                paddingHorizontal: 14,
                paddingVertical: 12,
                fontSize: 14,
                color: colors.textPrimary,
                backgroundColor: colors.surfaceAlt,
                marginBottom: 16,
              }}
            />

            {logSheetError && (
              <ThemedCard style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', marginBottom: 14 }} padding={12}>
                <Text style={{ color: colors.danger, fontSize: 12 }}>{logSheetError}</Text>
              </ThemedCard>
            )}

            <Pressable
              onPress={handleConfirmAndLog}
              disabled={logSheetState === 'logging'}
              style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 15, alignItems: 'center' }}
            >
              {logSheetState === 'logging' ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>
                  {logSheetState === 'error' ? 'Try Again' : hasAmbiguous ? 'Confirm & Log' : 'Confirm'}
                </Text>
              )}
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

// ---------------------------------------------------
// Sub-components
// ---------------------------------------------------

function MacroValue({ label, value, color }: { label: string; value: string; color: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ alignItems: 'center' }}>
      <Text style={{ fontSize: 15, fontWeight: '700', color }}>{value}</Text>
      <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 2 }}>{label}</Text>
    </View>
  );
}

function FoodCard({
  item,
  displayName,
  isAmbiguous,
  selectedLabel,
  onSelect,
  colors,
}: {
  item: FoodItem;
  displayName: string;
  isAmbiguous: boolean;
  selectedLabel: string;
  onSelect: (label: string) => void;
  colors: any;
}) {
  // Real confidence tiers from real backend data — no invented
  // percentages. Ambiguous (has alternatives) = low confidence,
  // gets the full AI-verification treatment. Otherwise, only a
  // subtle "AI estimate" tag for genuinely medium confidence;
  // high confidence shows no indicator at all.
  const isMediumConfidence = !isAmbiguous && item.confidence != null && item.confidence < 0.95;

  if (isAmbiguous) {
    const options = [{ name: item.name }, ...item.alternatives];
    return (
      <ThemedCard style={{ backgroundColor: colors.warningBg, borderColor: 'transparent' }} padding={16}>
        <Text style={{ fontSize: 12, fontWeight: '700', color: colors.warningText, marginBottom: 6 }}>
          ✨ AI NEEDS YOUR HELP
        </Text>
        <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary, marginBottom: 12 }}>
          Is this {item.name.toLowerCase()}?
        </Text>
        <View style={{ gap: 8 }}>
          {options.map((opt) => {
            const isSelected = selectedLabel === opt.name;
            return (
              <Pressable
                key={opt.name}
                onPress={() => onSelect(opt.name)}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  backgroundColor: isSelected ? colors.cardBg : 'transparent',
                  borderWidth: 1,
                  borderColor: isSelected ? colors.primary : colors.cardBorder,
                  borderRadius: RADIUS.button,
                  paddingVertical: 10,
                  paddingHorizontal: 14,
                }}
              >
                {isSelected && <Text style={{ marginRight: 6, color: colors.primary }}>✓</Text>}
                <Text style={{ fontSize: 13, fontWeight: '600', color: colors.textPrimary }}>{opt.name}</Text>
              </Pressable>
            );
          })}
        </View>
      </ThemedCard>
    );
  }

  return (
    <ThemedCard style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 14 }}>
      <Text style={{ fontSize: 22, marginRight: 12 }}>{getFoodEmoji(item.name)}</Text>
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary }}>{displayName}</Text>
          {isMediumConfidence && (
            <Text style={{ fontSize: 10, color: colors.textMuted, fontStyle: 'italic' }}>AI estimate</Text>
          )}
        </View>
        <Text style={{ fontSize: 12, color: colors.textSecondary, marginTop: 2 }}>
          {item.calories != null ? `${Math.round(item.calories)} kcal` : ''}
          {item.calories != null && item.protein_g != null ? ' • ' : ''}
          {item.protein_g != null ? `${Math.round(item.protein_g)}g protein` : ''}
        </Text>
      </View>
    </ThemedCard>
  );
}

// ---------------------------------------------------
// Helpers
// ---------------------------------------------------

function resolveImageMimeType(uri: string, assetMimeType?: string | null): string {
  if (assetMimeType) return assetMimeType;
  const lower = uri.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.heic')) return 'image/heic';
  if (lower.endsWith('.webp')) return 'image/webp';
  return 'image/jpeg';
}

function fileNameForMimeType(mimeType: string): string {
  const ext = mimeType.split('/')[1] ?? 'jpg';
  return `photo.${ext}`;
}
