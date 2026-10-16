import { useCallback, useState } from 'react';
import { View, Text, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { reportsApi } from '../../../src/api/reports';
import type { Report, ReportStatus, ReportCategory } from '../../../src/api/reports';
import { ApiError } from '../../../src/api/client';
import { useTheme } from '../../../src/theme/ThemeContext';
import { useAuthStore } from '../../../src/stores/authStore';
import { RADIUS, CARD_SHADOW } from '../../../src/theme/layout';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import ThemedCard from '../../../src/components/ThemedCard';

const STATUS_LABEL: Record<ReportStatus, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  resolved: 'Resolved',
};

const CATEGORY_LABEL: Record<ReportCategory, string> = {
  bug: 'Bug',
  suggestion: 'Suggestion',
  complaint: 'Complaint',
  praise: 'Praise',
};

const CATEGORY_ICON: Record<ReportCategory, string> = {
  bug: '🐛',
  suggestion: '💡',
  complaint: '⚠️',
  praise: '🎉',
};

function getStatusColors(status: ReportStatus, colors: ReturnType<typeof useTheme>['colors']) {
  if (status === 'resolved') return { bg: colors.primaryDark, text: '#fff' };
  if (status === 'in_progress') return { bg: colors.primary, text: '#fff' };
  return { bg: colors.border, text: colors.textSecondary };
}

export default function ReportsList() {
  const router = useRouter();
  const { colors } = useTheme();
  const { user } = useAuthStore();

  const [reports, setReports] = useState<Report[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await reportsApi.list();
      setReports(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load your reports');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  // A non-admin's list is always exclusively their own reports
  // (enforced server-side) — so seeing any report authored by
  // someone else is a reliable signal this viewer is an admin,
  // without needing a separate role field on the frontend.
  const isAdminView = reports.some((r) => r.user_email !== user?.email);
  const pendingCount = reports.filter((r) => r.status !== 'resolved').length;

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
    >
      <Text style={{ fontSize: 22, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
        Feedback & Reports 📝
      </Text>
      <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
        Tell us what's working, what's not, or what you'd like to see. We read every one.
      </Text>

      {isAdminView && (
        <View style={{ flexDirection: 'row', gap: 10, marginBottom: 20 }}>
          <ThemedCard style={{ flex: 1 }}>
            <Text style={{ fontSize: 24, fontWeight: '800', color: colors.textPrimary }}>
              {reports.length}
            </Text>
            <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>
              Total Reports
            </Text>
          </ThemedCard>
          <ThemedCard style={{ flex: 1 }}>
            <Text style={{ fontSize: 24, fontWeight: '800', color: pendingCount > 0 ? colors.primary : colors.textPrimary }}>
              {pendingCount}
            </Text>
            <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>
              Pending Threads
            </Text>
          </ThemedCard>
        </View>
      )}

      <Pressable
        onPress={() => router.push('/(main)/reports/new')}
        style={{
          backgroundColor: colors.primary,
          borderRadius: RADIUS.button,
          paddingVertical: 14,
          alignItems: 'center',
          marginBottom: 24,
          ...CARD_SHADOW,
        }}
      >
        <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>+ New Report</Text>
      </Pressable>

      {isLoading ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 20 }} />
      ) : error ? (
        <ThemedCard padding={14} style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent' }}>
          <Text style={{ color: colors.danger, fontSize: 13 }}>{error}</Text>
          <Pressable onPress={load} style={{ marginTop: 6 }}>
            <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
          </Pressable>
        </ThemedCard>
      ) : reports.length === 0 ? (
        <View style={{ paddingVertical: 40, alignItems: 'center' }}>
          <Text style={{ fontSize: 28, marginBottom: 8 }}>📭</Text>
          <Text style={{ fontSize: 13, color: colors.textSecondary, textAlign: 'center' }}>
            No reports yet. Anything you submit shows up here, along with our reply.
          </Text>
        </View>
      ) : (
        <View style={{ gap: 10 }}>
          {reports.map((report) => {
            const statusColors = getStatusColors(report.status, colors);
            return (
              <Pressable
                key={report.id}
                onPress={() => router.push(`/(main)/reports/${report.id}`)}
              >
                <ThemedCard>
                <View style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
                  <Text style={{ fontSize: 22, marginRight: 10 }}>{CATEGORY_ICON[report.category]}</Text>
                  <View style={{ flex: 1 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <Text style={{ fontSize: 11, fontWeight: '600', color: colors.textSecondary }}>
                        {CATEGORY_LABEL[report.category]}
                        {isAdminView && user?.email !== report.user_email ? ` · ${report.user_email}` : ''}
                      </Text>
                      <View
                        style={{
                          backgroundColor: statusColors.bg,
                          paddingHorizontal: 10,
                          paddingVertical: 4,
                          borderRadius: RADIUS.chip,
                        }}
                      >
                        <Text style={{ fontSize: 10, fontWeight: '700', color: statusColors.text }}>
                          {STATUS_LABEL[report.status]}
                        </Text>
                      </View>
                    </View>
                    <Text style={{ fontSize: 15, fontWeight: '600', color: colors.textPrimary }}>
                      {report.title}
                    </Text>
                  </View>
                </View>
                </ThemedCard>
              </Pressable>
            );
          })}
        </View>
      )}
    </ScrollView>

    <ModuleNavBar currentKey="reports" />
    </View>
  );
}
