import { useCallback, useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView, Alert } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { profileApi } from '../../../src/api/profile';
import { ApiError } from '../../../src/api/client';
import { useTheme } from '../../../src/theme/ThemeContext';
import ThemedCard from '../../../src/components/ThemedCard';
import type { Allergy, AllergySeverity } from '../../../src/types/profile';

const SEVERITIES: AllergySeverity[] = ['mild', 'moderate', 'severe'];

export default function ManageAllergies() {
  const router = useRouter();
  const { colors } = useTheme();

  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [severity, setSeverity] = useState<AllergySeverity>('moderate');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [removingId, setRemovingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const profile = await profileApi.getFull();
      setAllergies(profile.allergies);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load allergies');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleAdd = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;

    setIsSaving(true);
    setSaveError(null);
    try {
      await profileApi.addAllergy({ allergy_name: trimmed, severity });
      setName('');
      setSeverity('moderate');
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setSaveError(`You already have an allergy entry for "${trimmed}".`);
      } else {
        setSaveError(err instanceof Error ? err.message : 'Failed to add allergy');
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleRemove = (allergy: Allergy) => {
    Alert.alert(
      'Remove allergy?',
      `Remove "${allergy.allergy_name}" from your allergy list? Recipes and suggestions will stop filtering for it.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            setRemovingId(allergy.id);
            try {
              // Backend matches removal against the master allergy_id,
              // not this link row's own id — see ProfileService.remove_allergy.
              await profileApi.removeAllergy(allergy.allergy_id);
              setAllergies((prev) => prev.filter((a) => a.id !== allergy.id));
            } catch (err) {
              Alert.alert('Error', err instanceof Error ? err.message : 'Failed to remove allergy');
            } finally {
              setRemovingId(null);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        <Text style={{ fontSize: 18, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
          Manage allergies
        </Text>
        <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 20 }}>
          Recipes and suggestions are filtered based on this list
        </Text>

        {/* Current allergies */}
        {isLoading ? (
          <View style={{ paddingVertical: 24, alignItems: 'center' }}>
            <ActivityIndicator color={colors.danger} />
          </View>
        ) : loadError ? (
          <ThemedCard
            padding={12}
            style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', borderRadius: 10, marginBottom: 20 }}
          >
            <Text style={{ color: colors.danger, fontSize: 12 }}>{loadError}</Text>
            <Pressable onPress={load} style={{ marginTop: 6 }}>
              <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
            </Pressable>
          </ThemedCard>
        ) : allergies.length === 0 ? (
          <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
            No allergies on file yet — add your first one below.
          </Text>
        ) : (
          <View style={{ marginBottom: 24 }}>
            {allergies.map((allergy) => (
              <ThemedCard
                key={allergy.id}
                padding={0}
                style={{
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  backgroundColor: colors.screenBg,
                  borderColor: colors.border,
                  borderRadius: 10,
                  paddingVertical: 10,
                  paddingHorizontal: 14,
                  marginBottom: 8,
                }}
              >
                <View>
                  <Text style={{ fontSize: 14, fontWeight: '600', color: colors.textPrimary }}>
                    {allergy.allergy_name}
                  </Text>
                  <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2, textTransform: 'capitalize' }}>
                    {allergy.severity}
                  </Text>
                </View>
                <Pressable onPress={() => handleRemove(allergy)} disabled={removingId === allergy.id}>
                  {removingId === allergy.id ? (
                    <ActivityIndicator size="small" color={colors.danger} />
                  ) : (
                    <Text style={{ fontSize: 12, fontWeight: '600', color: colors.danger }}>Remove</Text>
                  )}
                </Pressable>
              </ThemedCard>
            ))}
          </View>
        )}

        {/* Add form */}
        <Text style={{ fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 10 }}>
          Add an allergy
        </Text>

        <TextInput
          placeholder="e.g. Peanuts, Shellfish, String bean"
          placeholderTextColor={colors.textMuted}
          value={name}
          onChangeText={(t) => {
            setName(t);
            if (saveError) setSaveError(null);
          }}
          style={{
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 8,
            paddingHorizontal: 14,
            paddingVertical: 10,
            fontSize: 13,
            color: colors.textPrimary,
            marginBottom: 12,
          }}
        />

        <View style={{ flexDirection: 'row', gap: 8, marginBottom: 14 }}>
          {SEVERITIES.map((s) => {
            const isActive = severity === s;
            return (
              <Pressable
                key={s}
                onPress={() => setSeverity(s)}
                style={{
                  flex: 1,
                  paddingVertical: 9,
                  borderRadius: 8,
                  alignItems: 'center',
                  backgroundColor: isActive ? colors.danger : colors.surfaceAlt,
                }}
              >
                <Text
                  style={{
                    fontSize: 12,
                    fontWeight: '600',
                    color: isActive ? '#fff' : colors.textSecondary,
                    textTransform: 'capitalize',
                  }}
                >
                  {s}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {saveError && (
          <Text style={{ fontSize: 12, color: colors.danger, marginBottom: 10 }}>{saveError}</Text>
        )}

        <Pressable
          onPress={handleAdd}
          disabled={!name.trim() || isSaving}
          style={{
            backgroundColor: colors.danger,
            borderRadius: 8,
            paddingVertical: 12,
            alignItems: 'center',
            opacity: !name.trim() || isSaving ? 0.5 : 1,
          }}
        >
          {isSaving ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={{ color: '#fff', fontSize: 13, fontWeight: '600' }}>+ Add allergy</Text>
          )}
        </Pressable>
      </ScrollView>
    </View>
  );
}
