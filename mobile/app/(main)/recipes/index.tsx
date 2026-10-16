import { useCallback, useMemo, useState } from 'react';
import { View, Text, Pressable, FlatList, ActivityIndicator, RefreshControl, ScrollView, TextInput } from 'react-native';
import { useRouter, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { recipeApi } from '../../../src/api/recipe';
import { pantryApi } from '../../../src/api/pantry';
import RecipeGenerator from '../../../src/components/RecipeGenerator';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';
import type { Recipe } from '../../../src/types/recipe';
import type { PantryItem } from '../../../src/types/pantry';

type Tab = 'mine' | 'discover';

export default function RecipesList() {
  const router = useRouter();
  const { colors } = useTheme();
  const params = useLocalSearchParams<{ tab?: string; prefill?: string }>();
  // A prefill param (from Health Insights) always implies discover
  // mode too — no point landing on "My Recipes" with a pre-filled
  // AI request sitting unused.
  const [activeTab, setActiveTab] = useState<Tab>(
    params.tab === 'discover' || params.prefill ? 'discover' : 'mine'
  );
  const [autoTriggerPantry, setAutoTriggerPantry] = useState(false);

  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const [pantryItems, setPantryItems] = useState<PantryItem[]>([]);

  const loadMine = useCallback(async (isRefresh = false) => {
    isRefresh ? setIsRefreshing(true) : setIsLoading(true);
    setError(null);
    try {
      const data = await recipeApi.mine();
      setRecipes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recipes');
    } finally {
      isRefresh ? setIsRefreshing(false) : setIsLoading(false);
    }
  }, []);

  const loadPantryPreview = useCallback(async () => {
    try {
      const items = await pantryApi.list();
      setPantryItems(items);
    } catch {
      // Silent — the "What can I cook?" card is a nice-to-have, not
      // core functionality worth surfacing an error banner for.
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      // Discover tab doesn't need a list fetch — it's the AI generator.
      if (activeTab === 'mine') {
        loadMine();
        loadPantryPreview();
      }
    }, [activeTab, loadMine, loadPantryPreview])
  );

  const filteredRecipes = useMemo(() => {
    if (!searchQuery.trim()) return recipes;
    const q = searchQuery.trim().toLowerCase();
    return recipes.filter(
      (r) => r.title.toLowerCase().includes(q) || (r.description ?? '').toLowerCase().includes(q)
    );
  }, [recipes, searchQuery]);

  const handleSuggestFromPantry = () => {
    setActiveTab('discover');
    setAutoTriggerPantry(true);
    // Reset the trigger flag shortly after — the effect inside
    // RecipeGenerator only needs to see the true->false->true edge if
    // tapped again later; this just prevents it from staying "stuck" true.
    setTimeout(() => setAutoTriggerPantry(false), 500);
  };

  const renderItem = ({ item }: { item: Recipe }) => (
    <Pressable
      onPress={() => router.push(`/(main)/recipes/${item.id}`)}
      style={{ marginBottom: 12 }}
    >
      <ThemedCard
        padding={16}
        style={{
          backgroundColor: item.contains_allergen ? colors.dangerBg : colors.cardBg,
          borderWidth: item.contains_allergen ? 1.5 : 1,
          borderColor: item.contains_allergen ? colors.danger : colors.cardBorder,
        }}
      >
        {item.contains_allergen ? (
          <Text style={{ color: colors.danger, fontSize: 11, fontWeight: '700', marginBottom: 4 }}>
            ⚠ Contains allergens
          </Text>
        ) : null}
        <Text
          style={{
            fontSize: 15,
            fontWeight: '700',
            color: item.contains_allergen ? colors.danger : colors.textPrimary,
            marginBottom: 4,
          }}
        >
          {item.title}
        </Text>
        {item.description ? (
          <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 10 }} numberOfLines={2}>
            {item.description}
          </Text>
        ) : null}
        <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap' }}>
          {item.calories_per_serving != null && (
            <Chip label={`${Math.round(item.calories_per_serving)} kcal`} tone="calories" />
          )}
          {(item.prep_time_minutes != null || item.cook_time_minutes != null) && (
            <Chip label={`${(item.prep_time_minutes ?? 0) + (item.cook_time_minutes ?? 0)} min`} />
          )}
          <Chip label={`${item.servings} serving${item.servings === 1 ? '' : 's'}`} />
          {item.is_ai_generated && <Chip label="AI" tone="ai" />}
        </View>
      </ThemedCard>
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <View style={{ flex: 1, paddingTop: 60, paddingHorizontal: 20 }}>
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
          <View
            style={{
              width: 40,
              height: 40,
              borderRadius: 20,
              backgroundColor: colors.iconCircleRecipesBg,
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: 10,
            }}
          >
            <Text style={{ fontSize: 18 }}>👨‍🍳</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary }}>Recipes 🧭</Text>
            <Text style={{ fontSize: 11, color: colors.textSecondary }}>Discover healthy & tasty recipes</Text>
          </View>
        </View>
        {activeTab === 'mine' && (
          <Pressable
            onPress={() => router.push('/(main)/recipes/form')}
            style={{
              backgroundColor: colors.primary,
              paddingHorizontal: 14,
              paddingVertical: 10,
              borderRadius: RADIUS.button,
            }}
          >
            <Text style={{ color: '#fff', fontSize: 12, fontWeight: '600' }}>+ Add recipe</Text>
          </Pressable>
        )}
      </View>

      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 16 }}>
        <TabButton label="My Recipes" isActive={activeTab === 'mine'} onPress={() => setActiveTab('mine')} />
        <TabButton
          label="AI Recipes"
          isActive={activeTab === 'discover'}
          onPress={() => setActiveTab('discover')}
        />
      </View>

      {activeTab === 'discover' ? (
        <ScrollView contentContainerStyle={{ paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
          <RecipeGenerator autoTriggerPantry={autoTriggerPantry} initialDescription={params.prefill} />
        </ScrollView>
      ) : (
        <>
          <TextInput
            placeholder="Search your recipes..."
            placeholderTextColor={colors.textMuted}
            value={searchQuery}
            onChangeText={setSearchQuery}
            style={{
              borderWidth: 1,
              borderColor: colors.border,
              borderRadius: 12,
              paddingHorizontal: 14,
              paddingVertical: 12,
              fontSize: 13,
              color: colors.textPrimary,
              backgroundColor: colors.cardBg,
              marginBottom: 14,
            }}
          />

          {/* "What can I cook?" — real pantry data, real Pantry Chef
              endpoint (POST /ai/recipes/from-pantry), previously never
              wired to any frontend. */}
          {pantryItems.length > 0 && !searchQuery.trim() && (
            <ThemedCard padding={16} style={{ backgroundColor: colors.mintBg, marginBottom: 16 }}>
              <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 8 }}>
                🥫 What can I cook?
              </Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
                {pantryItems.slice(0, 4).map((item) => (
                  <Chip key={item.id} label={item.ingredient_name} />
                ))}
                {pantryItems.length > 4 && <Chip label={`+${pantryItems.length - 4} more`} />}
              </View>
              <Pressable
                onPress={handleSuggestFromPantry}
                style={{
                  backgroundColor: colors.primary,
                  borderRadius: RADIUS.button,
                  paddingVertical: 12,
                  alignItems: 'center',
                }}
              >
                <Text style={{ color: '#fff', fontSize: 12, fontWeight: '600' }}>Suggest recipes</Text>
              </Pressable>
            </ThemedCard>
          )}

          {isLoading ? (
            <View style={{ paddingVertical: 40, alignItems: 'center' }}>
              <ActivityIndicator color={colors.primary} />
            </View>
          ) : error ? (
            <ThemedCard padding={14} style={{ backgroundColor: colors.dangerBg }}>
              <Text style={{ color: colors.danger, fontSize: 12 }}>{error}</Text>
              <Pressable onPress={() => loadMine()} style={{ marginTop: 6 }}>
                <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
              </Pressable>
            </ThemedCard>
          ) : filteredRecipes.length === 0 ? (
            <View style={{ paddingVertical: 40, alignItems: 'center' }}>
              <Text style={{ fontSize: 13, color: colors.textSecondary, textAlign: 'center' }}>
                {searchQuery.trim()
                  ? 'No recipes match your search.'
                  : 'No recipes yet. Tap "+ Add recipe" to create your first one.'}
              </Text>
            </View>
          ) : (
            <FlatList
              data={filteredRecipes}
              keyExtractor={(item) => item.id}
              renderItem={renderItem}
              refreshControl={
                <RefreshControl refreshing={isRefreshing} onRefresh={() => loadMine(true)} />
              }
            />
          )}
        </>
      )}
      </View>

      <ModuleNavBar currentKey="discover" />
    </View>
  );
}

function TabButton({
  label,
  isActive,
  onPress,
}: {
  label: string;
  isActive: boolean;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      style={{
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: RADIUS.chip,
        backgroundColor: isActive ? colors.primary : colors.primaryLight,
      }}
    >
      <Text style={{ fontSize: 12, fontWeight: '600', color: isActive ? '#fff' : colors.primaryDark }}>
        {label}
      </Text>
    </Pressable>
  );
}

function Chip({ label, tone }: { label: string; tone?: 'calories' | 'ai' }) {
  const { colors } = useTheme();
  const bg = tone === 'calories' ? colors.warningBg : tone === 'ai' ? colors.primaryLight : colors.surfaceAlt;
  const text = tone === 'calories' ? colors.warningText : tone === 'ai' ? colors.primaryDark : colors.textSecondary;
  return (
    <View style={{ backgroundColor: bg, paddingHorizontal: 9, paddingVertical: 4, borderRadius: RADIUS.chip }}>
      <Text style={{ fontSize: 10, fontWeight: '600', color: text }}>{label}</Text>
    </View>
  );
}
