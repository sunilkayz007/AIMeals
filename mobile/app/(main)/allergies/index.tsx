import { useCallback, useState } from 'react';
import { View, Text, Pressable, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { profileApi } from '../../../src/api/profile';
import { getAllergyFacts, type AllergyFact } from '../../../src/api/allergyFacts';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import { useTheme } from '../../../src/theme/ThemeContext';
import ThemedCard from '../../../src/components/ThemedCard';
import { RADIUS } from '../../../src/theme/layout';
import type { Allergy, AllergySeverity } from '../../../src/types/profile';
import type { ThemeColors } from '../../../src/theme/colors';

// Renamed from the old local `colors` (it shadowed useTheme()'s colors
// within .map() — harmless since it was never actually the theme, but
// confusing to read) to `severityColors`.
function getSeverityColors(
  colors: ThemeColors
): Record<AllergySeverity, { bg: string; text: string }> {
  return {
    mild: { bg: colors.severityMildBg, text: colors.severityMildText },
    moderate: { bg: colors.severityModerateBg, text: colors.severityModerateText },
    severe: { bg: colors.severitySevereBg, text: colors.severitySevereText },
  };
}

export default function Allergies() {
  const router = useRouter();
  const { colors } = useTheme();
  const severityColors = getSeverityColors(colors);

  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [facts, setFacts] = useState<AllergyFact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingFacts, setIsLoadingFacts] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const profile = await profileApi.getFull();
      setAllergies(profile.allergies);

      if (profile.allergies.length > 0) {
        setIsLoadingFacts(true);
        const generatedFacts = await getAllergyFacts();
        setFacts(generatedFacts);
        setIsLoadingFacts(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load allergies');
      setIsLoadingFacts(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
    <ScrollView
      style={{ flex: 1 }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
      </Pressable>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
        Allergies ⚠️
      </Text>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <Text style={{ fontSize: 13, color: colors.textSecondary, flex: 1, marginRight: 12 }}>
          What to watch out for based on your allergy settings
        </Text>
        <Pressable
          onPress={() => router.push('/(main)/allergies/manage')}
          style={{
            backgroundColor: colors.primary,
            paddingHorizontal: 14,
            paddingVertical: 9,
            borderRadius: RADIUS.button,
          }}
        >
          <Text style={{ color: '#fff', fontSize: 12, fontWeight: '600' }}>+ Manage</Text>
        </Pressable>
      </View>

      {isLoading ? (
        <View style={{ paddingVertical: 40, alignItems: 'center' }}>
          <ActivityIndicator color={colors.danger} />
        </View>
      ) : error ? (
        <ThemedCard padding={14} style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent' }}>
          <Text style={{ color: colors.danger, fontSize: 12 }}>{error}</Text>
          <Pressable onPress={load} style={{ marginTop: 6 }}>
            <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
          </Pressable>
        </ThemedCard>
      ) : allergies.length === 0 ? (
        <View style={{ paddingVertical: 40, alignItems: 'center' }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary, textAlign: 'center' }}>
            No allergies on file yet. Add them in Settings to see relevant facts here.
          </Text>
        </View>
      ) : (
        <>
          <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 }}>
            Your allergies
          </Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 24 }}>
            {allergies.map((allergy) => {
              const sevColors = severityColors[allergy.severity];
              return (
                <View
                  key={allergy.id}
                  style={{
                    backgroundColor: sevColors.bg,
                    paddingHorizontal: 10,
                    paddingVertical: 6,
                    borderRadius: RADIUS.chip,
                  }}
                >
                  <Text style={{ fontSize: 11, fontWeight: '600', color: sevColors.text }}>
                    {allergy.allergy_name} · {allergy.severity}
                  </Text>
                </View>
              );
            })}
          </View>

          <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 10 }}>
            About your allergies
          </Text>
          <ThemedCard padding={0} style={{ marginBottom: 24, overflow: 'hidden' }}>
            {allergies.map((allergy, i) => (
              <Pressable
                key={allergy.id}
                onPress={() =>
                  router.push(`/(main)/allergies/insight/${allergy.allergy_id}`)
                }
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingVertical: 14,
                  paddingHorizontal: 16,
                  borderBottomWidth: i === allergies.length - 1 ? 0 : 1,
                  borderBottomColor: colors.border,
                }}
              >
                <View style={{ flex: 1, marginRight: 10 }}>
                  <Text style={{ fontSize: 13, fontWeight: '600', color: colors.textPrimary }}>
                    {allergy.allergy_name}{' '}
                    <Text style={{ fontWeight: '400', color: colors.textSecondary }}>({allergy.severity})</Text>
                  </Text>
                </View>
                <Text style={{ fontSize: 16, color: colors.textMuted }}>›</Text>
              </Pressable>
            ))}
          </ThemedCard>

          <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 10 }}>
            Things you might not know
          </Text>

          {isLoadingFacts ? (
            <View style={{ paddingVertical: 20, alignItems: 'center' }}>
              <ActivityIndicator color={colors.danger} size="small" />
            </View>
          ) : (
            <>
              <ThemedCard padding={16}>
                {facts.map((fact, i) => (
                  <View
                    key={i}
                    style={{
                      flexDirection: 'row',
                      marginBottom: i === facts.length - 1 ? 0 : 12,
                    }}
                  >
                    <Text style={{ color: colors.severitySevereText, fontSize: 13, marginRight: 6 }}>●</Text>
                    <Text style={{ color: colors.textPrimary, fontSize: 13, flex: 1, lineHeight: 19 }}>
                      {fact.text}
                    </Text>
                  </View>
                ))}
              </ThemedCard>

              {/* Only shown when a fact actually touches medication/
                  treatment content — keyed off the backend's per-fact
                  category, not a text guess. */}
              {facts.some((f) => f.category === 'treatment') && (
                <ThemedCard
                  padding={10}
                  style={{
                    flexDirection: 'row',
                    backgroundColor: colors.warningBg,
                    borderColor: 'transparent',
                    borderRadius: 12,
                    marginTop: 10,
                  }}
                >
                  <Text style={{ fontSize: 12, marginRight: 6 }}>⚕️</Text>
                  <Text style={{ fontSize: 11, color: colors.warningText, flex: 1, lineHeight: 16 }}>
                    Any medications mentioned above should only be used if prescribed by your
                    physician or doctor — this isn't medical advice.
                  </Text>
                </ThemedCard>
              )}
            </>
          )}
        </>
      )}
    </ScrollView>

    <ModuleNavBar currentKey="allergies" />
    </View>
  );
}
