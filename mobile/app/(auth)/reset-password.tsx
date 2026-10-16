import { useState } from 'react';
import { View, Text, Pressable, KeyboardAvoidingView, ScrollView, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Button } from 'heroui-native';
import { useAuthStore } from '../../src/stores/authStore';
import { passwordResetApi } from '../../src/api/passwordReset';
import { useTheme } from '../../src/theme/ThemeContext';
import { TextInputField } from '../../src/components/TextInputField';

// Mirrors app/schemas/password_reset.py's
// ResetPasswordRequest.validate_password_strength exactly (itself a
// mirror of VerifySignupOTP's / UserCreate's) -- same checklist UX
// as verify-otp.tsx's signup step.
function getPasswordIssues(password: string): string[] {
  const issues: string[] = [];
  if (password.length < 8) issues.push('At least 8 characters');
  if (!/[A-Z]/.test(password)) issues.push('One uppercase letter');
  if (!/[a-z]/.test(password)) issues.push('One lowercase letter');
  if (!/\d/.test(password)) issues.push('One number');
  return issues;
}

export default function ResetPassword() {
  const router = useRouter();
  const { colors } = useTheme();
  const { completePasswordReset, isSubmitting, error, clearError } = useAuthStore();
  const params = useLocalSearchParams<{ email: string }>();

  const [otpCode, setOtpCode] = useState('');
  const [password, setPassword] = useState('');
  const [touchedPassword, setTouchedPassword] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  const passwordIssues = getPasswordIssues(password);
  const isPasswordValid = password.length > 0 && passwordIssues.length === 0;
  const isOtpValid = /^\d{6}$/.test(otpCode);

  const canSubmit = !isSubmitting && isOtpValid && isPasswordValid;

  const handleSubmit = async () => {
    clearError();
    try {
      await completePasswordReset(params.email, otpCode, password);
      // Navigation on success is handled by AuthGate in the root layout.
    } catch {
      // error is already set in the store and rendered below
    }
  };

  const handleResend = async () => {
    setResendMessage(null);
    setIsResending(true);
    try {
      await passwordResetApi.requestReset({ email: params.email });
      setResendMessage('A new code has been sent.');
    } catch (err) {
      setResendMessage(err instanceof Error ? err.message : 'Failed to resend code');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24 }}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable onPress={() => router.back()} style={{ marginBottom: 20 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
          Enter your code
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 28 }}>
          We sent a 6-digit code to {params.email}. It expires in 10 minutes.
        </Text>

        <TextInputField
          label="Verification code"
          isRequired
          placeholder="123456"
          keyboardType="number-pad"
          maxLength={6}
          value={otpCode}
          onChangeText={(text) => setOtpCode(text.replace(/[^0-9]/g, ''))}
          containerStyle={{ marginBottom: 16 }}
        />

        <TextInputField
          label="New password"
          isRequired
          placeholder="At least 8 characters"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          onBlur={() => setTouchedPassword(true)}
          containerStyle={{ marginBottom: 8 }}
        />

        {touchedPassword && passwordIssues.length > 0 ? (
          <View style={{ marginBottom: 16 }}>
            {passwordIssues.map((issue) => (
              <Text key={issue} style={{ fontSize: 11, color: colors.danger }}>
                • {issue}
              </Text>
            ))}
          </View>
        ) : (
          <View style={{ marginBottom: 20 }} />
        )}

        {error ? (
          <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 12 }}>{error}</Text>
        ) : null}

        <Button
          variant="primary"
          onPress={handleSubmit}
          isDisabled={!canSubmit}
          style={{ marginBottom: 16 }}
        >
          <Button.Label>{isSubmitting ? 'Resetting…' : 'Reset password'}</Button.Label>
        </Button>

        <Pressable onPress={handleResend} disabled={isResending} style={{ marginBottom: 8 }}>
          <Text style={{ fontSize: 12, color: colors.primaryDark, textAlign: 'center' }}>
            {isResending ? 'Sending…' : "Didn't get a code? Resend"}
          </Text>
        </Pressable>

        {resendMessage ? (
          <Text style={{ fontSize: 11, color: colors.textSecondary, textAlign: 'center' }}>
            {resendMessage}
          </Text>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
