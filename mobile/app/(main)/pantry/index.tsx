import { useCallback, useMemo, useState } from 'react';
import { View, Text, Pressable, FlatList, ActivityIndicator, RefreshControl, Alert } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { pantryApi } from '../../../src/api/pantry';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import ThemedCard from '../../../src/components/ThemedCard';
import { useTheme } from '../../../src/theme/ThemeContext';
import { categorizeIngredient, CATEGORY_ORDER, type PantryCategory } from '../../../src/utils/pantryCategories';
import type { PantryItem } from '../../../src/types/pantry';

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  target.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

type ListRow =
  | { kind: 'section'; category: PantryCategory }
  | { kind: 'item'; item: PantryItem };

export default function PantryList() {
  const router = useRouter();
  const { colors } = useTheme();
  const [items, setItems] = useState<PantryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<PantryCategory | 'All'>('All');

  const load = useCallback(async (isRefresh = false) => {
    isRefresh ? setIsRefreshing(true) : setIsLoading(true);
    setError(null);
    try {
      const data = await pantryApi.list();
      // Soonest-expiring first; items with no expiration date sort last.
      const sorted = [...data].sort((a, b) => {
        if (!a.expiration_date) return 1;
        if (!b.expiration_date) return -1;
        return a.expiration_date.localeCompare(b.expiration_date);
      });
      setItems(sorted);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pantry');
    } finally {
      isRefresh ? setIsRefreshing(false) : setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleDelete = (item: PantryItem) => {
    Alert.alert('Remove item?', `Remove "${item.ingredient_name}" from your pantry?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: async () => {
          try {
            await pantryApi.remove(item.id);
            setItems((prev) => prev.filter((i) => i.id !== item.id));
          } catch (err) {
            Alert.alert('Error', err instanceof Error ? err.message : 'Failed to remove item');
          }
        },
      },
    ]);
  };

  // Stats — derived entirely from what's already fetched, nothing new
  // to the backend.
  const stats = useMemo(() => {
    let expiringSoon = 0;
    let expired = 0;
    for (const item of items) {
      const days = daysUntil(item.expiration_date);
      if (days === null) continue;
      if (days < 0) expired += 1;
      else if (days <= 3) expiringSoon += 1;
    }
    return { total: items.length, expiringSoon, expired };
  }, [items]);

  // Category is derived at render time, never persisted.
  const itemsByCategory = useMemo(() => {
    const map = new Map<PantryCategory, PantryItem[]>();
    for (const item of items) {
      const cat = categorizeIngredient(item.ingredient_name);
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(item);
    }
    return map;
  }, [items]);

  const categoriesPresent = useMemo(
    () => CATEGORY_ORDER.filter((c) => (itemsByCategory.get(c)?.length ?? 0) > 0),
    [itemsByCategory]
  );

  const rows: ListRow[] = useMemo(() => {
    const cats = activeCategory === 'All' ? categoriesPresent : [activeCategory];
    const out: ListRow[] = [];
    for (const cat of cats) {
      const catItems = itemsByCategory.get(cat) ?? [];
      if (catItems.length === 0) continue;
      // No section header needed when a single category is isolated via
      // the filter chips — it'd just repeat the chip label above it.
      if (activeCategory === 'All') out.push({ kind: 'section', category: cat });
      for (const item of catItems) out.push({ kind: 'item', item });
    }
    return out;
  }, [activeCategory, categoriesPresent, itemsByCategory]);

  const renderRow = ({ item: row }: { item: ListRow }) => {
    if (row.kind === 'section') {
      return (
        <Text
          style={{
            fontSize: 11,
            fontWeight: '700',
            color: colors.textSecondary,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
            marginTop: 14,
            marginBottom: 6,
          }}
        >
          {row.category}
        </Text>
      );
    }

    const item = row.item;
    const days = daysUntil(item.expiration_date);
    const isExpiringSoon = days !== null && days <= 3;
    const isExpired = days !== null && days < 0;

    return (
      <Pressable onLongPress={() => handleDelete(item)}>
        <ThemedCard
          padding={0}
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingVertical: 12,
            paddingHorizontal: 14,
            backgroundColor: colors.screenBg,
            borderColor: colors.border,
            borderRadius: 10,
            marginBottom: 8,
          }}
        >
          <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary }}>
            {item.ingredient_name}
          </Text>
          {(item.quantity || item.unit) && (
            <Text style={{ fontSize: 12, color: colors.textSecondary, marginTop: 2 }}>
              {item.quantity ?? ''} {item.unit ?? ''}
            </Text>
          )}
        </View>

        {item.expiration_date && (
          <View
            style={{
              paddingHorizontal: 8,
              paddingVertical: 4,
              borderRadius: 100,
              backgroundColor: isExpired ? colors.dangerBg : isExpiringSoon ? colors.warningBg : colors.surfaceAlt,
            }}
          >
            <Text
              style={{
                fontSize: 10,
                fontWeight: '600',
                color: isExpired ? colors.danger : isExpiringSoon ? colors.warningText : colors.textSecondary,
              }}
            >
              {isExpired
                ? 'Expired'
                : days === 0
                  ? 'Today'
                  : days === 1
                    ? 'Tomorrow'
                    : `${days}d left`}
            </Text>
          </View>
          )}
        </ThemedCard>
      </Pressable>
    );
  };

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
          <View>
            <Pressable onPress={() => router.back()}>
              <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 4 }}>‹ Back</Text>
            </Pressable>
            <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary }}>Pantry 🍳</Text>
          </View>
          <Pressable
            onPress={() => router.push('/(main)/pantry/add')}
            style={{
              backgroundColor: colors.accentSage,
              paddingHorizontal: 16,
              paddingVertical: 10,
              borderRadius: 8,
            }}
          >
            <Text style={{ color: '#fff', fontSize: 13, fontWeight: '600' }}>+ Add</Text>
          </Pressable>
        </View>

        {!isLoading && !error && items.length > 0 && (
          <>
            {/* Stats row — all three numbers come straight out of the
                already-fetched list, nothing new fetched or fabricated. */}
            <ThemedCard
              padding={0}
              style={{
                flexDirection: 'row',
                backgroundColor: colors.screenBg,
                borderColor: colors.border,
                borderRadius: 12,
                marginBottom: 14,
                overflow: 'hidden',
              }}
            >
              <StatCell label="Items" value={stats.total} color={colors.textPrimary} labelColor={colors.textSecondary} />
              <Divider color={colors.border} />
              <StatCell
                label="Expiring soon"
                value={stats.expiringSoon}
                color={stats.expiringSoon > 0 ? colors.warningText : colors.textPrimary}
                labelColor={colors.textSecondary}
              />
              <Divider color={colors.border} />
              <StatCell
                label="Expired"
                value={stats.expired}
                color={stats.expired > 0 ? colors.danger : colors.textPrimary}
                labelColor={colors.textSecondary}
              />
            </ThemedCard>

            {/* Category filter chips — client-side grouping only, see
                utils/pantryCategories.ts. */}
            <FlatList
              horizontal
              showsHorizontalScrollIndicator={false}
              data={['All', ...categoriesPresent] as const}
              keyExtractor={(c) => c}
              // flexGrow: 0 — a horizontal FlatList in a column layout otherwise
              // expands to fill the free height, stretching the chips into tall pills.
              style={{ flexGrow: 0 }}
              contentContainerStyle={{ gap: 8, marginBottom: 14 }}
              renderItem={({ item: cat }) => {
                const isSelected = activeCategory === cat;
                return (
                  <Pressable
                    onPress={() => setActiveCategory(cat as PantryCategory | 'All')}
                    style={{
                      paddingHorizontal: 14,
                      paddingVertical: 8,
                      borderRadius: 100,
                      backgroundColor: isSelected ? colors.accentSage : colors.surfaceAlt,
                    }}
                  >
                    <Text
                      style={{
                        fontSize: 12,
                        fontWeight: '600',
                        color: isSelected ? '#fff' : colors.textSecondary,
                      }}
                    >
                      {cat}
                    </Text>
                  </Pressable>
                );
              }}
            />

            {/* CTA into the real Pantry Chef AI flow (already built and
                wired on the Recipes screen) — deliberately not a second,
                naive ingredient-matcher here. */}
            <Pressable
              onPress={() => router.push('/(main)/recipes')}
              style={{ marginBottom: 16 }}
            >
              <ThemedCard
                style={{
                  backgroundColor: colors.accentSage + '14',
                  borderColor: 'transparent',
                  borderRadius: 12,
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <View style={{ flex: 1, paddingRight: 10 }}>
                  <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 2 }}>
                    🥫 What can I cook?
                  </Text>
                  <Text style={{ fontSize: 11, color: colors.textSecondary }}>
                    Get an AI recipe suggestion from what's in your pantry
                  </Text>
                </View>
                <Text style={{ fontSize: 13, fontWeight: '700', color: colors.accentSage }}>Go ›</Text>
              </ThemedCard>
            </Pressable>
          </>
        )}

        {isLoading ? (
          <View style={{ paddingVertical: 40, alignItems: 'center' }}>
            <ActivityIndicator color={colors.accentSage} />
          </View>
        ) : error ? (
          <ThemedCard
            padding={12}
            style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', borderRadius: 10 }}
          >
            <Text style={{ color: colors.danger, fontSize: 12 }}>{error}</Text>
            <Pressable onPress={() => load()} style={{ marginTop: 6 }}>
              <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
            </Pressable>
          </ThemedCard>
        ) : items.length === 0 ? (
          <View style={{ paddingVertical: 40, alignItems: 'center' }}>
            <Text style={{ fontSize: 13, color: colors.textSecondary }}>
              Your pantry is empty. Tap "+ Add" to log your first item.
            </Text>
          </View>
        ) : (
          <FlatList
            data={rows}
            keyExtractor={(row, i) => (row.kind === 'section' ? `section-${row.category}` : row.item.id)}
            renderItem={renderRow}
            refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={() => load(true)} />}
            ListFooterComponent={
              <Text style={{ fontSize: 10, color: colors.textMuted, textAlign: 'center', marginTop: 8, marginBottom: 8 }}>
                Long-press an item to remove it
              </Text>
            }
          />
        )}
      </View>

      <ModuleNavBar currentKey="pantry" />
    </View>
  );
}

function StatCell({
  label,
  value,
  color,
  labelColor,
}: {
  label: string;
  value: number;
  color: string;
  labelColor: string;
}) {
  return (
    <View style={{ flex: 1, alignItems: 'center', paddingVertical: 12 }}>
      <Text style={{ fontSize: 18, fontWeight: '700', color }}>{value}</Text>
      <Text style={{ fontSize: 10, color: labelColor, marginTop: 2, textAlign: 'center' }}>{label}</Text>
    </View>
  );
}

function Divider({ color }: { color: string }) {
  return <View style={{ width: 1, backgroundColor: color }} />;
}
