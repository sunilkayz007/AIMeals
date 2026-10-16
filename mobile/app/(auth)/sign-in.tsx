import { useState } from 'react';
import { View, Text, Pressable, Image, KeyboardAvoidingView, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Button } from 'heroui-native';
import { useAuthStore } from '../../src/stores/authStore';
import { useTheme } from '../../src/theme/ThemeContext';
import { TextInputField } from '../../src/components/TextInputField';

export default function SignIn() {
  const router = useRouter();
  const { colors } = useTheme();
  const { signIn, isSubmitting, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSignIn = async () => {
    clearError();
    try {
      await signIn({ email: email.trim(), password });
      // Navigation on success is handled by AuthGate in the root layout.
    } catch {
      // error is already set in the store and rendered below
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
        {/* Logo — sits above the form, per the brand image */}
        <View style={{ alignItems: 'center', marginBottom: 28 }}>
          <Image
            source={require('../../assets/images/icon.png')}
            style={{ width: 96, height: 96, borderRadius: 24 }}
            resizeMode="contain"
          />
        </View>

        <Text style={{ fontSize: 22, fontWeight: '600', color: colors.textPrimary, marginBottom: 4, textAlign: 'center' }}>
          Welcome back
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 28, textAlign: 'center' }}>
          Sign in to AIMeals
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
          containerStyle={{ marginBottom: 16 }}
        />

        <TextInputField
          label="Password"
          isRequired
          placeholder="••••••••"
          secureTextEntry={!showPassword}
          value={password}
          onChangeText={setPassword}
          containerStyle={{ marginBottom: 8 }}
        />

        <Pressable onPress={() => setShowPassword((s) => !s)} style={{ marginBottom: 20 }}>
          <Text style={{ fontSize: 12, color: colors.primaryDark }}>
            {showPassword ? 'Hide password' : 'Show password'}
          </Text>
        </Pressable>

        <Pressable onPress={() => router.push('/(auth)/forgot-password')} style={{ marginBottom: 20 }}>
          <Text style={{ fontSize: 12, color: colors.primaryDark, textAlign: 'right' }}>
            Forgot password?
          </Text>
        </Pressable>

        {error ? (
          <Text style={{ color: colors.danger, fontSize: 12, marginBottom: 12 }}>{error}</Text>
        ) : null}

        <Button
          variant="primary"
          onPress={handleSignIn}
          isDisabled={isSubmitting || !email || !password}
          style={{ marginBottom: 16 }}
        >
          <Button.Label>{isSubmitting ? 'Signing in…' : 'Sign in'}</Button.Label>
        </Button>

        <Pressable onPress={() => router.push('/(auth)/sign-up')}>
          <Text style={{ fontSize: 12, color: colors.textSecondary, textAlign: 'center' }}>
            Don't have an account? <Text style={{ color: colors.primaryDark }}>Sign up</Text>
          </Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
