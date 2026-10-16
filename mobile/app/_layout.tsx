import { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { HeroUINativeProvider } from 'heroui-native';
import { View, ActivityIndicator } from 'react-native';
import { useFonts } from 'expo-font';
import {
  Poppins_400Regular,
  Poppins_500Medium,
  Poppins_600SemiBold,
  Poppins_700Bold,
} from '@expo-google-fonts/poppins';
import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
} from '@expo-google-fonts/inter';
import { useAuthStore } from '../src/stores/authStore';
import * as purchases from '../src/lib/purchases';
import { ThemeProvider, useTheme } from '../src/theme/ThemeContext';
import { initializeAnalytics } from '../src/lib/firebase';
import { analytics_user_identified, analytics_session_started } from '../src/lib/analytics';
import '../global.css';

/**
 * Redirects between the (auth) and (main) route groups based on
 * whether the user has a valid token. Runs on every navigation
 * segment change, not just at startup.
 */
function AuthGate({ children }: { children: React.ReactNode }) {
  const { tokens, user, isLoading, hydrate } = useAuthStore();
  const { colors } = useTheme();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    hydrate();
    initializeAnalytics();
    analytics_session_started();
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';
    const isAuthenticated = !!tokens?.access_token;

    if (!isAuthenticated && !inAuthGroup) {
      router.replace('/(auth)/sign-in');
    } else if (isAuthenticated && inAuthGroup) {
      router.replace('/(main)/home');
    }
  }, [isLoading, tokens, segments]);

  // Keep RevenueCat's app_user_id in lockstep with the signed-in
  // AIMeals user — the backend webhook resolves purchases by that id
  // (see src/lib/purchases.ts). Signing out resets it so the next
  // account never sees the previous one's subscription.
  const userId = tokens?.access_token ? user?.id ?? null : null;
  useEffect(() => {
    if (isLoading) return;
    if (userId) {
      purchases.identify(userId);
      analytics_user_identified(userId, user?.subscription_tier || 'free');
    } else {
      purchases.reset();
    }
  }, [isLoading, userId]);

  if (isLoading) {
    return (
      <View
        style={{
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.screenBg,
        }}
      >
        <ActivityIndicator color={colors.accentSage} />
      </View>
    );
  }

  return <>{children}</>;
}

export default function RootLayout() {
  // Real Poppins/Inter weights per the brand brief (see
  // src/theme/layout.ts's FONTS) — both @expo-google-fonts packages
  // and expo-font were already dependencies but nothing ever actually
  // loaded them, so every ThemedText fontFamily silently fell back to
  // the system font. Gate the whole app behind this so the real fonts
  // are registered before anything renders, rather than flashing the
  // system font first and jumping to Poppins/Inter a moment later.
  //
  // On fontError (e.g. Metro failed to bundle a .ttf) we deliberately
  // proceed anyway instead of hanging forever — an unregistered
  // fontFamily string is a safe, silent fallback to the platform font
  // in React Native, not a crash.
  const [fontsLoaded, fontError] = useFonts({
    Poppins_400Regular,
    Poppins_500Medium,
    Poppins_600SemiBold,
    Poppins_700Bold,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
  });

  if (!fontsLoaded && !fontError) {
    // Neutral, theme-independent colors — ThemeProvider hasn't mounted
    // yet at this point. Matches the brand's light-mode page background
    // and primary green; this is normally visible for well under a
    // second, so a dark-mode user seeing light colors here for one
    // brief flash is an accepted tradeoff against the complexity of
    // restructuring provider order just for this.
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#FAFBF8' }}>
        <ActivityIndicator color="#22C55E" />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ThemeProvider>
        <HeroUINativeProvider>
          <AuthGate>
            <Stack screenOptions={{ headerShown: false }}>
              <Stack.Screen name="index" />
              <Stack.Screen name="(auth)" />
              <Stack.Screen name="(main)" />
            </Stack>
          </AuthGate>
        </HeroUINativeProvider>
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}
