import { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, ActivityIndicator } from 'react-native';
import { generateRecipe } from '../api/aiRecipe';
import { suggestFromPantry } from '../api/aiPantryChef';
import { STAGE_LABELS, STAGE_ORDER } from '../types/aiRecipe';
import type { AllergenWarning, GeneratedRecipe, RecipeGenerationStage } from '../types/aiRecipe';
import { summarizeMicronutrients } from '../utils/micronutrientSummary';
import { stripLeadingStepNumber } from '../utils/recipeText';

const ACCENT = '#8873C2'; // lavender — AI Features section accent, per locked palette
const DANGER = '#B03B3B';

const ERROR_MESSAGES: Record<string, string> = {
  InsufficientCreditsError:
    "You're out of credits for this billing period. Upgrade your plan to keep generating recipes.",
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function typeText(
  text: string,
  onUpdate: (partial: string) => void,
  speedMs: number,
  isCancelled: () => boolean
): Promise<void> {
  return new Promise((resolve) => {
    let i = 0;
    const interval = setInterval(() => {
      if (isCancelled()) {
        clearInterval(interval);
        resolve();
        return;
      }
      i++;
      onUpdate(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(interval);
        resolve();
      }
    }, speedMs);
  });
}

// initialDescription pre-fills the request text box — used by the
// Health Insights results screen's "Recipes" card, which builds a
// short suggested request from the user's confirmed nutrition
// priorities (e.g. "A recipe to help with: Increase Dietary Fiber").
// This is ONLY a convenience starting point the user can freely edit
// before generating — it does NOT change what actually happens on
// generate: the backend already applies the user's confirmed health
// priorities as context to every recipe generation automatically
// (see AIService._build_nutrition_focus_context()), regardless of
// what text is typed here.
export default function RecipeGenerator({
  autoTriggerPantry,
  initialDescription,
}: {
  autoTriggerPantry?: boolean;
  initialDescription?: string;
}) {
  const [description, setDescription] = useState(initialDescription ?? '');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStage, setCurrentStage] = useState<RecipeGenerationStage | null>(null);
  const [result, setResult] = useState<GeneratedRecipe | null>(null);
  const [error, setError] = useState<{ type: string; message: string } | null>(null);
  const [allergenWarning, setAllergenWarning] = useState<AllergenWarning | null>(null);
  // Which flow raised the current allergenWarning — decides whether
  // "Generate anyway" retries via generateRecipe() (typed description)
  // or suggestFromPantry() (Pantry Chef), since both can now hit the
  // fail-open-with-confirmation flow.
  const [warningSource, setWarningSource] = useState<'typed' | 'pantry'>('typed');
  const abortRef = useRef<(() => void) | null>(null);

  // Sequential reveal state — driven by the effect below once `result` arrives.
  const [revealedTitle, setRevealedTitle] = useState('');
  const [revealedDescription, setRevealedDescription] = useState('');
  const [visibleBadges, setVisibleBadges] = useState(false);
  const [visibleIngredientCount, setVisibleIngredientCount] = useState(0);
  const [visibleInstructionCount, setVisibleInstructionCount] = useState(0);
  const [revealedClosingNote, setRevealedClosingNote] = useState('');
  const [isRevealing, setIsRevealing] = useState(false);
  const revealCancelledRef = useRef(false);

  useEffect(() => {
    return () => {
      abortRef.current?.();
      revealCancelledRef.current = true;
    };
  }, []);

  useEffect(() => {
    if (!result) return;

    revealCancelledRef.current = false;
    const cancelled = () => revealCancelledRef.current;

    setRevealedTitle('');
    setRevealedDescription('');
    setVisibleBadges(false);
    setVisibleIngredientCount(0);
    setVisibleInstructionCount(0);
    setRevealedClosingNote('');
    setIsRevealing(true);

    const ingredientLines = result.ingredients.split('\n').filter((l) => l.trim());
    const instructionLines = result.instructions.split('\n').filter((l) => l.trim());

    (async () => {
      await typeText(result.title, setRevealedTitle, 22, cancelled);
      if (cancelled()) return;

      if (result.description) {
        await typeText(result.description, setRevealedDescription, 12, cancelled);
        if (cancelled()) return;
      }

      setVisibleBadges(true);
      await sleep(200);

      for (let i = 0; i < ingredientLines.length; i++) {
        if (cancelled()) return;
        setVisibleIngredientCount(i + 1);
        await sleep(130);
      }
      if (cancelled()) return;

      await sleep(150);

      for (let i = 0; i < instructionLines.length; i++) {
        if (cancelled()) return;
        setVisibleInstructionCount(i + 1);
        await sleep(240);
      }
      if (cancelled()) return;

      if (result.closing_note) {
        await sleep(150);
        await typeText(result.closing_note, setRevealedClosingNote, 18, cancelled);
      }

      if (!cancelled()) setIsRevealing(false);
    })();

    return () => {
      revealCancelledRef.current = true;
    };
  }, [result]);

  const handleGenerate = (
    override = false,
    warningTextShown?: string,
    previewToReuse?: AllergenWarning
  ) => {
    if (!description.trim() || isGenerating) return;
    setIsGenerating(true);
    setCurrentStage(null);
    setResult(null);
    setError(null);
    setAllergenWarning(null);

    abortRef.current = generateRecipe(
      description.trim(),
      {
        onStage: (stage) => setCurrentStage(stage),
        onResult: (recipe) => {
          setResult(recipe);
          setIsGenerating(false);
          setCurrentStage(null);
        },
        onError: (errorType, detail, warning) => {
          setIsGenerating(false);
          setCurrentStage(null);
          if (errorType === 'AllergenDetectedError') {
            if (warning) {
              // Real backend data — show the actual preview with a
              // proper confirm/cancel choice.
              setWarningSource('typed');
              setAllergenWarning(warning);
            } else {
              // No preview available (shouldn't normally happen once
              // the backend is fully wired, but handled defensively).
              setError({
                type: errorType,
                message:
                  "This recipe was flagged against your allergy settings and couldn't be generated. " +
                  "Try rephrasing your request instead.",
              });
            }
          } else {
            setError({ type: errorType, message: ERROR_MESSAGES[errorType] ?? detail });
          }
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

  const handlePantrySuggest = (
    override = false,
    warningTextShown?: string,
    previewToReuse?: AllergenWarning
  ) => {
    if (isGenerating) return;
    setIsGenerating(true);
    setCurrentStage(null);
    setResult(null);
    setError(null);
    setAllergenWarning(null);

    abortRef.current = suggestFromPantry(
      undefined,
      '',
      {
        onStage: (stage) => setCurrentStage(stage),
        onResult: (recipe) => {
          setResult(recipe);
          setIsGenerating(false);
          setCurrentStage(null);
        },
        onError: (errorType, detail, warning) => {
          setIsGenerating(false);
          setCurrentStage(null);
          if (errorType === 'AllergenDetectedError') {
            if (warning) {
              // Real backend data — show the actual preview with a
              // proper confirm/cancel choice, same as typed generation.
              setWarningSource('pantry');
              setAllergenWarning(warning);
            } else {
              // No preview available (shouldn't normally happen once
              // the backend is fully wired, but handled defensively).
              setError({
                type: errorType,
                message:
                  "A pantry-based recipe was flagged against your allergy settings and couldn't be generated. " +
                  "Try rephrasing your request instead.",
              });
            }
          } else if (errorType === 'RecipeGenerationError' && detail.toLowerCase().includes('empty')) {
            setError({
              type: errorType,
              message: 'Your pantry is empty — add some ingredients first, or generate a recipe by description instead.',
            });
          } else {
            setError({ type: errorType, message: ERROR_MESSAGES[errorType] ?? detail });
          }
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

  // Auto-fires once when autoTriggerPantry flips to true — lets the
  // "What can I cook?" teaser card on the recipes list screen jump
  // straight to a pantry suggestion instead of requiring the user to
  // tap the button again after switching tabs.
  const hasAutoTriggeredRef = useRef(false);
  useEffect(() => {
    if (autoTriggerPantry && !hasAutoTriggeredRef.current) {
      hasAutoTriggeredRef.current = true;
      handlePantrySuggest();
    }
    if (!autoTriggerPantry) {
      hasAutoTriggeredRef.current = false;
    }
  }, [autoTriggerPantry]);

  const handleReset = () => {
    revealCancelledRef.current = true;
    setDescription('');
    setResult(null);
    setError(null);
    setAllergenWarning(null);
  };

  if (result) {
    const ingredientLines = result.ingredients.split('\n').filter((l) => l.trim());
    const instructionLines = result.instructions.split('\n').filter((l) => l.trim());

    return (
      <View>
        <View
          style={{
            backgroundColor: '#FFFFFF',
            borderWidth: 1,
            borderColor: '#EDEFE4',
            borderRadius: 12,
            padding: 16,
            marginBottom: 16,
          }}
        >
          <Text style={{ fontSize: 18, fontWeight: '600', color: '#4A4640', marginBottom: 6 }}>
            {revealedTitle}
          </Text>
          {revealedDescription ? (
            <Text style={{ fontSize: 13, color: '#9B9686', marginBottom: 12 }}>
              {revealedDescription}
            </Text>
          ) : null}

          {visibleBadges && (
            <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
              {result.calories_per_serving != null && (
                <Badge label={`${Math.round(result.calories_per_serving)} kcal`} />
              )}
              <Badge label={`${result.servings} serving${result.servings === 1 ? '' : 's'}`} />
              <Badge label="AI generated" />
            </View>
          )}

          {visibleIngredientCount > 0 && (
            <>
              <Text style={{ fontSize: 13, fontWeight: '600', color: '#4A4640', marginBottom: 6 }}>
                Ingredients
              </Text>
              {ingredientLines.slice(0, visibleIngredientCount).map((line, i) => (
                <Text key={i} style={{ fontSize: 13, color: '#4A4640', marginBottom: 3 }}>
                  •  {line.trim()}
                </Text>
              ))}
            </>
          )}

          {visibleInstructionCount > 0 && (
            <>
              <Text
                style={{
                  fontSize: 13,
                  fontWeight: '600',
                  color: '#4A4640',
                  marginTop: 14,
                  marginBottom: 6,
                }}
              >
                Instructions
              </Text>
              {instructionLines.slice(0, visibleInstructionCount).map((line, i) => (
                <Text key={i} style={{ fontSize: 13, color: '#4A4640', marginBottom: 6, lineHeight: 18 }}>
                  {i + 1}.  {stripLeadingStepNumber(line)}
                </Text>
              ))}
            </>
          )}

          {revealedClosingNote ? (
            <Text style={{ fontSize: 12, color: '#8873C2', fontStyle: 'italic', marginTop: 14 }}>
              {revealedClosingNote}
            </Text>
          ) : null}

          {/* One-line micronutrient callout — only shown once the full
              reveal animation has finished, so it doesn't compete with
              the ingredients/instructions being typed out. See
              summarizeMicronutrients()'s own docstring for the
              "notable amount" threshold logic. */}
          {!isRevealing && summarizeMicronutrients(result.micronutrients) && (
            <Text style={{ fontSize: 12, color: '#6B4FA0', marginTop: 10 }}>
              ✨ {summarizeMicronutrients(result.micronutrients)}
            </Text>
          )}
        </View>

        {!isRevealing && (
          <>
            <Text style={{ fontSize: 11, color: '#9B9686', textAlign: 'center', marginBottom: 12 }}>
              Saved to My Recipes
            </Text>
            <Pressable
              onPress={handleReset}
              style={{
                backgroundColor: ACCENT,
                borderRadius: 8,
                paddingVertical: 12,
                alignItems: 'center',
              }}
            >
              <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600' }}>Generate another</Text>
            </Pressable>
          </>
        )}
      </View>
    );
  }

  return (
    <View>
      <Text style={{ fontSize: 13, color: '#9B9686', marginBottom: 12 }}>
        Tell us what you'd like to eat — AIMeals will generate a recipe tailored to your allergies
        and dietary preferences.
      </Text>

      <TextInput
        placeholder="e.g. palak paneer, high-protein breakfast..."
        value={description}
        onChangeText={setDescription}
        editable={!isGenerating}
        multiline
        style={{
          borderWidth: 1,
          borderColor: '#E0DCC9',
          borderRadius: 8,
          paddingHorizontal: 12,
          paddingVertical: 10,
          fontSize: 14,
          color: '#4A4640',
          minHeight: 60,
          textAlignVertical: 'top',
          marginBottom: 12,
        }}
      />

      {isGenerating ? (
        <View style={{ backgroundColor: '#F3F1F8', borderRadius: 10, padding: 14, marginBottom: 12 }}>
          {STAGE_ORDER.map((stage) => {
            const currentIndex = currentStage ? STAGE_ORDER.indexOf(currentStage) : -1;
            const thisIndex = STAGE_ORDER.indexOf(stage);
            const isDone = thisIndex < currentIndex;
            const isActive = stage === currentStage;
            return (
              <View key={stage} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
                <Text style={{ width: 18, fontSize: 12 }}>{isDone ? '✓' : isActive ? '' : '○'}</Text>
                {isActive && <ActivityIndicator size="small" color={ACCENT} style={{ marginRight: 6 }} />}
                <Text
                  style={{
                    fontSize: 12,
                    color: isDone || isActive ? '#4A4640' : '#C4C0B0',
                    fontWeight: isActive ? '600' : '400',
                  }}
                >
                  {STAGE_LABELS[stage]}
                </Text>
              </View>
            );
          })}
        </View>
      ) : null}

      {allergenWarning ? (
        <View
          style={{
            backgroundColor: '#F9D9D9',
            borderWidth: 1,
            borderColor: DANGER,
            borderRadius: 10,
            padding: 14,
            marginBottom: 12,
          }}
        >
          <Text style={{ color: DANGER, fontSize: 13, fontWeight: '700', marginBottom: 6 }}>
            ⚠ Allergen warning
          </Text>
          <Text style={{ color: DANGER, fontSize: 12, marginBottom: 10 }}>
            This recipe contains {allergenWarning.flagged_allergens.join(', ')}, which is on your
            allergy list. Do you still want to generate it?
          </Text>
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <Pressable
              onPress={() => setAllergenWarning(null)}
              style={{
                flex: 1,
                borderWidth: 1,
                borderColor: DANGER,
                borderRadius: 8,
                paddingVertical: 10,
                alignItems: 'center',
              }}
            >
              <Text style={{ color: DANGER, fontSize: 13, fontWeight: '600' }}>Cancel</Text>
            </Pressable>
            <Pressable
              onPress={() => {
                const shownText = `This recipe contains ${allergenWarning.flagged_allergens.join(', ')}, which is on your allergy list. Do you still want to generate it?`;
                const warningToReuse = allergenWarning;
                const source = warningSource;
                setAllergenWarning(null);
                if (source === 'pantry') {
                  handlePantrySuggest(true, shownText, warningToReuse);
                } else {
                  handleGenerate(true, shownText, warningToReuse);
                }
              }}
              style={{
                flex: 1,
                backgroundColor: DANGER,
                borderRadius: 8,
                paddingVertical: 10,
                alignItems: 'center',
              }}
            >
              <Text style={{ color: '#fff', fontSize: 13, fontWeight: '600' }}>Generate anyway</Text>
            </Pressable>
          </View>
        </View>
      ) : null}

      {error ? (
        <View style={{ backgroundColor: '#FBE3DD', borderRadius: 10, padding: 12, marginBottom: 12 }}>
          <Text style={{ color: '#A85A45', fontSize: 12 }}>{error.message}</Text>
        </View>
      ) : null}

      <Pressable
        onPress={() => handleGenerate(false)}
        disabled={!description.trim() || isGenerating}
        style={{
          backgroundColor: !description.trim() || isGenerating ? '#D9D5C7' : ACCENT,
          borderRadius: 8,
          paddingVertical: 12,
          alignItems: 'center',
        }}
      >
        <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600' }}>
          {isGenerating ? 'Generating…' : 'Generate recipe'}
        </Text>
      </Pressable>

      <Pressable
        onPress={() => handlePantrySuggest()}
        disabled={isGenerating}
        style={{
          borderWidth: 1,
          borderColor: ACCENT,
          borderRadius: 8,
          paddingVertical: 11,
          alignItems: 'center',
          marginTop: 8,
          opacity: isGenerating ? 0.5 : 1,
        }}
      >
        <Text style={{ color: ACCENT, fontSize: 13, fontWeight: '600' }}>
          🥫 Suggest from my pantry
        </Text>
      </Pressable>
    </View>
  );
}

function Badge({ label }: { label: string }) {
  return (
    <View style={{ backgroundColor: '#F3F1F8', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 100 }}>
      <Text style={{ fontSize: 11, fontWeight: '600', color: '#6B4FA0' }}>{label}</Text>
    </View>
  );
}
