import { useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { deleteAccountApi } from '../../../src/api/deleteAccount';
import { useAuthStore } from '../../../src/stores/authStore';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';
import ThemedCard from '../../../src/components/ThemedCard';

type Stage = 'password' | 'otp';

export default function DeleteAccount() {
  const router = useRouter();
  const { colors } = useTheme();
  const { signOut } = useAuthStore();

  const [stage, setStage] = useState<Stage>('password');
  const [password, setPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  const isOtpValid = /^\d{6}$/.test(otpCode);

  const handleSendCode = async () => {
    if (!password || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await deleteAccountApi.requestOtp(password);
      setStage('otp');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to verify password — please try again');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    setResendMessage(null);
    setIsResending(true);
    try {
      await deleteAccountApi.requestOtp(password);
      setResendMessage('A new code has been sent.');
    } catch (err) {
      setResendMessage(err instanceof Error ? err.message : 'Failed to resend code');
    } finally {
      setIsResending(false);
    }
  };

  const handleDelete = async () => {
    if (!isOtpValid || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await deleteAccountApi.confirmDeletion(otpCode);
      // Account no longer exists server-side — clear local
      // session state directly. signOut() also best-effort
      // revokes the refresh token server-side, which will
      // simply no-op since the user row is already gone
      // (already wrapped in its own try/catch there).
      signOut();
      router.replace('/(auth)/sign-in');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete account — please try again');
      setIsSubmitting(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}
      keyboardShouldPersistTaps="handled"
    >
      <Pressable onPress={() => router.back()} style={{ marginBottom: 20 }} disabled={isSubmitting}>
        <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Cancel</Text>
      </Pressable>

      <Text style={{ fontSize: 22, fontWeight: '700', color: colors.danger, marginBottom: 12 }}>
        Delete Account
      </Text>

      <ThemedCard padding={16} style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', marginBottom: 24 }}>
        <Text style={{ fontSize: 13, color: colors.danger, lineHeight: 19, fontWeight: '600', marginBottom: 8 }}>
          This action is permanent and cannot be undone.
        </Text>
        <Text style={{ fontSize: 13, color: colors.danger, lineHeight: 19 }}>
          Deleting your account will permanently remove your profile, recipes, meal plans, nutrition
          logs, chat history, food scans, reports, and every other piece of data tied to your account.
          There is no way to recover this afterward.
        </Text>
      </ThemedCard>

      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 }}>
        Enter your password
      </Text>
      <TextInput
        placeholder="Password"
        placeholderTextColor={colors.textMuted}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
        editable={stage === 'password' && !isSubmitting}
        style={{
          borderWidth: 1,
          borderColor: colors.border,
          borderRadius: 12,
          paddingHorizontal: 14,
          paddingVertical: 12,
          fontSize: 14,
          color: colors.textPrimary,
          backgroundColor: stage === 'password' ? colors.cardBg : colors.surfaceAlt,
          marginBottom: 20,
          opacity: stage === 'otp' ? 0.6 : 1,
        }}
      />

      {stage === 'password' && (
        <>
          {error ? (
            <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 16 }}>{error}</Text>
          ) : null}

          <Pressable
            onPress={handleSendCode}
            disabled={!password || isSubmitting}
            style={{
              backgroundColor: password && !isSubmitting ? colors.primary : colors.border,
              borderRadius: RADIUS.button,
              paddingVertical: 14,
              alignItems: 'center',
            }}
          >
            {isSubmitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={{ color: '#fff', fontSize: 14, fontWeight: '700' }}>
                Send verification code
              </Text>
            )}
          </Pressable>
        </>
      )}

      {stage === 'otp' && (
        <>
          <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 16 }}>
            Password confirmed. We've sent a verification code to your email — enter it below to
            finish deleting your account.
          </Text>

          <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 }}>
            Verification code
          </Text>
          <TextInput
            placeholder="123456"
            placeholderTextColor={colors.textMuted}
            keyboardType="number-pad"
            maxLength={6}
            value={otpCode}
            onChangeText={(text) => setOtpCode(text.replace(/[^0-9]/g, ''))}
            editable={!isSubmitting}
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

          {error ? (
            <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 12 }}>{error}</Text>
          ) : null}

          <Pressable
            onPress={handleDelete}
            disabled={!isOtpValid || isSubmitting}
            style={{
              backgroundColor: isOtpValid && !isSubmitting ? colors.danger : colors.border,
              borderRadius: RADIUS.button,
              paddingVertical: 14,
              alignItems: 'center',
              marginBottom: 16,
            }}
          >
            {isSubmitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={{ color: '#fff', fontSize: 14, fontWeight: '700' }}>
                Permanently Delete My Account
              </Text>
            )}
          </Pressable>

          <Pressable onPress={handleResend} disabled={isResending}>
            <Text style={{ fontSize: 12, color: colors.primaryDark, textAlign: 'center' }}>
              {isResending ? 'Sending…' : "Didn't get a code? Resend"}
            </Text>
          </Pressable>

          {resendMessage ? (
            <Text style={{ fontSize: 11, color: colors.textSecondary, textAlign: 'center', marginTop: 8 }}>
              {resendMessage}
            </Text>
          ) : null}
        </>
      )}
    </ScrollView>
  );
}
