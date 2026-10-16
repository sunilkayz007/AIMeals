import { useCallback, useRef, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  ActivityIndicator,
  Animated,
  Alert,
  Linking,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { subscriptionApi } from '../../../src/api/subscription';
import { useTheme } from '../../../src/theme/ThemeContext';
import ThemedCard from '../../../src/components/ThemedCard';
import * as purchases from '../../../src/lib/purchases';
import type { BillingPeriod, PaidTier, TierPackage } from '../../../src/lib/purchases';
import type { ThemeColors } from '../../../src/theme/colors';
import type { Subscription, SubscriptionTier } from '../../../src/types/subscription';

// Mirrors TIER_DEFAULT_ALLOWANCES in app/services/subscription_service.py
// EXACTLY. If that dict changes, update this too — there's no live
// endpoint yet that returns these numbers for tiers the user isn't
// currently on, so they're duplicated here deliberately rather than
// derived. (The current tier's own allowance IS available live via
// subscriptionApi.get() — see the summary strip below.)
const TIER_ALLOWANCES: Record<SubscriptionTier, number> = {
  free: 50,
  plus: 300,
  pro: 600,
};

const TIER_LABELS: Record<SubscriptionTier, string> = {
  free: 'Free',
  plus: 'Plus',
  pro: 'Pro',
};

// Play's own subscription center — used for "Manage subscription"
// (cancel / change payment method). Google requires apps to make
// cancellation reachable; deep-linking here is the standard way.
const PLAY_SUBSCRIPTIONS_URL = 'https://play.google.com/store/account/subscriptions?package=com.aimeals.app';

// After a successful Play purchase the tier only changes once
// RevenueCat's webhook reaches the backend (usually 1-5s). Poll
// GET /subscription this many times, this far apart, before telling
// the user it's "still processing" rather than failing.
const TIER_POLL_ATTEMPTS = 10;
const TIER_POLL_INTERVAL_MS = 2000;

interface UpsellTierDef {
  tier: PaidTier;
  label: string;
  tagline: string;
  features: string[];
  accentKey: 'accentSage' | 'accentPeach';
  badge?: string;
}

// Only Plus/Pro get the big showcase treatment — Free is never
// something to "upgrade" TO, so it never needs a large card here.
const UPSELL_TIERS: UpsellTierDef[] = [
  {
    tier: 'plus',
    label: 'Plus',
    tagline: 'More credits, smarter AI',
    features: [
      `${TIER_ALLOWANCES.plus} AI credits / month`,
      'Upgraded AI model for sharper results',
      'Allergen deep-insight unlocks',
      'Earn bonus credits by watching ads',
    ],
    accentKey: 'accentSage',
    badge: 'Most Popular',
  },
  {
    tier: 'pro',
    label: 'Pro',
    tagline: 'For power users',
    features: [
      `${TIER_ALLOWANCES.pro} AI credits / month`,
      'Everything in Plus',
      'Highest-capability AI used for complex requests',
      'Earn bonus credits by watching ads',
    ],
    accentKey: 'accentPeach',
  },
];

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

interface TierCardProps {
  def: UpsellTierDef;
  isCurrent: boolean;
  colors: ThemeColors;
  /** Play package for the selected billing period, or null if the
   * store didn't return one (billing unavailable / not configured). */
  pkg: TierPackage | null;
  isBusy: boolean;
  onSubscribe: (pkg: TierPackage) => void;
}

/**
 * A single Plus/Pro showcase card. Press sequence: onPressIn scales
 * down to 0.97, onPressOut springs back, and only once that spring
 * settles does the Play purchase sheet open — so the sheet reads as
 * the direct result of the tap rather than interrupting the bounce.
 */
function TierCard({ def, isCurrent, colors, pkg, isBusy, onSubscribe }: TierCardProps) {
  const scale = useRef(new Animated.Value(1)).current;
  const accentColor = colors[def.accentKey];
  const isDisabled = isCurrent || !pkg || isBusy;

  const handlePressIn = () => {
    if (isDisabled) return;
    Animated.spring(scale, {
      toValue: 0.97,
      useNativeDriver: true,
      speed: 40,
      bounciness: 0,
    }).start();
  };

  const handlePressOut = () => {
    if (isDisabled) return;
    Animated.spring(scale, {
      toValue: 1,
      useNativeDriver: true,
      speed: 16,
      bounciness: 10,
    }).start(({ finished }) => {
      if (finished && pkg) onSubscribe(pkg);
    });
  };

  let buttonLabel: string;
  if (isCurrent) buttonLabel = 'Your current plan';
  else if (!pkg) buttonLabel = purchases.isBillingAvailable() ? 'Unavailable right now' : 'Coming soon';
  else buttonLabel = `Subscribe · ${pkg.priceString} / ${pkg.period === 'monthly' ? 'month' : 'year'}`;

  return (
    <Pressable disabled={isDisabled} onPressIn={handlePressIn} onPressOut={handlePressOut}>
      <Animated.View
        style={{
          transform: [{ scale }],
          backgroundColor: colors.surfaceAlt,
          borderRadius: 20,
          padding: 24,
          marginBottom: 18,
          borderWidth: 2,
          borderColor: isCurrent ? colors.accentSage : accentColor + '55',
        }}
      >
        {def.badge && !isCurrent && (
          <View
            style={{
              alignSelf: 'flex-start',
              backgroundColor: accentColor,
              paddingHorizontal: 10,
              paddingVertical: 4,
              borderRadius: 100,
              marginBottom: 10,
            }}
          >
            <Text style={{ fontSize: 10, fontWeight: '700', color: '#fff' }}>{def.badge}</Text>
          </View>
        )}

        <View
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 4,
          }}
        >
          <Text style={{ fontSize: 26, fontWeight: '800', color: colors.textPrimary }}>
            {def.label}
          </Text>
          {isCurrent && (
            <View
              style={{
                backgroundColor: colors.successBg,
                paddingHorizontal: 10,
                paddingVertical: 4,
                borderRadius: 100,
              }}
            >
              <Text style={{ fontSize: 11, fontWeight: '700', color: colors.successText }}>
                Current Plan
              </Text>
            </View>
          )}
        </View>

        <Text style={{ fontSize: 14, color: colors.textSecondary, marginBottom: 18 }}>
          {def.tagline}
        </Text>

        {def.features.map((feature, i) => (
          <View key={i} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10 }}>
            <Text style={{ fontSize: 15, color: accentColor, marginRight: 8 }}>✓</Text>
            <Text style={{ fontSize: 14, color: colors.textPrimary, flex: 1 }}>{feature}</Text>
          </View>
        ))}

        <View
          style={{
            borderRadius: 100,
            paddingVertical: 14,
            alignItems: 'center',
            marginTop: 14,
            borderWidth: isCurrent ? 1 : 0,
            borderColor: colors.border,
            backgroundColor: isCurrent ? 'transparent' : pkg ? accentColor : colors.border,
            opacity: isBusy && !isCurrent ? 0.6 : 1,
          }}
        >
          <Text
            style={{
              fontSize: 14,
              fontWeight: '700',
              color: isCurrent || !pkg ? colors.textSecondary : '#fff',
            }}
          >
            {buttonLabel}
          </Text>
        </View>
      </Animated.View>
    </Pressable>
  );
}

export default function Upgrade() {
  const router = useRouter();
  const { colors } = useTheme();

  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [packages, setPackages] = useState<TierPackage[]>([]);
  const [period, setPeriod] = useState<BillingPeriod>('monthly');
  const [isLoading, setIsLoading] = useState(true);
  // Non-null while a purchase/restore is in flight — the label shown
  // under the cards, and the reason every card is disabled.
  const [busyMessage, setBusyMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    const [subResult, pkgResult] = await Promise.allSettled([
      subscriptionApi.get(),
      purchases.getTierPackages(),
    ]);
    // Either half failing is non-fatal: the plan comparison is still
    // useful without the current tier, and without store packages the
    // cards just show "Unavailable right now".
    setSubscription(subResult.status === 'fulfilled' ? subResult.value : null);
    setPackages(pkgResult.status === 'fulfilled' ? pkgResult.value : []);
    setIsLoading(false);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  /** Re-reads the backend subscription until it reaches expectedTier
   * (webhook landed) or attempts run out. Returns whether it did. */
  const waitForTier = useCallback(async (expectedTier: PaidTier | null) => {
    for (let i = 0; i < TIER_POLL_ATTEMPTS; i++) {
      try {
        const sub = await subscriptionApi.get();
        setSubscription(sub);
        if (sub && (expectedTier ? sub.tier === expectedTier : sub.tier !== 'free')) return true;
      } catch {
        // Transient network error — keep polling.
      }
      await sleep(TIER_POLL_INTERVAL_MS);
    }
    return false;
  }, []);

  const handleSubscribe = useCallback(
    async (tierPkg: TierPackage) => {
      setBusyMessage('Opening Google Play…');
      try {
        const outcome = await purchases.purchase(tierPkg.pkg);
        if (outcome === 'cancelled') return;
        setBusyMessage('Activating your plan…');
        const activated = await waitForTier(tierPkg.tier);
        Alert.alert(
          activated ? `Welcome to ${TIER_LABELS[tierPkg.tier]}!` : 'Purchase received',
          activated
            ? `Your ${TIER_ALLOWANCES[tierPkg.tier]} monthly credits are ready to use.`
            : "Google Play confirmed your purchase. Your plan can take a minute to activate — pull down on Home or reopen this screen shortly."
        );
      } catch (err: any) {
        Alert.alert('Purchase failed', err?.message ?? 'Something went wrong with Google Play. You have not been charged.');
      } finally {
        setBusyMessage(null);
      }
    },
    [waitForTier]
  );

  const handleRestore = useCallback(async () => {
    setBusyMessage('Restoring purchases…');
    try {
      const info = await purchases.restore();
      const hasActive = !!info?.activeSubscriptions.some((id) => purchases.tierForProductId(id));
      if (!hasActive) {
        Alert.alert('Nothing to restore', 'No active AIMeals subscription was found on this Google account.');
        return;
      }
      const activated = await waitForTier(null);
      Alert.alert(
        'Purchases restored',
        activated ? 'Your subscription is active on this account.' : 'Your plan will update in a minute.'
      );
    } catch (err: any) {
      Alert.alert('Restore failed', err?.message ?? 'Please try again.');
    } finally {
      setBusyMessage(null);
    }
  }, [waitForTier]);

  const currentTier = subscription?.tier ?? 'free';
  const currentAllowance = subscription?.monthly_credit_allowance ?? TIER_ALLOWANCES.free;
  const billingReady = purchases.isBillingAvailable() && packages.length > 0;
  const hasAnnual = packages.some((p) => p.period === 'annual');
  const packageFor = (tier: PaidTier) =>
    packages.find((p) => p.tier === tier && p.period === period) ?? null;

  return (
    <View style={{ flex: 1, backgroundColor: colors.screenBg }}>
      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 20, paddingTop: 60 }}>
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 2 }}>
          Upgrade your plan
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 16 }}>
          More credits, smarter AI, and premium features
        </Text>

        {isLoading ? (
          <View style={{ paddingVertical: 40, alignItems: 'center' }}>
            <ActivityIndicator color={colors.accentPeach} />
          </View>
        ) : (
          <>
            {/* Small, compact current-plan strip — deliberately low-key
                so it doesn't compete visually with the upsell cards
                below. */}
            <ThemedCard
              padding={0}
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                backgroundColor: colors.surfaceAlt,
                borderColor: 'transparent',
                borderRadius: 10,
                paddingVertical: 8,
                paddingHorizontal: 12,
                marginBottom: 16,
              }}
            >
              <Text style={{ fontSize: 11, color: colors.textSecondary }}>
                Currently on{' '}
                <Text style={{ fontWeight: '700', color: colors.textPrimary }}>
                  {TIER_LABELS[currentTier]}
                </Text>{' '}
                · {currentAllowance} credits / month
              </Text>
            </ThemedCard>

            {/* Monthly / annual toggle — only when Play actually
                returned annual base plans. */}
            {hasAnnual && (
              <View
                style={{
                  flexDirection: 'row',
                  backgroundColor: colors.surfaceAlt,
                  borderRadius: 100,
                  padding: 4,
                  marginBottom: 20,
                }}
              >
                {(['monthly', 'annual'] as BillingPeriod[]).map((p) => (
                  <Pressable
                    key={p}
                    onPress={() => setPeriod(p)}
                    style={{
                      flex: 1,
                      paddingVertical: 10,
                      borderRadius: 100,
                      alignItems: 'center',
                      backgroundColor: period === p ? colors.screenBg : 'transparent',
                    }}
                  >
                    <Text
                      style={{
                        fontSize: 13,
                        fontWeight: '700',
                        color: period === p ? colors.textPrimary : colors.textSecondary,
                      }}
                    >
                      {p === 'monthly' ? 'Monthly' : 'Yearly'}
                    </Text>
                  </Pressable>
                ))}
              </View>
            )}

            {UPSELL_TIERS.map((def) => (
              <TierCard
                key={def.tier}
                def={def}
                isCurrent={currentTier === def.tier}
                colors={colors}
                pkg={packageFor(def.tier)}
                isBusy={busyMessage !== null}
                onSubscribe={handleSubscribe}
              />
            ))}

            {busyMessage && (
              <View style={{ flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginBottom: 12 }}>
                <ActivityIndicator color={colors.accentSage} />
                <Text style={{ fontSize: 13, color: colors.textSecondary, marginLeft: 8 }}>{busyMessage}</Text>
              </View>
            )}

            {billingReady ? (
              <>
                <View style={{ flexDirection: 'row', justifyContent: 'center', marginBottom: 12 }}>
                  <Pressable disabled={busyMessage !== null} onPress={handleRestore} style={{ padding: 8 }}>
                    <Text style={{ fontSize: 13, fontWeight: '600', color: colors.accentSage }}>
                      Restore purchases
                    </Text>
                  </Pressable>
                  {currentTier !== 'free' && (
                    <Pressable onPress={() => Linking.openURL(PLAY_SUBSCRIPTIONS_URL)} style={{ padding: 8 }}>
                      <Text style={{ fontSize: 13, fontWeight: '600', color: colors.accentSage }}>
                        Manage subscription
                      </Text>
                    </Pressable>
                  )}
                </View>
                {/* Google Play subscription disclosure — auto-renewal
                    and how to cancel must be stated near the offer. */}
                <Text style={{ fontSize: 10, color: colors.textMuted, textAlign: 'center', lineHeight: 15 }}>
                  Subscriptions are billed through Google Play and renew automatically at the price shown
                  until cancelled. Cancel anytime in Google Play › Payments & subscriptions; access
                  continues until the end of the current billing period. Switching plans replaces your
                  current subscription.
                </Text>
              </>
            ) : (
              <Text
                style={{
                  fontSize: 11,
                  color: colors.textMuted,
                  marginTop: 8,
                  fontStyle: 'italic',
                  textAlign: 'center',
                }}
              >
                {purchases.isBillingAvailable()
                  ? "Subscriptions couldn't be loaded from Google Play. Check your connection and try again."
                  : "Subscriptions aren't available yet — check back soon."}
              </Text>
            )}
          </>
        )}
      </ScrollView>
    </View>
  );
}
