import { useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView, Modal, Image } from 'react-native';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import {
  identifyIngredients,
  generateRecipeFromScan,
  INGREDIENT_SCAN_STAGE_ORDER,
  INGREDIENT_SCAN_STAGE_LABELS,
  RECIPE_FROM_SCAN_STAGE_ORDER,
  RECIPE_FROM_SCAN_STAGE_LABELS,
} from '../../../src/api/aiIngredientScan';
import type {
  IngredientScan,
  IngredientScanStage,
  RecipeFromScanStage,
  GeneratedRecipeFromScan,
  ScanAllergenWarning,
} from '../../../src/api/aiIngredientScan';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS, CARD_SHADOW } from '../../../src/theme/layout';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import ThemedCard from '../../../src/components/ThemedCard';
import { dailyTipApi } from '../../../src/api/dailyTip';
import { pantryApi } from '../../../src/api/pantry';
import { recipeApi } from '../../../src/api/recipe';
import type { PantryItem } from '../../../src/types/pantry';
import type { Recipe } from '../../../src/types/recipe';

const ERROR_MESSAGES: Record<string, string> = {
  InsufficientCreditsError:
    "You're out of credits for this billing period. Upgrade your plan to keep scanning.",
  UnsupportedImageFormatError:
    "This photo format isn't supported (this usually happens with HEIC photos on iPhone). Try retaking the photo, or turn off \"High Efficiency\" in Settings > Camera > Formats.",
};

type ScreenState = 'picking' | 'identifying' | 'reviewing' | 'generating' | 'error';

// Lightweight keyword heuristic for a per-ingredient icon — purely
// cosmetic (no ingredient photos are stored server-side), mirrors
// scan/index.tsx's getFoodEmoji() but tuned for raw produce/pantry
// items rather than prepared dishes.
function getIngredientEmoji(name: string): string {
  const n = name.toLowerCase();
  if (/tomato/.test(n)) return '\u{1F345}';
  if (/onion|shallot/.test(n)) return '\u{1F9C5}';
  if (/garlic/.test(n)) return '\u{1F9C4}';
  if (/chilli|chili|pepper|capsicum/.test(n)) return '\u{1F336}\uFE0F';
  if (/spinach|greens|kale|lettuce/.test(n)) return '\u{1F96C}';
  if (/carrot/.test(n)) return '\u{1F955}';
  if (/potato/.test(n)) return '\u{1F954}';
  if (/egg/.test(n)) return '\u{1F95A}';
  if (/chicken|meat|mutton|fish/.test(n)) return '\u{1F357}';
  if (/paneer|cheese|tofu/.test(n)) return '\u{1F9C0}';
  if (/rice|grain/.test(n)) return '\u{1F35A}';
  if (/lemon|lime/.test(n)) return '\u{1F34B}';
  if (/fruit|apple|banana|orange/.test(n)) return '\u{1F34E}';
  return '\u{1F955}';
}

// Local editable representation — flattened from the scan's
// structured ingredients, since corrections are sent back as
// plain name strings (see GenerateRecipeFromScanRequest).
interface EditableIngredient {
  name: string;
  displayMeta: string | null; // e.g. "200g" — display only, not sent back
  alternatives: string[];
}

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

export default function IngredientScanScreen() {
  const router = useRouter();
  const { colors } = useTheme();

  const [state, setState] = useState<ScreenState>('picking');
  const [showPickerSheet, setShowPickerSheet] = useState(false);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<IngredientScanStage | RecipeFromScanStage | null>(null);
  // Live "Found <ingredient name>" text during step 1's
  // 'analyzing_image' stage only — same live-detail pattern as
  // health-insights/index.tsx's currentDetail. Step 2 (recipe
  // generation) never sets this, so it stays null there.
  const [currentDetail, setCurrentDetail] = useState<string | null>(null);
  const [uploadPercent, setUploadPercent] = useState<number | null>(null);
  const [hasRealUploadProgress, setHasRealUploadProgress] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [allergenWarning, setAllergenWarning] = useState<ScanAllergenWarning | null>(null);

  const [scan, setScan] = useState<IngredientScan | null>(null);
  const [ingredientList, setIngredientList] = useState<EditableIngredient[]>([]);
  const [newIngredientText, setNewIngredientText] = useState('');
  const [preferences, setPreferences] = useState('');

  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  // Dashboard section shown on the initial (pre-photo) screen, so
  // that space isn't empty while waiting for a tap: the user's own
  // pantry contents, up to 3 saved-recipe matches against that
  // pantry (a free client-side heuristic — no AI call, no credit
  // cost, since it only compares against recipes/ingredients
  // already fetched), and the same daily tip Home shows. Every
  // piece loads independently (Promise.allSettled) and fails
  // silently — this is a secondary dashboard, not core scan
  // functionality.
  const [pantryItems, setPantryItems] = useState<PantryItem[]>([]);
  const [ownedAndSystemRecipes, setOwnedAndSystemRecipes] = useState<Recipe[]>([]);
  const [dailyTip, setDailyTip] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.allSettled([
      pantryApi.list(),
      recipeApi.mine(),
      recipeApi.system(),
      dailyTipApi.get(),
    ]).then(([pantryR, mineR, systemR, tipR]) => {
      if (cancelled) return;
      if (pantryR.status === 'fulfilled') setPantryItems(pantryR.value);
      const mine = mineR.status === 'fulfilled' ? mineR.value : [];
      const system = systemR.status === 'fulfilled' ? systemR.value : [];
      setOwnedAndSystemRecipes([...mine, ...system]);
      if (tipR.status === 'fulfilled') setDailyTip(tipR.value.tip_text);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  // Ranks saved recipes by how many distinct pantry ingredients they
  // mention (simple case-insensitive substring match against the
  // recipe's freeform ingredients text — not exact parsing, but
  // enough for a "here's an idea" nudge). Recipes with zero matches
  // are dropped; ties keep insertion order (own recipes before
  // system ones).
  const suggestedRecipes = pantryItems.length
    ? ownedAndSystemRecipes
        .map((recipe) => {
          const ingredientsLower = recipe.ingredients.toLowerCase();
          const matchCount = pantryItems.filter((item) =>
            ingredientsLower.includes(item.ingredient_name.toLowerCase())
          ).length;
          return { recipe, matchCount };
        })
        .filter((r) => r.matchCount > 0)
        .sort((a, b) => b.matchCount - a.matchCount)
        .slice(0, 3)
    : [];

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
        startIdentify(asset.uri, mimeType, fileNameForMimeType(mimeType));
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
        startIdentify(asset.uri, mimeType, fileNameForMimeType(mimeType));
      }
    }
  };

  const startIdentify = (uri: string, mimeType: string, fileName: string) => {
    setImageUri(uri);
    setState('identifying');
    setCurrentStage(null);
    setCurrentDetail(null);
    setUploadPercent(0);
    setHasRealUploadProgress(false);
    setError(null);
    setScan(null);

    abortRef.current = identifyIngredients(uri, mimeType, fileName, {
      onUploadProgress: (percent) => {
        setHasRealUploadProgress(true);
        setUploadPercent(percent);
      },
      onStage: (stage, detail) => {
        setUploadPercent(100);
        setCurrentStage(stage);
        setCurrentDetail(detail ?? null);
      },
      onResult: (result) => {
        setScan(result);
        setCurrentStage(null);
        setCurrentDetail(null);
        setIngredientList(
          result.ingredients.map((ing) => ({
            name: ing.name,
            displayMeta: ing.quantity != null ? `${ing.quantity}${ing.unit ? ` ${ing.unit}` : ''}` : null,
            alternatives: ing.alternatives,
          }))
        );
        setState('reviewing');
      },
      onError: (errType, detail) => {
        setCurrentStage(null);
        setCurrentDetail(null);
        setError(ERROR_MESSAGES[errType] ?? detail);
        setErrorType(errType);
        setState('error');
      },
    });
  };

  const handleRemoveIngredient = (index: number) => {
    setIngredientList((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSwitchToAlternative = (index: number, altName: string) => {
    setIngredientList((prev) =>
      prev.map((ing, i) => (i === index ? { ...ing, name: altName, alternatives: [] } : ing))
    );
  };

  const handleAddIngredient = () => {
    const trimmed = newIngredientText.trim();
    if (!trimmed) return;
    setIngredientList((prev) => [...prev, { name: trimmed, displayMeta: null, alternatives: [] }]);
    setNewIngredientText('');
  };

  const handleGenerateRecipe = (
    override = false,
    warningTextShown?: string,
    previewToReuse?: ScanAllergenWarning
  ) => {
    if (!scan || ingredientList.length === 0) return;
    setState('generating');
    setCurrentStage(null);
    setError(null);
    setErrorType(null);
    setAllergenWarning(null);

    abortRef.current = generateRecipeFromScan(
      scan.id,
      ingredientList.map((ing) => ing.name),
      preferences.trim(),
      {
        onStage: (stage) => setCurrentStage(stage),
        onResult: (recipe: GeneratedRecipeFromScan) => {
          setCurrentStage(null);
          router.replace(`/(main)/recipes/${recipe.id}`);
        },
        onError: (errType, detail, warning) => {
          setCurrentStage(null);
          if (errType === 'AllergenDetectedError' && warning) {
            // Real backend data — show the actual preview with a
            // proper confirm/cancel choice, same as typed recipe
            // generation's "Generate Anyway" flow.
            setAllergenWarning(warning);
            setState('reviewing');
            return;
          }
          setError(ERROR_MESSAGES[errType] ?? detail);
          setErrorType(errType);
          setState('reviewing');
        },
      },
      {
        confirmAllergenOverride: override,
        warningTextShown,
        recipePreviewOverride: previewToReuse?.recipe_preview,
        flaggedAllergensOverride: previewToReuse?.flagged_allergens,
      }
    );
  };

  const handleStartOver = () => {
    setState('picking');
    setImageUri(null);
    setScan(null);
    setIngredientList([]);
    setPreferences('');
    setError(null);
    setErrorType(null);
    setAllergenWarning(null);
  };

  // ---------------------------------------------------
  // Picking / Identifying
  // ---------------------------------------------------

  if (state === 'picking' || state === 'identifying') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
        <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, flexGrow: 1 }}>
          <Pressable onPress={() => router.back()} style={{ marginBottom: 20 }}>
            <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
          </Pressable>

          <Text style={{ fontSize: 22, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
            Ingredient Scan 🥕
          </Text>
          <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 24 }}>
            Take or choose a photo of your ingredients — AIMeals will identify them and build a recipe.
          </Text>

          {imageUri && (
            <Image
              source={{ uri: imageUri }}
              style={{ width: '100%', height: 220, borderRadius: RADIUS.card, marginBottom: 20 }}
              resizeMode="cover"
            />
          )}

          {state === 'identifying' ? (
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent' }} padding={16}>
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
                INGREDIENT_SCAN_STAGE_ORDER.map((stage) => {
                  const currentIndex = currentStage ? INGREDIENT_SCAN_STAGE_ORDER.indexOf(currentStage as IngredientScanStage) : -1;
                  const thisIndex = INGREDIENT_SCAN_STAGE_ORDER.indexOf(stage);
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
                        {INGREDIENT_SCAN_STAGE_LABELS[stage]}
                      </Text>
                    </View>
                  );
                })
              )}
            </ThemedCard>
          ) : (
            <>
              {error && (
                <ThemedCard style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', marginBottom: 16 }} padding={12}>
                  <Text style={{ color: colors.danger, fontSize: 12 }}>{error}</Text>
                </ThemedCard>
              )}
              <Pressable
                onPress={() => setShowPickerSheet(true)}
                style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 16, alignItems: 'center', ...CARD_SHADOW }}
              >
                <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>📷 Scan ingredients</Text>
              </Pressable>

              {state === 'picking' && pantryItems.length > 0 && (
                <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', marginTop: 28, marginBottom: 16 }} padding={16}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                    <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary }}>Your pantry ingredients</Text>
                    <Pressable onPress={() => router.push('/(main)/pantry')}>
                      <Text style={{ fontSize: 12, color: colors.primary, fontWeight: '600' }}>View all ›</Text>
                    </Pressable>
                  </View>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingRight: 8 }}>
                    {pantryItems.slice(0, 8).map((item) => (
                      <View key={item.id} style={{ alignItems: 'center', width: 64, marginRight: 12 }}>
                        <View
                          style={{
                            width: 52,
                            height: 52,
                            borderRadius: 12,
                            backgroundColor: colors.cardBg,
                            alignItems: 'center',
                            justifyContent: 'center',
                            marginBottom: 6,
                          }}
                        >
                          <Text style={{ fontSize: 24 }}>{getIngredientEmoji(item.ingredient_name)}</Text>
                        </View>
                        <Text style={{ fontSize: 10, color: colors.textSecondary, textAlign: 'center' }} numberOfLines={1}>
                          {item.ingredient_name}
                        </Text>
                      </View>
                    ))}
                  </ScrollView>
                  <Pressable
                    onPress={() => setShowPickerSheet(true)}
                    style={{
                      borderWidth: 1,
                      borderColor: colors.primary,
                      borderStyle: 'dashed',
                      borderRadius: RADIUS.button,
                      paddingVertical: 10,
                      alignItems: 'center',
                      marginTop: 12,
                    }}
                  >
                    <Text style={{ fontSize: 12, fontWeight: '700', color: colors.primary }}>+ Scan more ingredients</Text>
                  </Pressable>
                </ThemedCard>
              )}

              {state === 'picking' && suggestedRecipes.length > 0 && (
                <ThemedCard style={{ backgroundColor: colors.accentLavender + '15', borderColor: 'transparent', marginBottom: 16 }} padding={16}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                    <Text style={{ fontSize: 16, marginRight: 8 }}>👨‍🍳</Text>
                    <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary }}>What can you make today?</Text>
                  </View>
                  <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 12 }}>
                    Based on your ingredients, here are some ideas you might like.
                  </Text>
                  {suggestedRecipes.map(({ recipe, matchCount }) => (
                    <Pressable
                      key={recipe.id}
                      onPress={() => router.push(`/(main)/recipes/${recipe.id}`)}
                      style={{ marginBottom: 8 }}
                    >
                      <ThemedCard
                        style={{
                          flexDirection: 'row',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          borderColor: 'transparent',
                        }}
                        padding={12}
                      >
                        <View style={{ flex: 1, marginRight: 8 }}>
                          <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }} numberOfLines={1}>
                            {recipe.title}
                          </Text>
                          <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>
                            Uses {matchCount} of your ingredients
                          </Text>
                        </View>
                        <Text style={{ fontSize: 16, color: colors.textMuted }}>›</Text>
                      </ThemedCard>
                    </Pressable>
                  ))}
                  <Pressable onPress={() => router.push('/(main)/recipes')}>
                    <Text style={{ fontSize: 12, color: colors.accentLavender, fontWeight: '600' }}>Explore more recipes →</Text>
                  </Pressable>
                </ThemedCard>
              )}

              {state === 'picking' && dailyTip && (
                <ThemedCard style={{ flexDirection: 'row', backgroundColor: colors.surfaceAlt, borderColor: 'transparent', marginBottom: 12 }} padding={16}>
                  <Text style={{ fontSize: 18, marginRight: 10 }}>💡</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>AIMeals tip</Text>
                    <Text style={{ fontSize: 12, color: colors.textSecondary, lineHeight: 17 }}>{dailyTip}</Text>
                  </View>
                </ThemedCard>
              )}
            </>
          )}
        </ScrollView>

        <Modal visible={showPickerSheet} transparent animationType="fade" onRequestClose={() => setShowPickerSheet(false)}>
          <Pressable
            onPress={() => setShowPickerSheet(false)}
            style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' }}
          >
            <Pressable
              onPress={(e) => e.stopPropagation()}
              style={{ backgroundColor: colors.cardBg, borderTopLeftRadius: RADIUS.card, borderTopRightRadius: RADIUS.card, padding: 20, paddingBottom: 36 }}
            >
              <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 16, textAlign: 'center' }}>
                Scan ingredients
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

        <ModuleNavBar currentKey="ingredient_scan" />
      </View>
    );
  }

  // ---------------------------------------------------
  // Error state (identification itself failed)
  // ---------------------------------------------------

  if (state === 'error') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Text style={{ fontSize: 36, marginBottom: 12 }}>😕</Text>
        <Text style={{ fontSize: 17, fontWeight: '700', color: colors.textPrimary, marginBottom: 6, textAlign: 'center' }}>
          Couldn't identify ingredients
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
  // Reviewing / Generating
  // ---------------------------------------------------

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}>
      <Pressable onPress={handleStartOver} style={{ marginBottom: 16 }} disabled={state === 'generating'}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Scan a different photo</Text>
      </Pressable>

      {imageUri && (
        <Image source={{ uri: imageUri }} style={{ width: '100%', height: 160, borderRadius: RADIUS.card, marginBottom: 16 }} resizeMode="cover" />
      )}

      <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 2 }}>
        What AIMeals found
      </Text>
      <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 14 }}>
        Edit, remove, or add ingredients before generating your recipe.
      </Text>

      <View style={{ gap: 10, marginBottom: 16 }}>
        {ingredientList.map((ing, i) => (
          <ThemedCard
            key={i}
            style={{
              backgroundColor: ing.alternatives.length > 0 ? colors.warningBg : colors.cardBg,
              borderColor: ing.alternatives.length > 0 ? 'transparent' : colors.cardBorder,
            }}
          >
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary }}>
                  {ing.name}
                  {ing.displayMeta ? <Text style={{ color: colors.textSecondary, fontWeight: '400' }}> · {ing.displayMeta}</Text> : null}
                </Text>
              </View>
              <Pressable onPress={() => handleRemoveIngredient(i)} style={{ paddingHorizontal: 8, paddingVertical: 4 }}>
                <Text style={{ fontSize: 16, color: colors.textMuted }}>✕</Text>
              </Pressable>
            </View>

            {ing.alternatives.length > 0 && (
              <View style={{ marginTop: 10 }}>
                <Text style={{ fontSize: 11, color: colors.warningText, marginBottom: 6 }}>Not sure? Pick one:</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                  {ing.alternatives.map((alt) => (
                    <Pressable
                      key={alt}
                      onPress={() => handleSwitchToAlternative(i, alt)}
                      style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: RADIUS.chip, backgroundColor: colors.cardBg, borderWidth: 1, borderColor: colors.cardBorder }}
                    >
                      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary }}>{alt}</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            )}
          </ThemedCard>
        ))}
      </View>

      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 24 }}>
        <TextInput
          placeholder="Add an ingredient…"
          placeholderTextColor={colors.textMuted}
          value={newIngredientText}
          onChangeText={setNewIngredientText}
          onSubmitEditing={handleAddIngredient}
          style={{
            flex: 1,
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 12,
            paddingHorizontal: 14,
            paddingVertical: 10,
            fontSize: 14,
            color: colors.textPrimary,
            backgroundColor: colors.cardBg,
          }}
        />
        <Pressable
          onPress={handleAddIngredient}
          style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center' }}
        >
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Add</Text>
        </Pressable>
      </View>

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 }}>
        PREFERENCES (OPTIONAL)
      </Text>
      <TextInput
        placeholder="e.g. make it vegetarian, quick weeknight meal"
        placeholderTextColor={colors.textMuted}
        value={preferences}
        onChangeText={setPreferences}
        editable={state !== 'generating'}
        multiline
        numberOfLines={2}
        style={{
          borderWidth: 1,
          borderColor: colors.border,
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
          fontSize: 14,
          color: colors.textPrimary,
          backgroundColor: colors.cardBg,
          minHeight: 60,
          textAlignVertical: 'top',
          marginBottom: 20,
        }}
      />

      {state === 'generating' && (
        <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', marginBottom: 20 }} padding={16}>
          {RECIPE_FROM_SCAN_STAGE_ORDER.map((stage) => {
            const currentIndex = currentStage ? RECIPE_FROM_SCAN_STAGE_ORDER.indexOf(currentStage as RecipeFromScanStage) : -1;
            const thisIndex = RECIPE_FROM_SCAN_STAGE_ORDER.indexOf(stage);
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
                  {RECIPE_FROM_SCAN_STAGE_LABELS[stage]}
                </Text>
              </View>
            );
          })}
        </ThemedCard>
      )}

      {allergenWarning && (
        <ThemedCard
          style={{
            backgroundColor: colors.dangerBg,
            borderColor: colors.danger,
            marginBottom: 16,
          }}
          padding={14}
        >
          <Text style={{ color: colors.danger, fontSize: 13, fontWeight: '700', marginBottom: 6 }}>
            ⚠ Allergen warning
          </Text>
          <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 10 }}>
            This recipe contains {allergenWarning.flagged_allergens.join(', ')}, which is on your
            allergy list. Do you still want to generate it?
          </Text>
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <Pressable
              onPress={() => setAllergenWarning(null)}
              style={{
                flex: 1,
                borderWidth: 1,
                borderColor: colors.danger,
                borderRadius: RADIUS.button,
                paddingVertical: 10,
                alignItems: 'center',
              }}
            >
              <Text style={{ color: colors.danger, fontSize: 13, fontWeight: '600' }}>Cancel</Text>
            </Pressable>
            <Pressable
              onPress={() => {
                const shownText = `This recipe contains ${allergenWarning.flagged_allergens.join(', ')}, which is on your allergy list. Do you still want to generate it?`;
                const warningToReuse = allergenWarning;
                setAllergenWarning(null);
                handleGenerateRecipe(true, shownText, warningToReuse);
              }}
              style={{
                flex: 1,
                backgroundColor: colors.danger,
                borderRadius: RADIUS.button,
                paddingVertical: 10,
                alignItems: 'center',
              }}
            >
              <Text style={{ color: '#fff', fontSize: 13, fontWeight: '600' }}>Generate anyway</Text>
            </Pressable>
          </View>
        </ThemedCard>
      )}

      {error && (
        <ThemedCard style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', marginBottom: 16 }} padding={12}>
          <Text style={{ color: colors.danger, fontSize: 12 }}>{error}</Text>
        </ThemedCard>
      )}

      <Pressable
        onPress={() => handleGenerateRecipe()}
        disabled={state === 'generating' || ingredientList.length === 0}
        style={{
          backgroundColor: state === 'generating' || ingredientList.length === 0 ? colors.border : colors.primary,
          borderRadius: RADIUS.button,
          paddingVertical: 15,
          alignItems: 'center',
        }}
      >
        <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>
          {state === 'generating' ? 'Generating…' : 'Generate Recipe'}
        </Text>
      </Pressable>
    </ScrollView>
  );
}
