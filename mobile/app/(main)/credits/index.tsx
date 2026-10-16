import { useCallback, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, RefreshControl } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { subscriptionApi } from '../../../src/api/subscription';
import { useTheme } from '../../../src/theme/ThemeContext';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import CreditThresholdModal from '../../../src/components/CreditThresholdModal';
import ThemedCard from '../../../src/components/ThemedCard';
import { useCreditThresholdModal } from '../../../src/hooks/useCreditThresholdModal';
import type { Subscription, CreditCost, InteractionType } from '../../../src/types/subscription';

// Maps to your ACTUAL built features, not the mockup's slightly
// different naming — each one calls the real
// GET /subscription/credit-cost/{type} endpoint, so the numbers
// shown are genuinely correct, not copied from the reference image.
const FEATURE_LIST: { type: InteractionType; icon: string; label: string; description: string }[] = [
  { type: 'food_image_analysis', icon: '📷', label: 'AI Food Analysis', description: 'Scan & analyze food photos' },
  { type: 'recipe_generation', icon: '🍳', label: 'Recipe Generation', description: 'Generate custom recipes' },
  { type: 'chat', icon: '💬', label: 'Coach Chat', description: 'AI nutrition coach messages' },
  { type: 'meal_plan_generation', icon: '📅', label: 'Meal Plan Generation', description: 'Personalized meal plans' },
  { type: 'pantry_suggestion', icon: '🍽️', label: 'Pantry Chef', description: 'Recipes from your pantry' },
];

function formatDate(isoString: string | null): string {
  if (!isoString) return '—';
  const d = new Date(isoString);
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' });
}

export default function Credits() {
  const router = useRouter();
  const { colors } = useTheme();

  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [featureCosts, setFeatureCosts] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { isVisible: isThresholdModalVisible, dismiss: dismissThresholdModal } =
    useCreditThresholdModal(subscription);

  const load = useCallback(async (isRefresh = false) => {
    isRefresh ? setIsRefreshing(true) : setIsLoading(true);
    setError(null);
    try {
      const [sub, ...costs] = await Promise.all([
        subscriptionApi.get(),
        ...FEATURE_LIST.map((f) => subscriptionApi.getCreditCost(f.type)),
      ]);
      setSubscription(sub);
      const costMap: Record<string, number> = {};
      costs.forEach((c: CreditCost) => {
        costMap[c.interaction_type] = c.credit_cost;
      });
      setFeatureCosts(costMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load subscription');
    } finally {
      isRefresh ? setIsRefreshing(false) : setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleUpgradePress = () => {
    router.push('/(main)/upgrade' as any);
  };

  const creditsPercent =
    subscription && subscription.monthly_credit_allowance > 0
      ? Math.max(
          0,
          Math.min(100, (subscription.credits_remaining / subscription.monthly_credit_allowance) * 100)
        )
      : 0;

  return (
    <View style={{ flex: 1, backgroundColor: colors.screenBg }}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: 20, paddingTop: 60 }}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={() => load(true)} />}
      >
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 2 }}>
          Credits 💳
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
          Your AIMeals usage & plan details
        </Text>

        {isLoading ? (
          <View style={{ paddingVertical: 40, alignItems: 'center' }}>
            <ActivityIndicator color={colors.accentPeach} />
          </View>
        ) : error ? (
          <ThemedCard padding={12} style={{ backgroundColor: colors.warningBg, borderColor: 'transparent', borderRadius: 10 }}>
            <Text style={{ color: colors.warningText, fontSize: 12 }}>{error}</Text>
            <Pressable onPress={() => load()} style={{ marginTop: 6 }}>
              <Text style={{ color: colors.warningText, fontSize: 12, fontWeight: '600' }}>Retry</Text>
            </Pressable>
          </ThemedCard>
        ) : subscription ? (
          <>
            {/* Current plan card */}
            <ThemedCard
              padding={16}
              style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', borderRadius: 12, marginBottom: 20 }}
            >
              <View
                style={{
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                }}
              >
                <View>
                  <Text style={{ fontSize: 11, color: colors.accentSage, fontWeight: '600', marginBottom: 4 }}>
                    Current Plan
                  </Text>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <Text style={{ fontSize: 20, fontWeight: '700', color: colors.textPrimary }}>
                      {subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1)} Plan
                    </Text>
                    <View
                      style={{
                        backgroundColor: colors.successBg,
                        paddingHorizontal: 8,
                        paddingVertical: 3,
                        borderRadius: 100,
                      }}
                    >
                      <Text style={{ fontSize: 10, fontWeight: '600', color: colors.successText }}>
                        {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
                      </Text>
                    </View>
                  </View>
                  <Text style={{ fontSize: 12, color: colors.textSecondary }}>
                    Renews on {formatDate(subscription.current_period_end)}
                  </Text>
                </View>
              </View>

              <View style={{ height: 1, backgroundColor: colors.border, marginVertical: 14 }} />

              <Text style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 6 }}>
                Available Credits
              </Text>
              <View style={{ flexDirection: 'row', alignItems: 'baseline', marginBottom: 8 }}>
                <Text style={{ fontSize: 28, fontWeight: '700', color: colors.accentSage }}>
                  {Math.max(0, subscription.credits_remaining)}
                </Text>
                <Text style={{ fontSize: 16, color: colors.textSecondary }}>
                  {' '}/ {subscription.monthly_credit_allowance} credits
                </Text>
              </View>
              <View
                style={{
                  height: 8,
                  borderRadius: 100,
                  backgroundColor: colors.border,
                  overflow: 'hidden',
                  marginBottom: 6,
                }}
              >
                <View
                  style={{
                    height: 8,
                    borderRadius: 100,
                    backgroundColor: colors.accentSage,
                    width: `${creditsPercent}%`,
                  }}
                />
              </View>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <Text style={{ fontSize: 11, color: colors.accentSage, fontWeight: '600' }}>
                  {Math.round(creditsPercent)}% remaining this billing period
                </Text>
                <Text style={{ fontSize: 11, color: colors.textSecondary }}>
                  {subscription.credits_used_this_period} credits used
                </Text>
              </View>
            </ThemedCard>

            {/* What uses credits — real costs from the live endpoint */}
            <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 10 }}>
              What uses credits?
            </Text>
            <ThemedCard
              padding={0}
              style={{ backgroundColor: colors.screenBg, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 14, marginBottom: 20 }}
            >
              {FEATURE_LIST.map((feature, i) => (
                <View
                  key={feature.type}
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    paddingVertical: 12,
                    borderBottomWidth: i === FEATURE_LIST.length - 1 ? 0 : 1,
                    borderBottomColor: colors.border,
                  }}
                >
                  <View
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 17,
                      backgroundColor: colors.surfaceAlt,
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginRight: 10,
                    }}
                  >
                    <Text style={{ fontSize: 15 }}>{feature.icon}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 13, fontWeight: '600', color: colors.textPrimary }}>
                      {feature.label}
                    </Text>
                    <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 1 }}>
                      {feature.description}
                    </Text>
                  </View>
                  <View
                    style={{
                      backgroundColor: colors.successBg,
                      paddingHorizontal: 10,
                      paddingVertical: 4,
                      borderRadius: 100,
                    }}
                  >
                    <Text style={{ fontSize: 11, fontWeight: '600', color: colors.successText }}>
                      {featureCosts[feature.type] ?? '—'} credits
                    </Text>
                  </View>
                </View>
              ))}
            </ThemedCard>

            {/*
              Upgrade banner — now navigates to the real paywall screen
              at app/(main)/upgrade/index.tsx, which sells Plus/Pro via
              Google Play through RevenueCat (src/lib/purchases.ts).
            */}
            <ThemedCard
              padding={14}
              style={{ backgroundColor: colors.warningBg, borderColor: 'transparent', borderRadius: 12, flexDirection: 'row', alignItems: 'center' }}
            >
              <Text style={{ fontSize: 20, marginRight: 10 }}>👑</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }}>
                  Need more credits?
                </Text>
                <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>
                  Upgrade your plan to get more credits and unlock premium features.
                </Text>
              </View>
              <Pressable
                onPress={handleUpgradePress}
                style={{
                  backgroundColor: colors.accentSage,
                  borderRadius: 100,
                  paddingHorizontal: 16,
                  paddingVertical: 9,
                  marginLeft: 10,
                }}
              >
                <Text style={{ fontSize: 12, fontWeight: '700', color: '#fff' }}>Upgrade Plan</Text>
              </Pressable>
            </ThemedCard>

            <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 16, fontStyle: 'italic', textAlign: 'center' }}>
              Usage history and daily-average stats are coming in a future update.
            </Text>
          </>
        ) : (
          <Text style={{ fontSize: 12, color: colors.textSecondary }}>No subscription found yet.</Text>
        )}
      </ScrollView>

      <ModuleNavBar currentKey="credits" />

      <CreditThresholdModal
        visible={isThresholdModalVisible}
        onDismiss={dismissThresholdModal}
        creditsRemaining={subscription?.credits_remaining ?? 0}
        onRewardClaimed={() => load(true)}
      />
    </View>
  );
}
