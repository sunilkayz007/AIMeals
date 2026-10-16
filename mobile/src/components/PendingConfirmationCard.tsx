import { useState } from 'react';
import { View, Text, Pressable } from 'react-native';
import { nutritionLogApi } from '../api/nutritionLog';
import PercentageSlider from './PercentageSlider';
import type { MealType, PendingConfirmation } from '../types/nutritionLog';

const ACCENT = '#43A05A'; // sage

const MEAL_TYPES: { value: MealType; label: string }[] = [
  { value: 'breakfast', label: 'Breakfast' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'dinner', label: 'Dinner' },
  { value: 'snack', label: 'Snack' },
];

// Simple time-of-day heuristic for a sensible default — not asked to
// be clever about it, just avoids everyone having to manually pick
// "Snack" or whatever every single time when the obvious answer is
// usually right.
function defaultMealType(): MealType {
  const hour = new Date().getHours();
  if (hour < 11) return 'breakfast';
  if (hour < 15) return 'lunch';
  if (hour < 18) return 'snack';
  return 'dinner';
}

interface PendingConfirmationCardProps {
  item: PendingConfirmation;
  onResolved: () => void; // called after log or dismiss succeeds, to remove from the list
}

export default function PendingConfirmationCard({ item, onResolved }: PendingConfirmationCardProps) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [mealType, setMealType] = useState<MealType>(defaultMealType());
  const [portion, setPortion] = useState(100);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDismiss = async () => {
    setIsSubmitting(true);
    try {
      await nutritionLogApi.dismissConfirmation(item.source_type, item.source_id);
      onResolved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to dismiss');
      setIsSubmitting(false);
    }
  };

  const handleLogIt = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      if (item.source_type === 'recipe') {
        await nutritionLogApi.logFromRecipe(item.source_id, mealType, portion);
      } else {
        await nutritionLogApi.logFromFoodImage(item.source_id, mealType, portion);
      }
      onResolved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log');
      setIsSubmitting(false);
    }
  };

  return (
    <View
      style={{
        backgroundColor: '#FFFFFF',
        borderWidth: 1,
        borderColor: '#EDEFE4',
        borderRadius: 12,
        padding: 14,
        marginBottom: 10,
      }}
    >
      <Text style={{ fontSize: 13, color: '#4A4640', lineHeight: 19 }}>
        Did you have the{' '}
        <Text style={{ fontWeight: '700' }}>{item.title}</Text>
        {item.source_type === 'recipe' ? ' you made' : ' you scanned'} earlier?
      </Text>

      {!isConfirming ? (
        <View style={{ flexDirection: 'row', gap: 10, marginTop: 12 }}>
          <Pressable
            onPress={handleDismiss}
            disabled={isSubmitting}
            style={{
              flex: 1,
              borderWidth: 1,
              borderColor: '#E0DCC9',
              borderRadius: 8,
              paddingVertical: 10,
              alignItems: 'center',
              opacity: isSubmitting ? 0.5 : 1,
            }}
          >
            <Text style={{ fontSize: 13, fontWeight: '600', color: '#9B9686' }}>No</Text>
          </Pressable>
          <Pressable
            onPress={() => setIsConfirming(true)}
            disabled={isSubmitting}
            style={{
              flex: 1,
              backgroundColor: ACCENT,
              borderRadius: 8,
              paddingVertical: 10,
              alignItems: 'center',
              opacity: isSubmitting ? 0.5 : 1,
            }}
          >
            <Text style={{ fontSize: 13, fontWeight: '600', color: '#fff' }}>Yes</Text>
          </Pressable>
        </View>
      ) : (
        <View style={{ marginTop: 14 }}>
          <Text style={{ fontSize: 11, fontWeight: '600', color: '#5B5648', marginBottom: 8 }}>
            Which meal?
          </Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
            {MEAL_TYPES.map((mt) => {
              const isSelected = mealType === mt.value;
              return (
                <Pressable
                  key={mt.value}
                  onPress={() => setMealType(mt.value)}
                  style={{
                    paddingHorizontal: 12,
                    paddingVertical: 6,
                    borderRadius: 100,
                    backgroundColor: isSelected ? ACCENT : '#EEF2E7',
                  }}
                >
                  <Text
                    style={{
                      fontSize: 11,
                      fontWeight: '600',
                      color: isSelected ? '#fff' : '#5B5648',
                    }}
                  >
                    {mt.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
            <Text style={{ fontSize: 11, fontWeight: '600', color: '#5B5648' }}>
              How much did you eat?
            </Text>
            <Text style={{ fontSize: 13, fontWeight: '700', color: ACCENT }}>{portion}%</Text>
          </View>
          <PercentageSlider value={portion} onChange={setPortion} accentColor={ACCENT} />

          {error ? (
            <Text style={{ color: '#E05B5B', fontSize: 11, marginTop: 8 }}>{error}</Text>
          ) : null}

          <View style={{ flexDirection: 'row', gap: 10, marginTop: 16 }}>
            <Pressable
              onPress={() => setIsConfirming(false)}
              disabled={isSubmitting}
              style={{
                flex: 1,
                borderWidth: 1,
                borderColor: '#E0DCC9',
                borderRadius: 8,
                paddingVertical: 10,
                alignItems: 'center',
                opacity: isSubmitting ? 0.5 : 1,
              }}
            >
              <Text style={{ fontSize: 13, fontWeight: '600', color: '#9B9686' }}>Back</Text>
            </Pressable>
            <Pressable
              onPress={handleLogIt}
              disabled={isSubmitting}
              style={{
                flex: 1,
                backgroundColor: ACCENT,
                borderRadius: 8,
                paddingVertical: 10,
                alignItems: 'center',
                opacity: isSubmitting ? 0.5 : 1,
              }}
            >
              <Text style={{ fontSize: 13, fontWeight: '600', color: '#fff' }}>
                {isSubmitting ? 'Logging…' : 'Log it'}
              </Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}
