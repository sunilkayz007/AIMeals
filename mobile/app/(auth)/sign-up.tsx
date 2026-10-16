import { useState } from 'react';
import { View, Text, Pressable, KeyboardAvoidingView, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Button } from 'heroui-native';
import { authOtpApi } from '../../src/api/authOtp';
import { useTheme } from '../../src/theme/ThemeContext';
import { TextInputField } from '../../src/components/TextInputField';

export default function SignUp() {
  const router = useRouter();
  const { colors } = useTheme();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = !isSubmitting && !!email.trim() && !!firstName.trim() && !!lastName.trim();

  const handleRequestOtp = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await authOtpApi.requestOtp({
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
      router.push({
        pathname: '/(auth)/verify-otp',
        params: {
          email: email.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send verification code');
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
        <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4 }}>
          Create account
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 28 }}>
          We'll email you a code to verify it's really you
        </Text>

        <View style={{ flexDirection: 'row', gap: 10, marginBottom: 16 }}>
          <View style={{ flex: 1 }}>
            <TextInputField
              label="First name"
              isRequired
              placeholder="Sunil"
              autoCapitalize="words"
              value={firstName}
              onChangeText={setFirstName}
            />
          </View>
          <View style={{ flex: 1 }}>
            <TextInputField
              label="Last name"
              isRequired
              placeholder="Kumar"
              autoCapitalize="words"
              value={lastName}
              onChangeText={setLastName}
            />
          </View>
        </View>

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
          onPress={handleRequestOtp}
          isDisabled={!canSubmit}
          style={{ marginBottom: 16 }}
        >
          <Button.Label>{isSubmitting ? 'Sending code…' : 'Send verification code'}</Button.Label>
        </Button>

        <Text style={{ fontSize: 10, color: colors.textSecondary, textAlign: 'center', marginBottom: 16 }}>
          By continuing you agree to our Terms
        </Text>

        <Pressable onPress={() => router.push('/(auth)/sign-in')}>
          <Text style={{ fontSize: 12, color: colors.textSecondary, textAlign: 'center' }}>
            Already have an account? <Text style={{ color: colors.primaryDark }}>Sign in</Text>
          </Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
