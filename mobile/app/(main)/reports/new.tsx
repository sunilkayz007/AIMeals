import { useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { reportsApi } from '../../../src/api/reports';
import type { ReportCategory } from '../../../src/api/reports';
import { ApiError } from '../../../src/api/client';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';

const CATEGORIES: { value: ReportCategory; label: string }[] = [
  { value: 'bug', label: 'Bug' },
  { value: 'suggestion', label: 'Suggestion' },
  { value: 'complaint', label: 'Complaint' },
  { value: 'praise', label: 'Praise' },
];

export default function NewReport() {
  const router = useRouter();
  const { colors } = useTheme();

  const [category, setCategory] = useState<ReportCategory>('bug');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = title.trim().length > 0 && description.trim().length > 0 && !isSaving;

  const submit = async () => {
    if (!canSubmit) return;
    setIsSaving(true);
    setError(null);
    try {
      await reportsApi.create(category, title.trim(), description.trim());
      router.back();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to submit — please try again');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
    >
      <Text style={{ fontSize: 22, fontWeight: '700', color: colors.textPrimary, marginBottom: 20 }}>
        New Report
      </Text>

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 }}>
        CATEGORY
      </Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
        {CATEGORIES.map((c) => {
          const isSelected = category === c.value;
          return (
            <Pressable
              key={c.value}
              onPress={() => setCategory(c.value)}
              style={{
                paddingHorizontal: 14,
                paddingVertical: 8,
                borderRadius: RADIUS.chip,
                backgroundColor: isSelected ? colors.primary : colors.cardBg,
                borderWidth: 1,
                borderColor: isSelected ? colors.primary : colors.cardBorder,
              }}
            >
              <Text
                style={{
                  fontSize: 13,
                  fontWeight: '600',
                  color: isSelected ? '#fff' : colors.textPrimary,
                }}
              >
                {c.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 }}>
        TITLE
      </Text>
      <TextInput
        value={title}
        onChangeText={setTitle}
        placeholder="Short summary"
        placeholderTextColor={colors.textMuted}
        style={{
          backgroundColor: colors.cardBg,
          borderWidth: 1,
          borderColor: colors.cardBorder,
          borderRadius: RADIUS.card,
          padding: 12,
          fontSize: 14,
          color: colors.textPrimary,
          marginBottom: 20,
        }}
      />

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 }}>
        DESCRIPTION
      </Text>
      <TextInput
        value={description}
        onChangeText={setDescription}
        placeholder="Tell us what happened, or what you'd like to see"
        placeholderTextColor={colors.textMuted}
        multiline
        numberOfLines={6}
        textAlignVertical="top"
        style={{
          backgroundColor: colors.cardBg,
          borderWidth: 1,
          borderColor: colors.cardBorder,
          borderRadius: RADIUS.card,
          padding: 12,
          fontSize: 14,
          color: colors.textPrimary,
          minHeight: 120,
          marginBottom: 20,
        }}
      />

      {error && (
        <ThemedCard padding={12} style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', marginBottom: 16 }}>
          <Text style={{ color: colors.danger, fontSize: 13 }}>{error}</Text>
        </ThemedCard>
      )}

      <Pressable
        onPress={submit}
        disabled={!canSubmit}
        style={{
          backgroundColor: canSubmit ? colors.primary : colors.border,
          borderRadius: RADIUS.button,
          paddingVertical: 14,
          alignItems: 'center',
        }}
      >
        {isSaving ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>Submit</Text>
        )}
      </Pressable>
    </ScrollView>
  );
}
