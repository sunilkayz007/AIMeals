import { useState } from 'react';
import { View, Text, Pressable, KeyboardAvoidingView, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Button } from 'heroui-native';
import { passwordResetApi } from '../../src/api/passwordReset';
import { useTheme } from '../../src/theme/ThemeContext';
import { TextInputField } from '../../src/components/TextInputField';

export default function ForgotPassword() {
  const router = useRouter();
  const { colors } = useTheme();

  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEmailValid = /\S+@\S+\.\S+/.test(email.trim());
  const canSubmit = isEmailValid && !isSubmitting;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      // Always succeeds with the same 204 regardless of whether the
      // email is registered -- see passwordReset.ts's docstring. So
      // we always proceed to the code-entry screen; we never learn
      // (and never should) whether the email actually exists.
      await passwordResetApi.requestReset({ email: email.trim() });
      router.push({ pathname: '/(auth)/reset-password', params: { email: email.trim() } });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
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
          Forgot your password?
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 28 }}>
          Enter your account email and we'll send you a 6-digit code to reset it.
        </Text>

        <TextInputField
          label="Email"
          isRequired
          placeholder="name@email.com"
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
          value={email}
          onChangeText={setEmail}
          containerStyle={{ marginBottom: 20 }}
        />

        {error ? (
          <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 12 }}>{error}</Text>
        ) : null}

        <Button
          variant="primary"
          onPress={handleSubmit}
          isDisabled={!canSubmit}
          style={{ marginBottom: 16 }}
        >
          <Button.Label>{isSubmitting ? 'Sending…' : 'Send reset code'}</Button.Label>
        </Button>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
