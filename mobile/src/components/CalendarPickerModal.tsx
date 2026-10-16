import { useState } from 'react';
import { View, Text, Pressable, Modal } from 'react-native';
import { useTheme } from '../theme/ThemeContext';
import { RADIUS, CARD_SHADOW } from '../theme/layout';

const WEEKDAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

// Formats using LOCAL date components, not toISOString() (which is
// UTC-based and can silently shift the date by a day depending on
// timezone) — matters a lot here since this feeds straight into a
// YYYY-MM-DD string sent to the backend.
function formatDateYMD(date: Date): string {
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function parseYMD(dateStr: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr);
  if (!match) return null;
  const [, y, m, d] = match;
  return new Date(parseInt(y, 10), parseInt(m, 10) - 1, parseInt(d, 10));
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function startOfDay(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

interface CalendarPickerModalProps {
  visible: boolean;
  /** Currently selected date, YYYY-MM-DD, if any */
  selectedDate?: string;
  /** Dates before this (YYYY-MM-DD) are disabled — e.g. today, or a chosen start date */
  minDate?: string;
  /** Dates after this (YYYY-MM-DD) are disabled — e.g. today, to block future dates */
  maxDate?: string;
  onSelect: (dateStr: string) => void;
  onClose: () => void;
}

export default function CalendarPickerModal({
  visible,
  selectedDate,
  minDate,
  maxDate,
  onSelect,
  onClose,
}: CalendarPickerModalProps) {
  const { colors } = useTheme();
  const today = startOfDay(new Date());
  const initial = (selectedDate && parseYMD(selectedDate)) || today;

  const [viewYear, setViewYear] = useState(initial.getFullYear());
  const [viewMonth, setViewMonth] = useState(initial.getMonth());

  const minDateObj = minDate ? parseYMD(minDate) : undefined;
  const maxDateObj = maxDate ? parseYMD(maxDate) : undefined;
  const selectedDateObj = selectedDate ? parseYMD(selectedDate) : null;

  const firstOfMonth = new Date(viewYear, viewMonth, 1);
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const startWeekday = firstOfMonth.getDay();

  const cells: (Date | null)[] = [
    ...Array(startWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => new Date(viewYear, viewMonth, i + 1)),
  ];

  const goToPrevMonth = () => {
    if (viewMonth === 0) {
      setViewYear((y) => y - 1);
      setViewMonth(11);
    } else {
      setViewMonth((m) => m - 1);
    }
  };

  const goToNextMonth = () => {
    if (viewMonth === 11) {
      setViewYear((y) => y + 1);
      setViewMonth(0);
    } else {
      setViewMonth((m) => m + 1);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable
        onPress={onClose}
        style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'center', alignItems: 'center' }}
      >
        <Pressable
          onPress={(e) => e.stopPropagation()}
          style={{
            backgroundColor: colors.cardBg,
            borderRadius: RADIUS.card,
            padding: 18,
            width: 320,
            ...CARD_SHADOW,
          }}
        >
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Pressable onPress={goToPrevMonth} style={{ padding: 8 }}>
              <Text style={{ fontSize: 16, color: colors.textPrimary }}>‹</Text>
            </Pressable>
            <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary }}>
              {MONTH_LABELS[viewMonth]} {viewYear}
            </Text>
            <Pressable onPress={goToNextMonth} style={{ padding: 8 }}>
              <Text style={{ fontSize: 16, color: colors.textPrimary }}>›</Text>
            </Pressable>
          </View>

          <View style={{ flexDirection: 'row', marginBottom: 6 }}>
            {WEEKDAY_LABELS.map((label, i) => (
              <View key={i} style={{ width: 40, alignItems: 'center' }}>
                <Text style={{ fontSize: 11, fontWeight: '600', color: colors.textMuted }}>{label}</Text>
              </View>
            ))}
          </View>

          <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
            {cells.map((cellDate, i) => {
              if (!cellDate) return <View key={i} style={{ width: 40, height: 40 }} />;

              const isBeforeMin = minDateObj ? startOfDay(cellDate) < startOfDay(minDateObj) : false;
              const isAfterMax = maxDateObj ? startOfDay(cellDate) > startOfDay(maxDateObj) : false;
              const isDisabled = isBeforeMin || isAfterMax;
              const isSelected = selectedDateObj ? isSameDay(cellDate, selectedDateObj) : false;
              const isToday = isSameDay(cellDate, today);

              return (
                <Pressable
                  key={i}
                  disabled={isDisabled}
                  onPress={() => onSelect(formatDateYMD(cellDate))}
                  style={{
                    width: 40,
                    height: 40,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <View
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 16,
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: isSelected ? colors.primary : 'transparent',
                      borderWidth: isToday && !isSelected ? 1 : 0,
                      borderColor: colors.primary,
                    }}
                  >
                    <Text
                      style={{
                        fontSize: 13,
                        fontWeight: isSelected || isToday ? '700' : '400',
                        color: isDisabled
                          ? colors.textMuted
                          : isSelected
                            ? '#fff'
                            : colors.textPrimary,
                      }}
                    >
                      {cellDate.getDate()}
                    </Text>
                  </View>
                </Pressable>
              );
            })}
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
