import { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator, RefreshControl, Image, Animated } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import type { ThemeColors } from '../../src/theme/colors';
import { useAuthStore } from '../../src/stores/authStore';
import { subscriptionApi } from '../../src/api/subscription';
import { nutritionLogApi } from '../../src/api/nutritionLog';
import { waterApi, type WaterDaySummary } from '../../src/api/water';
import { profileApi } from '../../src/api/profile';
import { useTheme } from '../../src/theme/ThemeContext';
import { MODULES } from '../../src/config/modules';
import { formatLitersFromMl } from '../../src/utils/recipeText';
import { NUTRIENT_VISUALS } from '../../src/constants/nutritionEmoji';
import PendingConfirmationCard from '../../src/components/PendingConfirmationCard';
import ProgressRing from '../../src/components/ProgressRing';
import ThemedText from '../../src/components/ThemedText';
import ThemedCard from '../../src/components/ThemedCard';
import type { Subscription } from '../../src/types/subscription';
import type { PendingConfirmation, DailyTotals, NutritionLog, MealType } from '../../src/types/nutritionLog';

// Local calendar date (YYYY-MM-DD), NOT toISOString()-based.
// toISOString() converts to UTC first, which disagrees with the
// backend's own "today" (Python's date.today(), using the server's
// local system timezone) for part of every day in any timezone
// ahead of UTC — e.g. midnight-5:30 AM IST is still the previous
// day in UTC. That mismatch was real and confirmed via backend
// logs: /ai/daily-tip (server-computed) showed Aug 11 while this
// function (as it used to be written) showed Aug 10, at the same
// moment. Local date components avoid the UTC conversion entirely.
function todayString(): string {
  const d = new Date();
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
}

// Water is tracked in ml on the backend (fine-grained enough for the
// portion-scaling math), but shown in liters here since that's the unit
// people actually think in for daily water intake. Up to two decimals with
// trailing zeros dropped ("3L", "0.5L", "0.25L") so the +250 ml button's
// result is shown exactly rather than rounded to "0.3L".
function formatLiters(ml: number): string {
  return `${formatLitersFromMl(ml)}L`;
}

// Water ring color — deliberately the REVERSE of every other ring's
// convention (where red only ever means "over target"). Here red means
// "just getting started" and green means "close to/at your goal," per
// this exact stepped spec:
//   0%        -> no color (gray/border, nothing logged yet)
//   0% - 25%  -> fades in from gray to light red
//   25% - 50% -> flat light red
//   50% - 75% -> flat light green
//   75% - 100%-> fades from light green to full green
// Past 100% stays full green — there's no "danger" state for over-
// drinking water the way there is for going over a calorie target.
function getWaterRingColor(percent: number, colors: ThemeColors): string {
  const p = Math.max(0, Math.min(percent, 100));
  const noneColor = colors.border;
  const lightRed = '#FCA5A5';
  const lightGreen = '#86EFAC';
  const fullGreen = colors.primaryDark;

  if (p <= 25) return lerpColor(noneColor, lightRed, p / 25);
  if (p <= 50) return lightRed;
  if (p <= 75) return lightGreen;
  return lerpColor(lightGreen, fullGreen, (p - 75) / 25);
}

function lerpColor(fromHex: string, toHex: string, t: number): string {
  const from = hexToRgb(fromHex);
  const to = hexToRgb(toHex);
  const r = Math.round(from.r + (to.r - from.r) * t);
  const g = Math.round(from.g + (to.g - from.g) * t);
  const b = Math.round(from.b + (to.b - from.b) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const clean = hex.replace('#', '');
  const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean;
  const num = parseInt(full, 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

function timeOfDayGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

const MEAL_TYPE_ICON: Record<MealType, string> = {
  breakfast: '🍳',
  lunch: '🍛',
  dinner: '🍽️',
  snack: '🥜',
};

// Color + icon per nutrient now come from the shared, centralized
// NUTRIENT_VISUALS map (src/constants/nutritionEmoji.ts) — this used
// to be a locally-duplicated copy (and had a real bug: Fat and Water
// both used 💧). See that file's own docstring for the full reasoning.

function formatLoggedTime(isoString: string): string {
  const d = new Date(isoString);
  let hours = d.getHours();
  const minutes = d.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12;
  return `${hours}:${minutes} ${ampm}`;
}


interface MacroTargets {
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  water_ml: number | null;
}


export default function Home() {
  const router = useRouter();
  const { user, signOut } = useAuthStore();
  const { colors } = useTheme();

  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingConfirmations, setPendingConfirmations] = useState<PendingConfirmation[]>([]);
  const [dailyTotals, setDailyTotals] = useState<DailyTotals | null>(null);
  const [targets, setTargets] = useState<MacroTargets | null>(null);
  const [todaysMeals, setTodaysMeals] = useState<NutritionLog[]>([]);
  const [waterSummary, setWaterSummary] = useState<WaterDaySummary | null>(null);
  const [isLoggingWater, setIsLoggingWater] = useState(false);

  // Heartbeat pulse for the Health Insights card's healing-heart emoji
  // — a quick double-beat (like a real pulse), then a pause, looping.
  // Uses React Native's built-in Animated API (no extra dependency),
  // native-driven so it's cheap and doesn't block the JS thread.
  const heartbeatScale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const beat = Animated.sequence([
      Animated.timing(heartbeatScale, { toValue: 1.25, duration: 140, useNativeDriver: true }),
      Animated.timing(heartbeatScale, { toValue: 1, duration: 140, useNativeDriver: true }),
      Animated.timing(heartbeatScale, { toValue: 1.18, duration: 140, useNativeDriver: true }),
      Animated.timing(heartbeatScale, { toValue: 1, duration: 140, useNativeDriver: true }),
      Animated.delay(1400),
    ]);
    const loop = Animated.loop(beat);
    loop.start();
    return () => loop.stop();
  }, [heartbeatScale]);

  const loadSubscription = useCallback(async (isRefresh = false) => {
    isRefresh ? setIsRefreshing(true) : setIsLoading(true);
    setError(null);
    try {
      const data = await subscriptionApi.get();
      setSubscription(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load subscription');
    } finally {
      isRefresh ? setIsRefreshing(false) : setIsLoading(false);
    }
  }, []);

  const loadPendingConfirmations = useCallback(async () => {
    try {
      const data = await nutritionLogApi.getPendingConfirmations();
      setPendingConfirmations(data);
    } catch {
      // Silent failure — soft/optional prompt, not core functionality.
    }
  }, []);

  const loadTodayProgress = useCallback(async () => {
    try {
      const [totals, profile, meals] = await Promise.all([
        nutritionLogApi.getDailyTotals(todayString()),
        profileApi.getFull(),
        nutritionLogApi.getLogsForDay(todayString()),
      ]);
      setDailyTotals(totals);
      setTargets({
        calories: profile.profile?.daily_calorie_target ?? null,
        protein_g: profile.profile?.protein_g_target ?? null,
        carbs_g: profile.profile?.carbs_g_target ?? null,
        fat_g: profile.profile?.fat_g_target ?? null,
        fiber_g: profile.profile?.fiber_g_target ?? null,
        water_ml: profile.profile?.daily_water_ml_target ?? null,
      });
      // Most recently logged first, matching a "what did I just eat" feel.
      setTodaysMeals([...meals].sort((a, b) => b.created_at.localeCompare(a.created_at)));
    } catch {
      // Silent failure — Home's core content shouldn't break over this.
    }
  }, []);

  const loadWaterSummary = useCallback(async () => {
    try {
      const summary = await waterApi.getDaySummary(todayString());
      setWaterSummary(summary);
    } catch {
      // Silent failure — same reasoning as the other Home loaders.
      setWaterSummary(null);
    }
  }, []);


  const handleQuickLogWater = async (amountMl: number) => {
    setIsLoggingWater(true);
    try {
      await waterApi.logWater(todayString(), amountMl);
      await loadWaterSummary();
    } catch {
      // Silent failure — a missed quick-log tap isn't worth an alert;
      // the ring simply won't move and the user can try again.
    } finally {
      setIsLoggingWater(false);
    }
  };

  const handleConfirmationResolved = (resolvedItem: PendingConfirmation) => {
    setPendingConfirmations((prev) =>
      prev.filter(
        (item) =>
          !(item.source_type === resolvedItem.source_type && item.source_id === resolvedItem.source_id)
      )
    );
    loadTodayProgress();
  };

  // Silent, best-effort regional sync — runs ONCE on mount (not on
  // every focus, unlike the loaders below). Resolves the caller's
  // real IP address SERVER-SIDE to a country code and saves it —
  // REPLACES an earlier device-locale-based approach, which
  // conflated language preference with physical location (a user
  // can set their phone to "English (United States)" while living
  // anywhere else — confirmed as a real issue during testing). A
  // failure here is not shown to the user — recipe/meal-plan/coach
  // generation simply proceeds without a regional hint that
  // session, and this retries next app launch. Note: this always
  // resolves to null against a local/dev backend, since a
  // localhost/private IP has no geography to look up — only real
  // deployed traffic (e.g. the EC2 server) gets a real result. See
  // backend app/core/geolocation.py's module docstring.
  useEffect(() => {
    profileApi.detectRegion().catch(() => {
      // Silent — see comment above.
    });
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadSubscription();
      loadPendingConfirmations();
      loadTodayProgress();
      loadWaterSummary();
    }, [loadSubscription, loadPendingConfirmations, loadTodayProgress, loadWaterSummary])
  );

  const safePercent = (consumed: number, target: number | null): number => {
    if (!target || target <= 0) return 0;
    return (consumed / target) * 100;
  };

  // 6-card grid (3x2): Calories, Protein, Carbs, Fat, Fiber, Water.
  // Fiber added alongside the Home screen redesign (Aug 2026) — same
  // shape as every other macro ring (consumed/target/unit/color), so
  // it renders through the exact same grid-cell logic below with no
  // special-casing beyond the water ring's own pre-existing exception.
  const macroRings = [
    {
      key: 'calories',
      label: 'Calories',
      consumed: dailyTotals?.calories ?? 0,
      target: targets?.calories ?? null,
      unit: 'kcal',
      color: NUTRIENT_VISUALS.calories.color,
      icon: NUTRIENT_VISUALS.calories.icon,
    },
    {
      key: 'protein',
      label: 'Protein',
      consumed: dailyTotals?.protein_g ?? 0,
      target: targets?.protein_g ?? null,
      unit: 'g',
      color: NUTRIENT_VISUALS.protein.color,
      icon: NUTRIENT_VISUALS.protein.icon,
    },
    {
      key: 'carbs',
      label: 'Carbs',
      consumed: dailyTotals?.carbs_g ?? 0,
      target: targets?.carbs_g ?? null,
      unit: 'g',
      color: NUTRIENT_VISUALS.carbs.color,
      icon: NUTRIENT_VISUALS.carbs.icon,
    },
    {
      key: 'fat',
      label: 'Fat',
      consumed: dailyTotals?.fat_g ?? 0,
      target: targets?.fat_g ?? null,
      unit: 'g',
      color: NUTRIENT_VISUALS.fat.color,
      icon: NUTRIENT_VISUALS.fat.icon,
    },
    {
      key: 'fiber',
      label: 'Fiber',
      consumed: dailyTotals?.fiber_g ?? 0,
      target: targets?.fiber_g ?? null,
      unit: 'g',
      color: NUTRIENT_VISUALS.fiber.color,
      icon: NUTRIENT_VISUALS.fiber.icon,
    },
    {
      key: 'water',
      label: 'Water',
      consumed: waterSummary?.total_ml ?? 0,
      target: targets?.water_ml ?? null,
      unit: 'L',
      color: NUTRIENT_VISUALS.water.color,
      icon: NUTRIENT_VISUALS.water.icon,
    },
  ];

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.screenBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
      refreshControl={
        <RefreshControl refreshing={isRefreshing} onRefresh={() => loadSubscription(true)} />
      }
    >
      {/* Header */}
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 20,
        }}
      >
        <View style={{ flex: 1 }}>
          <ThemedText variant="h1">
            {timeOfDayGreeting()}, {user?.first_name ?? 'there'}! 👋
          </ThemedText>
          <ThemedText variant="body" color="textSecondary" style={{ marginTop: 2 }}>
            Let's make today a healthy one.
          </ThemedText>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <Image
            source={require('../../assets/images/avatar-male.png')}
            style={{ width: 44, height: 44, borderRadius: 22 }}
          />
          <Pressable
            onPress={signOut}
            style={{
              width: 32,
              height: 32,
              borderRadius: 16,
              overflow: 'hidden',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Image
              source={require('../../assets/images/logout-icon.png')}
              style={{ width: 32, height: 32 }}
              resizeMode="cover"
            />
          </Pressable>
        </View>
      </View>

      {/* Today at a glance — 3x2 card grid (was a horizontal scroll
          of 5 rings; now 6, including Fiber, laid out as two full rows
          of three so every card is visible at once with no scrolling).
          Converted to ThemedCard (Sep 4 2026 Phase 3) — style override
          keeps the original surfaceAlt bg + 12px radius exactly as
          before; glossy/shadow are ThemedCard's own additions. */}
      <ThemedCard
        style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', borderRadius: 12, padding: 16, marginBottom: 20 }}
      >
        <View
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 14,
          }}
        >
          <ThemedText variant="label" color="textPrimary">
            Today at a glance ⚡
          </ThemedText>
          <Pressable
            onPress={() => router.push('/(main)/goals')}
            style={{
              backgroundColor: colors.screenBg,
              borderWidth: 1,
              borderColor: colors.border,
              borderRadius: 100,
              paddingHorizontal: 10,
              paddingVertical: 4,
            }}
          >
            <ThemedText variant="label" style={{ color: colors.accentPeach }}>
              Edit goals ›
            </ThemedText>
          </Pressable>
        </View>

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
                ? getWaterRingColor(percent, colors)
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
                  {ring.icon} {ring.label}
                </Text>
                <Text
                  style={{
                    fontSize: 10,
                    color: ring.target
                      ? isOver && ring.key !== 'water'
                        ? colors.danger
                        : colors.textPrimary
                      : colors.textMuted,
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

        {/* Quick water log + pacing nudge — only shown once there's
            something real to react to (a target set, or at least one
            logged ml today), so an unset feature doesn't clutter Home. */}
        {(targets?.water_ml || (waterSummary?.total_ml ?? 0) > 0) && (
          <View style={{ marginTop: 14 }}>
            {waterSummary?.pace_status === 'behind' && (
              <Text style={{ fontSize: 11, color: colors.ringWater, marginBottom: 8 }}>
                💧 You're at {formatLiters(waterSummary.total_ml)}, aiming for ~
                {formatLiters(waterSummary.expected_so_far_ml ?? 0)} by now — grab a glass?
              </Text>
            )}
            <View style={{ flexDirection: 'row', gap: 8 }}>
              {[250, 500].map((amount) => (
                <Pressable
                  key={amount}
                  onPress={() => handleQuickLogWater(amount)}
                  disabled={isLoggingWater}
                  style={{
                    backgroundColor: colors.accentBlue + '1A',
                    borderRadius: 100,
                    paddingHorizontal: 14,
                    paddingVertical: 7,
                  }}
                >
                  <Text style={{ fontSize: 12, fontWeight: '600', color: colors.accentBlue }}>
                    + {amount}ml water
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        )}

        <Pressable
          onPress={() => router.push('/(main)/body-details')}
          style={{
            marginTop: 14,
            backgroundColor: colors.screenBg,
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 10,
            paddingVertical: 10,
            paddingHorizontal: 12,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Text style={{ fontSize: 11, color: colors.textSecondary, flex: 1, marginRight: 8 }}>
            Add your age, height & weight for your full nutrient breakdown
          </Text>
          <Text style={{ fontSize: 11, color: colors.accentPeach, fontWeight: '600' }}>Know more ›</Text>
        </Pressable>
      </ThemedCard>

      {/* Health Insights entry card — deliberately a rose/coral color
          family, distinct from every other card's palette on this
          screen (Calories orange, Protein green, Carbs blue, Fat
          gold, Fiber purple, Water teal), so it visually stands apart
          and draws the eye. The stethoscope + healing-heart combo
          icon reinforces the "health" theme; the heart pulses with a
          lightweight native-driven heartbeat animation (see
          heartbeatScale above) — a quick double-beat then a pause,
          matching a real pulse rather than continuous motion, so it
          stays eye-catching without becoming annoying. */}
      <Pressable
        onPress={() => router.push('/(main)/health-insights')}
        style={{ marginBottom: 20 }}
      >
        <ThemedCard
          style={{
            backgroundColor: colors.healthInsightsBg,
            borderColor: colors.healthInsightsBorder,
            borderRadius: 12,
            padding: 14,
            flexDirection: 'row',
            alignItems: 'center',
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center', marginRight: 10 }}>
            <Text style={{ fontSize: 20 }}>🩺</Text>
            <Animated.Text style={{ fontSize: 20, transform: [{ scale: heartbeatScale }] }}>
              ❤️‍🩹
            </Animated.Text>
          </View>
          <View style={{ flex: 1 }}>
            <ThemedText variant="h3" style={{ color: colors.healthInsightsText, marginBottom: 2 }}>
              Health Insights — only your health matters
            </ThemedText>
            <ThemedText variant="caption" style={{ color: colors.healthInsightsTextSecondary, lineHeight: 15 }}>
              Click here — take the first step toward understanding your health, honestly.
            </ThemedText>
          </View>
          <Text style={{ fontSize: 16, color: colors.healthInsightsText }}>›</Text>
        </ThemedCard>
      </Pressable>

      {/* "My History" — jumps straight to the most recently CONFIRMED
          health report's results, skipping the upload screen entirely.
          Placed right below the main card (not merged into the same
          Pressable) so the two actions stay clearly distinct: the card
          itself always starts a fresh upload, this always resumes a
          past one. */}
      <Pressable
        onPress={() => router.push('/(main)/health-insights?view=history' as any)}
        style={{
          alignSelf: 'flex-start',
          marginTop: -12,
          marginBottom: 20,
          paddingHorizontal: 4,
        }}
      >
        <ThemedText variant="label" style={{ color: colors.healthInsightsText }}>
          📄 My History ›
        </ThemedText>
      </Pressable>

      {isLoading ? (
        <View style={{ paddingVertical: 20, alignItems: 'center' }}>
          <ActivityIndicator color={colors.accentSage} />
        </View>
      ) : error ? (
        <ThemedCard
          padding={12}
          style={{ backgroundColor: colors.warningBg, borderColor: 'transparent', marginBottom: 20 }}
        >
          <ThemedText variant="bodySmall" style={{ color: colors.warningText }}>{error}</ThemedText>
          <Pressable onPress={() => loadSubscription()} style={{ marginTop: 6 }}>
            <ThemedText variant="label" style={{ color: colors.warningText }}>Retry</ThemedText>
          </Pressable>
        </ThemedCard>
      ) : null}

      {/* Quick actions — colored full-card style, reusing existing
          emoji icon system for visual consistency with the rest of
          the app rather than introducing a second icon system. */}
      <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 10 }}>
        Quick actions
      </ThemedText>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 24 }}>
        {MODULES.filter((mod) => mod.showInQuickActions !== false).map((mod) => (
          // Pressable is now just the touch target + width/opacity —
          // the actual card look (bg/radius/padding/shadow/gloss)
          // lives on the nested ThemedCard, since ThemedCard itself
          // is a plain View and can't carry onPress. The colored
          // per-module tint is passed through style, same override
          // pattern as every other ThemedCard conversion this pass.
          <Pressable
            key={mod.key}
            onPress={() => {
              if (mod.route) router.push(mod.route as any);
            }}
            disabled={!mod.route}
            style={{ width: '47%', opacity: mod.route ? 1 : 0.5 }}
          >
            <ThemedCard
              style={{
                backgroundColor: colors[mod.badgeColorKey] + '40',
                borderColor: 'transparent',
                borderRadius: 14,
                padding: 14,
                // Fixed minHeight so every tile matches regardless of
                // label/subtitle length — "Feedback & Reports" (the
                // longest label) was wrapping to 2 lines and growing
                // both itself and its row partner (RN stretches
                // same-row wrapped children to match height by
                // default), while every other tile's shorter label
                // stayed on 1 line. numberOfLines below is the actual
                // fix (caps every tile's content to the same shape);
                // minHeight is a floor so short-content tiles don't
                // look emptier than a tile with a truncated 2-line
                // subtitle sitting next to them.
                minHeight: 112,
              }}
            >
              <View
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 18,
                  backgroundColor: colors.screenBg,
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 10,
                }}
              >
                <Text style={{ fontSize: 16 }}>{mod.icon}</Text>
              </View>
              <ThemedText variant="h3" color="textPrimary" style={{ marginBottom: 2 }} numberOfLines={1}>
                {mod.label}
              </ThemedText>
              <ThemedText variant="caption" color="textSecondary" numberOfLines={2}>
                {mod.subtitle}
              </ThemedText>
            </ThemedCard>
          </Pressable>
        ))}
      </View>

      {/* Today's meals — real data from GET /nutrition-logs/day/{date}.
          Food-type emoji instead of photos, since food images are
          deliberately never stored server-side. */}
      <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 10 }}>
        Today's meals
      </ThemedText>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ flexGrow: 0, marginBottom: 24 }}
        contentContainerStyle={{ gap: 10, paddingRight: 8 }}
      >
        {todaysMeals.map((meal) => (
          <Pressable
            key={meal.id}
            onPress={() =>
              router.push({
                pathname: '/(main)/meal-detail/[logId]',
                params: { logId: meal.id, mealData: JSON.stringify(meal) },
              })
            }
            style={{
              width: 110,
              backgroundColor: colors.screenBg,
              borderWidth: 1,
              borderColor: colors.border,
              borderRadius: 12,
              padding: 10,
            }}
          >
            <View
              style={{
                height: 56,
                borderRadius: 8,
                backgroundColor: colors.surfaceAlt,
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 8,
              }}
            >
              <Text style={{ fontSize: 26 }}>{MEAL_TYPE_ICON[meal.meal_type]}</Text>
            </View>
            <Text
              style={{ fontSize: 11, fontWeight: '700', color: colors.textPrimary, marginBottom: 2 }}
              numberOfLines={1}
            >
              {meal.meal_type.charAt(0).toUpperCase() + meal.meal_type.slice(1)}
            </Text>
            <Text style={{ fontSize: 9, color: colors.textMuted, marginBottom: 3 }}>
              {formatLoggedTime(meal.created_at)}
            </Text>
            <Text style={{ fontSize: 10, color: colors.accentSage, fontWeight: '700' }}>
              {Math.round(meal.calories)} kcal
            </Text>
          </Pressable>
        ))}

        {/* "Add meal" — now wired to the real manual-entry form. */}
        <Pressable
          onPress={() => router.push('/(main)/log-meal')}
          style={{
            width: 110,
            borderWidth: 1,
            borderColor: colors.border,
            borderStyle: 'dashed',
            borderRadius: 12,
            padding: 10,
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Text style={{ fontSize: 22, color: colors.accentSage, marginBottom: 4 }}>+</Text>
          <Text style={{ fontSize: 10, color: colors.textSecondary }}>Add meal</Text>
        </Pressable>
      </ScrollView>

      {/* Chat prompt banner — reuses the mood check-in already built
          inside Coach; this is just a shortcut entry point to it. */}
      <Pressable
        onPress={() => router.push('/(main)/coach')}
        style={{ marginBottom: 24 }}
      >
        <ThemedCard
          style={{
            backgroundColor: colors.accentSage + '40',
            borderColor: 'transparent',
            borderRadius: 14,
            padding: 16,
            flexDirection: 'row',
            alignItems: 'center',
          }}
        >
          <Image
            source={require('../../assets/images/avatar-female.png')}
            style={{ width: 48, height: 48, borderRadius: 24, marginRight: 12 }}
          />
          <View style={{ flex: 1 }}>
            <ThemedText variant="h3">
              Hey {user?.first_name ?? 'there'}! 👋
            </ThemedText>
            <ThemedText variant="bodySmall" color="textSecondary" style={{ marginTop: 2 }}>
              How are you feeling today?
            </ThemedText>
          </View>
          <View
            style={{
              backgroundColor: colors.accentSage,
              borderRadius: 100,
              paddingHorizontal: 14,
              paddingVertical: 8,
            }}
          >
            <Text style={{ fontSize: 12, fontWeight: '700', color: '#fff' }}>Let's chat ›</Text>
          </View>
        </ThemedCard>
      </Pressable>

      {pendingConfirmations.length > 0 && (
        <View>
          <ThemedText variant="label" color="textPrimary" style={{ marginBottom: 4 }}>
            Log your calories
          </ThemedText>
          <ThemedText variant="caption" color="textSecondary" style={{ marginBottom: 10 }}>
            Quick check-ins for what you've recently made or scanned
          </ThemedText>
          {pendingConfirmations.map((item) => (
            <PendingConfirmationCard
              key={`${item.source_type}-${item.source_id}`}
              item={item}
              onResolved={() => handleConfirmationResolved(item)}
            />
          ))}
        </View>
      )}
    </ScrollView>
  );
}
