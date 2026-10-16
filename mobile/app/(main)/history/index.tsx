import { useCallback, useState } from 'react';
import { View, Text, Pressable, ActivityIndicator } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { nutritionLogApi } from '../../../src/api/nutritionLog';
import { profileApi } from '../../../src/api/profile';
import { useTheme } from '../../../src/theme/ThemeContext';
import ThemedCard from '../../../src/components/ThemedCard';

const WEEKDAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

// Bucket thresholds for coloring a logged day. Tunable — these are a
// reasonable default, not derived from any existing backend constant
// (no "low"/"on target" threshold exists elsewhere in this codebase
// to reuse). ONLY applied when a calorie target is actually set on
// the profile; a logged day with no target falls back to a neutral
// "logged, no target to compare" style instead of guessing.
const LOW_THRESHOLD_PERCENT = 90; // < this % of target = "low"
const OVER_THRESHOLD_PERCENT = 110; // > this % of target = "over"

type DayBucket = 'low' | 'on_target' | 'over' | 'logged_no_target' | 'none';

interface DayCell {
  dateStr: string; // YYYY-MM-DD, local
  dayOfMonth: number;
  isInCurrentMonth: boolean;
  isToday: boolean;
}

function todayString(): string {
  const d = new Date();
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
}

function toDateStr(year: number, monthIndex: number, day: number): string {
  return `${year}-${(monthIndex + 1).toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
}

// Builds a 6-row x 7-column grid covering the given month, padded
// with the trailing days of the previous month and leading days of
// the next month so every week row is always full. isInCurrentMonth
// distinguishes real cells from padding (padding cells are rendered
// blank/non-interactive).
function buildMonthGrid(year: number, monthIndex: number): DayCell[] {
  const firstOfMonth = new Date(year, monthIndex, 1);
  const startWeekday = firstOfMonth.getDay(); // 0 = Sunday
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, monthIndex, 0).getDate();
  const today = todayString();

  const cells: DayCell[] = [];

  // Leading padding from the previous month.
  for (let i = 0; i < startWeekday; i++) {
    const day = daysInPrevMonth - startWeekday + 1 + i;
    const prevMonthIndex = monthIndex === 0 ? 11 : monthIndex - 1;
    const prevYear = monthIndex === 0 ? year - 1 : year;
    const dateStr = toDateStr(prevYear, prevMonthIndex, day);
    cells.push({ dateStr, dayOfMonth: day, isInCurrentMonth: false, isToday: dateStr === today });
  }

  // The actual month.
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = toDateStr(year, monthIndex, day);
    cells.push({ dateStr, dayOfMonth: day, isInCurrentMonth: true, isToday: dateStr === today });
  }

  // Trailing padding from the next month, to fill out to a multiple of 7.
  const remainder = cells.length % 7;
  if (remainder !== 0) {
    const nextMonthIndex = monthIndex === 11 ? 0 : monthIndex + 1;
    const nextYear = monthIndex === 11 ? year + 1 : year;
    for (let day = 1; day <= 7 - remainder; day++) {
      const dateStr = toDateStr(nextYear, nextMonthIndex, day);
      cells.push({ dateStr, dayOfMonth: day, isInCurrentMonth: false, isToday: dateStr === today });
    }
  }

  return cells;
}

function bucketFor(caloriesForDay: number | undefined, target: number | null): DayBucket {
  if (caloriesForDay === undefined) return 'none';
  if (!target || target <= 0) return 'logged_no_target';
  const percent = (caloriesForDay / target) * 100;
  if (percent < LOW_THRESHOLD_PERCENT) return 'low';
  if (percent > OVER_THRESHOLD_PERCENT) return 'over';
  return 'on_target';
}

function bucketStyle(bucket: DayBucket, colors: any): { bg: string; text: string } {
  switch (bucket) {
    case 'low':
      return { bg: colors.dangerBg, text: colors.danger };
    case 'on_target':
      return { bg: colors.successBg, text: colors.successText };
    case 'over':
      // Solid bg + white text (not colors.dangerBg, which is meant as
      // a subtle tint behind colored text, not a background FOR white
      // text) — deliberately a bolder treatment than 'low', to make
      // "well over target" visually distinct from "a bit under."
      return { bg: colors.danger, text: '#FFFFFF' };
    case 'logged_no_target':
      return { bg: colors.surfaceAlt, text: colors.textPrimary };
    default:
      return { bg: colors.border + '40', text: colors.textMuted };
  }
}

export default function History() {
  const router = useRouter();
  const { colors } = useTheme();

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [monthIndex, setMonthIndex] = useState(now.getMonth());

  const [caloriesByDate, setCaloriesByDate] = useState<Record<string, number>>({});
  const [calorieTarget, setCalorieTarget] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
      const startDate = toDateStr(year, monthIndex, 1);
      const endDate = toDateStr(year, monthIndex, daysInMonth);

      const [logs, profileFull] = await Promise.all([
        nutritionLogApi.getLogsForRange(startDate, endDate),
        profileApi.getFull(),
      ]);

      const totals: Record<string, number> = {};
      for (const log of logs) {
        totals[log.logged_at] = (totals[log.logged_at] ?? 0) + log.calories;
      }
      setCaloriesByDate(totals);
      setCalorieTarget(profileFull.profile?.daily_calorie_target ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setIsLoading(false);
    }
  }, [year, monthIndex]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const goToPrevMonth = () => {
    if (monthIndex === 0) {
      setYear((y) => y - 1);
      setMonthIndex(11);
    } else {
      setMonthIndex((m) => m - 1);
    }
  };

  const goToNextMonth = () => {
    if (monthIndex === 11) {
      setYear((y) => y + 1);
      setMonthIndex(0);
    } else {
      setMonthIndex((m) => m + 1);
    }
  };

  const grid = buildMonthGrid(year, monthIndex);
  const monthLabel = new Date(year, monthIndex, 1).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  return (
    <View style={{ flex: 1, backgroundColor: colors.screenBg, padding: 20, paddingTop: 60 }}>
      <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
      </Pressable>

      <Text style={{ fontSize: 20, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
        History
      </Text>
      <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 20 }}>
        Tap a logged day to see what you ate
      </Text>

      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <Pressable onPress={goToPrevMonth} style={{ padding: 8 }}>
          <Text style={{ fontSize: 16, color: colors.accentPeach }}>‹</Text>
        </Pressable>
        <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary }}>{monthLabel}</Text>
        <Pressable onPress={goToNextMonth} style={{ padding: 8 }}>
          <Text style={{ fontSize: 16, color: colors.accentPeach }}>›</Text>
        </Pressable>
      </View>

      {isLoading ? (
        <View style={{ paddingVertical: 40, alignItems: 'center' }}>
          <ActivityIndicator color={colors.accentPeach} />
        </View>
      ) : error ? (
        <ThemedCard padding={12} style={{ backgroundColor: colors.warningBg, borderColor: 'transparent' }}>
          <Text style={{ color: colors.warningText, fontSize: 12 }}>{error}</Text>
          <Pressable onPress={load} style={{ marginTop: 6 }}>
            <Text style={{ color: colors.warningText, fontSize: 12, fontWeight: '600' }}>Retry</Text>
          </Pressable>
        </ThemedCard>
      ) : (
        <>
          <View style={{ flexDirection: 'row', marginBottom: 6 }}>
            {WEEKDAY_LABELS.map((label, i) => (
              <View key={i} style={{ flex: 1, alignItems: 'center' }}>
                <Text style={{ fontSize: 11, fontWeight: '600', color: colors.textMuted }}>{label}</Text>
              </View>
            ))}
          </View>

          <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
            {grid.map((cell) => {
              const bucket = cell.isInCurrentMonth ? bucketFor(caloriesByDate[cell.dateStr], calorieTarget) : 'none';
              const isClickable = cell.isInCurrentMonth && bucket !== 'none';
              const style = cell.isInCurrentMonth
                ? bucketStyle(bucket, colors)
                : { bg: 'transparent', text: colors.textMuted };

              return (
                <View key={cell.dateStr} style={{ width: `${100 / 7}%`, aspectRatio: 1, padding: 3 }}>
                  <Pressable
                    disabled={!isClickable}
                    onPress={() =>
                      router.push({ pathname: '/(main)/day-logs/[date]', params: { date: cell.dateStr } })
                    }
                    style={{
                      flex: 1,
                      borderRadius: 8,
                      backgroundColor: cell.isInCurrentMonth ? style.bg : 'transparent',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderWidth: cell.isToday ? 1.5 : 0,
                      borderColor: colors.accentPeach,
                      opacity: cell.isInCurrentMonth ? 1 : 0,
                    }}
                  >
                    <Text
                      style={{
                        fontSize: 12,
                        fontWeight: cell.isToday ? '700' : '500',
                        color: cell.isInCurrentMonth ? style.text : 'transparent',
                      }}
                    >
                      {cell.dayOfMonth}
                    </Text>
                  </Pressable>
                </View>
              );
            })}
          </View>

          {/* Legend */}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 14, marginTop: 24 }}>
            {[
              { bucket: 'low' as DayBucket, label: 'Low' },
              { bucket: 'on_target' as DayBucket, label: 'On target' },
              { bucket: 'over' as DayBucket, label: 'Over' },
              { bucket: 'none' as DayBucket, label: 'Not logged' },
            ].map(({ bucket, label }) => {
              const style = bucketStyle(bucket, colors);
              return (
                <View key={bucket} style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <View style={{ width: 12, height: 12, borderRadius: 4, backgroundColor: style.bg }} />
                  <Text style={{ fontSize: 11, color: colors.textSecondary }}>{label}</Text>
                </View>
              );
            })}
          </View>

          {!calorieTarget && (
            <Text style={{ fontSize: 10, color: colors.textMuted, marginTop: 14, textAlign: 'center' }}>
              Set a daily calorie goal to see Low/On target/Over coloring — logged days without a
              goal show neutral for now.
            </Text>
          )}
        </>
      )}
    </View>
  );
}
