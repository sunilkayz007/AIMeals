import { useCallback, useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { useFocusEffect, useLocalSearchParams } from 'expo-router';
import { reportsApi } from '../../../src/api/reports';
import type { ReportDetail, ReportStatus, ReportCategory, ReportComment } from '../../../src/api/reports';
import { ApiError } from '../../../src/api/client';
import { useTheme } from '../../../src/theme/ThemeContext';
import { useAuthStore } from '../../../src/stores/authStore';
import { RADIUS, CARD_SHADOW } from '../../../src/theme/layout';
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

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function getCommentAuthorLabel(comment: ReportComment, viewerEmail: string | undefined): string {
  if (comment.author_email === viewerEmail) return 'You';
  if (comment.is_admin_reply) return 'AIMeals Team';
  return comment.author_email;
}

export default function ReportDetailScreen() {
  const { colors } = useTheme();
  const { user } = useAuthStore();
  const { reportId } = useLocalSearchParams<{ reportId: string }>();

  const [report, setReport] = useState<ReportDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [replyText, setReplyText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [isClosing, setIsClosing] = useState(false);
  const [closeError, setCloseError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!reportId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await reportsApi.getDetail(reportId);
      setReport(data);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Failed to load this report');
    } finally {
      setIsLoading(false);
    }
  }, [reportId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const sendReply = async () => {
    if (!reportId || !replyText.trim() || isSending) return;
    setIsSending(true);
    setSendError(null);
    try {
      await reportsApi.addComment(reportId, replyText.trim());
      setReplyText('');
      await load();
    } catch (err) {
      setSendError(err instanceof ApiError ? err.message : 'Failed to send — please try again');
    } finally {
      setIsSending(false);
    }
  };

  const closeThread = async () => {
    if (!reportId || isClosing) return;
    setIsClosing(true);
    setCloseError(null);
    try {
      await reportsApi.closeReport(reportId);
      await load();
    } catch (err) {
      setCloseError(err instanceof ApiError ? err.message : 'Failed to close — please try again');
    } finally {
      setIsClosing(false);
    }
  };

  if (isLoading) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, justifyContent: 'center' }}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  if (loadError || !report) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, padding: 20 }}>
        <ThemedCard padding={14} style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent' }}>
          <Text style={{ color: colors.danger, fontSize: 13 }}>{loadError ?? 'Report not found'}</Text>
          <Pressable onPress={load} style={{ marginTop: 6 }}>
            <Text style={{ color: colors.danger, fontSize: 12, fontWeight: '600' }}>Retry</Text>
          </Pressable>
        </ThemedCard>
      </View>
    );
  }

  const statusColors = getStatusColors(report.status, colors);
  const isOwnReport = user?.email === report.user_email;
  const hasAdminReply = report.comments.some((c) => c.is_admin_reply);

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 20 }}>
        <ThemedCard padding={16} style={{ marginBottom: 20 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Text style={{ fontSize: 18 }}>{CATEGORY_ICON[report.category]}</Text>
              <Text style={{ fontSize: 11, fontWeight: '700', color: colors.textSecondary, textTransform: 'uppercase', letterSpacing: 0.4 }}>
                {CATEGORY_LABEL[report.category]}
              </Text>
            </View>
            <View
              style={{
                backgroundColor: statusColors.bg,
                paddingHorizontal: 10,
                paddingVertical: 5,
                borderRadius: RADIUS.chip,
              }}
            >
              <Text style={{ fontSize: 11, fontWeight: '700', color: statusColors.text }}>
                {STATUS_LABEL[report.status]}
              </Text>
            </View>
          </View>

          <Text style={{ fontSize: 19, fontWeight: '700', color: colors.textPrimary, marginBottom: 8 }}>
            {report.title}
          </Text>
          <Text style={{ fontSize: 14, color: colors.textSecondary, lineHeight: 20, marginBottom: 10 }}>
            {report.description}
          </Text>
          <Text style={{ fontSize: 11, color: colors.textMuted }}>
            Submitted {formatTimestamp(report.created_at)}
            {user?.email !== report.user_email ? ` by ${report.user_email}` : ''}
          </Text>
        </ThemedCard>

        {report.comments.length > 0 && (
          <>
            <Text style={{ fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.4 }}>
              Replies
            </Text>
            <View style={{ gap: 10 }}>
              {report.comments.map((comment) => (
                <View
                  key={comment.id}
                  style={{
                    backgroundColor: comment.is_admin_reply ? colors.cardBg : colors.surfaceAlt ?? colors.cardBg,
                    borderLeftWidth: 3,
                    borderLeftColor: comment.is_admin_reply ? colors.primary : colors.border,
                    borderTopRightRadius: RADIUS.card,
                    borderBottomRightRadius: RADIUS.card,
                    padding: 12,
                    ...CARD_SHADOW,
                  }}
                >
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text style={{ fontSize: 11, fontWeight: '700', color: comment.is_admin_reply ? colors.primary : colors.textSecondary }}>
                      {comment.is_admin_reply ? '✓ ' : ''}{getCommentAuthorLabel(comment, user?.email)}
                    </Text>
                    <Text style={{ fontSize: 10, color: colors.textMuted }}>
                      {formatTimestamp(comment.created_at)}
                    </Text>
                  </View>
                  <Text style={{ fontSize: 13, color: colors.textPrimary, lineHeight: 18 }}>
                    {comment.comment_text}
                  </Text>
                </View>
              ))}
            </View>
          </>
        )}

        {isOwnReport && hasAdminReply && report.status !== 'resolved' && (
          <ThemedCard padding={16} style={{ borderColor: colors.primary, marginTop: 20 }}>
            <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
              Are you satisfied with our reply?
            </Text>
            <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 14 }}>
              If this resolves it for you, you can close the thread. You can still add a follow-up below if not.
            </Text>
            {closeError && (
              <Text style={{ fontSize: 12, color: colors.danger, marginBottom: 10 }}>{closeError}</Text>
            )}
            <View style={{ flexDirection: 'row', gap: 10 }}>
              <Pressable
                onPress={closeThread}
                disabled={isClosing}
                style={{
                  flex: 1,
                  backgroundColor: colors.primary,
                  borderRadius: RADIUS.button,
                  paddingVertical: 10,
                  alignItems: 'center',
                }}
              >
                {isClosing ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={{ color: '#fff', fontWeight: '700', fontSize: 13 }}>Yes, close this</Text>
                )}
              </Pressable>
              <View
                style={{
                  flex: 1,
                  borderWidth: 1,
                  borderColor: colors.cardBorder,
                  borderRadius: RADIUS.button,
                  paddingVertical: 10,
                  alignItems: 'center',
                }}
              >
                <Text style={{ color: colors.textSecondary, fontWeight: '600', fontSize: 13 }}>Not yet</Text>
              </View>
            </View>
          </ThemedCard>
        )}
      </ScrollView>

      <View
        style={{
          flexDirection: 'row',
          alignItems: 'flex-end',
          gap: 8,
          padding: 12,
          borderTopWidth: 1,
          borderTopColor: colors.border,
          backgroundColor: colors.pageBg,
        }}
      >
        <TextInput
          value={replyText}
          onChangeText={setReplyText}
          placeholder="Add a follow-up..."
          placeholderTextColor={colors.textMuted}
          multiline
          style={{
            flex: 1,
            backgroundColor: colors.cardBg,
            borderWidth: 1,
            borderColor: colors.cardBorder,
            borderRadius: RADIUS.card,
            paddingHorizontal: 12,
            paddingVertical: 10,
            fontSize: 14,
            color: colors.textPrimary,
            maxHeight: 100,
          }}
        />
        <Pressable
          onPress={sendReply}
          disabled={!replyText.trim() || isSending}
          style={{
            backgroundColor: replyText.trim() && !isSending ? colors.primary : colors.border,
            borderRadius: RADIUS.button,
            paddingHorizontal: 18,
            paddingVertical: 12,
          }}
        >
          {isSending ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={{ color: '#fff', fontWeight: '700', fontSize: 13 }}>Send</Text>
          )}
        </Pressable>
      </View>
      {sendError && (
        <View style={{ paddingHorizontal: 12, paddingBottom: 8, backgroundColor: colors.pageBg }}>
          <Text style={{ color: colors.danger, fontSize: 12 }}>{sendError}</Text>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}
