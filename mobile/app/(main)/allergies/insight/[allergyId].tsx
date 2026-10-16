import { useCallback, useState } from 'react';
import { View, Text, Pressable, ActivityIndicator, ScrollView, Alert } from 'react-native';
import { useRouter, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { allergenInsightApi, TierUpgradeRequiredError, type AllergenInsight } from '../../../../src/api/allergenInsight';
import { ApiError } from '../../../../src/api/client';
import { useTheme } from '../../../../src/theme/ThemeContext';
import ThemedCard from '../../../../src/components/ThemedCard';

export default function AllergenInsightScreen() {
  const router = useRouter();
  const { colors } = useTheme();
  const { allergyId } = useLocalSearchParams<{ allergyId: string }>();

  const [insight, setInsight] = useState<AllergenInsight | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [isUnlocking, setIsUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!allergyId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await allergenInsightApi.getInsight(allergyId);
      setInsight(data);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load allergen info');
    } finally {
      setIsLoading(false);
    }
  }, [allergyId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleKnowMore = async () => {
    if (!allergyId) return;
    setIsUnlocking(true);
    setUnlockError(null);
    try {
      const result = await allergenInsightApi.getDeepInsight(allergyId);
      setInsight((prev) =>
        prev ? { ...prev, is_unlocked: true, deep_insight_text: result.deep_insight_text } : prev
      );
    } catch (err) {
      if (err instanceof TierUpgradeRequiredError) {
        Alert.alert(
          'Upgrade required',
          'Deep allergen breakdowns are available on Plus and Pro plans.',
          [
            { text: 'Not now', style: 'cancel' },
            { text: 'View plans', onPress: () => router.push('/(main)/credits') },
          ]
        );
      } else if (err instanceof ApiError && err.status === 402) {
        setUnlockError("You're out of credits this period — check Credits for your renewal date.");
      } else {
        setUnlockError(err instanceof Error ? err.message : 'Failed to load the deep breakdown');
      }
    } finally {
      setIsUnlocking(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}
      >
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        {isLoading ? (
          <View style={{ paddingVertical: 40, alignItems: 'center' }}>
            <ActivityIndicator color={colors.danger} />
          </View>
        ) : loadError ? (
          <ThemedCard padding={12} style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', borderRadius: 10 }}>
            <Text style={{ color: colors.danger, fontSize: 12 }}>{loadError}</Text>
            <Pressable onPress={load} style={{ marginTop: 6 }}>
              <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
            </Pressable>
          </ThemedCard>
        ) : insight ? (
          <>
            <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary, marginBottom: 16 }}>
              {insight.allergy_name}
            </Text>

            {/* Free short insight — always shown */}
            <ThemedCard
              padding={14}
              style={{ backgroundColor: colors.screenBg, borderColor: colors.border, borderRadius: 10, marginBottom: 16 }}
            >
              <Text style={{ fontSize: 13, color: colors.textPrimary, lineHeight: 19 }}>
                {insight.short_insight_text}
              </Text>
            </ThemedCard>

            {/* Deep insight — unlocked, or the "Know more" gate */}
            {insight.is_unlocked && insight.deep_insight_text ? (
              <ThemedCard padding={14} style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', borderRadius: 10 }}>
                <Text style={{ fontSize: 11, fontWeight: '700', color: colors.textSecondary, marginBottom: 8 }}>
                  FULL BREAKDOWN
                </Text>
                <Text style={{ fontSize: 13, color: colors.textPrimary, lineHeight: 20 }}>
                  {insight.deep_insight_text}
                </Text>
              </ThemedCard>
            ) : (
              <Pressable onPress={handleKnowMore} disabled={isUnlocking}>
                <ThemedCard
                  style={{
                    backgroundColor: colors.accentLavender + '1A',
                    borderColor: colors.accentLavender,
                    borderRadius: 10,
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <View style={{ flex: 1, paddingRight: 10 }}>
                    <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }}>
                      Know more →
                    </Text>
                    <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>
                      Hidden sources, label names to watch for, and cross-contact risks
                    </Text>
                  </View>
                  {isUnlocking && <ActivityIndicator size="small" color={colors.accentLavender} />}
                </ThemedCard>
              </Pressable>
            )}

            {unlockError && (
              <Text style={{ fontSize: 12, color: colors.danger, marginTop: 10 }}>{unlockError}</Text>
            )}

            <ThemedCard
              padding={10}
              style={{ flexDirection: 'row', backgroundColor: colors.warningBg, borderColor: 'transparent', borderRadius: 8, marginTop: 14 }}
            >
              <Text style={{ fontSize: 12, marginRight: 6 }}>⚕️</Text>
              <Text style={{ fontSize: 11, color: colors.warningText, flex: 1, lineHeight: 16 }}>
                Any medications mentioned above should only be used if prescribed by your
                physician or doctor — this isn't medical advice.
              </Text>
            </ThemedCard>
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}
