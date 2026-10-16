import { useState } from 'react';
import { View, Text, Pressable, TextInput, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { pantryApi } from '../../../src/api/pantry';
import { COMMON_UNITS } from '../../../src/types/pantry';
import { getIngredientSuggestions } from '../../../src/data/commonIngredients';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';

function isValidDateFormat(value: string): boolean {
  if (!value) return true;
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !isNaN(Date.parse(value));
}

export default function AddPantryItem() {
  const router = useRouter();
  const { colors } = useTheme();

  const [ingredientName, setIngredientName] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState<string | null>(null);
  const [expirationDate, setExpirationDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const suggestions = showSuggestions ? getIngredientSuggestions(ingredientName) : [];
  const dateError = expirationDate && !isValidDateFormat(expirationDate);
  const canSubmit = !!ingredientName.trim() && !dateError && !isSubmitting;

  const handleSelectSuggestion = (name: string) => {
    setIngredientName(name);
    setShowSuggestions(false);
  };

  const handleSubmit = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await pantryApi.add({
        ingredient_name: ingredientName.trim(),
        quantity: quantity ? parseFloat(quantity) : undefined,
        unit: unit ?? undefined,
        expiration_date: expirationDate || undefined,
      });
      router.back();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add item');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60 }}
      keyboardShouldPersistTaps="handled"
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Cancel</Text>
      </Pressable>

      <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 20 }}>
        Add pantry item
      </Text>

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 }}>
        Ingredient name
      </Text>
      <TextInput
        placeholder="e.g. Tomatoes"
        placeholderTextColor={colors.textMuted}
        value={ingredientName}
        onChangeText={(text) => {
          setIngredientName(text);
          setShowSuggestions(true);
        }}
        onFocus={() => setShowSuggestions(true)}
        style={{
          borderWidth: 1,
          borderColor: colors.border,
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
          fontSize: 14,
          color: colors.textPrimary,
          backgroundColor: colors.cardBg,
        }}
      />

      {suggestions.length > 0 && (
        <View
          style={{
            borderWidth: 1,
            borderColor: colors.border,
            borderTopWidth: 0,
            borderBottomLeftRadius: 12,
            borderBottomRightRadius: 12,
            backgroundColor: colors.cardBg,
            marginTop: -1,
            overflow: 'hidden',
          }}
        >
          {suggestions.map((s, i) => (
            <Pressable
              key={s}
              onPress={() => handleSelectSuggestion(s)}
              style={{
                paddingHorizontal: 14,
                paddingVertical: 10,
                borderTopWidth: i === 0 ? 0 : 1,
                borderTopColor: colors.border,
              }}
            >
              <Text style={{ fontSize: 13, color: colors.textPrimary }}>{s}</Text>
            </Pressable>
          ))}
        </View>
      )}

      <View style={{ height: 16 }} />

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 }}>
        Quantity (optional)
      </Text>
      <TextInput
        placeholder="e.g. 500"
        placeholderTextColor={colors.textMuted}
        value={quantity}
        onChangeText={setQuantity}
        keyboardType="numeric"
        onFocus={() => setShowSuggestions(false)}
        style={{
          borderWidth: 1,
          borderColor: colors.border,
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
          fontSize: 14,
          color: colors.textPrimary,
          backgroundColor: colors.cardBg,
          marginBottom: 16,
        }}
      />

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 }}>
        Unit (optional)
      </Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {COMMON_UNITS.map((u) => {
          const isSelected = unit === u;
          return (
            <Pressable
              key={u}
              onPress={() => setUnit(isSelected ? null : u)}
              style={{
                paddingHorizontal: 14,
                paddingVertical: 8,
                borderRadius: RADIUS.chip,
                backgroundColor: isSelected ? colors.primary : colors.primaryLight,
              }}
            >
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: '600',
                  color: isSelected ? '#fff' : colors.primaryDark,
                }}
              >
                {u}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 }}>
        Expiration date (optional)
      </Text>
      <TextInput
        placeholder="YYYY-MM-DD"
        placeholderTextColor={colors.textMuted}
        value={expirationDate}
        onChangeText={setExpirationDate}
        onFocus={() => setShowSuggestions(false)}
        style={{
          borderWidth: 1,
          borderColor: dateError ? colors.danger : colors.border,
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
          fontSize: 14,
          color: colors.textPrimary,
          backgroundColor: colors.cardBg,
          marginBottom: 4,
        }}
      />
      {dateError ? (
        <Text style={{ fontSize: 11, color: colors.danger, marginBottom: 12 }}>
          Use format YYYY-MM-DD, e.g. 2026-08-15
        </Text>
      ) : (
        <View style={{ marginBottom: 16 }} />
      )}

      {error ? (
        <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 12 }}>{error}</Text>
      ) : null}

      <Pressable
        onPress={handleSubmit}
        disabled={!canSubmit}
        style={{
          backgroundColor: canSubmit ? colors.primary : colors.border,
          borderRadius: RADIUS.button,
          paddingVertical: 14,
          alignItems: 'center',
        }}
      >
        <Text style={{ color: '#fff', fontSize: 14, fontWeight: '600' }}>
          {isSubmitting ? 'Adding…' : 'Add to pantry'}
        </Text>
      </Pressable>
    </ScrollView>
  );
}
